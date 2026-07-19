param(
    [Parameter(Mandatory = $true)][string]$RunId,
    [ValidateSet('naive', 'protected')][string]$Mode = 'protected',
    [string]$Region = 'eu-west-2',
    [string]$Profile = '',
    [string]$ArtifactBucket = ''
)

$ErrorActionPreference = 'Stop'
$scenarioRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$stackName = "fault-tolerance-recovery-$RunId-$Mode"
$profileArgs = @()
if ($Profile) { $profileArgs = @('--profile', $Profile) }

if (-not $ArtifactBucket) {
    $account = aws @profileArgs --region $Region sts get-caller-identity --query Account --output text
    $ArtifactBucket = "fault-tolerance-evidence-$account-$Region"
}

aws @profileArgs --region $Region s3api head-bucket --bucket $ArtifactBucket 2>$null
if ($LASTEXITCODE -ne 0) {
    if ($Region -eq 'us-east-1') {
        aws @profileArgs --region $Region s3api create-bucket --bucket $ArtifactBucket | Out-Null
    } else {
        aws @profileArgs --region $Region s3api create-bucket --bucket $ArtifactBucket --create-bucket-configuration "LocationConstraint=$Region" | Out-Null
    }
}

$packagedTemplate = Join-Path $scenarioRoot "tmp-packaged-$Mode.yaml"
aws @profileArgs --region $Region cloudformation package `
    --template-file (Join-Path $PSScriptRoot 'template.yaml') `
    --s3-bucket $ArtifactBucket `
    --s3-prefix "recovery-and-isolation/$RunId/$Mode" `
    --output-template-file $packagedTemplate | Out-Null

aws @profileArgs --region $Region cloudformation deploy `
    --template-file $packagedTemplate `
    --stack-name $stackName `
    --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND `
    --parameter-overrides "RunId=$RunId" "PolicyMode=$Mode" `
    --tags "Project=ArchitectingFaultTolerant" "RunId=$RunId" "Mode=$Mode"

aws @profileArgs --region $Region cloudformation describe-stacks `
    --stack-name $stackName `
    --query 'Stacks[0].Outputs' `
    --output json

