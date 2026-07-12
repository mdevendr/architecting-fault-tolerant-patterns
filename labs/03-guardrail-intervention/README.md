# Lab 03 - Guardrail Intervention

## What This Proves

Guardrail intervention is a resilience control. The AI path should not fail open when a prompt violates safety, compliance, or business-policy boundaries.

## AWS Services Used

- Amazon Bedrock
- Bedrock Guardrails
- AWS Lambda
- Amazon CloudWatch

## Failure Injected

Send prompts that attempt unsafe, unauthorised, or unsupported requests.

## Expected Behaviour

- guardrail evaluates the request or response
- unsafe path is blocked
- controlled safe response is returned
- audit event or metric is emitted

## Evidence Captured

- guardrail result
- blocked category
- safe response
- CloudWatch log with `guardrail_action=blocked`
- blocked-count metric

## Status

Planned.
