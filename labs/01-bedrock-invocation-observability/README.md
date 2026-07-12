# Lab 01 - Bedrock Invocation Observability

## What This Proves

AI inference must be operationally traceable. A successful model response is not enough unless the platform can show which model, prompt version, caller, request metadata, latency, and token usage produced the answer.

## AWS Services Used

- Amazon Bedrock
- AWS Lambda
- Amazon CloudWatch Logs
- AWS CloudFormation

## Failure Injected

Run normal, degraded, and policy-sensitive prompts so the evidence captures different inference paths.

## Expected Behaviour

The application logs each model invocation with operational metadata:

- model ID or inference profile ID
- prompt version
- request ID
- latency
- token usage when available
- degradation mode
- capability name

## Evidence Captured

- Bedrock invocation log
- application log entry
- CloudWatch Logs Insights query result
- sample Lambda response
- screenshot saved under `evidence/screenshots/`

## Files

- `template.yaml` - CloudFormation stack for Lambda, IAM role, and log group
- `events/normal.json` - normal inference path
- `events/degraded.json` - degraded-path metadata test
- `events/policy-sensitive.json` - policy-sensitive metadata test
- `scripts/deploy.sh` - deploys the lab
- `scripts/invoke.sh` - invokes the lab Lambda
- `scripts/capture-logs.sh` - captures structured logs into `evidence/logs/`
- `scripts/destroy.sh` - deletes the stack

## Deploy

From the repository root:

```bash
cd "/c/mahesh/AWS SA/work/architecting-fault-tolerant-patterns"
./labs/01-bedrock-invocation-observability/scripts/deploy.sh --profile melon --region us-east-1
```

The default model is:

```text
anthropic.claude-3-haiku-20240307-v1:0
```

Override it if your account uses a different Bedrock model:

```bash
./labs/01-bedrock-invocation-observability/scripts/deploy.sh \
  --profile melon \
  --region us-east-1 \
  --model-id "anthropic.claude-3-haiku-20240307-v1:0"
```

## Run Evidence Invocations

```bash
./labs/01-bedrock-invocation-observability/scripts/invoke.sh --profile melon --region us-east-1 --scenario normal
./labs/01-bedrock-invocation-observability/scripts/invoke.sh --profile melon --region us-east-1 --scenario degraded
./labs/01-bedrock-invocation-observability/scripts/invoke.sh --profile melon --region us-east-1 --scenario policy-sensitive
```

Responses are written to:

```text
evidence/sample-responses/
```

## Capture Logs

```bash
./labs/01-bedrock-invocation-observability/scripts/capture-logs.sh --profile melon --region us-east-1
```

Captured logs are written to:

```text
evidence/logs/01-bedrock-invocation-observability-logs.json
```

## Evidence To Screenshot

Capture screenshots for the article:

- Lambda function configuration showing environment variables
- CloudWatch log entry containing `ai_invocation_observability`
- CloudWatch Logs Insights query result grouped by model ID, prompt version, and degradation mode
- sample response showing `observability` metadata

Suggested CloudWatch Logs Insights query:

```sql
fields @timestamp, event_type, capability, model_id, prompt_version, degradation_mode, latency_ms, input_tokens, output_tokens, request_id
| filter event_type = "ai_invocation_observability"
| sort @timestamp desc
| limit 20
```

## Clean Up

```bash
./labs/01-bedrock-invocation-observability/scripts/destroy.sh --profile melon --region us-east-1
```

## Status

Implemented - pending AWS deployment and evidence capture.
