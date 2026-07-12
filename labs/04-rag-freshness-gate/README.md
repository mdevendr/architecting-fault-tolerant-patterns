# Lab 04 - RAG Freshness Gate

## What This Proves

A RAG assistant can be available but untrustworthy when the vector index is stale. Freshness must be checked before generation.

## AWS Services Used

- Amazon S3
- Amazon DynamoDB
- Amazon Bedrock
- Vector store to be selected
- AWS Lambda
- Amazon CloudWatch

## Failure Injected

Update the source document but do not refresh the vector index. Ask a question whose correct answer depends on the newer source.

## Expected Behaviour

- application detects source version is newer than retrieval index version
- generation is blocked or routed to degraded response
- stale retrieval event is logged
- stale retrieval metric increments

## Evidence Captured

- S3 source object version or timestamp
- DynamoDB metadata showing index version
- application log with `retrieval_status=stale`
- controlled degraded response

## Status

Planned.
