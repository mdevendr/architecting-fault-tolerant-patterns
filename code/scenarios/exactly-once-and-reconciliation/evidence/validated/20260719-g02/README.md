# Validated AWS evidence: 20260719-g02

## Scope

- Region: `eu-west-2`
- Execution environment: AWS
- Business operation: `20260719-g02-payment-1`
- Authoritative operation store: DynamoDB
- External provider-effect simulator: DynamoDB with provider idempotency key
- Outbox: DynamoDB transactionally committed with operation completion
- Delivery: DynamoDB Streams to Lambda projector
- Derived projection: independent DynamoDB table
- Repair: explicit reconciliation Lambda

## Failure sequence and results

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
| Final operation version | 1 |
| Final projection version | 1 |
| Final source/projection comparison | Match |

Contract result: **PASS**

## What the run demonstrates

- At-least-once execution did not create a second provider effect.
- An active ownership lease prevented concurrent takeover.
- An expired lease allowed abandoned work to be reclaimed.
- The external provider boundary used the business operation key as its idempotency key and returned its original result during recovery.
- Operation completion and outbox creation shared one DynamoDB transaction.
- The derived projection committed independently from outbox acknowledgement.
- A crash after projection commit caused stream replay, but version/result comparison suppressed a duplicate projection effect.
- A repeated original request returned the stored canonical result.
- Reconciliation detected and repaired an intentionally corrupted derived record.

## Important interpretation

The implementation does not claim end-to-end exactly-once execution. Lambda invocation and DynamoDB Streams delivery remain at least once. The demonstrated property is one business outcome for one immutable operation identity, achieved through ownership leases, provider idempotency, atomic source/outbox commit, idempotent projection and reconciliation.

## Limitations

- The external provider is a DynamoDB-backed simulator, not a real payment or booking provider.
- A real provider must accept and persist an idempotency key or expose a reconciliation mechanism.
- The scenario uses one operation to make every state transition independently inspectable; load and contention tests are separate concerns.
- The reconciler uses a table scan for the bounded experiment. Production reconciliation should be partitioned, checkpointed and capacity-aware.
- DynamoDB Streams retention bounds replay time; long-lived reconstruction requires another durable history or source snapshot.
- The projection repair overwrites derived state from the authoritative completed operation. Domain-specific conflict rules may require human review instead.

