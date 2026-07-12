# Full Review - Architecting AWS Fault-Tolerant Architecture

Review target:

Article draft PDF for "Architecting AWS Fault-Tolerant Architecture"

Review date: 2026-07-11

## Executive Verdict

The article has strong architectural ingredients: failure contracts, failure domains, Multi-AZ limits, dependency protection, shock absorbers, state protection, AI/ML and GenAI trust recovery, observability, DR, governance, and cost trade-offs.

However, it does not yet fully answer the central question:

> How would you design a fault-tolerant architecture on AWS?

The article currently reads more like a broad resilience framework than an end-to-end design method. It needs to become more explicit about the design sequence:

```text
Business capability
-> failure contract
-> primary service path
-> fault positions
-> failure behaviour
-> resilience controls
-> recovery/degraded path
-> operational evidence
```

The strongest next move is to use one running business capability and traverse it end to end. Recommended capability:

```text
Customer order placement and support/returns assistant
```

This lets the article cover both traditional application fault tolerance and AI/ML/GenAI fault tolerance in one coherent architecture.

## Current Fault-Tolerant Architectures Already Listed

The PDF currently covers or mentions these patterns:

1. Failure contracts and business capability framing.
2. Failure domains across AZ, Region, VPC, service, queue, database, model, tenant, and dependency.
3. Edge protection and routing with Route 53, CloudFront, WAF.
4. Ingress controls with API Gateway and ALB.
5. Multi-AZ placement.
6. Stateless compute and replaceable capacity with ECS, EKS, Lambda, EC2 Auto Scaling.
7. Health checks, readiness checks, liveness checks.
8. Autoscaling and graceful shutdown.
9. Rolling, blue/green, and canary deployment.
10. Timeouts.
11. Retries with jitter.
12. Circuit breakers.
13. Bulkheads.
14. SQS, EventBridge, SNS, Kinesis as shock absorbers.
15. DLQs and replay.
16. Idempotency.
17. Backups, restore, PITR.
18. Multi-AZ database design.
19. DynamoDB Global Tables.
20. Aurora/RDS style state recovery concepts.
21. Disaster recovery strategies: backup/restore, pilot light, warm standby, active-passive, active-active.
22. Zonal shift, shuffle sharding, cell-based isolation.
23. Observability with logs, metrics, traces, alarms, synthetic checks, DLQ count, queue depth.
24. Governance: SoR/NFR, ADR, HLD, LLD, runbooks, playbooks, game days, PIRs.
25. AI/ML model fallback.
26. Feature freshness.
27. Model registry and model rollback.
28. Vector index staleness.
29. Prompt versioning.
30. Guardrails.
31. Human escalation.
32. GenAI tool-call failure.

## Important Missing Or Underdeveloped Architectures

### 1. CDC / Change Data Capture

Status: missing.

Why it matters:

CDC is a core architectural decoupling mechanism. It protects the primary transaction path from downstream side effects. For example:

```text
API Gateway -> Order Lambda -> DynamoDB Orders
                       |
                       v
              DynamoDB Streams
                       |
                       v
              Operations Lambda
                       |
                       v
                    SNS fan-out
             /          |          \
        Email      Fulfilment     AI indexing
```

Architectural value:

- Commit the business transaction first.
- Decouple notifications, fulfilment, analytics, search, and AI indexing.
- Support retry, replay, and projection rebuilds.
- Avoid synchronous fan-out from the request path.

Outside comparison:

AWS Prescriptive Guidance describes the transactional outbox pattern as a way to avoid dual-write inconsistency when a service must both update a database and notify other systems. It highlights failure modes where the database update succeeds but the event notification fails, or notification is sent while the database transaction rolls back. It also calls out duplicate messages and ordering as issues to handle with idempotent consumers and ordered processing.

Document change:

Add CDC under the integration/state protection section and use it as one of the main diagrams.

### 2. Transactional Outbox

Status: missing.

Why it matters:

CDC from DynamoDB Streams is excellent when DynamoDB is the system of record. For relational stores or service-owned databases, the transactional outbox pattern is often the correct way to make state change and event publishing reliable.

Architecture:

```text
Service transaction
-> write business row
-> write outbox row in same transaction
-> outbox poller/CDC publisher
-> EventBridge/SNS/SQS/Kinesis
-> consumers
```

Document change:

Add as a pattern alongside CDC:

> Use CDC when the data store emits a reliable stream. Use transactional outbox when the application must atomically persist state and publish an integration event.

### 3. Saga / Process Manager

Status: not sufficiently covered.

Why it matters:

Fault tolerance is not only keeping infrastructure up. Multi-step business processes need compensation and recovery.

Architecture:

```text
Step Functions
-> Reserve inventory
-> Authorise payment
-> Create order
-> Notify fulfilment
-> Catch/compensate on failure
```

Outside comparison:

AWS Step Functions supports explicit retry and catch behaviour for workflow errors. That makes it suitable for modelling business recovery paths rather than hiding them in code.

Document change:

Add a section: "Workflow Fault Tolerance and Compensation".

### 4. Backpressure, Load Shedding, and Admission Control

Status: partially implied but not explicit enough.

Why it matters:

Fault-tolerant architecture must decide when not to accept more work. Retry storms and overload are common failure amplifiers.

Architecture:

```text
API Gateway throttling
-> WAF rate limiting
-> reserved Lambda concurrency
-> SQS buffer
-> consumer autoscaling
-> shed non-critical work
```

Document change:

Add this under dependency protection and shock absorbers.

### 5. Consumer Idempotency and Poison Message Isolation

Status: mentioned, but not architecturally shown.

Why it matters:

Every asynchronous architecture needs idempotent consumers, deduplication, DLQ routing, replay, and reconciliation.

Document change:

Show it in the CDC fan-out diagram and evidence lab.

### 6. Event Archive and Replay

Status: underdeveloped.

Why it matters:

Replay is how you rebuild downstream projections after consumer failure, data corruption, or new consumer onboarding.

Outside comparison:

Amazon EventBridge supports archiving events and replaying them later. This is a clean AWS-native pattern for operational recovery of event-driven systems.

Document change:

Add "archive and replay" as a separate recovery control, not only DLQ replay.

### 7. Data Plane vs Control Plane Recovery

Status: mentioned through the outage, but not converted into design action.

Why it matters:

AWS Well-Architected warns against dependency on control-plane operations during recovery. Fault-tolerant designs should rely on data-plane operations where possible during incidents.

Document change:

Add a design rule:

> Pre-provision recovery paths and avoid requiring new infrastructure, IAM, DNS, or control-plane changes during impairment where the failure contract requires rapid recovery.

### 8. Static Stability

Status: mentioned, not deeply implemented.

Why it matters:

Static stability means the workload can continue during dependency/control-plane impairment without needing immediate control-plane changes.

Document change:

Show examples:

- pre-provisioned capacity
- multi-AZ NAT and VPC endpoints
- pre-created failover resources
- provisioned concurrency for critical Lambda paths
- pre-warmed standby region for lower RTO

### 9. Cell-Based Architecture

Status: mentioned but not shown as an architecture.

Why it matters:

Cells contain blast radius by partitioning tenants, customers, or workloads into isolated stacks.

Document change:

Add a diagram:

```text
Route by tenant/customer
-> Cell A API/compute/state/queue
-> Cell B API/compute/state/queue
-> Cell C API/compute/state/queue
```

### 10. Shuffle Sharding

Status: mentioned but not actionable.

Outside comparison:

The Amazon Builders' Library explains shuffle sharding as a way to reduce scope of impact in multi-tenant systems. Instead of every customer sharing every worker, customers are assigned to combinations of workers so that one noisy or harmful workload does not affect the whole service.

Document change:

Add when it applies:

- multi-tenant queue workers
- tenant-specific consumers
- AI inference worker pools
- embedding pipelines
- API request routing for high-volume tenants

### 11. Multi-Account Blast Radius

Status: missing.

Why it matters:

Account boundaries are fault and security isolation boundaries.

Document change:

Add:

- production vs non-production accounts
- shared services account
- logging/security account
- workload account per domain/cell
- SCPs and least privilege

### 12. Quota and Capacity Faults

Status: underdeveloped.

Why it matters:

AWS service quotas, Bedrock model quotas, Lambda concurrency, API Gateway throttling, DynamoDB WCU/RCU, Kinesis shard limits, and NAT/ENI limits are common failure positions.

Document change:

Add quota exhaustion as a first-class fault position.

### 13. Schema Evolution and Contract Compatibility

Status: missing.

Why it matters:

Asynchronous systems fail when producers and consumers disagree on event schema.

Document change:

Add:

- versioned event schemas
- backward-compatible consumers
- contract testing
- schema registry where appropriate
- canary consumers

### 14. AI/ML CDC For RAG and Feature Freshness

Status: partially covered as freshness, but missing CDC mechanism.

Why it matters:

RAG and feature stores are derived state. Derived state must be rebuilt, replayed, and freshness-gated.

Architecture:

```text
Source of record
-> CDC stream
-> embedding/indexing pipeline
-> vector index
-> metadata table with source_version and indexed_at
-> freshness gate before generation
```

Document change:

Add CDC as the bridge between traditional fault tolerance and AI trust recovery.

### 15. AI Tool-Call Containment

Status: mentioned, but needs diagram and evidence.

Why it matters:

Agents can amplify downstream faults by repeatedly calling tools.

Architecture:

```text
Agent orchestrator
-> tool proxy Lambda
-> circuit state in DynamoDB
-> downstream tool
-> SQS fallback queue when circuit is open
```

## Changes Needed To The Document

### Change 1: Reframe The Article Promise

Current feel:

> A broad tour of AWS resilience concepts.

Needed:

> A practical method for designing a fault-tolerant AWS architecture for a business capability, including traditional, AI/ML, and GenAI paths.

Suggested opening insertion:

```markdown
This article answers a practical architecture question: how would you design a fault-tolerant AWS architecture for a real business capability, and how would you prove that it behaves correctly when faults occur?
```

### Change 2: Add A Design Actions Section Near The Front

Add before selecting AWS patterns:

1. Identify the business capability.
2. Define the failure contract.
3. Map the primary service path.
4. Identify fault positions.
5. Classify failure behaviour.
6. Bound the failure domain.
7. Select resilience controls.
8. Protect state and correctness.
9. Design degradation and fallback.
10. Design recovery and failback.
11. Instrument evidence.
12. Validate through controlled fault injection.

### Change 3: Use A Running Business Capability

Recommended running example:

```text
Order placement and customer support assistant
```

This supports:

- synchronous order write path
- CDC/event fan-out
- downstream email/fulfilment/analytics
- AI/RAG indexing pipeline
- agent tool calls
- guardrails and fallback

### Change 4: Convert Service Lists Into Fault Scenarios

For every major architecture pattern, use:

```text
Fault injected
Failure risk
Architecture control
Expected behaviour
Evidence captured
```

### Change 5: Move Observability After Architecture

Observability is evidence, not the architecture itself. It should prove the behaviour of the fault-tolerant pattern.

### Change 6: Add CDC and Outbox As First-Class Patterns

These are central to decoupling synchronous commits from downstream side effects.

### Change 7: Expand AI Architecture Around Derived State

AI fault tolerance should include:

- feature freshness
- vector freshness
- embedding pipeline replay
- source document versioning
- prompt rollback
- guardrails
- model fallback
- tool-call circuit breakers
- human escalation

## Architectural Patterns To Add

1. CDC with DynamoDB Streams.
2. Transactional outbox.
3. Event archive and replay.
4. Saga orchestration with compensation.
5. Backpressure and load shedding.
6. Idempotent consumers.
7. Poison message isolation.
8. Schema evolution and event contracts.
9. Data plane recovery and static stability.
10. Cell-based architecture.
11. Shuffle sharding for tenant/workload isolation.
12. Multi-account blast-radius isolation.
13. Quota and capacity protection.
14. AI/RAG freshness gate from CDC.
15. Agent tool-call circuit breaker.
16. Prompt deployment rollback.
17. Human escalation as safe degradation.

## Diagrams Needed

### Diagram 1: End-To-End Business Capability Fault-Tolerant Architecture

Purpose:

Show the whole capability, not just services.

Flow:

```text
User
-> CloudFront/WAF/Route 53
-> API Gateway
-> Order Lambda
-> DynamoDB Orders
-> DynamoDB Streams
-> Operations Lambda
-> SNS fan-out
-> Email / Fulfilment / Analytics / AI indexing
```

Include labels:

- synchronous business commit path
- asynchronous CDC recovery path
- downstream side effects
- DLQ/replay
- observability/evidence

### Diagram 2: CDC Fan-Out Fault-Tolerant Order Placement

Purpose:

Show that downstream failure does not break order placement.

Faults:

- email subscriber fails
- fulfilment subscriber slow
- AI indexing pipeline unavailable

Controls:

- DynamoDB durable commit
- stream retry
- SNS fan-out
- subscriber DLQ
- idempotent consumers

### Diagram 3: Transactional Outbox For Relational Workloads

Purpose:

Show how to avoid dual-write inconsistency.

Flow:

```text
Order service
-> Aurora transaction
   -> orders row
   -> outbox row
-> outbox publisher
-> EventBridge/SQS/SNS
```

### Diagram 4: Dependency Protection

Purpose:

Show timeouts, retries with jitter, circuit breaker, and fallback queue.

Flow:

```text
Service
-> dependency proxy
-> circuit state
-> downstream dependency
-> SQS fallback when open
```

### Diagram 5: Step Functions Saga And Compensation

Purpose:

Show multi-step recovery.

Flow:

```text
Create order
-> reserve inventory
-> authorise payment
-> create fulfilment request
-> catch failure
-> compensate / cancel / refund / notify
```

### Diagram 6: AI/RAG Freshness Architecture

Purpose:

Show AI trust recovery, not just model availability.

Flow:

```text
Source document / product policy / order state
-> CDC
-> embedding pipeline
-> vector index
-> metadata table
-> freshness gate
-> Bedrock response
```

### Diagram 7: GenAI Agent Tool Circuit Breaker

Purpose:

Show containment of agent tool failure.

Flow:

```text
Agent
-> tool proxy
-> circuit breaker
-> downstream tool
-> SQS replay queue
-> degraded response / human escalation
```

### Diagram 8: Cell-Based Isolation

Purpose:

Show blast-radius containment.

Flow:

```text
Tenant router
-> Cell A stack
-> Cell B stack
-> Cell C stack
```

### Diagram 9: DR Pattern Decision Diagram

Purpose:

Show RTO/RPO-driven pattern choice.

Options:

- backup and restore
- pilot light
- warm standby
- active-passive
- active-active

### Diagram 10: Evidence Map

Purpose:

Show how every architecture control is proven.

Columns:

- fault
- expected behaviour
- evidence
- recovery proof

## Evidencing Plan - Fault-Tolerant Architectures

Do not lead with "Bedrock invocation observability." It is useful supporting evidence, but it is not a fault-tolerant architecture.

Instead, implement these labs.

### Lab A: Fault-Tolerant Order Placement With CDC Fan-Out

Architecture:

```text
API Gateway -> Order Lambda -> DynamoDB Orders
DynamoDB Streams -> Operations Lambda -> SNS Topic
SNS -> Email Lambda
SNS -> Fulfilment Lambda
SNS -> Analytics Lambda
SNS -> AI Indexing Lambda
Subscriber failures -> DLQ
```

Fault injected:

Email subscriber fails after order is placed.

Expected behaviour:

- API still returns success.
- order is stored in DynamoDB.
- DynamoDB stream record exists.
- operations processor publishes to SNS.
- email path fails into DLQ.
- fulfilment/analytics subscribers continue.

Evidence:

- successful API response
- DynamoDB order item
- CloudWatch logs for stream processing
- SNS delivery attempt
- DLQ message
- replay succeeds after fixing subscriber

Why this is strong:

It proves primary business commit is decoupled from downstream failure.

### Lab B: Transactional Outbox

Architecture:

```text
Order service -> Aurora/RDS or SQLite local simulation for article code
transaction writes order + outbox event
publisher reads outbox
publisher sends to EventBridge/SQS
consumer processes event
```

Fault injected:

Publisher fails after transaction commits.

Expected behaviour:

- order remains committed
- outbox event remains pending
- publisher resumes and publishes later
- consumer processes once

Evidence:

- order row
- pending outbox row
- publisher retry log
- event delivered
- outbox marked published

### Lab C: Dependency Circuit Breaker With Queue Fallback

Architecture:

```text
API/Lambda -> dependency proxy -> downstream service
                           |
                           v
                    DynamoDB circuit state
                           |
                           v
                    SQS fallback queue
```

Fault injected:

Downstream service returns errors or times out.

Expected behaviour:

- first failures are attempted
- circuit opens
- later calls fail fast
- work is queued
- user receives degraded response

Evidence:

- circuit state CLOSED -> OPEN
- no repeated downstream calls while open
- SQS message
- CloudWatch alarm
- recovery half-open success

### Lab D: Step Functions Saga Failure And Compensation

Architecture:

```text
Step Functions order workflow
-> reserve inventory
-> authorise payment
-> create fulfilment
-> catch failure
-> compensate payment/inventory
```

Fault injected:

Fulfilment creation fails after payment authorisation.

Expected behaviour:

- failure caught
- compensation runs
- final workflow state is controlled failure or manual review

Evidence:

- Step Functions graph
- payment compensation log
- final state
- audit record

### Lab E: RAG Freshness From CDC

Architecture:

```text
S3 source docs or DynamoDB policy table
-> CDC/EventBridge
-> embedding/indexing Lambda
-> vector metadata table
-> freshness gate
-> Bedrock
```

Fault injected:

Indexing Lambda disabled while source changes.

Expected behaviour:

- source update succeeds
- indexing lag detected
- assistant refuses to answer as current
- after recovery, index catches up

Evidence:

- source version
- index version
- stale response
- indexing retry/catch-up logs
- freshness gate passes after recovery

### Lab F: Model Failure And Fallback

Architecture:

```text
API -> Step Functions
-> primary Bedrock model
-> retry
-> fallback model
-> degraded response
-> metric/alarm
```

Fault injected:

Primary model path forced to fail.

Expected behaviour:

- retry bounded
- fallback model invoked
- response marked degraded
- alarm/metric emitted

Evidence:

- Step Functions graph
- logs
- fallback metric
- sample degraded response

### Lab G: Guardrail Intervention

Architecture:

```text
Prompt -> Guardrail -> Model -> Guardrail -> Response
```

Fault injected:

Unsafe or unauthorised prompt.

Expected behaviour:

- blocked
- safe response returned
- audit event emitted

Evidence:

- guardrail result
- blocked category
- application log
- blocked-count metric

## Compare With External/AWS Practice

### AWS Well-Architected Reliability Pillar

How AWS does it:

- Define recovery objectives before choosing DR strategy.
- Use backup/restore, pilot light, warm standby, or active-active based on RTO/RPO.
- Avoid ad-hoc recovery.
- Avoid relying on control-plane operations during recovery.
- Test recovery implementation.

Gap in article:

The article mentions these concepts but should make them design actions and evidence requirements.

### AWS Builders' Library - Shuffle Sharding

How AWS does it:

- Reduces scope of impact in multi-tenant systems.
- Assigns customers/resources to combinations of workers.
- Prevents one customer's problem from impacting the whole fleet.

Gap in article:

Shuffle sharding is named but not shown as an architecture.

### AWS Prescriptive Guidance - Transactional Outbox

How AWS does it:

- Solves dual-write inconsistency.
- Ensures database update and event notification are reliable.
- Requires duplicate handling and ordering consideration.

Gap in article:

CDC and outbox are missing, yet they are central to fault-tolerant decoupling.

### AWS Lambda With DynamoDB Streams

How AWS does it:

- DynamoDB Streams can trigger Lambda when table records change.
- This is the natural AWS-native CDC path for DynamoDB-backed business transactions.

Gap in article:

Article uses SQS/EventBridge/SNS broadly, but misses DynamoDB Streams as a business-state CDC mechanism.

### EventBridge Archive And Replay

How AWS does it:

- Archives events so they can be replayed later.
- Useful for rebuilding projections and recovering consumers.

Gap in article:

Replay is mentioned but not enough as a first-class recovery architecture.

### Step Functions Error Handling

How AWS does it:

- Retry and Catch define explicit workflow recovery paths.
- This supports sagas, compensation, and model fallback.

Gap in article:

Step Functions should be elevated from an example to a core workflow fault-tolerance architecture.

### Bedrock Guardrails

How AWS does it:

- Guardrails provide configurable safeguards for generative AI applications.

Gap in article:

Guardrails are mentioned, but should be tied to a fault scenario: unsafe prompt -> block -> audit -> safe response.

## Recommended Article Structure

1. Introduction: fault tolerance as business behaviour under impairment.
2. Real failure anchor: October 2025 outage and design lessons.
3. Fault-tolerant architecture design actions.
4. Running business capability: order placement and support assistant.
5. End-to-end service path.
6. Fault positions and failure behaviours.
7. Pattern 1: synchronous commit with asynchronous CDC fan-out.
8. Pattern 2: dependency protection and circuit breakers.
9. Pattern 3: shock absorbers, DLQ, replay, idempotent consumers.
10. Pattern 4: workflow sagas and compensation.
11. Pattern 5: state protection, backup, restore, PITR, reconciliation.
12. Pattern 6: Multi-AZ, static stability, data-plane recovery.
13. Pattern 7: cell-based and shuffle-sharded isolation.
14. Pattern 8: DR strategy by RTO/RPO.
15. AI/ML and GenAI extension: model, retrieval, prompt, guardrail, tool-call, human escalation.
16. Evidence: fault injection labs and what each proves.
17. Governance and operational readiness.
18. Cost/complexity trade-offs.
19. Conclusion.

## Immediate Actions

1. Add CDC/outbox section to the article.
2. Add the design actions section near the beginning.
3. Add the running order-placement/support-assistant capability.
4. Replace generic implementation examples with fault-scenario evidence.
5. Create the CDC fan-out diagram first.
6. Rework the repo labs so Lab 01 is the CDC order placement architecture, not Bedrock invocation observability.
7. Keep Bedrock invocation observability as supporting material under AI evidence, not as the first architecture lab.

## Sources

- AWS Well-Architected Reliability Pillar: https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html
- REL13-BP02 Use defined recovery strategies: https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_disaster_recovery.html
- AWS Builders' Library - Workload isolation using shuffle-sharding: https://aws.amazon.com/builders-library/workload-isolation-using-shuffle-sharding/
- AWS Prescriptive Guidance - Transactional outbox pattern: https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html
- AWS Lambda with DynamoDB Streams: https://docs.aws.amazon.com/lambda/latest/dg/with-ddb.html
- Amazon EventBridge archive and replay: https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-archive.html
- AWS Step Functions error handling: https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html
- Amazon Bedrock Guardrails: https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html
