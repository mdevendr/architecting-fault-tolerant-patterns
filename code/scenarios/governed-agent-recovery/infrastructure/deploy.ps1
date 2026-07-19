param(
    [Parameter(Mandatory = $true)][string]$RunId,
    [Parameter(Mandatory = $true)][string]$RunName,
    [string]$Region = 'eu-west-2',
    [string]$Profile = 'melon',
    [string]$ArtifactBucket = ''
)

$ErrorActionPreference = 'Stop'
$scenarioRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$stackName = "fault-tolerance-governed-agent-$RunId"
$profileArgs = @('--profile', $Profile)

if (-not $ArtifactBucket) {
    $account = aws @profileArgs --region $Region sts get-caller-identity --query Account --output text
    $ArtifactBucket = "fault-tolerance-evidence-$account-$Region"
}
$exists = aws @profileArgs --region $Region s3api list-buckets --query "contains(Buckets[].Name, '$ArtifactBucket')" --output text
if ($exists -ne 'True') {
    aws @profileArgs --region $Region s3api create-bucket --bucket $ArtifactBucket `
        --create-bucket-configuration "LocationConstraint=$Region" | Out-Null
}

$packaged = Join-Path $scenarioRoot 'tmp-packaged.yaml'
aws @profileArgs --region $Region cloudformation package `
    --template-file (Join-Path $PSScriptRoot 'template.yaml') `
    --s3-bucket $ArtifactBucket `
    --s3-prefix "governed-agent/$RunId" `
    --output-template-file $packaged | Out-Null

aws @profileArgs --region $Region cloudformation deploy `
    --template-file $packaged `
    --stack-name $stackName `
    --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND `
    --parameter-overrides "RunId=$RunId" "RunName=$RunName" `
    --tags "Project=ArchitectingFaultTolerant" "RunId=$RunId"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
