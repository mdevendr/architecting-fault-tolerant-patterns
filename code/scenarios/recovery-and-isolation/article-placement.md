# Article placement: recovery and isolation

This file is authoritative by section heading; PDF page numbers are navigation aids only and will change as the article is edited.

## Remove before implementation evidence is published

### Dependency Protection: Timeouts, Retries, Circuit Breakers and Bulkheads

Remove the entire subsection beginning `2. Deployed Implementations: Code Invariants`, including:

- `A. Centralized Python Circuit Breaker Core`;
- `B. DynamoDB Idempotency Key Reservation Handler`;
- `3. Step Functions Asynchronous Retry & Fallback Configuration`; and
- each associated `Traceability` paragraph.

Retain the architectural discussion of timeout budgets, bounded retries, circuit breaking, bulkheads and safe retry requirements.

### Failure Isolation and Blast-Radius Control

Remove the entire subsection beginning `2. Deployed Implementations: Code Invariants`, including:

- `A. Compound Partition Key Generation and Shard Dispatcher`;
- `B. AWS AppConfig Tenant Polling Regulator`; and
- each associated `Traceability` paragraph.

Retain the architectural discussion after correcting claims about Kinesis shard isolation, ordering boundaries, EKS controls and AppConfig propagation.

## Validated insertion after AWS evidence pass `20260719-g01`

### Architectural Pattern: Containing a Recovery Storm

Insert after the architectural explanation of recovery traffic shaping:

> **Reference implementation - containing a recovery storm.** A controlled AWS experiment placed 300 messages in an impaired processing cell while a separate healthy cell processed 100 messages. Both cells used independent SQS queues and event-source concurrency boundaries. The naive worker continued invoking the impaired dependency; the protected worker checked a shared circuit state before applying rate-limited admission and retained rejected work for retry.
>
> Both modes eventually completed all 400 accepted outcomes, including all 100 healthy-cell outcomes. The protected path reduced downstream attempts from 850 to 400 and attempt amplification from 2.125x to 1.0x. It rejected 440 calls at the open circuit and reduced the impaired cell's peak from 300 to 160 attempts per minute. Recovery time remained comparable: 63.746 seconds for the naive path and 63.422 seconds for the protected path.
>
> The values are specific to the bounded test configuration and are not production capacity targets. The experiment used a Regional Lambda concurrency quota of 10, with each cell capped at five concurrent SQS event-source executions.

Add the validated results table from `evidence/validated/20260719-g01/README.md`.

Use a short excerpt from `src/aws_worker/handler.py` beginning with the `running = cell_is_running()` decision and ending after the protected admission decision. Do not reproduce the complete handler.

### Failure Isolation and Blast-Radius Control

Insert after the cell/lane isolation explanation:

> The reference implementation assigns tenants to stable processing cells with separate SQS queues and independently capped consumers. During the cell-A impairment, cell B completed all 100 accepted outcomes. The result demonstrates isolation for this workload and quota configuration; it does not imply that hashing partition keys within one shared Kinesis stream creates a hard tenant boundary.

Use the stable assignment excerpt from `src/routing.py`. If Kinesis is discussed, retain the ordering-boundary qualification: do not append a random event UUID where per-entity ordering is required.

Add the architecture diagram and healthy-cell outcome result. Do not claim AppConfig propagation evidence: this implementation uses a DynamoDB control record for deterministic circuit-state injection. AppConfig remains an architectural option requiring a separate propagation test.

## Do not source from this scenario

- Exactly-once idempotency implementation evidence belongs to the state-protection scenario.
- Bedrock semantic fallback evidence belongs to the RAG and agent trust scenario.
