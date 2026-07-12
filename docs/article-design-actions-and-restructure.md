# Article Design Actions and Restructure

This note reshapes the article around the question:

> How would you design a fault-tolerant architecture on AWS?

The article should answer this as an architecture method, not as a catalogue of AWS services.

## Fault-Tolerant Architecture Design Actions

1. Identify the business capability.

   Define the user journey or business function that must remain trustworthy, such as customer authentication, order submission, payment authorisation, fulfilment updates, document processing, or a GenAI support assistant.

2. Define the failure contract.

   Capture availability target, latency target, RTO, RPO, data-loss tolerance, correctness requirement, degraded mode, fail-closed conditions, and human escalation requirements.

3. Map the primary service path.

   Trace the end-to-end runtime path from user to edge, ingress, compute, integration, state, AI/ML or GenAI components, observability, and operations.

4. Identify fault positions.

   Mark where faults can occur: DNS, edge, API ingress, compute, dependency calls, queues, databases, storage, model endpoint, vector index, prompt version, guardrails, agent tools, deployment, and operator process.

5. Classify the failure behaviour.

   Decide what the business capability does when each fault occurs: continue, retry, queue, shed load, degrade, fallback, fail closed, escalate, reconcile, or recover.

6. Bound the failure domain.

   Decide where the blast radius must stop: AZ, Region, account, VPC, cell, tenant, queue, database partition, model endpoint, vector index, or external dependency.

7. Choose resilience controls.

   Select controls that match the failure contract: Multi-AZ, health checks, autoscaling, timeouts, retries with jitter, circuit breakers, bulkheads, SQS, DLQ, replay, idempotency, PITR, backups, replication, fallback model, guardrails, freshness gates, prompt rollback, and human review.

8. Protect state and correctness.

   Make duplicate handling, ordering, transaction boundaries, replay, reconciliation, backup restore, corruption recovery, model lineage, feature freshness, and vector freshness explicit.

9. Design degradation and fallback paths.

   Define safe user-facing behaviour when the ideal path is unavailable. The fallback must be encoded in the platform, not improvised during an incident.

10. Design recovery and failback.

    Define how the system returns from degraded mode, drains backlog, replays messages, reconciles state, restores data, validates AI outputs, and fails back safely.

11. Instrument evidence.

    Capture service signals and trust signals: health, errors, latency, saturation, queue depth, DLQ count, fallback count, stale retrieval count, guardrail block count, circuit state, recovery time, RPO, model ID, prompt version, and retrieval version.

12. Validate with game days.

    Inject controlled faults, observe behaviour, capture evidence, update runbooks, and feed findings back into architecture decisions.

## Recommended Article Flow

### 1. Opening

Keep the current opening, but make the article promise explicit:

> This article answers a practical architecture question: how would you design a fault-tolerant AWS architecture for a real business capability, including AI/ML and GenAI workloads, and how would you prove the design works?

### 2. Real Failure Anchor

Keep the October 2025 outage section, but make the lesson clearer:

> The lesson is not only that AWS services can fail. The lesson is that a hidden control-plane dependency, retry storm, backlog, or recovery bottleneck can break the business capability even when many infrastructure components remain healthy.

### 3. Add A New Section: Fault-Tolerant Architecture Design Actions

Insert the twelve design actions near the front, before choosing AWS patterns.

### 4. Use One Business Capability As The Running Example

Recommended capability:

> Customer support assistant for order and returns resolution.

This is useful because it crosses traditional and AI layers:

- user request
- API ingress
- orchestration
- order lookup tool
- SQS fallback queue
- DynamoDB state
- S3 knowledge base
- vector index
- Bedrock model
- guardrails
- human escalation
- CloudWatch evidence

### 5. Traverse The Capability End To End

Use this structure:

1. User sends request.
2. Edge and ingress absorb bad traffic and route only to healthy entry points.
3. Compute remains stateless and replaceable.
4. Dependency calls are protected by timeouts, retries, circuit breakers, and bulkheads.
5. Shock absorbers decouple slow downstream paths.
6. State is protected through idempotency, backups, PITR, and reconciliation.
7. AI path validates model, prompt, retrieval freshness, guardrails, and tool calls.
8. Observability proves both service recovery and trust recovery.
9. Runbooks define failover, replay, rollback, escalation, and failback.

### 6. Replace Generic Implementation Examples With Fault Scenarios

Each scenario should follow this format:

- Fault injected
- Failure risk
- Architecture control
- Expected behaviour
- Evidence captured

### 7. Evidence Scenarios

#### Scenario 1: Primary Model Failure

Fault injected: primary Bedrock model invocation fails, times out, or is throttled.

Failure risk: user journey fails or the application retries aggressively into a failing dependency.

Architecture control: Step Functions bounded retry, fallback model, degraded response marker, fallback alarm.

Expected behaviour: retry is attempted, fallback model handles the request, response is marked degraded, fallback count increments.

Evidence captured: Step Functions execution graph, CloudWatch logs, fallback metric, sample degraded response.

#### Scenario 2: Stale RAG Context

Fault injected: S3 source document is updated but vector index is not refreshed.

Failure risk: model returns a fluent answer from stale context.

Architecture control: retrieval freshness gate compares approved source version with index version before generation.

Expected behaviour: generation is blocked or degraded response is returned.

Evidence captured: S3 object version, DynamoDB index metadata, freshness-check log, stale retrieval metric.

#### Scenario 3: Agent Tool Failure

Fault injected: order lookup or refund tool times out repeatedly.

Failure risk: agent repeatedly calls a failing tool and creates a retry storm.

Architecture control: circuit breaker state in DynamoDB, SQS queue for replay, degraded response, alarm.

Expected behaviour: circuit opens, future calls fail fast, work is queued, user receives controlled response.

Evidence captured: DynamoDB circuit state, SQS queued message, CloudWatch alarm, logs showing no repeated tool calls.

#### Scenario 4: Guardrail Intervention

Fault injected: prompt violates safety or business-policy boundary.

Failure risk: unsafe, unauthorised, or non-compliant answer.

Architecture control: Bedrock Guardrails and safe response path.

Expected behaviour: unsafe path is blocked, audit event emitted, safe response returned.

Evidence captured: guardrail result, blocked category, CloudWatch log, blocked-count metric.

#### Scenario 5: Prompt Regression

Fault injected: new prompt version breaks answer quality or output format.

Failure risk: model endpoint is available but answers become untrustworthy.

Architecture control: prompt registry, validation check, rollback to previous prompt version.

Expected behaviour: quality check fails, rollback occurs, restored prompt passes validation.

Evidence captured: prompt registry before/after, failed validation, rollback log, restored output.

## Article Correction Summary

The article currently has strong concepts, but it should become more explicit about architecture action.

Change from:

> Here are resilience concepts and AWS services.

Change to:

> Here is how I design the business capability, identify faults, choose controls, validate degradation and recovery, and prove the architecture works.

The most important addition is the design-action section near the beginning. The second most important change is using one running business capability across the whole article, including the AI/ML and GenAI path.
