param(
    [Parameter(Mandatory = $true)][string]$RunId,
    [string]$Region = 'eu-west-2',
    [string]$Profile = '',
    [string]$EvidenceDirectory = ''
)

$ErrorActionPreference = 'Stop'
$stackName = "fault-tolerance-exactly-once-$RunId"
$profileArgs = @()
if ($Profile) { $profileArgs = @('--profile', $Profile) }
if (-not $EvidenceDirectory) {
    $EvidenceDirectory = Join-Path $PSScriptRoot "..\evidence\runs\$RunId"
}
$EvidenceDirectory = [System.IO.Path]::GetFullPath($EvidenceDirectory)
New-Item -ItemType Directory -Force -Path $EvidenceDirectory | Out-Null
$utf8WithoutBom = New-Object System.Text.UTF8Encoding($false)

function Write-JsonRequest {
    param([string]$Path, [object]$Value)
    $json = $Value | ConvertTo-Json -Compress -Depth 12
    [System.IO.File]::WriteAllText($Path, $json, $utf8WithoutBom)
}

function Invoke-ScenarioLambda {
    param([string]$FunctionName, [object]$Payload, [string]$Name)
    $requestPath = Join-Path $EvidenceDirectory "$Name-request.json"
    $responsePath = Join-Path $EvidenceDirectory "$Name-response.json"
    Write-JsonRequest $requestPath $Payload
    $metadata = aws @profileArgs --region $Region lambda invoke `
        --function-name $FunctionName `
        --cli-binary-format raw-in-base64-out `
        --payload "fileb://$requestPath" `
        $responsePath | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw "Lambda invocation command failed: $Name" }
    return [ordered]@{
        metadata = $metadata
        payload = Get-Content -Raw $responsePath | ConvertFrom-Json
    }
}

function Get-TableScan {
    param([string]$TableName)
    $raw = aws @profileArgs --region $Region dynamodb scan --table-name $TableName --output json
    if ($LASTEXITCODE -ne 0) { throw "Unable to scan $TableName" }
    return $raw | ConvertFrom-Json
}

$outputsRaw = aws @profileArgs --region $Region cloudformation describe-stacks `
    --stack-name $stackName --query 'Stacks[0].Outputs' --output json
if ($LASTEXITCODE -ne 0) { throw "Unable to read stack outputs" }
$outputs = $outputsRaw | ConvertFrom-Json
$outputMap = @{}
foreach ($output in $outputs) { $outputMap[$output.OutputKey] = $output.OutputValue }

$operationKey = "$RunId-payment-1"
$manifest = [ordered]@{
    schema_version = '1.0'
    execution_environment = 'aws'
    run_id = $RunId
    region = $Region
    stack_name = $stackName
    operation_key = $operationKey
    started_at = [DateTimeOffset]::UtcNow.ToString('o')
    steps = [ordered]@{}
}

$crash = Invoke-ScenarioLambda $outputMap.WorkerFunctionName @{
    operation_key = $operationKey
    owner = 'worker-a'
    now = 100
    lease_seconds = 5
    crash_after_provider = $true
    projection_fault_mode = 'CRASH_AFTER_PROJECTION_ONCE'
} '01-crash-after-provider'
$manifest.steps.crash_after_provider = [bool]$crash.metadata.FunctionError

$busy = Invoke-ScenarioLambda $outputMap.WorkerFunctionName @{
    operation_key = $operationKey
    owner = 'worker-b'
    now = 103
    lease_seconds = 5
} '02-before-lease-expiry'
$manifest.steps.before_lease_expiry_rejected = [bool]$busy.metadata.FunctionError

$recovered = Invoke-ScenarioLambda $outputMap.WorkerFunctionName @{
    operation_key = $operationKey
    owner = 'worker-b'
    now = 106
    lease_seconds = 5
    projection_fault_mode = 'CRASH_AFTER_PROJECTION_ONCE'
} '03-reclaim-and-complete'
$manifest.steps.lease_reclaimed = -not [bool]$recovered.metadata.FunctionError
$manifest.steps.provider_result_replayed = [bool]$recovered.payload.provider_replayed

$deliveryDeadline = [DateTimeOffset]::UtcNow.AddSeconds(180)
do {
    $outbox = Get-TableScan $outputMap.OutboxTableName
    $delivered = $false
    if ($outbox.Count -eq 1) {
        $delivered = $outbox.Items[0].delivery_status.S -eq 'DELIVERED'
    }
    if (-not $delivered) { Start-Sleep -Seconds 5 }
} while (-not $delivered -and [DateTimeOffset]::UtcNow -lt $deliveryDeadline)
$manifest.steps.outbox_delivered_after_projection_retry = $delivered

$duplicate = Invoke-ScenarioLambda $outputMap.WorkerFunctionName @{
    operation_key = $operationKey
    owner = 'worker-c'
    now = 107
    lease_seconds = 5
} '04-duplicate-replay'
$manifest.steps.canonical_result_replayed = [bool]$duplicate.payload.replayed

$corruptRequestPath = Join-Path $EvidenceDirectory '05-corrupt-projection.json'
Write-JsonRequest $corruptRequestPath @{
    TableName = $outputMap.ProjectionTableName
    Key = @{ operation_key = @{ S = $operationKey } }
    UpdateExpression = 'SET #result=:result, source_version=:version'
    ExpressionAttributeNames = @{ '#result' = 'result' }
    ExpressionAttributeValues = @{
        ':result' = @{ S = 'CORRUPT' }
        ':version' = @{ N = '0' }
    }
}
aws @profileArgs --region $Region dynamodb update-item --cli-input-json "file://$corruptRequestPath" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Unable to inject projection corruption" }

$reconciled = Invoke-ScenarioLambda $outputMap.ReconcilerFunctionName @{} '06-reconcile'
$manifest.steps.mismatch_detected = [int]$reconciled.payload.mismatched -eq 1
$manifest.steps.projection_repaired = [int]$reconciled.payload.repaired -eq 1

$operations = Get-TableScan $outputMap.OperationsTableName
$providers = Get-TableScan $outputMap.ProviderEffectsTableName
$outbox = Get-TableScan $outputMap.OutboxTableName
$projection = Get-TableScan $outputMap.ProjectionTableName

$manifest.counts = [ordered]@{
    operations = [int]$operations.Count
    provider_effects = [int]$providers.Count
    outbox_records = [int]$outbox.Count
    projections = [int]$projection.Count
}
$manifest.final_state = [ordered]@{
    operation_status = $operations.Items[0].status.S
    outbox_delivery_status = $outbox.Items[0].delivery_status.S
    operation_version = [int]$operations.Items[0].version.N
    projection_version = [int]$projection.Items[0].source_version.N
    projection_matches_source = $projection.Items[0].result.S -eq $operations.Items[0].result.S
}
$manifest.completed_at = [DateTimeOffset]::UtcNow.ToString('o')
$manifest.contract = [ordered]@{
    crash_injected = $manifest.steps.crash_after_provider
    active_lease_protected = $manifest.steps.before_lease_expiry_rejected
    expired_lease_recovered = $manifest.steps.lease_reclaimed
    provider_effect_occurred_once = $manifest.counts.provider_effects -eq 1
    provider_result_reused = $manifest.steps.provider_result_replayed
    operation_completed = $manifest.final_state.operation_status -eq 'COMPLETE'
    outbox_committed_once = $manifest.counts.outbox_records -eq 1
    projection_retry_converged = $manifest.steps.outbox_delivered_after_projection_retry
    duplicate_returned_canonical_result = $manifest.steps.canonical_result_replayed
    reconciliation_detected_mismatch = $manifest.steps.mismatch_detected
    reconciliation_repaired_projection = $manifest.steps.projection_repaired
    source_and_projection_match = $manifest.final_state.projection_matches_source
}
$manifest.passed = -not ($manifest.contract.Values -contains $false)

$manifestPath = Join-Path $EvidenceDirectory 'run-manifest.json'
$manifest | ConvertTo-Json -Depth 12 | Set-Content -Encoding utf8 $manifestPath

if (-not $manifest.passed) { exit 1 }

