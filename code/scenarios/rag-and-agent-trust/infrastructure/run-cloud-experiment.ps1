param(
    [Parameter(Mandatory = $true)][string]$RunId,
    [string]$Region = 'eu-west-1',
    [string]$Profile = '',
    [string]$EvidenceDirectory = ''
)

$ErrorActionPreference = 'Stop'
$stackName = "fault-tolerance-rag-trust-$RunId"
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
    if ($LASTEXITCODE -ne 0 -or $metadata.FunctionError) {
        $body = Get-Content -Raw $responsePath
        throw "Lambda invocation failed: $Name - $body"
    }
    return Get-Content -Raw $responsePath | ConvertFrom-Json
}

$outputsRaw = aws @profileArgs --region $Region cloudformation describe-stacks `
    --stack-name $stackName --query 'Stacks[0].Outputs' --output json
if ($LASTEXITCODE -ne 0) { throw "Unable to read stack outputs" }
$outputs = $outputsRaw | ConvertFrom-Json
$outputMap = @{}
foreach ($output in $outputs) { $outputMap[$output.OutputKey] = $output.OutputValue }

$manifest = [ordered]@{
    schema_version = '1.0'
    execution_environment = 'aws'
    run_id = $RunId
    region = $Region
    stack_name = $stackName
    started_at = [DateTimeOffset]::UtcNow.ToString('o')
    steps = [ordered]@{}
}

$publishedV1 = Invoke-ScenarioLambda $outputMap.PublishFunctionName @{
    tenant_id = 'tenant-a'
    document_id = 'policy-1'
    source_version = 1
    previous_indexed_version = 0
    policy_version = 'policy-v1'
    text = 'The approved transaction limit is 5000.'
} '01-publish-v1'
$ingestedV1 = Invoke-ScenarioLambda $outputMap.IngestFunctionName @{
    tenant_id = 'tenant-a'
    document_id = 'policy-1'
} '02-ingest-v1'
$currentV1 = Invoke-ScenarioLambda $outputMap.GatewayFunctionName @{
    caller_tenant = 'tenant-a'
    document_id = 'policy-1'
    query = 'What is the approved transaction limit?'
} '03-current-query-v1'
$manifest.steps.current_v1_answered = $currentV1.status -eq 'ANSWER'
$manifest.steps.current_v1_cited = $currentV1.citations[0] -match 'version=1'

$publishedV2 = Invoke-ScenarioLambda $outputMap.PublishFunctionName @{
    tenant_id = 'tenant-a'
    document_id = 'policy-1'
    source_version = 2
    previous_indexed_version = 1
    policy_version = 'policy-v2'
    text = 'The approved transaction limit is 7000.'
} '04-publish-v2-no-ingestion'
$stale = Invoke-ScenarioLambda $outputMap.GatewayFunctionName @{
    caller_tenant = 'tenant-a'
    document_id = 'policy-1'
    query = 'What is the approved transaction limit?'
} '05-stale-query'
$manifest.steps.stale_response_blocked = $stale.status -eq 'SAFE_NON_ANSWER'
$manifest.steps.stale_reason = $stale.reason
$manifest.steps.stale_source_version = [int]$stale.evidence.authoritative_version
$manifest.steps.stale_indexed_version = [int]$stale.evidence.indexed_version

$unauthorized = Invoke-ScenarioLambda $outputMap.GatewayFunctionName @{
    caller_tenant = 'tenant-b'
    document_tenant = 'tenant-a'
    document_id = 'policy-1'
    query = 'What is the approved transaction limit?'
} '06-cross-tenant-query'
$manifest.steps.cross_tenant_blocked = $unauthorized.reason -eq 'CALLER_NOT_AUTHORIZED'

$publishedDistractor = Invoke-ScenarioLambda $outputMap.PublishFunctionName @{
    tenant_id = 'tenant-b'
    document_id = 'policy-b'
    source_version = 1
    previous_indexed_version = 0
    policy_version = 'policy-v1'
    text = 'The approved transaction limit is 999999.'
} '07-publish-tenant-b'
$ingestedDistractor = Invoke-ScenarioLambda $outputMap.IngestFunctionName @{
    tenant_id = 'tenant-b'
    document_id = 'policy-b'
} '08-ingest-tenant-b'

$ingestedV2 = Invoke-ScenarioLambda $outputMap.IngestFunctionName @{
    tenant_id = 'tenant-a'
    document_id = 'policy-1'
} '09-ingest-v2'
$recovered = Invoke-ScenarioLambda $outputMap.GatewayFunctionName @{
    caller_tenant = 'tenant-a'
    document_id = 'policy-1'
    query = 'What is the approved transaction limit?'
    top_k = 5
} '10-trust-recovered-query'
$manifest.steps.trust_recovered = $recovered.status -eq 'ANSWER'
$manifest.steps.recovered_answer_uses_v2 = $recovered.answer -match '7000'
$manifest.steps.recovered_citation_uses_v2 = $recovered.citations[0] -match 'version=2'
$manifest.steps.cross_tenant_distractor_excluded = $recovered.answer -notmatch '999999'
$manifest.final_response = $recovered
$manifest.completed_at = [DateTimeOffset]::UtcNow.ToString('o')
$manifest.contract = [ordered]@{
    current_authorized_response_cited = $manifest.steps.current_v1_answered -and $manifest.steps.current_v1_cited
    stale_answer_not_served = $manifest.steps.stale_response_blocked
    stale_versions_recorded = $manifest.steps.stale_source_version -eq 2 -and $manifest.steps.stale_indexed_version -eq 1
    cross_tenant_request_rejected = $manifest.steps.cross_tenant_blocked
    trust_recovered_after_ingestion = $manifest.steps.trust_recovered
    latest_authoritative_version_served = $manifest.steps.recovered_answer_uses_v2 -and $manifest.steps.recovered_citation_uses_v2
    tenant_metadata_filter_excluded_distractor = $manifest.steps.cross_tenant_distractor_excluded
}
$manifest.passed = -not ($manifest.contract.Values -contains $false)
$manifest | ConvertTo-Json -Depth 12 | Set-Content -Encoding utf8 (Join-Path $EvidenceDirectory 'run-manifest.json')

if (-not $manifest.passed) { exit 1 }

