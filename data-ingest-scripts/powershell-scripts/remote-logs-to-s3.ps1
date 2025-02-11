# -----------------------------------
# Load configuration
# -----------------------------------
Write-Host "Loading configuration from config.json..."
$config = Get-Content -Path "./config.json" | ConvertFrom-Json

# Define common variables
$remoteServer = $config.remoteServer          # Remote server hostname or IP address
$remoteShare = $config.remoteShare            # Shared folder name on the remote server
$s3BucketName = $config.s3BucketName
$awsProfile = $config.awsProfile
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

# Define remote path for logs (UNC path)
$remoteLogPath = "\\$remoteServer\$remoteShare"

# -----------------------------------
# AWS CLI Authentication
# -----------------------------------

Write-Host "`n--- AWS CLI AUTHENTICATION ---"

# --------------------------------------------------------------------
# Option 1: Retrieve AWS credentials from Secrets Manager (most secure)
# Uncomment this entire section and comment out config-file-based AWS 
# credentials if you want to securely fetch them from Secrets Manager.
'''
Write-Host "Retrieving AWS credentials from AWS Secrets Manager..."

$awsSecretName = $config.awsSecretName
$awsRegion     = $config.awsRegion

# Get the secret value from AWS Secrets Manager
$secretValueRaw  = aws secretsmanager get-secret-value --secret-id $awsSecretName --region $awsRegion | ConvertFrom-Json
$secretValueJson = $secretValueRaw.SecretString | ConvertFrom-Json

# Extract access key and secret key from the JSON in Secrets Manager
$awsAccessKeyId     = $secretValueJson.aws_access_key_id
$awsSecretAccessKey = $secretValueJson.aws_secret_access_key

Write-Host "Successfully retrieved AWS credentials from Secrets Manager."
'''

# --------------------------------------------------------------------
# Option 2: Use AWS credentials from config file (less secure)
# Keep this active (and comment out Secrets Manager block) if you want
# to continue storing credentials in config.json
$awsAccessKeyId     = $config.awsAccessKeyId
$awsSecretAccessKey = $config.awsSecretAccessKey

Write-Host "Using AWS credentials from config file (not recommended for production)."

# --------------------------------------------------------------------
# Configure AWS CLI Profile
Write-Host "Configuring AWS CLI profile '$awsProfile'..."
aws configure set profile.$awsProfile.aws_access_key_id     $awsAccessKeyId
aws configure set profile.$awsProfile.aws_secret_access_key $awsSecretAccessKey
aws configure set profile.$awsProfile.region                $config.awsRegion

Write-Host "AWS CLI configuration complete."

# -----------------------------------
# Validate Remote Connection
# -----------------------------------
Write-Host "Checking access to remote share: $remoteLogPath..."
if (!(Test-Path $remoteLogPath)) {
    Write-Host "Error: Could not access remote share at $remoteLogPath" -ForegroundColor Red
    exit 1
}
Write-Host "Access to remote share verified."

# -----------------------------------
# Upload files from last 24 hours
# -----------------------------------
Write-Host "Uploading remote log files modified in the last 24 hours..."
$cutoffTime = (Get-Date).AddHours(-24)

try {
    # Retrieve and upload files
    Get-ChildItem -Path $remoteLogPath | Where-Object {
        $_.LastWriteTime -ge $cutoffTime
    } | ForEach-Object {
        # Generate a unique S3 key with prefix and timestamp
        $newFileName = "remote-logs-$timestamp-$($_.Name)"
        Write-Host "Uploading file: $($_.FullName) as $newFileName"

        # Upload the file to S3 with new name
        aws s3 cp $_.FullName "s3://$s3BucketName/logs/$newFileName" --profile $awsProfile
    }

    Write-Host "Remote log file upload completed."
} catch {
    Write-Host "Error during log file retrieval or upload: $_" -ForegroundColor Red
    exit 1
}
