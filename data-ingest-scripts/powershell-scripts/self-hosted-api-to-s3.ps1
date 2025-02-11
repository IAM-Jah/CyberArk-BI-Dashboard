# -----------------------------------
# Load configuration
# -----------------------------------
Write-Host "Loading configuration from config.json..."
$config = Get-Content -Path "./config.json" | ConvertFrom-Json

# Define common variables
$apiBaseUrl = $config.apiBaseUrl
$authType = $config.authType
$username = $config.username
$outputFolderPath = $config.outputFolderPath
$s3BucketName = $config.s3BucketName
$awsProfile = $config.awsProfile

# -----------------------------------
# Option 1: Retrieve API user password from CyberArk CCP (most secure)
# Uncomment this entire section and comment out other password sections if using CCP
'''
Write-Host "Retrieving API user password from CyberArk CCP..."
# Define CCP API parameters
$ccpBaseUrl = $config.ccpBaseUrl
$safeName   = $config.safeName
$objectName = $config.objectName
$appId      = $config.appId

# Construct the CCP request URI
$ccpUri      = "$ccpBaseUrl/AIMWebService/api/Accounts?AppID=$appId&Safe=$safeName&Object=$objectName"
$ccpResponse = Invoke-RestMethod -Uri $ccpUri -Method Get

# Extract password from CCP response
$password = $ccpResponse.Content
Write-Host "Successfully retrieved password from CCP."
'''

# -----------------------------------
# Option 2: Retrieve API user password from config file (not secure)
# Keep this section commented out if using CyberArk CCP
$password = $config.password
Write-Host "Using password from config file (not recommended for production)."

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
# Authenticate to CyberArk PAM Self-Hosted
# -----------------------------------
Write-Host "Authenticating to PAM Self-Hosted with method: '$authType'..."
$tokenEndpoint = "$apiBaseUrl/auth/$authType/Logon"
$body = @{
    username = $username
    password = $password
    concurrentSession = $config.concurrentSession
}
$token = Invoke-RestMethod -Uri $tokenEndpoint -Method Post -Body ($body | ConvertTo-Json) -ContentType "application/json"

# Generate headers with the authentication token
$headers = @{
    Authorization = "Bearer $($token)"
}
Write-Host "Successfully retrieved Authorization headers."

# -----------------------------------
# Helper function to save and upload data
# -----------------------------------
function Save-And-UploadData {
    param (
        [string]$endpoint,
        [string]$prefix
    )

    Write-Host "`n--- Save-And-UploadData: $prefix ---"
    Write-Host "Querying API at endpoint: $endpoint"

    # Query the API
    $response = Invoke-RestMethod -Uri $endpoint -Method Get -Headers $headers
    
    # Generate a unique filename with a timestamp
    $timestamp   = Get-Date -Format "yyyyMMdd_HHmmss"
    $outputFile  = "$outputFolderPath\$($prefix)_$timestamp.json"

    if ($response) {
        Write-Host "API response received. Saving to file: $outputFile"

        # Save the response to a JSON file with increased depth and compression
        $response | ConvertTo-Json -Depth 10 -Compress | Out-File -FilePath $outputFile
        Write-Host "File saved. Preparing to upload to S3..."

        # Upload to S3 with the appropriate prefix
        $s3Key = "$prefix-$timestamp.json"
        aws s3 cp $outputFile s3://$s3BucketName/$s3Key --profile $awsProfile

        Write-Host "Uploaded $s3Key to S3." -ForegroundColor Green
    }
    else {
        Write-Host "Error: API response is null or empty for $prefix data." -ForegroundColor Red
    }
}

# -----------------------------------
# Query and upload data for accounts
# -----------------------------------
Write-Host "`n--- Querying and uploading 'accounts' data ---"
Save-And-UploadData -endpoint "$apiBaseUrl/Accounts" -prefix "accounts"

# -----------------------------------
# Query and upload data for platforms
# -----------------------------------
Write-Host "`n--- Querying and uploading 'platforms' data ---"
Save-And-UploadData -endpoint "$apiBaseUrl/Platforms" -prefix "platforms"

# -----------------------------------
# Query and upload data for safes
# -----------------------------------
Write-Host "`n--- Querying and uploading 'safes' data ---"
Save-And-UploadData -endpoint "$apiBaseUrl/Safes" -prefix "safes"

Write-Host "`nAll data has been retrieved and uploaded successfully!"