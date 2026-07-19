param(
    [Parameter(Mandatory = $true)][string]$RunId,
    [string]$Region = 'eu-west-1',
    [string]$Profile = ''
)

$ErrorActionPreference = 'Stop'
$profileArgs = @()
if ($Profile) { $profileArgs = @('--profile', $Profile) }
$stackName = "fault-tolerance-rag-trust-$RunId"

$bucket = aws @profileArgs --region $Region cloudformation describe-stacks `
    --stack-name $stackName `
    --query "Stacks[0].Outputs[?OutputKey=='SourceBucketName'].OutputValue" `
    --output text

$versions = aws @profileArgs --region $Region s3api list-object-versions --bucket $bucket --output json | ConvertFrom-Json
$objects = @()
foreach ($version in @($versions.Versions)) {
    $objects += @{ Key = $version.Key; VersionId = $version.VersionId }
}
foreach ($marker in @($versions.DeleteMarkers)) {
    $objects += @{ Key = $marker.Key; VersionId = $marker.VersionId }
}
if ($objects.Count -gt 0) {
    $request = @{ Objects = $objects; Quiet = $true } | ConvertTo-Json -Compress -Depth 6
    $path = Join-Path $PSScriptRoot 'delete-source-versions.json'
    $utf8WithoutBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($path, $request, $utf8WithoutBom)
    aws @profileArgs --region $Region s3api delete-objects --bucket $bucket --delete "file://$path" | Out-Null
}

aws @profileArgs --region $Region cloudformation delete-stack --stack-name $stackName
aws @profileArgs --region $Region cloudformation wait stack-delete-complete --stack-name $stackName

