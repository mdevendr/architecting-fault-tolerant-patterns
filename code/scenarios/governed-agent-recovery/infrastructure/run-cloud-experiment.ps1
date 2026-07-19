param(
    [Parameter(Mandatory = $true)][string]$RunId,
    [string]$Region = 'eu-west-2',
    [string]$Profile = 'melon',
    [string]$EvidenceDirectory = ''
)

$ErrorActionPreference = 'Stop'
$stackName = "fault-tolerance-governed-agent-$RunId"
if (-not $EvidenceDirectory) {
    $EvidenceDirectory = Join-Path $PSScriptRoot "..\evidence\runs\$RunId"
}
$EvidenceDirectory = [System.IO.Path]::GetFullPath($EvidenceDirectory)
New-Item -ItemType Directory -Force -Path $EvidenceDirectory | Out-Null
$utf8 = New-Object System.Text.UTF8Encoding($false)

function Write-Json([string]$Path, [object]$Value) {
    [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Compress -Depth 12), $utf8)
}

function Output([string]$Key) {
    aws cloudformation describe-stacks --profile $Profile --region $Region --stack-name $stackName `
        --query "Stacks[0].Outputs[?OutputKey=='$Key'].OutputValue" --output text
}

function Call-Gateway([string]$Name, [string]$ToolName, [hashtable]$Arguments) {
    $request = Join-Path $EvidenceDirectory "$Name-request.json"
    $response = Join-Path $EvidenceDirectory "$Name-response.json"
    Write-Json $request @{
        jsonrpc = '2.0'; id = $Name; method = 'tools/call'
        params = @{ name = $ToolName; arguments = $Arguments }
    }
    curl.exe -sS -X POST $gatewayUrl -H 'Content-Type: application/json' `
        --data-binary "@$request" -o $response
    return Get-Content -Raw $response | ConvertFrom-Json
}

function Invoke-ToolLambda([string]$Name, [hashtable]$Payload) {
    $request = Join-Path $EvidenceDirectory "$Name-request.json"
    $response = Join-Path $EvidenceDirectory "$Name-response.json"
    Write-Json $request $Payload
    $metadata = aws lambda invoke --profile $Profile --region $Region `
        --function-name $functionName --cli-binary-format raw-in-base64-out `
        --payload "fileb://$request" $response | ConvertFrom-Json
    return @{
        Metadata = $metadata
        Body = (Get-Content -Raw $response | ConvertFrom-Json)
    }
}

$gatewayUrl = Output 'GatewayUrl'
$functionName = Output 'ToolFunctionName'
$tableName = Output 'ToolStateTableName'
$toolName = 'CreditTool___reserve_credit'
$operationId = "$RunId-r3"

$denied = Call-Gateway '01-policy-denied' $toolName @{
    call_id = "$operationId-denied"; tenant_id = 'tenant-a'; actor_role = 'credit-operator'; amount = 1500
}
$deniedKeyPath = Join-Path $EvidenceDirectory 'denied-key.json'
Write-Json $deniedKeyPath @{ call_id = @{ S = "$operationId-denied" } }
$deniedItem = aws dynamodb get-item --profile $Profile --region $Region --table-name $tableName `
    --key "file://$deniedKeyPath" --consistent-read --output json | ConvertFrom-Json

$lost = Call-Gateway '02-response-lost-after-commit' $toolName @{
    call_id = "$operationId-reservation"; tenant_id = 'tenant-a'; actor_role = 'credit-operator'; amount = 500
    inject_failure_after_commit = $true
}
$replayed = Call-Gateway '03-canonical-result-replayed' $toolName @{
    call_id = "$operationId-reservation"; tenant_id = 'tenant-a'; actor_role = 'credit-operator'; amount = 500
}

$compensationLost = Invoke-ToolLambda '04-compensation-response-lost' @{
    _tool_name = 'compensate_credit'; call_id = "$operationId-reservation"; tenant_id = 'tenant-a'
    actor_role = 'recovery-controller'; inject_failure_after_commit = $true
}
$compensationReplay = Invoke-ToolLambda '05-compensation-replayed' @{
    _tool_name = 'compensate_credit'; call_id = "$operationId-reservation"; tenant_id = 'tenant-a'
    actor_role = 'recovery-controller'
}
$finalKeyPath = Join-Path $EvidenceDirectory 'final-key.json'
Write-Json $finalKeyPath @{ call_id = @{ S = "$operationId-reservation" } }
$finalItemRaw = aws dynamodb get-item --profile $Profile --region $Region --table-name $tableName `
    --key "file://$finalKeyPath" --consistent-read --output json
[System.IO.File]::WriteAllText((Join-Path $EvidenceDirectory '06-final-state.json'), $finalItemRaw, $utf8)
$finalItem = $finalItemRaw | ConvertFrom-Json

$manifest = [ordered]@{
    schema_version = '1.0'; execution_environment = 'aws'; run_id = $RunId; region = $Region
    contract = [ordered]@{
        policy_denied_request = $null -ne $denied.error
        denied_request_created_no_effect = $null -eq $deniedItem.Item
        ambiguous_forward_completion_injected = [bool]$lost.result.isError
        canonical_forward_result_replayed = $replayed.result.content[0].text -match 'replayed.*true'
        compensation_ambiguous_completion_injected = $null -ne $compensationLost.Metadata.FunctionError
        canonical_compensation_result_replayed = [bool]$compensationReplay.Body.replayed
        final_state_compensated = $finalItem.Item.status.S -eq 'COMPENSATED'
        one_forward_result_identity = $finalItem.Item.result.S -eq "reservation:$operationId-reservation:500"
        one_compensation_result_identity = $finalItem.Item.compensation_result.S -eq "released:$operationId-reservation"
    }
}
$manifest.passed = -not ($manifest.contract.Values -contains $false)
$manifest | ConvertTo-Json -Depth 12 | Set-Content -Encoding utf8 (Join-Path $EvidenceDirectory 'run-manifest.json')
if (-not $manifest.passed) { exit 1 }
