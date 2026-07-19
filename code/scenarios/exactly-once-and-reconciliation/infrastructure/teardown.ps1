param(
    [Parameter(Mandatory = $true)][string]$RunId,
    [string]$Region = 'eu-west-2',
    [string]$Profile = ''
)

$ErrorActionPreference = 'Stop'
$profileArgs = @()
if ($Profile) { $profileArgs = @('--profile', $Profile) }
$stackName = "fault-tolerance-exactly-once-$RunId"

aws @profileArgs --region $Region cloudformation delete-stack --stack-name $stackName
aws @profileArgs --region $Region cloudformation wait stack-delete-complete --stack-name $stackName

