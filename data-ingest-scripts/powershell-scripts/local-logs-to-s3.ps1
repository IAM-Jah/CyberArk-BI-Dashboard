# -----------------------------------
# Load configuration
# -----------------------------------
Write-Host "Loading configuration from config.json..."
$config = Get-Content -Path "./config.json" | ConvertFrom-Json

# Define common variables
$localLogPath = "C:\Program Files (x86)\CyberArk\PSM\Logs\"
$s3BucketName = $config.s3BucketName
$awsProfile = $config.awsProfile
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

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
# Upload files from last 24 hours
# -----------------------------------
Write-Host "Uploading log files from the last 24 hours..."
$cutoffTime = (Get-Date).AddHours(-24)

try {
    # Process each file in the local log path
    Get-ChildItem -Path $localLogPath | Where-Object {
        $_.LastWriteTime -ge $cutoffTime
    } | ForEach-Object {
        # Generate a unique S3 key with a prefix and timestamp
        $newFileName = "logs-$timestamp-$($_.Name)"
        Write-Host "Uploading file: $($_.FullName) as $newFileName"

        # Upload the file to S3 with the new name
        aws s3 cp $_.FullName "s3://$s3BucketName/logs/$newFileName" --profile $awsProfile
    }

    Write-Host "Log file upload completed."
} catch {
    Write-Host "Error during log file retrieval or upload: $_" -ForegroundColor Red
    exit 1
}