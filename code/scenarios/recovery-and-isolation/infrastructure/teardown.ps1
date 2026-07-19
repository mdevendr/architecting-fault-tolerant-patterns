param(
    [Parameter(Mandatory = $true)][string]$RunId,
    [ValidateSet('naive', 'protected')][string]$Mode = 'protected',
    [string]$Region = 'eu-west-2',
    [string]$Profile = ''
)

$ErrorActionPreference = 'Stop'
$stackName = "fault-tolerance-recovery-$RunId-$Mode"
$profileArgs = @()
if ($Profile) { $profileArgs = @('--profile', $Profile) }

aws @profileArgs --region $Region cloudformation delete-stack --stack-name $stackName
aws @profileArgs --region $Region cloudformation wait stack-delete-complete --stack-name $stackName

