# Article placement: exactly-once outcome and reconciliation

Section headings are authoritative; PDF page numbers are navigation aids only.

## Remove unevidenced code

Under **Dependency Protection: Timeouts, Retries, Circuit Breakers and Bulkheads**, remove the unevidenced DynamoDB idempotency reservation handler and its Traceability claim. A conditional `attribute_not_exists` reservation alone does not demonstrate the complete outcome lifecycle.

## Add validated implementation evidence

### Architectural Pattern: Exactly-Once Business Outcome

Place the validated implementation immediately after the architectural explanation of ownership, lease expiry, canonical results and outbox boundaries. Place it before **Continuous Anti-Entropy Reconciliation Metrics**.

Add the validated failure-sequence table from `evidence/validated/20260719-g02/README.md`.

Use a short excerpt covering:

- active lease rejection and expired lease takeover from `src/aws_handlers/handler.py`;
- the DynamoDB transaction that completes the operation and creates the outbox; and
- canonical result return for a completed duplicate.

Do not reproduce the entire handler.

### Continuous Anti-Entropy Reconciliation Metrics

Replace the formula `Delta Entropy = Hash(Source Ledger) - Hash(Derived Index)` with explicit reconciliation measurements:

- missing derived records;
- unexpected derived records;
- source/projection version mismatches;
- result or checksum mismatches;
- age of oldest unresolved divergence;
- repair throughput; and
- remaining unreconciled records.

Add the validated result that one injected version/result mismatch was detected and repaired, leaving source version 1 and projection version 1 with matching results.

## Terminology constraint

Use **exactly-once business outcome under at-least-once execution**. Do not claim exactly-once Lambda execution, exactly-once stream delivery or a universal exactly-once distributed transaction.

