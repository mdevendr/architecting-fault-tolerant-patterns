# Implementation Evidence Backlog

## Purpose

Replace illustrative, syntax-only code in *Architecting AWS Fault-Tolerant Architecture* with reproducible implementation evidence. Each implementation must answer four questions:

1. What failure was injected?
2. What architectural control changed the outcome?
3. What evidence demonstrates safe recovery?
4. What limitation or trade-off remains?

Routine Availability Zone failover is intentionally excluded. The implementations below focus on recovery behaviour, state correctness, and AI trust under impairment.

## Executive recommendation

Build these three evidence packages first:

1. **Recovery-storm containment** — demonstrates static stability and unimodal recovery when a dependency returns after an outage.
2. **RAG trust recovery** — demonstrates that an available GenAI endpoint can still be operationally failed because its context is stale, unauthorised, or inconsistent with policy.
3. **Exactly-once business outcome under at-least-once execution** — demonstrates safe replay after a crash between an external side effect and workflow acknowledgement.

Together, these are more distinctive than infrastructure failover and map directly to the article's central argument: technical execution can recover before correctness and trust recover.

---

## Review of the current code sections

| PDF pages | Current example | Verdict | Required action |
|---|---|---|---|
| 28–30 | In-process Python circuit breaker | Replace | It is local to one process, catches every exception, uses a simple consecutive-failure counter, and does not protect half-open probes across concurrent workers. Replace it with the recovery-storm experiment and show the combined effect of bounded retries, jitter, admission control, and controlled recovery concurrency. |
| 30 | DynamoDB idempotency-key reservation | Replace | Reserving `IN_PROGRESS` is only the first transition. The example lacks an ownership token, in-progress lease expiry, completed-result caching, recovery of abandoned work, and coupling to the business side effect. Replace it with the exactly-once outcome experiment. |
| 31 | Step Functions retry and Bedrock fallback | Replace | The example proves state-machine syntax, not safe fallback. It does not distinguish transient faults from invalid requests or policy failures, and does not demonstrate that fallback output meets the same quality and safety contract. Use a deployed workflow with fault classification and evaluation evidence. |
| 49–50 | Timestamp-based RAG freshness gate and model fallback | Replace | The age of the oldest retrieved chunk is not a reliable index-freshness proof. The gate needs source version, indexed version, ingestion status, tenant authorisation, and provenance. A different model cannot repair stale context. Replace with the RAG trust-recovery experiment. |
| 52–53 | Agent tool execution and SQS human escalation | Replace | Sending a task token in a normal SQS task does not by itself implement a callback/resume contract. The workflow also lacks a demonstrated idempotent tool boundary and compensation outcome. Replace with an AgentCore policy and compensating-recovery implementation, or implement the Step Functions callback pattern fully. |
| 64–68 | SQS/DLQ, circuit breaker, idempotency, and Step Functions appendix examples | Remove | These repeat earlier sections and remain generic. Retain concise architectural explanations, but link to the repository evidence packages instead of repeating code. |

### Specific corrections to make while editing

- Do not describe a local circuit-breaker instance as isolating a distributed failure domain completely.
- Do not claim that `attribute_not_exists` alone guarantees exactly-once processing; it only conditionally reserves a key.
- Classify retryable and non-retryable errors explicitly. Do not route every `States.ALL` failure to another model.
- Treat cross-Region inference and semantic model fallback as different controls: the former addresses capacity and regional routing; the latter changes model behaviour and must be separately evaluated.
- Replace `Hash(Source Ledger) - Hash(Derived Index)` with measurable reconciliation results: missing records, extra records, version mismatches, oldest divergence age, and repair rate. Hashes are comparable, but subtraction does not define useful “entropy.”
- Prefer deployed source files and captured test results over large code blocks in the article.

---

## P0 — Implementation 1: Recovery-Storm Containment

### Architectural question

Can the system recover from a dependency blackout without entering a second, more destructive operating mode when queued work and synchronized retries are released?

### Proposed system

- An SQS queue holds business work.
- Lambda consumers or ECS workers call a constrained downstream dependency backed by DynamoDB or Aurora.
- Two selectable policies are implemented:
  - **Naive recovery:** per-request retries and unrestricted consumer recovery.
  - **Controlled recovery:** retry budget, exponential backoff with full jitter, token-bucket admission control, and queue-depth/downstream-health-based concurrency.
- AWS AppConfig can hold the lane-level recovery policy and ramp rate.

### Failure injection

1. Block or fault the downstream operation for a fixed period while producers continue.
2. Accumulate a known backlog.
3. Restore the dependency and release workers simultaneously.
4. Run once with the naive policy and once with controlled recovery.

Use an explicit application fault-injection seam or a tightly scoped AWS Fault Injection Service experiment. Do not depend on causing a real managed-service outage.

### Recovery evidence

- Queue age and backlog drain curve.
- Retry volume as a percentage of total attempts.
- Downstream throttles, connection usage, and rejected requests.
- Worker concurrency and token consumption.
- End-to-end p95/p99 latency.
- Time to restore the business SLO.
- Evidence that controlled recovery does not exceed a declared downstream protection threshold.

### Article value

This turns static stability and bimodal behaviour into a visible experiment. It proves that “the dependency became healthy” is not equivalent to “the capability recovered.”

### Repository evidence

- Infrastructure as code.
- Load generator and fault-controller commands.
- Naive and controlled policy configurations.
- CloudWatch dashboard definition.
- Two test-run result folders with timestamps and run manifests.
- A short findings document comparing outcomes and limitations.

---

## P0 — Implementation 2: RAG Trust Recovery

### Architectural question

Can a GenAI capability refuse an unsafe answer when its API and model are available but its retrieval context is stale, unauthorised, or inconsistent with an approved policy?

### Proposed system

- Versioned documents in Amazon S3 are the authoritative source.
- Amazon Bedrock Knowledge Bases retrieves content, using Amazon S3 Vectors where the selected Region and workload fit.
- An ingestion ledger records source version, expected index version, ingestion execution, completion state, tenant, and policy version.
- The request gateway enforces:
  - source-to-index version freshness;
  - tenant and document authorisation;
  - citation/provenance requirements;
  - a safe non-answer when the trust contract is not satisfied.
- Amazon Bedrock Guardrails Automated Reasoning checks validate answers against an explicit domain policy for a bounded, rule-heavy use case.

### Failure injection

1. Publish a new source-document version but deliberately delay or fail ingestion.
2. Query for a fact changed by the new version.
3. Attempt cross-tenant retrieval using misleading metadata.
4. Introduce a document statement that conflicts with the approved policy.
5. Complete ingestion and repeat the request.

### Recovery evidence

- Source version versus indexed version and measured ingestion lag.
- Safe-answer rejection reason before recovery.
- Authorisation-filter rejection count.
- Retrieved document IDs and versions.
- Automated Reasoning findings and policy version.
- Successful, cited response only after the freshness and policy gates pass.
- Time from technical recovery to trust recovery.

### Why it stands out

The experiment proves the article's distinction between service recovery and trust recovery. It also uses newer AWS capabilities in a way that matters architecturally rather than adding them as a feature list.

### Limitations to state

- Automated Reasoning checks are best suited to explicit, formalizable policies; they are not a universal hallucination detector.
- Strong vector-store consistency does not prove that an upstream ingestion workflow has indexed the latest authoritative source version.
- A fallback model does not correct stale or unauthorised retrieval context.

---

## P0 — Implementation 3: Exactly-Once Business Outcome Under At-Least-Once Execution

### Architectural question

Can a workflow survive a crash after an external side effect without charging, booking, notifying, or modifying the business record twice when execution is retried?

### Proposed system

- Implement the same bounded business workflow with AWS Lambda durable functions, or compare it with AWS Step Functions if time permits.
- Use an immutable business idempotency key derived from the operation identity—not a random retry identifier.
- Store `IN_PROGRESS`, ownership/lease information, `COMPLETE`, and the canonical result in DynamoDB.
- Couple internal state changes to a transactional outbox where possible.
- Put genuinely external side effects behind an idempotent adapter and reconciliation process.

### Failure injection

1. Crash immediately before the side effect.
2. Crash immediately after the side effect but before checkpoint/acknowledgement.
3. Deliver the same event concurrently.
4. Replay the event after the in-progress lease expires.
5. Make compensation fail once before succeeding.

### Recovery evidence

- One and only one committed business effect.
- Duplicate requests return the canonical completed result.
- Workflow history shows checkpoint/resume or state-machine recovery.
- Abandoned `IN_PROGRESS` records are safely reclaimed through ownership and lease rules.
- Outbox and destination reconciliation reach equality.
- Compensation is itself idempotent and leaves an auditable terminal state.

### New AWS angle

Lambda durable functions provide code-first, checkpointed execution for long-running Lambda workflows. The article should demonstrate their boundaries as well as their benefits: step logic remains at-least-once, qualified versions/aliases matter for replay consistency, and event-source idempotency still needs an explicit design.

---

## P1 — Implementation 4: Governed Agent Tool Execution and Compensation

### Architectural question

Can an agent resume after partial completion without repeating tool side effects, and can policy prevent a technically valid but unauthorised action?

### Proposed system

- Amazon Bedrock AgentCore Policy for deterministic tool authorization.
- AgentCore Evaluations for repeatable quality and policy tests.
- A durable workflow state record containing plan version, tool-call identity, status, result, and compensation status.
- Human approval through a real callback contract for high-impact actions.

### Failure injection and evidence

- Attempt an action beyond the caller's authority: policy denies it before tool execution.
- Time out after the tool commits but before the agent receives the response: replay returns the original tool result.
- Fail a later step: compensation executes once and the workflow enters an auditable terminal state.
- Record policy decision, tool-call identity, evaluation result, workflow history, and business-state reconciliation.

### Caution

Do not imply that agent memory is a transaction coordinator. Persist business workflow state independently and use memory only for the context it is designed to retain.

---

## P1 — Implementation 5: Source-to-Derived-State Reconciliation

### Architectural question

Can an asynchronously maintained projection recover after missed, duplicated, delayed, or poison change events without corrupting the source of truth?

### Proposed system

- DynamoDB source table and DynamoDB Streams.
- EventBridge Pipes routes changes to a projection consumer.
- The projection stores source record version and last-applied event identity.
- A partitioned reconciliation job detects missing, extra, and version-mismatched records and performs controlled repairs.
- EventBridge enhanced logging supplies delivery-stage evidence to CloudWatch Logs or S3.

### Failure injection

1. Pause or disable the projection path.
2. Inject a poison event and partial-batch failure.
3. Deliver duplicate/out-of-order test events where the integration permits.
4. Resume processing and run reconciliation.

### Recovery evidence

- Missing, extra, and version-mismatch counts by partition.
- Age of oldest unresolved divergence.
- Replay and repair throughput.
- Duplicate events ignored through version/idempotency rules.
- Source remains unchanged by projection repair.
- Final reconciled state and an immutable run manifest.

### AWS-specific caveats to test and document

- DynamoDB Streams have finite retention.
- Creating or updating a pipe is eventually consistent.
- Starting from `LATEST` can miss events during creation; test whether `TRIM_HORIZON` fits the scenario.
- Partial-batch failure handling must be configured and verified, not merely described.

---

## P2 — Optional Implementation 6: Capacity Routing Versus Semantic Model Fallback

Demonstrate that Bedrock cross-Region inference profiles and application-level model fallback solve different failure contracts.

- Use an inference profile for capacity/Region routing where residency and supported-Region constraints allow it.
- Use a test seam to inject 429 and 503 responses deterministically.
- Fall back to a different model only for classified transient failures.
- Run an evaluation set against primary and fallback models before permitting the fallback path.
- Mark responses as degraded when the fallback has a narrower capability or different quality contract.
- Capture latency, throttling, fallback count, evaluation score, token cost, and residency constraints.

This should follow the first three implementations because reliable injection of genuine Bedrock capacity impairment is not under application control.

---

## Recent AWS capabilities worth featuring

Use new services only where they strengthen a failure contract and can be demonstrated with evidence.

| Capability | Architectural use | Important boundary |
|---|---|---|
| Lambda durable functions | Code-first, checkpointed long-running workflows and deterministic resume | Steps remain at-least-once; idempotency and version pinning remain architectural responsibilities. |
| Bedrock Guardrails Automated Reasoning checks | Validate bounded responses against explicit domain policies | Not a general truth or hallucination detector; policy quality and ambiguity still matter. |
| Bedrock AgentCore Policy and Evaluations | Deterministic agent tool authorization plus repeatable quality assessment | Policy prevents unauthorized execution; it does not make side effects transactional. |
| Amazon S3 Vectors with Bedrock Knowledge Bases | Cost-oriented vector storage and retrieval with strong consistency | Vector-store consistency does not establish end-to-end source-to-index freshness. |
| EventBridge enhanced logging | Delivery-stage evidence for event-driven recovery and replay | Logging improves diagnosis and evidence; it is not a delivery or correctness guarantee. |
| Bedrock cross-Region inference profiles | Route requests across supported Regions to improve throughput and availability | It is not semantic model fallback, and geography/residency constraints must be checked. |

---

## Work sequence when development starts

### Phase 1 — Decide and bound

- [ ] Select one P0 implementation for the first repository evidence package. Recommended: **Recovery-Storm Containment**.
- [ ] Define the business capability and failure contract in one paragraph.
- [ ] Set measurable pass/fail thresholds before writing infrastructure code.
- [ ] Select the AWS Region after confirming feature availability.
- [ ] Agree a budget ceiling and teardown policy.
- [ ] Select infrastructure as code: CDK, SAM, or Terraform. Use one consistently.

### Phase 2 — Build the evidence harness first

- [ ] Create a run manifest format: run ID, Git commit, Region, configuration, timestamps, and expected result.
- [ ] Implement deterministic failure-injection controls.
- [ ] Define CloudWatch metrics, logs, traces, and dashboard before the happy path.
- [ ] Add an automated pass/fail evaluator for the declared recovery contract.
- [ ] Add teardown and cost-verification commands.

### Phase 3 — Implement and compare

- [ ] Deploy the baseline/naive path.
- [ ] Execute the failure scenario and preserve its evidence.
- [ ] Deploy the architectural control.
- [ ] Repeat under the same workload and fault profile.
- [ ] Compare recovery curves, business-state correctness, and remaining limitations.

### Phase 4 — Integrate into the article

- [ ] Replace generic code blocks with short, relevant excerpts from the deployed implementation.
- [ ] Link each excerpt to the exact repository file and commit/tag.
- [ ] Add a compact diagram showing failure injection, control, and evidence path.
- [ ] Add one chart or table comparing baseline and controlled outcomes.
- [ ] State costs, quotas, Region support, and what the experiment does **not** prove.
- [ ] Remove duplicated appendix snippets on pages 64–68.

---

## Suggested repository structure

```text
code/
  recovery-storm-containment/
    infrastructure/
    src/
    fault-injection/
    load-test/
    dashboards/
    tests/
    evidence/
      README.md
      run-manifest.schema.json
    README.md
  rag-trust-recovery/
    infrastructure/
    src/
    policies/
    evaluation/
    fault-injection/
    dashboards/
    evidence/
    README.md
  exactly-once-outcome/
    infrastructure/
    src/
    fault-injection/
    reconciliation/
    dashboards/
    evidence/
    README.md
architecture/
  implementation-evidence/
```

Do not commit live credentials, generated dependency folders, raw customer data, or unreviewed model prompts containing sensitive information. Evidence folders should contain sanitized metrics, run manifests, screenshots, and result summaries—not secrets or full production logs.

---

## Official sources reviewed

- [AWS Lambda durable functions and Step Functions](https://docs.aws.amazon.com/lambda/latest/dg/durable-step-functions.html)
- [Invoking Lambda durable functions](https://docs.aws.amazon.com/lambda/latest/dg/durable-invoking.html)
- [Lambda durable functions best practices](https://docs.aws.amazon.com/lambda/latest/dg/durable-best-practices.html)
- [Idempotency for Lambda durable executions](https://docs.aws.amazon.com/lambda/latest/dg/durable-execution-idempotency.html)
- [Automated Reasoning checks in Amazon Bedrock Guardrails](https://aws.amazon.com/about-aws/whats-new/2025/08/automated-reasoning-checks-amazon-bedrock-guardrails/)
- [Automated policy refinement for Automated Reasoning checks](https://aws.amazon.com/about-aws/whats-new/2026/06/amazon-bedrock-guardrails/)
- [AgentCore Policy and AgentCore Evaluations](https://aws.amazon.com/blogs/aws/amazon-bedrock-agentcore-adds-quality-evaluations-and-policy-controls-for-deploying-trusted-ai-agents/)
- [Amazon S3 Vectors preview announcement](https://aws.amazon.com/about-aws/whats-new/2025/07/amazon-s3-vectors-preview-native-support-storing-querying-vectors/)
- [S3 Vectors and Bedrock Knowledge Bases example](https://aws.amazon.com/blogs/storage/optimize-agent-tool-selection-using-s3-vectors-and-bedrock-knowledge-bases/)
- [EventBridge enhanced logging](https://aws.amazon.com/about-aws/whats-new/2025/07/amazon-eventbridge-enhanced-logging-improved-observability/)
- [EventBridge Pipes with DynamoDB Streams](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-pipes-dynamodb.html)
- [Bedrock cross-Region inference](https://docs.aws.amazon.com/bedrock/latest/userguide/cross-region-inference.html)
- [DynamoDB distributed locking best practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/BestPractices_DistributedLocking.html)

## Recommended first decision

Start with **Recovery-Storm Containment**. It is distinctive, directly supports the static-stability and bimodal-behaviour argument, is deterministic to test, produces strong visual evidence, and avoids claiming that a simulated Availability Zone failure proves application correctness.
