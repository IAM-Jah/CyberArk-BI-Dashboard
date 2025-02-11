import boto3
import psycopg2
import json
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

def process_platforms(data, cursor, conn):
    """
    Process each platform in the JSON payload, inserting/updating the pam_platforms table.
    Rolls back on individual insert failures to avoid blocking subsequent records.
    """
    print("Starting platform data processing...")
    platform_count = 0

    for platform in data.get('Platforms', []):
        general = platform.get('general', {})
        if not general:
            print(f"Skipping platform with missing 'general' data: {platform}")
            continue

        # 'platform_id' is required
        platform_id = general.get('id')
        if not platform_id:
            print(f"Skipping platform due to missing 'id': {platform}")
            continue

        platform_count += 1
        print(f"Processing platform: {platform_id}")

        credentials_management = platform.get('credentialsManagement', {})
        session_management = platform.get('sessionManagement', {})

        try:
            print(f"Inserting or updating platform: {platform_id}")
            cursor.execute(
                """
                INSERT INTO pam_platforms (
                    platform_id,
                    platform_name,
                    system_type,
                    active,
                    description,
                    platform_base_id,
                    platform_type,
                    require_password_change_days,
                    require_verification_days,
                    automatic_reconcile,
                    require_psm,
                    record_session_activity
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (platform_id)
                DO UPDATE SET
                    platform_name = EXCLUDED.platform_name,
                    system_type = EXCLUDED.system_type,
                    active = EXCLUDED.active,
                    description = EXCLUDED.description,
                    platform_base_id = EXCLUDED.platform_base_id,
                    platform_type = EXCLUDED.platform_type,
                    require_password_change_days = EXCLUDED.require_password_change_days,
                    require_verification_days = EXCLUDED.require_verification_days,
                    automatic_reconcile = EXCLUDED.automatic_reconcile,
                    require_psm = EXCLUDED.require_psm,
                    record_session_activity = EXCLUDED.record_session_activity
                """,
                (
                    platform_id,                                # 1) platform_id
                    general.get('name', ''),                    # 2) platform_name
                    general.get('systemType', ''),              # 3) system_type
                    general.get('active', True),                # 4) active (boolean)
                    general.get('description', ''),             # 5) description
                    general.get('platformBaseID', ''),          # 6) platform_base_id
                    general.get('platformType', ''),            # 7) platform_type
                    credentials_management.get(
                        'requirePasswordChangeEveryXDays', 0
                    ),                                          # 8) require_password_change_days
                    credentials_management.get(
                        'requirePasswordVerificationEveryXDays', 0
                    ),                                          # 9) require_verification_days
                    credentials_management.get(
                        'automaticReconcileWhenUnsynched', False
                    ),                                          # 10) automatic_reconcile
                    session_management.get(
                        'requirePrivilegedSessionMonitoringAndIsolation', False
                    ),                                          # 11) require_psm
                    session_management.get(
                        'recordAndSaveSessionActivity', False
                    )                                           # 12) record_session_activity
                )
            )
            print(f"Successfully inserted/updated: {platform_id}")

        except psycopg2.Error as e:
            print(f"Error inserting platform {platform_id}: {e}")
            conn.rollback()
            continue

    print(f"Completed processing {platform_count} platforms.")

def rename_processed_file(key):
    """
    Rename the processed JSON file so it’s not repeatedly ingested.
    """
    try:
        new_key = f"platforms-processed-{key}"
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

            # Skip files we've already processed
            if key.startswith('platforms-processed-'):
                continue

            # Only handle files that start with "platforms-" and end with ".json"
            if key.startswith('platforms-') and key.endswith('.json'):
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
                    process_platforms(data, cursor, conn)
                    conn.commit()
                    print("Database transaction committed.")
                except Exception as e:
                    print(f"Error during processing: {e}")
                    if conn:
                        conn.rollback()
                finally:
                    if cursor:
                        cursor.close()
                    if conn:
                        conn.close()
                        print("Database connection closed.")

                # Rename file to avoid reprocessing
                rename_processed_file(key)

    except Exception as e:
        print(f"Error processing platforms data: {e}")
