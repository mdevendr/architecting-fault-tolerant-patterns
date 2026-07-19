# Source-to-Derived-State Reconciliation

## Architectural objective

Asynchronous delivery must keep the source write independent from derived-state availability while still providing a measurable route to convergence. A healthy stream or empty retry queue does not prove source and projection equality.

The validated architecture uses three controls:

1. EventBridge Pipes transports DynamoDB Stream records at least once.
2. The projection accepts only a strictly newer source version, suppressing duplicate and out-of-order delivery.
3. An independent reconciler measures missing, extra and version/value-mismatched records and repairs the projection from the source.

## Validated result

Run `20260719-g05` injected a duplicate version-2 event and a late version-1 event. Both were suppressed and the projection remained at version 2. A poison record was quarantined without advancing derived state. The experiment then created two missing projections, one unexpected projection and one corrupted older projection.

Reconciliation reported those categories explicitly, repaired four divergences and verified zero remaining missing, extra or mismatched records. A normalized source comparison proved that repair did not modify the source of truth.

## Starting-position choice

The Pipe starts at `TRIM_HORIZON`. DynamoDB Stream polling during Pipe creation and source-configuration updates is eventually consistent; selecting `LATEST` can miss records written during that interval. `TRIM_HORIZON` reduces that creation-window risk, but it does not replace consumer idempotency or reconciliation.

## Observability boundary

Enhanced EventBridge Pipes logging records polling, transformation and target invocation stages. It exposed a real Lambda packaging failure during the first run. Those logs prove what the delivery system attempted; only state comparison proves convergence.

