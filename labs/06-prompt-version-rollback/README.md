# Lab 06 - Prompt Version Rollback

## What This Proves

Prompts are deployable artefacts. A bad prompt version should fail validation and roll back like any other production change.

## AWS Services Used

- Amazon Bedrock
- AWS Lambda
- Amazon DynamoDB or AWS AppConfig
- Amazon CloudWatch

## Failure Injected

Deploy a prompt version that reduces answer quality or breaks the expected response format.

## Expected Behaviour

- quality check fails
- prompt is rolled back to previous version
- rollback event is recorded
- restored prompt passes validation

## Evidence Captured

- prompt registry entry
- before/after output comparison
- rollback log
- restored quality-check result

## Status

Planned.
