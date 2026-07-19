# Article Change Sheet 02: Exactly-Once Outcome and Reconciliation

Apply these changes by section heading. PDF page numbers are intentionally omitted because pagination changes after each edit.

## Change 1: Remove the unevidenced idempotency code

### Find

**Dependency Protection: Timeouts, Retries, Circuit Breakers and Bulkheads**

### Remove

- `B. DynamoDB Idempotency Key Reservation Handler`
- the complete Python code block under that heading;
- the associated `Traceability` paragraph; and
- any statement implying that `attribute_not_exists` alone demonstrates exactly-once processing.

### Retain

Retain the architectural explanation that retries of non-idempotent operations can duplicate payments, bookings, writes or agent tool effects.

### Replace with this cross-reference

> Safe retry requires more than initial key reservation. The complete ownership, lease recovery, canonical result and outbox pattern is demonstrated under **Exactly-Once Business Outcome**.

---

## Change 2: Add the validated reference implementation

### Find

Under **Protect State: Data Durability, Consistency and Trust Boundaries**, locate:

**Architectural Pattern: Exactly-Once Business Outcome**

### Placement

Insert the following material after the architectural explanation of operation ownership, lease expiry, canonical results and transactional outbox.

Place it before:

**Continuous Anti-Entropy Reconciliation Metrics**

### Add this heading

#### Validated Reference Implementation: One Outcome Under At-Least-Once Execution

### Add this text

> A controlled AWS experiment injected a crash after an external business effect succeeded but before workflow completion was recorded. The active ownership lease prevented another worker from taking over prematurely. After lease expiry, a new owner reclaimed the operation and invoked the provider with the same immutable operation key. The provider returned its original result rather than repeating the effect.
>
> The recovering worker atomically marked the operation complete, persisted the canonical result and created an outbox record through one DynamoDB transaction. DynamoDB Streams then delivered the outbox to an independently committed projection. A second injected crash occurred after the projection write but before delivery acknowledgement; stream replay detected the existing version and result and converged without creating another derived effect.
>
> The final state contained one provider effect, one completed operation, one outbox record and one matching projection. Repeating the original request returned the canonical completed result. The demonstrated property is an exactly-once business outcome under at-least-once execution—not exactly-once Lambda invocation or stream delivery.

### Add this evidence table

| Failure or control | Observed result |
|---|---|
| Crash after provider effect | Injected successfully |
| New owner before lease expiry | Rejected |
| New owner after lease expiry | Lease reclaimed |
| Provider invoked during recovery | Existing provider result reused |
| Provider business effects | 1 |
| Completed operations | 1 |
| Outbox records | 1 |
| Crash after projection commit | Injected successfully |
| Stream retry | Existing projection recognized; replay converged |
| Duplicate original request | Canonical completed result returned |
| Projection corruption | Mismatch detected |
| Reconciliation | Projection repaired |
| Final source/projection state | Version 1, matching result |

### Add this evidence note

> **Evidence scope:** Run `20260719-g02` was executed in `eu-west-2`. The provider was a DynamoDB-backed idempotent provider simulator, allowing every source, provider, outbox and projection state transition to be inspected independently.

---

## Change 3: Add short implementation excerpts

Use excerpts from the deployed implementation, not the earlier illustrative handler.

### Excerpt A: completed duplicate

```python
if item and item["status"]["S"] == "COMPLETE":
    emit("CanonicalResultReplayed")
    return {"result": item["result"]["S"], "replayed": True}
```

### Excerpt B: active lease and takeover boundary

```python
if lease_expires > now and current_owner != owner:
    raise ExecutionBusy(operation_key)

# Reclaim only when the operation remains in progress and
# the existing lease has expired.
```

### Excerpt C: atomic completion and outbox

Use a shortened excerpt of the `TransactWriteItems` call showing only:

```text
Transaction
├── Update operation: IN_PROGRESS → COMPLETE + canonical result
└── Put outbox record: PENDING + source version + payload
```

Do not paste the complete transaction request. Link to the implementation instead.

Add beneath the excerpts:

> Simplified excerpts from the deployed reference implementation; the complete transaction conditions and evidence runner are available in the repository.

---

## Change 4: Correct the anti-entropy section

### Find

**Continuous Anti-Entropy Reconciliation Metrics**

### Remove

```text
Delta Entropy = Hash(Source Ledger) - Hash(Derived Index)
```

Also remove language suggesting that cryptographic hashes can be meaningfully subtracted to quantify divergence.

### Replace with

> Reconciliation should report explicit divergence rather than subtracting cryptographic hashes. Useful measures include missing derived records, unexpected derived records, source/projection version mismatches, checksum or result mismatches, the age of the oldest unresolved divergence, repair throughput and remaining unreconciled records.

### Add this validated result

> In the reference implementation, the projection was deliberately changed to version 0 with a corrupted result while the authoritative operation remained at version 1. Reconciliation detected one mismatch, rebuilt the projection and restored a matching version-1 result.

---

## Change 5: Add limitations

Add immediately after the implementation evidence:

> The provider in this experiment is a DynamoDB-backed simulator. A real payment, booking or tool provider must accept and persist an idempotency key or expose a reconciliation mechanism. The bounded reconciler scans the operation table for evidence clarity; production reconciliation should be partitioned, checkpointed and capacity-aware. DynamoDB Streams delivery remains at least once and its retention period is not a substitute for long-term reconstruction history.

---

## Change 6: Add the visual

Suggested title:

> **One Business Outcome Across Ambiguous Completion and Replay**

Show:

```text
Provider effect committed
      │
      X  Crash before workflow completion
      │
Lease expiry → provider result replay → atomic completion + outbox
      │
Projection committed
      │
      X  Crash before delivery acknowledgement
      │
Stream replay → version check → converge
      │
Projection corruption → reconciliation → repaired state
```

The diagram must distinguish:

- the external effect boundary;
- the source/outbox transaction boundary;
- the independently committed projection; and
- the out-of-band reconciliation path.

---

## Change 7: Repository links

After the repository is pushed, link to:

- `code/scenarios/exactly-once-and-reconciliation/README.md`
- `code/scenarios/exactly-once-and-reconciliation/src/aws_handlers/handler.py`
- `code/scenarios/exactly-once-and-reconciliation/infrastructure/template.yaml`
- `code/scenarios/exactly-once-and-reconciliation/evidence/validated/20260719-g02/README.md`

Use an immutable tag or commit. Suggested tag:

```text
evidence/exactly-once-reconciliation-20260719-g02
```

---

## Final terminology check

Use:

> exactly-once business outcome under at-least-once execution

Do not use:

- exactly-once Lambda execution;
- exactly-once DynamoDB Streams delivery;
- exactly-once distributed processing; or
- guaranteed exactly-once external side effects without a provider idempotency or reconciliation contract.

