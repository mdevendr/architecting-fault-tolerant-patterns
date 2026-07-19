param(
    [Parameter(Mandatory = $true)][string]$RunId,
    [string]$Region = 'eu-west-2',
    [string]$Profile = '',
    [string]$EvidenceRoot = '.\tmp\aws-evidence'
)

$ErrorActionPreference = 'Stop'
$profileArgs = @()
if ($Profile) { $profileArgs = @('--profile', $Profile) }
$EvidenceRoot = [System.IO.Path]::GetFullPath($EvidenceRoot)

function Get-MetricSummary {
    param(
        [string]$MetricName,
        [string]$Mode,
        [string]$CellId,
        [datetime]$StartTime,
        [datetime]$EndTime
    )
    $raw = aws @profileArgs --region $Region cloudwatch get-metric-statistics `
        --namespace FaultToleranceEvidence `
        --metric-name $MetricName `
        --dimensions "Name=RunId,Value=$RunId" "Name=Mode,Value=$Mode" "Name=CellId,Value=$CellId" `
        --start-time $StartTime.ToUniversalTime().ToString('o') `
        --end-time $EndTime.ToUniversalTime().ToString('o') `
        --period 60 `
        --statistics Sum `
        --output json
    if ($LASTEXITCODE -ne 0) { throw "Unable to retrieve $MetricName for $Mode/$CellId" }
    $data = $raw | ConvertFrom-Json
    $values = @($data.Datapoints | ForEach-Object { [double]$_.Sum })
    return [ordered]@{
        total = if ($values.Count) { [Math]::Round(($values | Measure-Object -Sum).Sum, 3) } else { 0 }
        peak_per_minute = if ($values.Count) { [Math]::Round(($values | Measure-Object -Maximum).Maximum, 3) } else { 0 }
        datapoints = $data.Datapoints
    }
}

$metrics = @('DownstreamAttempt', 'DownstreamRejected', 'CircuitOpenRejected', 'AdmissionRejected', 'Completed', 'DuplicateSuppressed')
$comparison = [ordered]@{
    schema_version = '1.0'
    execution_environment = 'aws'
    run_id = $RunId
    region = $Region
    collected_at = [DateTimeOffset]::UtcNow.ToString('o')
    modes = [ordered]@{}
}

foreach ($mode in @('naive', 'protected')) {
    $manifestPath = Join-Path $EvidenceRoot "$mode\run-manifest.json"
    $manifest = Get-Content -Raw $manifestPath | ConvertFrom-Json
    $start = ([datetime]$manifest.started_at).AddMinutes(-2)
    $end = ([datetime]$manifest.completed_at).AddMinutes(5)
    $modeResult = [ordered]@{
        manifest = $manifest
        cells = [ordered]@{}
    }
    foreach ($cell in @('cell-a', 'cell-b')) {
        $cellResult = [ordered]@{}
        foreach ($metric in $metrics) {
            $cellResult[$metric] = Get-MetricSummary $metric $mode $cell $start $end
        }
        $modeResult.cells[$cell] = $cellResult
    }
    $attempts = $modeResult.cells.'cell-a'.DownstreamAttempt.total + $modeResult.cells.'cell-b'.DownstreamAttempt.total
    $completed = $modeResult.cells.'cell-a'.Completed.total + $modeResult.cells.'cell-b'.Completed.total
    $duplicates = $modeResult.cells.'cell-a'.DuplicateSuppressed.total + $modeResult.cells.'cell-b'.DuplicateSuppressed.total
    $modeResult.summary = [ordered]@{
        downstream_attempts = $attempts
        circuit_open_rejections = $modeResult.cells.'cell-a'.CircuitOpenRejected.total + $modeResult.cells.'cell-b'.CircuitOpenRejected.total
        completed = $completed
        duplicate_suppressed = $duplicates
        attempt_amplification = if ($completed) { [Math]::Round($attempts / $completed, 3) } else { 0 }
        cell_a_peak_attempts_per_minute = $modeResult.cells.'cell-a'.DownstreamAttempt.peak_per_minute
        cell_b_completed = $modeResult.cells.'cell-b'.Completed.total
        recovery_seconds = $manifest.recovery_seconds
    }
    $comparison.modes[$mode] = $modeResult
}

$protected = $comparison.modes.protected
$comparison.contract = [ordered]@{
    all_outcomes_completed = ($protected.summary.completed -eq $protected.manifest.expected_outcomes)
    healthy_cell_completed = ($protected.summary.cell_b_completed -eq $protected.manifest.healthy_cell_messages)
    duplicate_business_outcomes = ($protected.summary.duplicate_suppressed -eq 0)
    protected_peak_within_rate_contract = ($protected.summary.cell_a_peak_attempts_per_minute -le 720)
    protected_attempt_amplification_lower_than_naive = ($protected.summary.attempt_amplification -lt $comparison.modes.naive.summary.attempt_amplification)
}
$comparison.passed = -not ($comparison.contract.Values -contains $false)

$outputPath = Join-Path $EvidenceRoot 'cloud-comparison.json'
$comparison | ConvertTo-Json -Depth 15 | Set-Content -Encoding utf8 $outputPath

$markdown = @(
    '# Recovery-storm containment: AWS evidence',
    '',
    "Run ID: ``$RunId``",
    '',
    '| Metric | Naive | Protected |',
    '|---|---:|---:|',
    "| Downstream attempts | $($comparison.modes.naive.summary.downstream_attempts) | $($comparison.modes.protected.summary.downstream_attempts) |",
    "| Circuit-open rejections | $($comparison.modes.naive.summary.circuit_open_rejections) | $($comparison.modes.protected.summary.circuit_open_rejections) |",
    "| Attempt amplification | $($comparison.modes.naive.summary.attempt_amplification) | $($comparison.modes.protected.summary.attempt_amplification) |",
    "| Cell A peak attempts/minute | $($comparison.modes.naive.summary.cell_a_peak_attempts_per_minute) | $($comparison.modes.protected.summary.cell_a_peak_attempts_per_minute) |",
    "| Completed outcomes | $($comparison.modes.naive.summary.completed) | $($comparison.modes.protected.summary.completed) |",
    "| Healthy cell outcomes | $($comparison.modes.naive.summary.cell_b_completed) | $($comparison.modes.protected.summary.cell_b_completed) |",
    "| Recovery seconds | $($comparison.modes.naive.summary.recovery_seconds) | $($comparison.modes.protected.summary.recovery_seconds) |",
    '',
    "Contract result: **$(if ($comparison.passed) { 'PASS' } else { 'FAIL' })**",
    '',
    '> Values are scoped to the tagged AWS test stacks and Run ID. The experiment uses an account concurrency quota of 10 and is not a production capacity benchmark.'
)
$markdown | Set-Content -Encoding utf8 (Join-Path $EvidenceRoot 'cloud-comparison.md')

if (-not $comparison.passed) { exit 1 }
