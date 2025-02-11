import boto3
import psycopg2
import json
from datetime import datetime
from botocore.exceptions import ClientError

# AWS clients and configuration
s3 = boto3.client('s3')
secrets_client = boto3.client('secretsmanager')
bucket_name = 'S3BucketName'
secret_name = 'RDSSecretName'

# If using Secrets Manager, uncomment this function:
"""
def get_db_password(secret_name):
    try:
        response = secrets_client.get_secret_value(SecretId=secret_name)
        secret_string = json.loads(response['SecretString'])
        return secret_string['password']
    except ClientError as e:
        print(f"Error retrieving secret: {e}")
        raise e
"""

# RDS connection configuration
rds_config = {
    'host': 'RDSPostgresEndpoint',
    'database': 'postgres',
    'user': 'postgres',
    'password': 'password'
}

def convert_epoch_s_to_datetime(raw_ts):
    """
    Interprets raw_ts as SECONDS since epoch.
    """
    if not raw_ts:
        return None
    try:
        epoch_s = int(raw_ts)
        return datetime.utcfromtimestamp(epoch_s)
    except (ValueError, TypeError):
        return None

def convert_epoch_us_to_datetime(raw_ts):
    """
    Interprets raw_ts as MICROSECONDS since epoch.
    Example: 1739084217619678 -> ~2025-02-08
    """
    if not raw_ts:
        return None
    try:
        epoch_us = int(raw_ts)
        return datetime.utcfromtimestamp(epoch_us / 1e6)
    except (ValueError, TypeError, OverflowError) as e:
        print(f"Error converting microsecond timestamp {raw_ts}: {e}")
        return None

def log_missing_fields(safe):
    missing_fields = []
    required_fields = ['safeName', 'creator', 'creationTime', 'lastModificationTime', 'managingCPM']
    for field in required_fields:
        if not safe.get(field):
            missing_fields.append(field)
    if missing_fields:
        print(f"Safe '{safe.get('safeName', 'N/A')}' is missing fields: {', '.join(missing_fields)}")

def process_safes(data, cursor, conn):
    print("Starting safe data processing...")
    safe_count = 0

    for safe in data.get('value', []):
        safe_name = safe.get('safeName')
        if not safe_name:
            print("Skipping safe with missing name.")
            continue

        log_missing_fields(safe)

        raw_lmt = safe.get('lastModificationTime')
        print(f"Raw lastModificationTime for safe={safe_name}: {raw_lmt}")

        # creationTime is in SECONDS
        creation_time = convert_epoch_s_to_datetime(safe.get('creationTime'))

        # lastModificationTime is in MICROSECONDS
        last_modification_time = convert_epoch_us_to_datetime(safe.get('lastModificationTime'))

        creator_data = safe.get('creator', {})
        creator_id = creator_data.get('id') if creator_data.get('id') else None
        creator_name = creator_data.get('name') if creator_data.get('name') else None

        safe_number = safe.get('safeNumber', 0)
        managing_cpm = safe.get('managingCPM', '')
        description = safe.get('description', '')
        location = safe.get('location', '\\')
        olac_enabled = safe.get('olacEnabled', False)

        # NOTE: If managing_cpm can exceed 255 characters, consider ALTER TABLE pam_safes 
        #       ALTER COLUMN managing_cpm TYPE text;
        #       or else manually truncate the string here.
        if len(managing_cpm) > 255:
            print(f"Warning: managing_cpm exceeds 255 chars. (Length={len(managing_cpm)})")
            # e.g. managing_cpm = managing_cpm[:255]  # Optionally truncate here

        print(f"Extracted values for safe '{safe_name}':")
        print(f"  Creation Time (UTC): {creation_time}")
        print(f"  Last Modification Time (UTC): {last_modification_time}")
        print(f"  Creator Name: {creator_name}")
        print(f"  Managing CPM: {managing_cpm}")
        print(f"  Safe Number: {safe_number}")

        try:
            print(f"Inserting or updating safe: {safe_name}")
            cursor.execute("""
                INSERT INTO pam_safes (
                    safe_name,
                    description,
                    olac_enabled,
                    managing_cpm,
                    safe_number,
                    creator_id,
                    creator_name,
                    location,
                    creation_date,
                    last_modification_time
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (safe_name)
                DO UPDATE SET
                    description = EXCLUDED.description,
                    olac_enabled = EXCLUDED.olac_enabled,
                    managing_cpm = EXCLUDED.managing_cpm,
                    safe_number = EXCLUDED.safe_number,
                    creator_id = EXCLUDED.creator_id,
                    creator_name = EXCLUDED.creator_name,
                    location = EXCLUDED.location,
                    creation_date = EXCLUDED.creation_date,
                    last_modification_time = EXCLUDED.last_modification_time
            """, (
                safe_name,
                description,
                olac_enabled,
                managing_cpm,
                safe_number,
                creator_id,
                creator_name,
                location,
                creation_time,
                last_modification_time
            ))
            safe_count += 1

        except psycopg2.Error as e:
            if conn:
                conn.rollback()
            print(f"Database error on safe '{safe_name}': {e}")
            print(f"Query data: {safe_name}, {creation_time}, {last_modification_time}")
            continue

        # If there's a nested 'accounts' array, handle that too
        accounts = safe.get('accounts', [])
        for account in accounts:
            account_id = account.get('accountId') if account.get('accountId') else None
            account_name = account.get('accountName') if account.get('accountName') else None

            try:
                cursor.execute("""
                    INSERT INTO pam_safe_accounts (safe_name, account_id, account_name)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (safe_name, account_id)
                    DO NOTHING
                """, (safe_name, account_id, account_name))
            except psycopg2.Error as e:
                if conn:
                    conn.rollback()
                print(f"Database error on account '{account_name}' in safe '{safe_name}': {e}")
                continue

    print(f"Completed processing {safe_count} safes.")

def rename_processed_file(key):
    try:
        new_key = f"safes-processed-{key}"
        s3.copy_object(Bucket=bucket_name, CopySource={'Bucket': bucket_name, 'Key': key}, Key=new_key)
        s3.delete_object(Bucket=bucket_name, Key=key)
        print(f"File renamed to: {new_key}")
    except ClientError as e:
        print(f"Error renaming file {key}: {e}")
        raise e

def lambda_handler(event, context):
    print("Lambda execution started.")
    print(f"Received event: {json.dumps(event)}")

    try:
        response = s3.list_objects_v2(Bucket=bucket_name)
        if 'Contents' not in response or not response['Contents']:
            print("No objects found in the S3 bucket.")
            return

        for obj in response['Contents']:
            key = obj['Key']
            if key.startswith('safes-processed-'):
                continue

            if key.startswith('safes-') and key.endswith('.json'):
                print(f"Processing file: {key}")
                try:
                    file_obj = s3.get_object(Bucket=bucket_name, Key=key)
                    data = json.loads(file_obj['Body'].read().decode('utf-8'))
                except ClientError as e:
                    print(f"Error retrieving file from S3: {e}")
                    continue
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON from file {key}: {e}")
                    continue

                conn = None
                cursor = None
                try:
                    conn = psycopg2.connect(**rds_config)
                    cursor = conn.cursor()
                    process_safes(data, cursor, conn)
                    conn.commit()
                    print(f"Transaction committed for file: {key}")
                except psycopg2.Error as e:
                    print(f"Database connection error: {e}")
                    if conn:
                        conn.rollback()
                finally:
                    if cursor:
                        cursor.close()
                    if conn:
                        conn.close()
                        print("Database connection closed.")

                try:
                    rename_processed_file(key)
                except ClientError as e:
                    print(f"Error renaming file {key}: {e}")

    except Exception as e:
        print(f"Unexpected error: {e}")
