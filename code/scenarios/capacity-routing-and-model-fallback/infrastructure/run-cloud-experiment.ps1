param(
    [Parameter(Mandatory = $true)][string]$RunId,
    [string]$Region = 'eu-west-2',
    [string]$Profile = 'melon',
    [string]$EvidenceDirectory = ''
)
$ErrorActionPreference = 'Stop'
$stackName = "fault-tolerance-model-routing-$RunId"
if (-not $EvidenceDirectory) { $EvidenceDirectory = Join-Path $PSScriptRoot "..\evidence\runs\$RunId" }
$EvidenceDirectory = [System.IO.Path]::GetFullPath($EvidenceDirectory)
New-Item -ItemType Directory -Force -Path $EvidenceDirectory | Out-Null
$utf8 = New-Object System.Text.UTF8Encoding($false)

function Write-Json([string]$Path, [object]$Value) {
  [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Compress -Depth 20), $utf8)
}
function Output([string]$Key) {
  aws cloudformation describe-stacks --profile $Profile --region $Region --stack-name $stackName `
    --query "Stacks[0].Outputs[?OutputKey=='$Key'].OutputValue" --output text
}
function Invoke-Function([string]$Function, [string]$Name, [object]$Payload) {
  $request = Join-Path $EvidenceDirectory "$Name-request.json"; Write-Json $request $Payload
  $response = Join-Path $EvidenceDirectory "$Name-response.json"
  $metadata = aws lambda invoke --profile $Profile --region $Region --function-name $Function `
    --cli-binary-format raw-in-base64-out --payload "fileb://$request" $response | ConvertFrom-Json
  if ($metadata.FunctionError) { throw "Lambda failure in $Name`: $(Get-Content -Raw $response)" }
  return Get-Content -Raw $response | ConvertFrom-Json
}

$evaluationFunction = Output 'EvaluationFunctionName'
$gatewayFunction = Output 'GatewayFunctionName'
$primaryProfile = Output 'PrimaryProfile'
$fallbackModel = Output 'FallbackModel'

$evaluation = Invoke-Function $evaluationFunction '01-fallback-evaluation' @{}
$healthy = Invoke-Function $gatewayFunction '02-primary-capacity-route' @{
  prompt='Reply with exactly the single word PRIMARY.'
}
$invalid = Invoke-Function $gatewayFunction '03-invalid-request' @{
  injected_status=400; reason='INVALID_REQUEST'
}
$policy = Invoke-Function $gatewayFunction '04-policy-denial' @{
  injected_status=403; reason='POLICY_DENIED'
}
$geography = Invoke-Function $gatewayFunction '05-geography-not-approved' @{
  injected_status=503; reason='CAPACITY'; geography='US'
}
$lowEvaluation = Invoke-Function $evaluationFunction '06-low-evaluation-injection' @{override_score=0.33}
$belowThreshold = Invoke-Function $gatewayFunction '07-fallback-below-threshold' @{
  injected_status=429; reason='THROTTLED'; geography='EU'
}
$restoredEvaluation = Invoke-Function $evaluationFunction '08-evaluation-restored' @{}
$fallback = Invoke-Function $gatewayFunction '09-evaluated-semantic-fallback' @{
  injected_status=503; reason='CAPACITY'; geography='EU';
  prompt='Reply with exactly the single word FALLBACK.'
}

$manifest = [ordered]@{
  schema_version='1.0'; execution_environment='aws'; run_id=$RunId; region=$Region
  primary_profile=$primaryProfile; fallback_model=$fallbackModel
  evaluation_score=$evaluation.measured_score
  contract=[ordered]@{
    fallback_evaluation_passed=[bool]$evaluation.passed
    primary_used_inference_profile=$healthy.decision -eq 'CAPACITY_ROUTED' -and $healthy.model_id -eq $primaryProfile
    primary_not_marked_degraded=$healthy.degraded -eq $false
    invalid_request_not_retried_or_fallen_back=$invalid.decision -eq 'RETURN_ERROR' -and $invalid.model_invoked -eq $false
    policy_denial_failed_closed=$policy.decision -eq 'FAIL_CLOSED' -and $policy.model_invoked -eq $false
    geography_constraint_blocked_fallback=$geography.reason -eq 'GEOGRAPHY_NOT_APPROVED' -and $geography.model_invoked -eq $false
    low_evaluation_blocked_fallback=$belowThreshold.reason -eq 'FALLBACK_BELOW_THRESHOLD' -and $belowThreshold.model_invoked -eq $false
    evaluation_restored=[bool]$restoredEvaluation.passed
    transient_failure_used_semantic_fallback=$fallback.decision -eq 'SEMANTIC_FALLBACK' -and $fallback.model_id -eq $fallbackModel
    fallback_marked_degraded=[bool]$fallback.degraded
    fallback_carries_evaluation_evidence=$fallback.evaluation_suite -eq 'fallback-contract-v1' -and $fallback.evaluation_score -ge 0.66
  }
}
$manifest.passed = -not ($manifest.contract.Values -contains $false)
$manifest | ConvertTo-Json -Depth 20 | Set-Content -Encoding utf8 (Join-Path $EvidenceDirectory 'run-manifest.json')
if (-not $manifest.passed) { exit 1 }

