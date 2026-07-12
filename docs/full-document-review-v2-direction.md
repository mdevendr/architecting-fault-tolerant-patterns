# Full Document Review - V2 Direction

This note supersedes the earlier recommendation to use one running business architecture. The article should remain generic so it can cover multiple use cases, domains, and workload styles.

The new direction is:

```text
1. List fault-tolerant architecture gaps by domain.
2. For each domain, identify the fault positions.
3. For each fault, define the architecture pattern that addresses it.
4. Then create diagrams for each architecture pattern.
5. Then build evidence by injecting the relevant fault and proving the architecture behaviour.
```

Do not lead with Lab 01 Bedrock observability. Park it. Observability is supporting proof, not the architecture.

## Correct Evidence Shape

Evidence must show the architecture created for a fault.

Use this structure:

```text
Fault domain
-> fault injected
-> failure risk
-> architecture created
-> expected behaviour
-> evidence captured
```

Example:

```text
Domain: Data and integration resilience
Fault injected: downstream notification subscriber fails after primary write
Failure risk: customer transaction becomes coupled to email/fulfilment/analytics failure
Architecture created: DynamoDB commit + DynamoDB Streams CDC + SNS fan-out + subscriber DLQs
Expected behaviour: primary transaction succeeds; failed subscriber isolates; other subscribers continue
Evidence captured: API success, DynamoDB item, stream record, SNS publish, DLQ message, replay success
```

## Domain-By-Domain Fault-Tolerant Architecture Gaps

This should be the first major architecture section after the introduction and failure-contract discussion.

### 1. Edge, Routing, And Ingress

Current article coverage:

- Route 53
- CloudFront
- WAF
- API Gateway
- ALB
- health checks
- throttling

Gaps to add:

- API Gateway token-bucket throttling and per-client fairness
- WAF rate-based rules for request floods
- Route 53 failover routing and health-check limitations
- ARC zonal shift/autoshift as operational fail-away control
- CloudFront origin failover where applicable
- admission control before expensive compute or AI paths

Architecture patterns:

- edge request filtering
- rate limiting and quotas
- failover routing
- origin failover
- zonal evacuation

Evidence examples:

- request flood produces 429/WAF blocks while normal traffic continues
- unhealthy origin is bypassed
- zonal shift reduces traffic to impaired AZ

Outside comparison:

AWS API Gateway uses a token bucket algorithm for request throttling and supports account, stage, method, and usage-plan throttling targets.

### 2. Compute And Runtime Resilience

Current article coverage:

- stateless compute
- ECS/EKS/Lambda/Auto Scaling
- health checks
- graceful shutdown
- deployment rollback

Gaps to add:

- Lambda reserved concurrency as a bulkhead
- provisioned concurrency for static stability on critical paths
- ECS/EKS pod disruption budgets and topology spread constraints
- adaptive concurrency limiting based on latency/error signals
- brownout mode for non-critical features

Architecture patterns:

- replaceable stateless compute
- runtime bulkheads
- graceful termination
- adaptive admission control
- non-critical feature shedding

Evidence examples:

- dependency slowness triggers reduced concurrency
- critical function protected by reserved concurrency
- pod disruption does not violate minimum healthy capacity

### 3. Integration, Messaging, And Shock Absorbers

Current article coverage:

- SQS
- EventBridge
- SNS
- Kinesis
- DLQ
- replay
- backpressure

Gaps to add:

- queue-based load leveling as a named architecture
- EventBridge archive and replay
- SNS subscription DLQs
- FIFO queues where ordering matters
- mandatory idempotent consumers
- poison message quarantine and replay workflow
- schema evolution and event compatibility

Architecture patterns:

- queue-based load leveling
- pub/sub fan-out
- DLQ and replay
- event archive/replay
- idempotent consumers
- schema versioning

Evidence examples:

- downstream consumer fails while producer continues
- poison message moves to DLQ
- replay repairs missed processing

### 4. Data And State Resilience

Current article coverage:

- backups
- restore
- PITR
- idempotency
- Global Tables
- replication

Gaps to add:

- CDC/change data capture
- transactional outbox
- dual-write prevention
- write-ahead log tailing
- reconciliation and self-healing loops
- anti-entropy checks
- read-after-write consistency failsafes
- data corruption detection, not just backup existence

Architecture patterns:

- DynamoDB Streams CDC
- RDS/Aurora CDC with AWS DMS or WAL/binlog tailing
- transactional outbox
- reconciliation scanner
- repair events
- source-of-truth fallback reads

Evidence examples:

- downstream projection misses update and reconciliation repairs it
- outbox publisher fails after commit and later catches up
- read replica lag triggers source-of-truth read fallback

Outside comparison:

AWS Prescriptive Guidance describes the transactional outbox pattern as a way to avoid dual-write inconsistency when a service must update a database and notify other systems. It also calls out duplicate messages and ordering as issues that must be handled by consumers.

### 5. Dependency Protection

Current article coverage:

- timeouts
- retries with jitter
- circuit breakers
- bulkheads
- fallback

Gaps to add:

- adaptive concurrency limits
- per-dependency budgets
- dependency health scoring
- fallback queues for unavailable dependencies
- explicit fail-closed vs fail-open decisions

Architecture patterns:

- timeout envelope
- retry with jitter
- circuit breaker
- fallback queue
- dependency bulkhead
- degraded response

Evidence examples:

- downstream timeout opens circuit
- later requests fail fast
- work is queued
- downstream call count drops while user receives controlled response

### 6. Traffic And Load Management

Current article coverage:

- throttling
- rate limiting
- autoscaling
- backpressure

Gaps to add:

- adaptive concurrency limiting
- queue-based load leveling
- leaky bucket/token bucket rate limiting
- tenant-level fairness
- overload brownout mode

Architecture patterns:

- token bucket at API edge
- queue buffer between bursty producers and constrained consumers
- adaptive admission controller
- tenant quota guard

Evidence examples:

- burst traffic is throttled before saturating compute
- queue absorbs spike and drains within SLO
- tenant flood does not affect other tenants

### 7. Deployment, Configuration, And Change Safety

Current article coverage:

- rolling deployment
- blue/green
- canary
- rollback

Gaps to add:

- automated canary rollback
- AWS AppConfig configuration rollback
- feature flag circuit breakers
- schema migration safety
- backward-compatible event contracts
- prompt/config rollback for AI

Architecture patterns:

- canary with CloudWatch alarm rollback
- dynamic config deployment with automatic rollback
- feature flag kill switch
- contract-compatible releases

Evidence examples:

- bad canary increases error rate and rolls back
- bad feature flag trips alarm and reverts
- incompatible event schema is blocked before production

Outside comparison:

AWS CodeDeploy supports automatic rollback when deployments fail or configured monitoring thresholds are met. AWS AppConfig supports automatic rollback of configuration data using deployment strategies and CloudWatch alarms.

### 8. Multi-Tenant And Blast-Radius Isolation

Current article coverage:

- cell-based architecture
- shuffle sharding
- tenant failure domains

Gaps to add:

- multi-account isolation
- per-cell quotas and alarms
- tenant-level throttling
- tenant-specific queues
- noisy-neighbour containment
- cell evacuation process

Architecture patterns:

- cell-based architecture
- shuffle sharding
- tenant queue isolation
- per-tenant quota
- account boundary isolation

Evidence examples:

- one tenant floods workload and only its cell/shard degrades
- other tenants continue successfully
- cell alarm and evacuation runbook execute

Outside comparison:

The Amazon Builders' Library describes shuffle sharding as a way to reduce scope of impact in multi-tenant systems by assigning customers/resources to combinations of workers instead of sharing every worker with every customer.

### 9. Disaster Recovery And Regional Resilience

Current article coverage:

- backup and restore
- pilot light
- warm standby
- active-passive
- active-active
- failover/failback

Gaps to add:

- data-plane vs control-plane dependency during recovery
- pre-provisioned recovery capacity
- failback data consistency validation
- region evacuation runbook
- DR evidence per capability, not only per infrastructure stack

Architecture patterns:

- backup and restore
- pilot light
- warm standby
- active-passive
- active-active
- ARC routing control
- data-plane failover

Evidence examples:

- regional failover drill meets RTO/RPO
- backup restore validates data correctness
- failback reconciliation proves consistency

Outside comparison:

AWS Well-Architected REL13 recommends defining recovery objectives and choosing DR strategies such as backup/restore, standby, or active-active. It also warns against ad-hoc DR and dependency on control-plane operations during recovery.

### 10. Observability And Operational Evidence

Current article coverage:

- metrics
- logs
- traces
- alarms
- synthetic checks
- DLQ count
- model drift

Gaps to add:

- evidence pack per fault scenario
- business KPI alarms
- recovery progress dashboards
- reconciliation dashboards
- runbook execution evidence
- game-day evidence

Architecture patterns:

- service health dashboard
- business capability dashboard
- recovery dashboard
- evidence pack
- runbook-linked alarms

Evidence examples:

- alarm fires
- runbook executed
- degraded mode confirmed
- recovery validated
- post-test evidence stored

### 11. AI/ML And GenAI

Current article coverage:

- model fallback
- feature freshness
- vector staleness
- prompt versioning
- guardrails
- tool-call failure
- human escalation

Gaps to add:

- CDC-driven RAG and feature freshness
- semantic cache fallback
- multi-provider LLM fallback routing
- model quota protection
- prompt/config rollback through registry or AppConfig
- agent tool-call circuit breakers
- AI answer trust evidence, not only service health

Architecture patterns:

- RAG freshness gate
- embedding/index replay from CDC
- model fallback router
- semantic cache fallback
- guardrail safe refusal
- tool proxy circuit breaker
- human escalation

Evidence examples:

- stale vector index blocks generation
- primary model throttles and fallback route is used
- semantic cache serves safe answer when model unavailable
- tool failure opens circuit and queues work

## Additional Patterns To Add To Checklist

Add these to the previous pattern list:

```text
[ ] Anti-entropy / data reconciliation loops
[ ] Adaptive concurrency limiting
[ ] Queue-based load leveling
[ ] Token bucket / leaky bucket rate limiting
[ ] Automated canary rollback
[ ] Configuration / feature flag circuit breakers
[ ] Read-after-write consistency failsafes
[ ] Semantic cache fallback
[ ] Multi-provider LLM fallback routing
```

## Diagrams Needed - Revised Order

Do not start with CDC fan-out. First list all fault-tolerant architectural gaps by domain, then create diagrams for each area.

### Diagram 0: Fault-Tolerant Architecture Gap Map By Domain

Show:

```text
Domain -> common fault -> architecture control -> evidence type
```

Domains:

- Edge/routing/ingress
- Compute/runtime
- Integration/messaging
- Data/state
- Dependency protection
- Traffic/load management
- Deployment/configuration
- Multi-tenant isolation
- DR/regional resilience
- Observability/evidence
- AI/ML/GenAI

### Diagram 1: Generic End-To-End Fault-Tolerant Service Path

Show:

```text
User
-> edge/routing
-> ingress
-> stateless compute
-> dependency protection
-> integration/shock absorber
-> state
-> downstream consumers
-> AI/ML/GenAI extension
-> observability/evidence
```

### Diagram 2: CDC Fan-Out / Asynchronous Side-Effect Isolation

Generic form:

```text
API Gateway
-> command handler
-> source-of-truth store
-> CDC stream
-> event processor
-> fan-out topic/bus
-> independent subscribers
-> DLQs/replay
```

### Diagram 3: Transactional Outbox / Dual-Write Prevention

Generic form:

```text
service transaction
-> business table
-> outbox table
-> publisher
-> broker
-> consumers
```

### Diagram 4: Queue-Based Load Leveling

Generic form:

```text
bursty producer
-> queue buffer
-> controlled consumers
-> constrained downstream dependency
```

### Diagram 5: Dependency Circuit Breaker And Fallback Queue

Generic form:

```text
service
-> dependency proxy
-> circuit state
-> downstream dependency
-> fallback queue when open
```

### Diagram 6: Saga And Compensation

Generic form:

```text
workflow orchestrator
-> step A
-> step B
-> step C fails
-> compensate A/B
-> manual review or controlled failure
```

### Diagram 7: Deployment And Configuration Fault Tolerance

Generic form:

```text
canary/config rollout
-> metrics/alarm
-> automatic rollback
-> last known good version
```

### Diagram 8: Cell-Based / Shuffle-Sharded Isolation

Generic form:

```text
tenant/router
-> cell/shard A
-> cell/shard B
-> cell/shard C
```

### Diagram 9: AI/RAG Freshness And Replay

Generic form:

```text
source of truth
-> CDC/event
-> embedding/indexing pipeline
-> vector index
-> metadata/freshness table
-> freshness gate
-> model response or safe degradation
```

### Diagram 10: GenAI Agent Tool Circuit Breaker

Generic form:

```text
agent
-> tool proxy
-> circuit breaker
-> downstream tool
-> queue / human escalation / degraded response
```

## Evidence Set - Revised

Ignore the current Lab 01 for now. Define the proving set after the domain gaps and diagrams are accepted.

Evidence must be architecture-level. Suggested proving set:

1. CDC fan-out with failed subscriber and DLQ/replay.
2. Transactional outbox with publisher failure and catch-up.
3. Queue-based load leveling under spike.
4. Circuit breaker with fallback queue.
5. Saga compensation after mid-workflow failure.
6. Canary rollback after bad deployment.
7. AppConfig rollback after bad feature flag/config.
8. Cell/tenant throttling and isolation.
9. RAG freshness gate with stale index.
10. Agent tool circuit breaker.
11. Model/provider fallback routing.

For each evidence lab, document:

```text
Architecture created
Fault injected
Failure risk
Expected behaviour
Evidence captured
Recovery validation
Cleanup
```

## Immediate Corrections To Earlier Review

1. Do not use one running architecture as the article spine.
2. Do not make CDC the first diagram.
3. Do not lead with Bedrock observability.
4. Keep Lab 01 parked until the revised architecture list is approved.
5. First article addition should be the domain-by-domain fault-tolerant architecture gap map.

## Sources

- AWS API Gateway throttling: https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-request-throttling.html
- AWS AppConfig automatic rollback: https://docs.aws.amazon.com/appconfig/latest/userguide/monitoring-deployments.html
- AWS CodeDeploy rollback: https://docs.aws.amazon.com/codedeploy/latest/userguide/deployments-rollback-and-redeploy.html
- AWS Prescriptive Guidance - Transactional outbox: https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html
- AWS Lambda with DynamoDB Streams: https://docs.aws.amazon.com/lambda/latest/dg/with-ddb.html
- AWS Well-Architected REL13 DR strategies: https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_disaster_recovery.html
- AWS Builders' Library - Shuffle sharding: https://aws.amazon.com/builders-library/workload-isolation-using-shuffle-sharding/
