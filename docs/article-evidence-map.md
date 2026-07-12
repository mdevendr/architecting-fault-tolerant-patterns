# Article Evidence Map

This file maps article claims to implementation evidence that will be captured in this repository.

## Core Claim

Fault tolerance is not proven by the number of redundant components. It is proven by observed behaviour under impairment.

Evidence required:

- failure injected deliberately
- expected behaviour defined before the test
- operational telemetry captured during the test
- recovery or degraded behaviour verified
- cleanup and repeatability documented

## AI/ML and GenAI Claim

AI systems need service recovery and trust recovery.

Service recovery restores the technical execution path.

Trust recovery proves the answer is grounded, current, safe, authorised, traceable, and acceptable for the business decision.

## Evidence Scenarios

### 1. Bedrock Invocation Observability

Article claim: AI inference must be traceable by model, caller, prompt version, token usage, latency, and request metadata.

Evidence:

- Bedrock invocation log
- CloudWatch Logs query
- application request metadata
- screenshot of log entry or query result

### 2. Model Fallback

Article claim: Model fallback should be encoded into the platform, not improvised during an incident.

Evidence:

- Step Functions execution showing primary failure
- retry attempt
- fallback model success
- degraded response marker
- CloudWatch fallback-count metric

### 3. Guardrail Intervention

Article claim: Guardrail intervention is a resilience control because it prevents fail-open behaviour.

Evidence:

- guardrail blocked response
- blocked category
- safe user-facing message
- audit log or CloudWatch metric

### 4. Stale RAG Context

Article claim: A RAG system can be available but untrustworthy when retrieval context is stale.

Evidence:

- source document version or timestamp
- vector index timestamp
- freshness check failure
- controlled degraded response

### 5. Agent Tool Failure

Article claim: Agentic workflows need dependency protection because failed tool calls can create retry storms.

Evidence:

- tool failure logs
- circuit breaker state change
- queued work in SQS
- degraded response
- recovery after half-open test

### 6. Prompt Regression

Article claim: Prompts are deployable artefacts and need rollback controls.

Evidence:

- prompt version registry
- failed quality check
- rollback event
- before/after output comparison
