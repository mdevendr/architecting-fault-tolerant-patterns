param(
    [Parameter(Mandatory = $true)][string]$RunId,
    [string]$Region = 'eu-west-2',
    [string]$Profile = 'melon',
    [string]$ArtifactBucket = ''
)
$ErrorActionPreference = 'Stop'
$scenarioRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$stackName = "fault-tolerance-model-routing-$RunId"
if (-not $ArtifactBucket) {
    $account = aws sts get-caller-identity --profile $Profile --region $Region --query Account --output text
    $ArtifactBucket = "fault-tolerance-evidence-$account-$Region"
}
$exists = aws s3api list-buckets --profile $Profile --region $Region --query "contains(Buckets[].Name, '$ArtifactBucket')" --output text
if ($exists -ne 'True') {
    aws s3api create-bucket --profile $Profile --region $Region --bucket $ArtifactBucket `
      --create-bucket-configuration "LocationConstraint=$Region" | Out-Null
}
$packaged = Join-Path $scenarioRoot 'tmp-packaged.yaml'
aws cloudformation package --profile $Profile --region $Region `
  --template-file (Join-Path $PSScriptRoot 'template.yaml') `
  --s3-bucket $ArtifactBucket --s3-prefix "model-routing/$RunId" `
  --output-template-file $packaged | Out-Null
aws cloudformation deploy --profile $Profile --region $Region `
  --template-file $packaged --stack-name $stackName `
  --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND `
  --parameter-overrides "RunId=$RunId" `
  --tags "Project=ArchitectingFaultTolerant" "RunId=$RunId"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

