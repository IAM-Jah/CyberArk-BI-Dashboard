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
    Converts a Unix epoch in SECONDS (e.g. 1675868057)
    to a Python datetime object in UTC.
    Returns None if raw_ts is missing or parsing fails.
    """
    if not raw_ts:
        return None
    try:
        epoch_s = int(raw_ts)
        return datetime.utcfromtimestamp(epoch_s)
    except (ValueError, TypeError):
        return None

def process_accounts(data, cursor, conn):
    print("Starting account data processing...")
    account_count = 0

    for account in data.get('value', []):
        account_name = account.get('name')
        if not account_name:
            print(f"Skipping account with missing name: {account}")
            continue

        account_count += 1
        print(f"Processing account: {account_name}")

        # Since the JSON shows createdTime and lastModifiedTime in SECONDS,
        # use convert_epoch_s_to_datetime (no /1000).
        created_time = convert_epoch_s_to_datetime(account.get('createdTime'))
        last_modified_time = convert_epoch_s_to_datetime(
            account.get('secretManagement', {}).get('lastModifiedTime')
        )

        automatic_management_enabled = account.get('secretManagement', {}).get('automaticManagementEnabled', False)

        try:
            print(f"Inserting/Updating account: {account_name}")
            cursor.execute("""
                INSERT INTO pam_accounts (
                    account_name,
                    address,
                    user_name,
                    safe_name,
                    platform_id,
                    secret_type,
                    automatic_management_enabled,
                    last_modified_time,
                    creation_time
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (account_name)
                DO UPDATE SET
                    address = EXCLUDED.address,
                    user_name = EXCLUDED.user_name,
                    safe_name = EXCLUDED.safe_name,
                    platform_id = EXCLUDED.platform_id,
                    secret_type = EXCLUDED.secret_type,
                    automatic_management_enabled = EXCLUDED.automatic_management_enabled,
                    last_modified_time = EXCLUDED.last_modified_time,
                    creation_time = EXCLUDED.creation_time
            """, (
                account_name,
                account.get('address', ''),
                account.get('userName', ''),
                account.get('safeName', ''),
                account.get('platformId', ''),
                account.get('secretType', ''),
                automatic_management_enabled,
                last_modified_time,
                created_time
            ))
            print(f"Successfully inserted/updated account: {account_name}")
        except psycopg2.Error as e:
            print(f"Error inserting account {account_name}: {e}")
            conn.rollback()
            continue

    print(f"Completed processing {account_count} accounts.")

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

            # Skip already processed files
            if key.startswith('accounts-processed-'):
                continue

            # Process only matching JSON objects
            if key.startswith('accounts-') and key.endswith('.json'):
                print(f"Processing file: {key}")
                file_obj = s3.get_object(Bucket=bucket_name, Key=key)
                data = json.loads(file_obj['Body'].read().decode('utf-8'))

                conn = psycopg2.connect(**rds_config)
                cursor = conn.cursor()

                try:
                    process_accounts(data, cursor, conn)
                    conn.commit()
                    print("Database transaction committed.")
                except Exception as e:
                    print(f"Error during processing: {e}")
                    conn.rollback()
                finally:
                    cursor.close()
                    conn.close()
                    print("Database connection closed.")

                # Rename the processed file
                new_key = f"accounts-processed-{key}"
                s3.copy_object(
                    Bucket=bucket_name,
                    CopySource={'Bucket': bucket_name, 'Key': key},
                    Key=new_key
                )
                s3.delete_object(Bucket=bucket_name, Key=key)
                print(f"File renamed to: {new_key}")

    except Exception as e:
        print(f"Error processing accounts data: {e}")
