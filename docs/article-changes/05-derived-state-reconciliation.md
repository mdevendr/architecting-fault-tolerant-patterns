# Article Change Sheet 05: Source-to-Derived-State Reconciliation

Apply changes by heading, not PDF page number.

## Change 1: Normalize the section format

### Find

**State Decoupling and Derived Data Recovery**

Keep its opening explanation, then present the implementation using the same structure as the other evidence sections:

- failure contract;
- architectural controls;
- injected failures;
- recovery evidence; and
- limitations.

## Change 2: Add the validated implementation

### Add this heading

#### Validated Reference Implementation: Detect and Repair Projection Divergence

### Add this text

> A controlled AWS experiment used a DynamoDB Stream and Amazon EventBridge Pipes to maintain an independently committed DynamoDB projection. The consumer stored the source version with each derived record and accepted only a strictly newer version. A duplicate version-2 event and a late version-1 event were both suppressed, leaving the projection at version 2.
>
> Delivery correctness did not establish projection completeness. The experiment deliberately skipped one valid event, quarantined a poison event, inserted an unexpected derived record and replaced another projection with an older corrupted version. An independent reconciler reported two missing records, one extra record and one version/value mismatch.
>
> Reconciliation repaired all four divergences from the authoritative source, then reported zero missing, extra or mismatched records. A normalized before-and-after comparison confirmed that projection repair did not modify the source of truth.

## Change 3: Add the evidence table

| Injected condition | Observed outcome |
|---|---|
| Duplicate version 2 | Suppressed |
| Version 1 delivered after version 2 | Suppressed; projection remained v2 |
| Poison event | Quarantined |
| Missing projections | 2 detected |
| Unexpected projection | 1 detected |
| Version/value mismatch | 1 detected |
| Repair | 4 divergences repaired |
| Final comparison | Missing 0; extra 0; mismatched 0 |
| Source state during repair | Unchanged |

Add:

> **Evidence scope:** Run `20260719-g05` executed in `eu-west-2` with EventBridge Pipes TRACE logging enabled. The bounded dataset makes every source and projection transition independently inspectable.

## Change 4: Add the version-control excerpt

```python
ConditionExpression="attribute_not_exists(record_id) OR #version < :incoming"
```

Explain:

> This condition suppresses duplicate and stale delivery. It does not detect a record that was never projected; reconciliation remains a separate control.

## Change 5: Replace the entropy expression

Remove:

```text
Delta Entropy = Hash(Source Ledger) - Hash(Derived Index)
```

Replace with:

> Report explicit divergence: missing records, unexpected records, source/projection version or checksum mismatches, the age of the oldest unresolved divergence, repair throughput and remaining unreconciled records. Hashes may be compared for equality, but subtracting them does not define useful recovery entropy.

## Change 6: Add the EventBridge Pipes choice and limitation

> The reference Pipe starts from `TRIM_HORIZON` because stream polling during Pipe creation and source updates is eventually consistent; `LATEST` can miss records written during that interval. DynamoDB Streams retention still bounds replay time, and long-lived reconstruction requires an authoritative snapshot or durable history beyond the stream.

## Change 7: Bound observability claims

> EventBridge Pipes enhanced logging provides delivery-stage evidence and exposed a Lambda packaging failure during validation. Logs and CloudWatch metrics improve diagnosis but do not prove source/projection equality; reconciliation provides that proof.

## Change 8: Add the visual

Suggested title:

> **Delivery Prevents Coupling; Reconciliation Proves Convergence**

```text
Authoritative write → DynamoDB Stream → EventBridge Pipe → versioned projection
                                               │
                                  duplicate/stale → suppress
                                  poison          → quarantine

Authoritative source ───────────────┐
                                    ├→ compare → missing / extra / mismatch
Derived projection ─────────────────┘                 │
                                                      ▼
                                             controlled repair
```

## Change 9: Repository links

Link to:

- `code/scenarios/derived-state-reconciliation/README.md`
- `code/scenarios/derived-state-reconciliation/src/aws_handlers/handler.py`
- `code/scenarios/derived-state-reconciliation/infrastructure/template.yaml`
- `code/scenarios/derived-state-reconciliation/evidence/validated/20260719-g05/README.md`

Suggested immutable tag:

```text
evidence/derived-state-reconciliation-20260719-g05
```

