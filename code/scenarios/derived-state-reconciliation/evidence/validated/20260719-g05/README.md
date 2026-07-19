# Validated AWS evidence: 20260719-g05

## Scope

- Region: `eu-west-2`
- Source of truth: DynamoDB table with `NEW_AND_OLD_IMAGES` stream
- Delivery: EventBridge Pipes, starting at `TRIM_HORIZON`
- Projection: version-aware Lambda consumer and independent DynamoDB table
- Poison isolation: encrypted SQS quarantine queue
- Recovery: explicit anti-entropy reconciliation Lambda
- Delivery evidence: EventBridge Pipes TRACE logs with execution data

## Results

| Fault or control | Observed result |
|---|---|
| Duplicate version-2 event | Suppressed |
| Late version-1 event after version 2 | Suppressed |
| Projection after replay | Remained at version 2 |
| Poison event | Quarantined; projection not advanced |
| Intentionally missed records | 2 detected |
| Unexpected projection records | 1 detected |
| Version/value mismatches | 1 detected |
| Total repairs | 4 |
| Final missing records | 0 |
| Final extra records | 0 |
| Final mismatches | 0 |
| Source modified by repair | No |

Contract result: **PASS**

## Architectural finding

At-least-once delivery and a version-aware consumer prevented duplicate and stale events from regressing the projection. They did not prove completeness. Independent reconciliation was still required to detect records deliberately skipped or quarantined, an unexpected derived record and a corrupted older projection.

## Implementation defect found during validation

The first package placed SAM `CodeUri` in `Globals`, which produced an archive containing infrastructure files rather than the Lambda handler. EventBridge Pipes TRACE logs exposed the target import failure and retry sequence. Moving `CodeUri` to each function corrected the package. This is retained as implementation evidence that delivery-stage observability is diagnostic evidence, not a correctness guarantee.

## Limitations

- The reconciler performs a bounded table scan for inspectable evidence; production reconciliation should be partitioned and checkpointed.
- DynamoDB Streams retention bounds direct replay time.
- Poison records require an operator-defined clearance policy before repair.
- EventBridge metrics are operational indicators, not complete accounting records.
- Deletion and tombstone policy must be explicit for real derived stores.

