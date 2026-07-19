param(
    [Parameter(Mandatory = $true)][string]$RunId,
    [ValidateSet('naive', 'protected')][string]$Mode,
    [string]$Region = 'eu-west-2',
    [string]$Profile = '',
    [int]$FaultedCellMessages = 600,
    [int]$HealthyCellMessages = 180,
    [int]$FaultHoldSeconds = 60,
    [int]$DrainTimeoutSeconds = 600,
    [string]$EvidenceDirectory = ''
)

$ErrorActionPreference = 'Stop'
$stackName = "fault-tolerance-recovery-$RunId-$Mode"
$profileArgs = @()
if ($Profile) { $profileArgs = @('--profile', $Profile) }

if (-not $EvidenceDirectory) {
    $EvidenceDirectory = Join-Path $PSScriptRoot "..\evidence\runs\$RunId-$Mode"
}
$EvidenceDirectory = [System.IO.Path]::GetFullPath($EvidenceDirectory)
New-Item -ItemType Directory -Force -Path $EvidenceDirectory | Out-Null

function Invoke-AwsJson {
    param([string[]]$Arguments)
    $value = aws @profileArgs --region $Region @Arguments
    if ($LASTEXITCODE -ne 0) { throw "AWS command failed: $($Arguments -join ' ')" }
    if (-not $value) { return $null }
    return $value | ConvertFrom-Json
}

function Write-JsonRequest {
    param([string]$Path, [string]$Json)
    $utf8WithoutBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Json, $utf8WithoutBom)
}

function Set-CellState {
    param([string]$TableName, [string]$CellId, [string]$State)
    $request = @{
        TableName = $TableName
        Item = @{
            cell_id = @{ S = $CellId }
            state = @{ S = $State }
            changed_at = @{ N = [string][DateTimeOffset]::UtcNow.ToUnixTimeSeconds() }
        }
    } | ConvertTo-Json -Compress
    $requestPath = Join-Path $EvidenceDirectory "set-$CellId-$State.json"
    Write-JsonRequest $requestPath $request
    aws @profileArgs --region $Region dynamodb put-item --cli-input-json "file://$requestPath" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Unable to set $CellId to $State" }
}

function Send-Work {
    param([string]$QueueUrl, [string]$TenantId, [string]$CellId, [int]$Count)
    for ($start = 0; $start -lt $Count; $start += 10) {
        $entries = @()
        $end = [Math]::Min($start + 10, $Count)
        for ($index = $start; $index -lt $end; $index++) {
            $messageId = "$RunId-$CellId-$index"
            $body = @{
                message_id = $messageId
                tenant_id = $TenantId
                cell_id = $CellId
                created_at = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
            } | ConvertTo-Json -Compress
            $entries += @{
                Id = "m$index"
                MessageBody = $body
            }
        }
        $request = @{
            QueueUrl = $QueueUrl
            Entries = $entries
        } | ConvertTo-Json -Compress -Depth 6
        $requestPath = Join-Path $EvidenceDirectory "batch-$CellId-$start.json"
        Write-JsonRequest $requestPath $request
        aws @profileArgs --region $Region sqs send-message-batch --cli-input-json "file://$requestPath" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Unable to publish batch at offset $start" }
    }
}

function Reset-Outcomes {
    param([string]$TableName)
    $raw = aws @profileArgs --region $Region dynamodb scan --table-name $TableName --projection-expression message_id --output json
    if ($LASTEXITCODE -ne 0) { throw "Unable to scan outcome table for reset" }
    $items = @(($raw | ConvertFrom-Json).Items)
    for ($start = 0; $start -lt $items.Count; $start += 25) {
        $requests = @()
        $end = [Math]::Min($start + 25, $items.Count)
        for ($index = $start; $index -lt $end; $index++) {
            $requests += @{ DeleteRequest = @{ Key = @{ message_id = $items[$index].message_id } } }
        }
        $request = @{ RequestItems = @{ $TableName = $requests } } | ConvertTo-Json -Compress -Depth 8
        $requestPath = Join-Path $EvidenceDirectory "reset-outcomes-$start.json"
        Write-JsonRequest $requestPath $request
        aws @profileArgs --region $Region dynamodb batch-write-item --cli-input-json "file://$requestPath" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Unable to reset outcomes at offset $start" }
    }
}

function Get-QueueSnapshot {
    param([string]$QueueUrl, [string]$CellId, [string]$Phase)
    $attributes = Invoke-AwsJson @(
        'sqs', 'get-queue-attributes',
        '--queue-url', $QueueUrl,
        '--attribute-names', 'ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible'
    )
    return [ordered]@{
        timestamp = [DateTimeOffset]::UtcNow.ToString('o')
        phase = $Phase
        cell_id = $CellId
        visible = [int]$attributes.Attributes.ApproximateNumberOfMessages
        in_flight = [int]$attributes.Attributes.ApproximateNumberOfMessagesNotVisible
    }
}

$outputs = Invoke-AwsJson @(
    'cloudformation', 'describe-stacks',
    '--stack-name', $stackName,
    '--query', 'Stacks[0].Outputs'
)
$outputMap = @{}
foreach ($output in $outputs) { $outputMap[$output.OutputKey] = $output.OutputValue }

Reset-Outcomes $outputMap.OutcomeTableName

$manifest = [ordered]@{
    schema_version = '1.0'
    execution_environment = 'aws'
    run_id = $RunId
    mode = $Mode
    region = $Region
    stack_name = $stackName
    started_at = [DateTimeOffset]::UtcNow.ToString('o')
    fault = 'cell-a downstream impairment while cell-b remains healthy'
    faulted_cell_messages = $FaultedCellMessages
    healthy_cell_messages = $HealthyCellMessages
    fault_hold_seconds = $FaultHoldSeconds
}
$snapshots = @()

Set-CellState $outputMap.ControlTableName 'cell-a' 'IMPAIRED'
Set-CellState $outputMap.ControlTableName 'cell-b' 'RUNNING'
Send-Work $outputMap.CellAQueueUrl 'tenant-noisy' 'cell-a' $FaultedCellMessages
Send-Work $outputMap.CellBQueueUrl 'tenant-normal' 'cell-b' $HealthyCellMessages

$snapshots += Get-QueueSnapshot $outputMap.CellAQueueUrl 'cell-a' 'fault'
$snapshots += Get-QueueSnapshot $outputMap.CellBQueueUrl 'cell-b' 'fault'
Start-Sleep -Seconds $FaultHoldSeconds

Set-CellState $outputMap.ControlTableName 'cell-a' 'RUNNING'
$recoveryStarted = [DateTimeOffset]::UtcNow

do {
    $cellA = Get-QueueSnapshot $outputMap.CellAQueueUrl 'cell-a' 'recovery'
    $cellB = Get-QueueSnapshot $outputMap.CellBQueueUrl 'cell-b' 'recovery'
    $snapshots += $cellA
    $snapshots += $cellB
    $drained = ($cellA.visible + $cellA.in_flight -eq 0) -and ($cellB.visible + $cellB.in_flight -eq 0)
    if (-not $drained) { Start-Sleep -Seconds 10 }
} while (-not $drained -and ([DateTimeOffset]::UtcNow - $recoveryStarted).TotalSeconds -lt $DrainTimeoutSeconds)

$outcome = Invoke-AwsJson @(
    'dynamodb', 'scan',
    '--table-name', $outputMap.OutcomeTableName,
    '--select', 'COUNT'
)
$manifest.completed_at = [DateTimeOffset]::UtcNow.ToString('o')
$manifest.recovery_seconds = [Math]::Round(([DateTimeOffset]::UtcNow - $recoveryStarted).TotalSeconds, 3)
$manifest.expected_outcomes = $FaultedCellMessages + $HealthyCellMessages
$manifest.observed_outcomes = [int]$outcome.Count
$manifest.queues_drained = $drained
$manifest.passed = $drained -and ($manifest.expected_outcomes -eq $manifest.observed_outcomes)

$manifest | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 (Join-Path $EvidenceDirectory 'run-manifest.json')
$snapshots | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 (Join-Path $EvidenceDirectory 'queue-snapshots.json')

if (-not $manifest.passed) { exit 1 }
