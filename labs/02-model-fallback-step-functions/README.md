# Lab 02 - Model Fallback with Step Functions

## What This Proves

Model fallback should be encoded into the workflow. The platform should retry bounded transient failures, route to a fallback model, mark the response as degraded, and emit an operational signal.

## AWS Services Used

- AWS Step Functions
- AWS Lambda
- Amazon Bedrock
- Amazon CloudWatch
- Amazon EventBridge optional

## Failure Injected

Force the primary model path to fail using a test flag, invalid test model ID, or test-stage permission denial.

## Expected Behaviour

- primary model invocation fails
- retry policy runs with bounded backoff
- fallback model invocation succeeds
- response is marked as degraded
- fallback metric or log event is emitted

## Evidence Captured

- Step Functions execution graph
- CloudWatch log showing primary failure and fallback success
- fallback-count metric
- sample degraded response

## Status

Planned.
