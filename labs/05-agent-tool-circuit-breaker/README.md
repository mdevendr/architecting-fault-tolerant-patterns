# Lab 05 - Agent Tool Circuit Breaker

## What This Proves

Agentic workflows need dependency protection. A failing tool should not cause repeated uncontrolled calls into the same failing dependency.

## AWS Services Used

- Amazon Bedrock
- AWS Lambda
- Amazon DynamoDB
- Amazon SQS
- Amazon CloudWatch

## Failure Injected

Force a downstream tool Lambda to time out or return repeated errors.

## Expected Behaviour

- initial tool failures are recorded
- circuit breaker moves from `CLOSED` to `OPEN`
- later requests fail fast without calling the dependency
- work is queued for replay
- degraded response is returned
- alarm is emitted

## Evidence Captured

- DynamoDB circuit-breaker state
- SQS queued message
- CloudWatch alarm
- application log showing degraded path
- recovery after half-open test

## Status

Planned.
