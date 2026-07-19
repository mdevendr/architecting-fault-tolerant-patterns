# Article Change Sheet 01: Recovery-Storm Containment and Cell Isolation

Apply these changes by section heading; do not use PDF page numbers.

## Change 1: Remove unevidenced dependency-protection code

### Find

**Dependency Protection: Timeouts, Retries, Circuit Breakers and Bulkheads**

### Remove

Remove the subsection **Deployed Implementations: Code Invariants**, including:

- Centralized Python Circuit Breaker Core;
- DynamoDB Idempotency Key Reservation Handler;
- Step Functions Asynchronous Retry & Fallback Configuration; and
- their associated `Traceability` paragraphs.

### Retain

Retain the architectural explanation of timeout budgets, bounded retries, circuit breakers, bulkheads and retry safety.

The complete idempotency and model-fallback evidence belongs to change sheets 02 and 06 respectively.

## Change 2: Add the recovery-storm implementation

### Find

**Architectural Pattern: Containing a Recovery Storm**

### Placement

Insert after the explanation of retry budgets, circuit breaking, admission control and gradual recovery. Place it before **Timeout Budgets & Downstream Stratification**.

### Add this heading

#### Validated Reference Implementation: Circuit-First Recovery Admission

### Add this text

> A controlled AWS experiment tested whether accumulated work could be released without overwhelming a returning dependency. The implementation used two independently consumed SQS cells. Cell A represented an impaired processing lane and received 300 messages; cell B remained healthy and received 100 messages. Each cell had its own queue and a maximum of five concurrent Lambda event-source executions.
>
> The same workload was executed under two policies. The naive worker continued calling the impaired dependency and relied on SQS retry. The protected worker checked shared circuit state before invoking the dependency, applied distributed rate-limited admission after recovery and retained rejected messages for a later attempt.
>
> Both policies completed all 400 accepted outcomes, including every healthy-cell outcome. The naive path made 850 downstream attempts for 400 outcomes. The protected path made 400 attempts, rejected 440 calls at the open circuit and reduced attempt amplification from 2.125x to 1.0x. Peak impaired-cell pressure fell from 300 to 160 attempts per minute without extending recovery time in this bounded run.

## Change 3: Add the recovery evidence table

| Recovery signal | Naive | Protected |
|---|---:|---:|
| Downstream attempts | 850 | 400 |
| Circuit-open rejections | 0 | 440 |
| Attempt amplification | 2.125x | 1.0x |
| Impaired-cell peak attempts/minute | 300 | 160 |
| Completed outcomes | 400 | 400 |
| Healthy-cell outcomes | 100 | 100 |
| Recovery time | 63.746 seconds | 63.422 seconds |

Add below the table:

> **Evidence scope:** Run `20260719-g01` executed in `eu-west-2`. The Regional Lambda concurrency quota was 10, so each cell was capped at five concurrent SQS event-source executions. These values demonstrate the control under the test configuration; they are not production capacity recommendations.

## Change 4: Replace the circuit-breaker code with a deployed excerpt

Use only this shortened excerpt:

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

Add:

> Simplified excerpt from the deployed worker; the complete handler, distributed admission counter and evidence runner are available in the repository.

Do not reproduce client construction, environment configuration or the complete metric envelope.

## Change 5: Explain the defect found by validation

Add after the implementation excerpt:

> The first protected run applied admission control before checking circuit state. It limited call rate but still invoked the dependency during impairment, so the evidence contract failed. Reordering the controls to check the circuit before consuming admission capacity eliminated outage-period dependency calls. This demonstrates why control ordering is part of the failure contract, not an implementation detail.

## Change 6: Replace unevidenced isolation code

### Find

**Failure Isolation and Blast-Radius Control**

### Remove

Remove the subsection **Deployed Implementations: Code Invariants**, including:

- Compound Partition Key Generation and Shard Dispatcher;
- AWS AppConfig Tenant Polling Regulator; and
- their associated `Traceability` paragraphs.

Retain the architectural discussion of cells, tenant quotas, polling regulation and blast-radius boundaries.

### Placement

Add the following after **Invariant Tenant Quotas and Polling Regulators** and before **Deployment Resilience and Safe Change**.

### Add this heading

#### Validated Isolation Result: Healthy-Cell Continuity

### Add this text

> The reference implementation assigned workloads to independent processing cells with separate SQS queues and independently capped Lambda consumers. During the cell-A impairment, cell B completed all 100 accepted outcomes without waiting for cell A to recover.
>
> Stable tenant-to-cell assignment makes routing repeatable, while exceptionally large or sensitive tenants can be assigned to dedicated cells. Business ordering remains a separate decision based on the tenant and business entity. This creates a stronger boundary than hashing tenants into one shared Kinesis stream: partition keys influence shard placement and ordering, but unrelated keys can still share a physical shard.

## Change 7: Add the stable-routing excerpt

```python
def assign_cell(tenant_id, cells, dedicated_assignments):
    if tenant_id in dedicated_assignments:
        return dedicated_assignments[tenant_id]

    digest = sha256(tenant_id.encode("utf-8")).digest()
    return cells[int.from_bytes(digest[:8], "big") % len(cells)]
```

Add below it:

> Cell assignment defines the containment boundary. The event partition key must still follow the required business-ordering boundary; appending a random event identifier would remove stable per-entity ordering.

## Change 8: Qualify the AppConfig statement

Use:

> AWS AppConfig can distribute lane-level pause and recovery-rate configuration. Its polling interval, cache behaviour and propagation delay must be tested separately. The validated experiment used a DynamoDB control record to provide deterministic circuit-state injection and does not claim to prove AppConfig propagation.

## Change 9: Add limitations

> The experiment used an application fault-injection record rather than inducing failure of an AWS managed service. SQS queue attributes are approximate, CloudWatch one-minute values do not expose sub-second burst shape, and the Lambda concurrency quota constrained the test. A production circuit breaker also requires health-based transitions, transition ownership and stale-state handling.

## Change 10: Add the visual

Suggested title:

> **Cell-Isolated Recovery with Circuit-First Admission**

```text
                         Workload
                            |
                 +----------+----------+
                 |                     |
                 v                     v
          Cell A queue            Cell B queue
          impaired lane           healthy lane
                 |                     |
          bounded consumer        bounded consumer
                 |                     |
          circuit check           circuit check
                 |                     |
          admission limit         admission limit
                 +----------+----------+
                            |
                            v
                    protected dependency
                            |
                            v
                    conditional outcome
```

Label the retry decisions:

- circuit open: retain work for retry;
- admission denied: retain work for retry; and
- completed outcome: remove the SQS message.

## Change 11: Repository links

After push, link to:

- `code/scenarios/recovery-and-isolation/README.md`
- `code/scenarios/recovery-and-isolation/src/aws_worker/handler.py`
- `code/scenarios/recovery-and-isolation/src/routing.py`
- `code/scenarios/recovery-and-isolation/infrastructure/template.yaml`
- `code/scenarios/recovery-and-isolation/evidence/validated/20260719-g01/README.md`

Use an immutable tag or commit. Suggested tag:

```text
evidence/recovery-isolation-20260719-g01
```

