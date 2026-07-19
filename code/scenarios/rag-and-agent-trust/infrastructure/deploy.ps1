param(
    [Parameter(Mandatory = $true)][string]$RunId,
    [string]$Region = 'eu-west-1',
    [string]$Profile = '',
    [string]$ArtifactBucket = ''
)

$ErrorActionPreference = 'Stop'
$scenarioRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$stackName = "fault-tolerance-rag-trust-$RunId"
$profileArgs = @()
if ($Profile) { $profileArgs = @('--profile', $Profile) }

if (-not $ArtifactBucket) {
    $account = aws @profileArgs --region $Region sts get-caller-identity --query Account --output text
    $ArtifactBucket = "fault-tolerance-evidence-$account-$Region"
}

$artifactBucketExists = aws @profileArgs --region $Region s3api list-buckets `
    --query "contains(Buckets[].Name, '$ArtifactBucket')" --output text
if ($artifactBucketExists -ne 'True') {
    aws @profileArgs --region $Region s3api create-bucket --bucket $ArtifactBucket --create-bucket-configuration "LocationConstraint=$Region" | Out-Null
}

$packagedTemplate = Join-Path $scenarioRoot 'tmp-packaged.yaml'
aws @profileArgs --region $Region cloudformation package `
    --template-file (Join-Path $PSScriptRoot 'template.yaml') `
    --s3-bucket $ArtifactBucket `
    --s3-prefix "rag-trust/$RunId" `
    --output-template-file $packagedTemplate | Out-Null

aws @profileArgs --region $Region cloudformation deploy `
    --template-file $packagedTemplate `
    --stack-name $stackName `
    --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND `
    --parameter-overrides "RunId=$RunId" `
    --tags "Project=ArchitectingFaultTolerant" "RunId=$RunId"
