param(
    [Parameter(Mandatory = $true)][string]$RunId,
    [string]$Region = 'eu-west-2',
    [string]$Profile = 'melon',
    [string]$EvidenceDirectory = ''
)
$ErrorActionPreference = 'Stop'
$stackName = "fault-tolerance-derived-state-$RunId"
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
function Put-Item([string]$Table, [string]$Name, [object]$Item) {
    $path = Join-Path $EvidenceDirectory "$Name.json"; Write-Json $path $Item
    aws dynamodb put-item --profile $Profile --region $Region --table-name $Table --item "file://$path" | Out-Null
}
function Get-Item([string]$Table, [string]$Id, [string]$Name) {
    $key = Join-Path $EvidenceDirectory "$Name-key.json"; Write-Json $key @{record_id=@{S=$Id}}
    $raw = aws dynamodb get-item --profile $Profile --region $Region --table-name $Table `
      --key "file://$key" --consistent-read --output json
    [System.IO.File]::WriteAllText((Join-Path $EvidenceDirectory "$Name.json"), $raw, $utf8)
    return $raw | ConvertFrom-Json
}
function Invoke-Function([string]$Function, [string]$Name, [object]$Payload) {
    $request = Join-Path $EvidenceDirectory "$Name-request.json"; Write-Json $request $Payload
    $response = Join-Path $EvidenceDirectory "$Name-response.json"
    aws lambda invoke --profile $Profile --region $Region --function-name $Function `
      --cli-binary-format raw-in-base64-out --payload "fileb://$request" $response | Out-Null
    return Get-Content -Raw $response | ConvertFrom-Json
}
function Wait-Version([string]$Id, [int]$Version) {
    for ($attempt=0; $attempt -lt 40; $attempt++) {
        $item = Get-Item $projectionTable $Id "wait-$Id"
        if ($item.Item.version.N -and [int]$item.Item.version.N -eq $Version) { return $item }
        Start-Sleep -Seconds 2
    }
    throw "Projection $Id did not reach version $Version"
}

$sourceTable = Output 'SourceTableName'
$projectionTable = Output 'ProjectionTableName'
$projector = Output 'ProjectionFunctionName'
$reconciler = Output 'ReconciliationFunctionName'
$queueUrl = Output 'QuarantineQueueUrl'
$pipeName = Output 'PipeName'
$idCurrent = 'r3-current'
$idMissing = 'r3-missing'
$idPoison = 'r3-poison'
$idMismatch = 'r3-mismatch'
$idExtra = 'r3-extra'

Put-Item $sourceTable 'source-current-v1' @{
  record_id=@{S=$idCurrent}; version=@{N='1'}; value=@{S='v1'}
}
Wait-Version $idCurrent 1 | Out-Null
Put-Item $sourceTable 'source-current-v2' @{
  record_id=@{S=$idCurrent}; version=@{N='2'}; value=@{S='v2'}
}
Wait-Version $idCurrent 2 | Out-Null

Put-Item $sourceTable 'source-missing' @{
  record_id=@{S=$idMissing}; version=@{N='1'}; value=@{S='needs-repair'}; inject_skip_projection=@{BOOL=$true}
}
Put-Item $sourceTable 'source-poison' @{
  record_id=@{S=$idPoison}; version=@{N='1'}; value=@{S='operator-reviewed'}; inject_poison=@{BOOL=$true}
}
Put-Item $sourceTable 'source-mismatch' @{
  record_id=@{S=$idMismatch}; version=@{N='3'}; value=@{S='authoritative-v3'}
}
Wait-Version $idMismatch 3 | Out-Null
Start-Sleep -Seconds 4

$synthetic = @{
  Records=@(
    @{eventID='duplicate-v2'; dynamodb=@{NewImage=@{record_id=@{S=$idCurrent};version=@{N='2'};value=@{S='v2'}}}},
    @{eventID='late-v1'; dynamodb=@{NewImage=@{record_id=@{S=$idCurrent};version=@{N='1'};value=@{S='obsolete'}}}}
  )
}
$replayOutcome = Invoke-Function $projector 'synthetic-duplicate-and-stale' $synthetic
$currentAfterReplay = Get-Item $projectionTable $idCurrent 'current-after-replay'

Put-Item $projectionTable 'corrupt-mismatch' @{
  record_id=@{S=$idMismatch}; version=@{N='2'}; value=@{S='corrupted-v2'}; source_event_id=@{S='FAULT'}; projected_at=@{N='0'}
}
Put-Item $projectionTable 'extra-projection' @{
  record_id=@{S=$idExtra}; version=@{N='1'}; value=@{S='orphan'}; source_event_id=@{S='FAULT'}; projected_at=@{N='0'}
}

$sourceBefore = aws dynamodb scan --profile $Profile --region $Region --table-name $sourceTable --consistent-read --output json
[System.IO.File]::WriteAllText((Join-Path $EvidenceDirectory 'source-before-repair.json'), $sourceBefore, $utf8)
$sourceBeforeNormalized = (($sourceBefore | ConvertFrom-Json).Items | Sort-Object { $_.record_id.S } | ConvertTo-Json -Compress -Depth 10)
$before = Invoke-Function $reconciler 'reconciliation-detect' @{repair=$false}
$repair = Invoke-Function $reconciler 'reconciliation-repair' @{repair=$true}
$after = Invoke-Function $reconciler 'reconciliation-verify' @{repair=$false}
$sourceAfter = aws dynamodb scan --profile $Profile --region $Region --table-name $sourceTable --consistent-read --output json
[System.IO.File]::WriteAllText((Join-Path $EvidenceDirectory 'source-after-repair.json'), $sourceAfter, $utf8)
$sourceAfterNormalized = (($sourceAfter | ConvertFrom-Json).Items | Sort-Object { $_.record_id.S } | ConvertTo-Json -Compress -Depth 10)

$quarantine = aws sqs receive-message --profile $Profile --region $Region --queue-url $queueUrl `
  --max-number-of-messages 10 --wait-time-seconds 2 --output json
[System.IO.File]::WriteAllText((Join-Path $EvidenceDirectory 'quarantine.json'), $quarantine, $utf8)
$quarantineObject = $quarantine | ConvertFrom-Json
$pipe = aws pipes describe-pipe --profile $Profile --region $Region --name $pipeName --output json
[System.IO.File]::WriteAllText((Join-Path $EvidenceDirectory 'pipe.json'), $pipe, $utf8)
$pipeObject = $pipe | ConvertFrom-Json

$manifest = [ordered]@{
  schema_version='1.0'; execution_environment='aws'; run_id=$RunId; region=$Region
  detected=[ordered]@{
    missing=$before.missing; extra=$before.extra; mismatched=$before.mismatched
  }
  contract=[ordered]@{
    pipe_running=$pipeObject.currentState -eq 'RUNNING'
    duplicate_event_suppressed=$replayOutcome.outcomes[0].outcome -eq 'DUPLICATE_OR_STALE'
    out_of_order_event_suppressed=$replayOutcome.outcomes[1].outcome -eq 'DUPLICATE_OR_STALE'
    projection_did_not_regress=[int]$currentAfterReplay.Item.version.N -eq 2
    poison_event_quarantined=$quarantineObject.Messages.Count -ge 1
    missing_detected=$before.missing -contains $idMissing
    poison_missing_detected=$before.missing -contains $idPoison
    extra_detected=$before.extra -contains $idExtra
    mismatch_detected=$before.mismatched -contains $idMismatch
    four_divergences_repaired=[int]$repair.repaired_count -eq 4
    final_missing_zero=[int]$after.missing_count -eq 0
    final_extra_zero=[int]$after.extra_count -eq 0
    final_mismatch_zero=[int]$after.version_or_value_mismatch_count -eq 0
    source_unchanged_by_repair=[bool]($sourceBeforeNormalized -ceq $sourceAfterNormalized)
  }
}
$manifest.passed = -not ($manifest.contract.Values -contains $false)
$manifest | ConvertTo-Json -Depth 20 | Set-Content -Encoding utf8 (Join-Path $EvidenceDirectory 'run-manifest.json')
if (-not $manifest.passed) { exit 1 }
