# Exactly-Once Business Outcome and Derived-State Reconciliation

This document explains the validated implementation and provides publication-ready article integration instructions.

## 1. Architectural objective

The objective is not to make distributed execution exactly once. The objective is:

> For one immutable business operation identity, commit one business effect, return one canonical result and converge all derived state despite crashes, duplicate delivery and replay.

The implementation separates five controls:

1. operation ownership and lease expiry;
2. idempotency at the external effect boundary;
3. canonical result persistence;
4. atomic operation completion and outbox creation; and
5. idempotent projection plus reconciliation.

## 2. Deployed architecture

```text
Request / replay
      │
      ▼
Worker Lambda
      │
      ├── acquire operation owner + lease ──► Operations table
      │
      ├── invoke with operation key ────────► Provider-effect table
      │
      └── DynamoDB transaction
             ├── operation = COMPLETE + canonical result
             └── outbox record = PENDING
                           │
                           ▼
                    DynamoDB Streams
                           │
                           ▼
                    Projector Lambda
                           │
                           ▼
                    Derived projection
                           │
                           ▼
                       Reconciler
```

## 3. Failure sequence

### Step 1: acquire ownership

The first worker creates an `IN_PROGRESS` operation with:

- immutable operation key;
- execution owner;
- lease expiry;
- status; and
- source version.

A different owner is rejected while the lease is active. After expiry, a new owner may conditionally reclaim the operation.

### Step 2: commit the external effect

The provider simulator uses the same business operation key as its idempotency key. The first call commits an approved result. A repeated call returns the original result rather than creating another provider effect.

### Step 3: inject ambiguous completion

The first worker crashes after the provider effect succeeds but before the operation is marked complete. At this point:

- the provider effect exists;
- the operation remains `IN_PROGRESS`;
- no outbox record exists; and
- the caller cannot know whether the external effect occurred.

### Step 4: recover through lease and provider idempotency

A second owner is rejected before lease expiry. After expiry, it reclaims the operation and invokes the provider with the same operation key. The provider returns the previously committed result.

The worker then uses one DynamoDB transaction to:

- change the operation from `IN_PROGRESS` to `COMPLETE`;
- persist the canonical provider result; and
- create the outbox record.

### Step 5: inject delivery ambiguity

The DynamoDB Stream invokes the projector. The projector commits the derived record and then crashes before acknowledging delivery.

On stream retry, the projector finds the same source version and result already present. It suppresses a duplicate projection effect and marks the outbox delivered.

### Step 6: replay the original request

A third owner repeats the original request. Because the operation is complete, the worker returns the stored canonical result without invoking the provider again.

### Step 7: corrupt and reconcile derived state

The experiment deliberately changes the projection result and version. The reconciler compares authoritative completed operations with derived records, detects the mismatch and rebuilds the projection from the source.

## 4. Validated AWS evidence

Run ID: `20260719-g02`  
Region: `eu-west-2`

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

Contract result: **PASS**

## 5. What to remove from the article

Under **Dependency Protection: Timeouts, Retries, Circuit Breakers and Bulkheads**, remove the unevidenced DynamoDB key-reservation handler and its Traceability paragraph.

The handler only demonstrated initial reservation. It did not demonstrate:

- operation ownership;
- lease expiry;
- safe takeover;
- canonical result return;
- external effect idempotency;
- atomic completion and outbox creation; or
- reconciliation.

## 6. What and where to add

### Placement 1: Exactly-Once Business Outcome

Under **Protect State: Data Durability, Consistency and Trust Boundaries**, place this evidence immediately after **Architectural Pattern: Exactly-Once Business Outcome** and before **Continuous Anti-Entropy Reconciliation Metrics**.

Suggested heading:

#### Validated Reference Implementation: One Outcome Under At-Least-Once Execution

Suggested article text:

> A controlled AWS experiment injected a crash after an external business effect succeeded but before workflow completion was recorded. The active ownership lease prevented another worker from taking over prematurely. After lease expiry, a new owner reclaimed the operation and invoked the provider with the same immutable operation key. The provider returned its original result rather than repeating the effect.
>
> The recovering worker atomically marked the operation complete, persisted the canonical result and created an outbox record through one DynamoDB transaction. DynamoDB Streams then delivered the outbox to an independently committed projection. A second injected crash occurred after the projection write but before delivery acknowledgement; stream replay detected the existing version and result and converged without creating another derived effect.
>
> The final state contained one provider effect, one completed operation, one outbox record and one matching projection. Repeating the original request returned the canonical completed result. The demonstrated property is an exactly-once business outcome under at-least-once execution—not exactly-once Lambda invocation or stream delivery.

Add the validated failure-sequence table.

Recommended code excerpts:

1. active lease rejection and expired lease takeover;
2. the DynamoDB transaction joining operation completion and outbox creation; and
3. canonical result return for a duplicate completed operation.

Keep the excerpts short and link to the immutable repository version.

### Placement 2: Continuous Anti-Entropy Reconciliation Metrics

Replace:

```text
Delta Entropy = Hash(Source Ledger) - Hash(Derived Index)
```

with:

> Reconciliation should report explicit divergence rather than subtracting cryptographic hashes. Useful measures include missing records, unexpected records, source/projection version mismatches, checksum or result mismatches, the age of the oldest unresolved divergence, repair throughput and remaining unreconciled records.

Then add:

> In the reference implementation, the projection was deliberately changed to version 0 with a corrupted result while the authoritative operation remained at version 1. Reconciliation detected one mismatch, rebuilt the projection and restored a matching version-1 result.

## 7. Recommended visual

Suggested title:

> **One Business Outcome Across Ambiguous Completion and Replay**

Show two explicit uncertainty windows:

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
```

## 8. Limitations to retain

- The provider is a DynamoDB-backed simulator.
- A real provider must support an idempotency key or reconciliation API.
- The reconciler uses a bounded table scan for evidence clarity.
- Production reconciliation must be partitioned and checkpointed.
- DynamoDB Streams retention is not a long-term reconstruction history.
- Domain conflicts may require escalation rather than automatic overwrite.

## 9. Repository citation

After push, cite an immutable release or commit. Suggested tag:

```text
evidence/exactly-once-reconciliation-20260719-g02
```

