# Recovery-Storm Containment and Cell Isolation

This document explains the validated reference implementation and records exactly how its evidence should be incorporated into the article. Section headings, rather than PDF page numbers, are authoritative because pagination changes as the article is edited.

## 1. Implementation walkthrough

### Failure contract

The implementation starts with the required business behaviour:

> Accepted tenant work may queue during dependency impairment, but it must not be lost. Recovery traffic must not overwhelm the returning dependency, and a fault in one processing cell must not prevent healthy cells from completing their work.

The machine-readable contract is defined in `code/scenarios/recovery-and-isolation/failure-contract.json`.

### Deployed architecture

```text
                    TEST WORKLOAD
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
        CELL A SQS QUEUE         CELL B SQS QUEUE
        impaired lane            healthy lane
              │                       │
       max concurrency 5        max concurrency 5
              │                       │
              ▼                       ▼
        CELL A WORKER            CELL B WORKER
              │                       │
              ├───────────┬───────────┤
              │           │           │
              ▼           ▼           ▼
       CIRCUIT STATE   RATE COUNTER  OUTCOME TABLE
       DynamoDB        DynamoDB      DynamoDB
```

Each cell has:

- its own SQS queue;
- its own DLQ;
- its own Lambda event-source mapping;
- a maximum of five concurrent Lambda executions; and
- independent queue and worker telemetry.

The queues and concurrency boundaries are defined in `code/scenarios/recovery-and-isolation/infrastructure/template.yaml`.

### Stable cell assignment

The router assigns each tenant to a stable cell using a SHA-256 hash:

```python
digest = hashlib.sha256(tenant_id.encode("utf-8")).digest()
index = int.from_bytes(digest[:8], byteorder="big") % len(cells)
return cells[index]
```

Large or sensitive tenants can be explicitly assigned to dedicated cells.

The business ordering key is separate:

```python
return f"{tenant_id}#{business_entity_id}"
```

The separation is deliberate:

- cell assignment defines the blast-radius boundary;
- the ordering key defines which business events require ordered processing; and
- a random event UUID is not added to the ordering key because that would remove stable per-entity ordering.

The deployed routing logic is in `code/scenarios/recovery-and-isolation/src/routing.py`.

### Naive operating mode

In naive mode, the worker:

1. receives a message from SQS;
2. records a downstream attempt;
3. calls the dependency even while it is marked impaired;
4. reports the message as a partial batch failure; and
5. allows SQS to make the message available for another attempt.

This recreates the dangerous recovery sequence:

```text
Dependency impaired
    → calls continue
    → messages retry
    → attempts multiply
    → returning dependency receives accumulated pressure
```

### Protected operating mode

The protected worker evaluates controls in this order:

```python
running = cell_is_running()
if POLICY_MODE == "protected" and not running:
    emit("CircuitOpenRejected")
    return False

if POLICY_MODE == "protected" and not increment_with_limit(
    "admission", PROTECTED_RATE
):
    emit("AdmissionRejected")
    return False
```

The order is important:

1. **Circuit state:** is the dependency considered callable?
2. **Admission control:** is another call permitted by the rate contract?
3. **Downstream capacity:** can the dependency accept the operation?
4. **Outcome reservation:** has this business outcome already completed?

When the circuit is open, the message is retained for retry without making a downstream call. After recovery, admission control releases queued work at the configured rate while consumer concurrency remains bounded.

The deployed decision begins in `code/scenarios/recovery-and-isolation/src/aws_worker/handler.py` at `process_record`.

### Distributed rate limiting

A DynamoDB counter provides a distributed per-cell, per-second admission boundary. The key contains:

```text
Run ID + Cell ID + Counter Type + Epoch Second
```

A conditional update increments the counter only while it remains below the configured limit. This prevents independent Lambda execution environments from maintaining conflicting local token counts.

### Safe SQS retry

The worker uses SQS partial batch failure reporting:

```json
{
  "batchItemFailures": [
    {
      "itemIdentifier": "failed-message-id"
    }
  ]
}
```

Only records that did not complete are retried. Successfully processed records are removed rather than replaying the entire batch.

### Outcome protection

Successful operations are written using a conditional expression equivalent to:

```text
attribute_not_exists(message_id)
```

For this bounded experiment, the condition prevents an SQS retry from creating a second completed outcome. This is not the article's full exactly-once implementation. Ownership leases, canonical result caching, transactional outbox and abandoned-operation recovery belong to the next reference implementation.

### Fault sequence

The cloud runner:

1. clears previous outcomes from its own test stack;
2. sets cell A to `IMPAIRED`;
3. keeps cell B as `RUNNING`;
4. sends 300 messages to cell A;
5. sends 100 messages to cell B;
6. holds the impairment for 30 seconds;
7. restores cell A to `RUNNING`;
8. samples both queues during recovery;
9. counts committed outcomes;
10. collects CloudWatch metrics; and
11. evaluates the failure contract.

The runner is `code/scenarios/recovery-and-isolation/infrastructure/run-cloud-experiment.ps1`.

### Validated AWS results

Run ID: `20260719-g01`  
Region: `eu-west-2`

| Metric | Naive | Protected |
|---|---:|---:|
| Downstream attempts | 850 | 400 |
| Circuit-open rejections | 0 | 440 |
| Attempt amplification | 2.125x | 1.0x |
| Cell A peak attempts/minute | 300 | 160 |
| Completed outcomes | 400 | 400 |
| Healthy-cell outcomes | 100 | 100 |
| Recovery time | 63.746 s | 63.422 s |

Contract result: **PASS**

The significant result is not merely that both queues drained. The protected architecture:

- completed every accepted outcome;
- preserved the healthy cell;
- prevented 440 calls from reaching the impaired dependency;
- eliminated downstream attempt amplification;
- reduced peak recovery pressure; and
- did not extend recovery time in this bounded experiment.

### Defect found by the evidence gate

The first protected run applied admission control before checking the circuit state. It limited the call rate but still invoked the impaired dependency. The evidence contract failed because protected attempt amplification was not lower than the naive path.

The worker was corrected to evaluate circuit state before consuming an admission token or recording a downstream attempt. Both stacks were updated to the same code version and the complete comparison was rerun.

### Limitations

- The dependency impairment was injected through a DynamoDB control record.
- The experiment did not induce an outage of an AWS managed service.
- A production circuit breaker requires health-based transitions and stale-state handling.
- CloudWatch one-minute values do not expose sub-second burst shape.
- The account had a Regional Lambda concurrency quota of 10.
- Each cell was therefore capped at five concurrent SQS event-source executions.
- The results are not production capacity recommendations.
- The implementation did not validate AWS AppConfig propagation behaviour.

## 2. Article integration

The implementation supports two existing article sections:

1. **Dependency Protection: Timeouts, Retries, Circuit Breakers and Bulkheads**
2. **Failure Isolation and Blast-Radius Control**

Do not create a separate implementation chapter.

### A. Dependency Protection

#### Placement

Under **Architectural Pattern: Containing a Recovery Storm**, place the validated evidence after the architectural explanation of retry budgets, circuit breaking, admission control and gradual recovery.

Place it before **A. Timeout Budgets & Downstream Stratification**.

#### Remove

Remove the complete subsection **2. Deployed Implementations: Code Invariants**, including:

- Centralized Python Circuit Breaker Core;
- DynamoDB Idempotency Key Reservation Handler;
- Step Functions Asynchronous Retry & Fallback Configuration; and
- their Traceability paragraphs.

Keep the architectural explanations of timeouts, retries, circuit breakers and bulkheads.

#### Add this heading

##### Validated Reference Implementation: Recovery-Storm Containment

#### Add this introduction

> A controlled AWS experiment tested whether queued recovery traffic could be released without overwhelming a returning dependency. The implementation used two independently consumed SQS cells: cell A represented the impaired lane, while cell B represented an unaffected tenant boundary. Each cell had its own queue and a maximum of five concurrent Lambda event-source executions.
>
> The same workload was executed under two policies. The naive worker continued invoking the impaired dependency and relied on SQS retry. The protected worker checked a shared circuit state before invoking the dependency, applied distributed rate-limited admission after recovery and retained rejected messages for subsequent retry.

#### Add the results table

| Recovery signal | Naive | Protected |
|---|---:|---:|
| Downstream attempts | 850 | 400 |
| Circuit-open rejections | 0 | 440 |
| Attempt amplification | 2.125x | 1.0x |
| Impaired-cell peak attempts/minute | 300 | 160 |
| Completed outcomes | 400 | 400 |
| Healthy-cell outcomes | 100 | 100 |
| Recovery time | 63.746 seconds | 63.422 seconds |

#### Add this interpretation

> Both modes eventually completed all 400 accepted outcomes, including all 100 outcomes assigned to the healthy cell. However, the naive path made 850 downstream attempts for 400 outcomes. The protected path made 400 downstream attempts and rejected 440 calls at the open circuit before they reached the impaired dependency.
>
> In this bounded run, circuit-first admission removed downstream attempt amplification, reduced peak recovery pressure and preserved cell isolation without extending recovery time. The result demonstrates why dependency availability alone is not proof of capability recovery: the rate at which queued and retried work re-enters the dependency must also be controlled.

#### Code excerpt

Use only this simplified publication excerpt:

```python
running = cell_is_running()

if policy_mode == "protected" and not running:
    emit("CircuitOpenRejected")
    return RETRY_LATER

if policy_mode == "protected" and not admission.try_acquire(cell_id):
    emit("AdmissionRejected")
    return RETRY_LATER

return invoke_dependency(record)
```

Label it:

> Simplified excerpt; deployed implementation linked in the repository.

Do not include the complete handler, DynamoDB client construction, environment handling or the complete EMF metric envelope.

#### Add this limitation note

> The values are specific to the test configuration and are not production capacity targets. The experiment used a Regional Lambda concurrency quota of 10 and capped each cell at five concurrent SQS event-source executions. The dependency impairment was injected through a shared control record to make the experiment repeatable.

### B. Failure Isolation and Blast-Radius Control

#### Placement

Place a shorter evidence box after **C. Invariant Tenant Quotas and Polling Regulators** and before **Deployment Resilience and Safe Change**.

Do not repeat the complete recovery results table here.

#### Remove

Remove **2. Deployed Implementations: Code Invariants**, including:

- Compound Partition Key Generation and Shard Dispatcher;
- AWS AppConfig Tenant Polling Regulator; and
- their Traceability statements.

#### Add this heading

##### Validated Isolation Result: Healthy-Cell Continuity

#### Add this text

> The reference implementation assigned workloads to independent processing cells with separate SQS queues and independently capped Lambda consumers. During the cell-A impairment, cell B completed all 100 accepted outcomes without waiting for cell A to recover.
>
> The implementation uses stable tenant-to-cell assignment so the routing decision is repeatable. Exceptionally large or sensitive tenants can be assigned to dedicated cells. Business ordering is handled separately through an ordering key derived from the tenant and business entity.
>
> This creates a stronger boundary than hashing tenant identifiers into one shared Kinesis stream. Kinesis partition keys determine shard placement and ordering, but unrelated keys may still share a physical shard. Harder isolation requires separately controlled cells, consumer capacity and recovery state.

#### Routing excerpt

```python
def assign_cell(tenant_id, cells, dedicated_assignments):
    if tenant_id in dedicated_assignments:
        return dedicated_assignments[tenant_id]

    digest = sha256(tenant_id.encode("utf-8")).digest()
    return cells[int.from_bytes(digest[:8], "big") % len(cells)]
```

Add immediately below it:

> Cell assignment defines the containment boundary. The event partition key must still follow the required business ordering boundary; appending a random event identifier would improve distribution but remove stable per-entity ordering.

#### AppConfig qualification

Use:

> AWS AppConfig can be used as an operational mechanism for distributing lane-level pause or recovery-rate configuration. Its polling interval, cache behaviour and propagation delay must be tested separately. The validated experiment used a DynamoDB control record to provide deterministic circuit-state injection.

Do not claim that this implementation proved AppConfig propagation.

## 3. Recommended article visual

Add one diagram to the Dependency Protection section and reference it from Failure Isolation.

Suggested title:

> **Cell-Isolated Recovery with Circuit-First Admission Control**

```text
                         Workload
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
     Cell A: impaired lane       Cell B: healthy lane
          SQS queue                   SQS queue
              │                           │
     concurrency limit 5          concurrency limit 5
              │                           │
              ▼                           ▼
        Circuit check                Circuit check
              │                           │
        Admission limit              Admission limit
              │                           │
              └─────────────┬─────────────┘
                            ▼
                  Protected dependency
                            │
                            ▼
                  Idempotent outcome
```

Suggested callouts:

- Open circuit: retain for retry
- Admission denied: retain for retry
- Independent queue and concurrency boundary
- Conditional outcome write

## 4. Repository citation

After the repository is pushed, link the article to:

- the scenario README;
- the validated evidence report;
- the worker control path;
- tenant routing;
- the infrastructure template; and
- an immutable tagged release or commit.

Do not cite a moving branch as the evidence version. A suitable tag is:

```text
evidence/recovery-isolation-20260719-g01
```

