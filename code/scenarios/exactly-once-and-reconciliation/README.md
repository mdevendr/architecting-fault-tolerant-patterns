# Exactly-Once Business Outcome and Derived-State Reconciliation

This scenario proves one business outcome under at-least-once execution. It deliberately separates four guarantees:

1. workflow ownership and lease recovery;
2. idempotency at the external business-effect boundary;
3. atomic source completion and outbox creation; and
4. idempotent projection plus reconciliation.

The local SQLite model validates the failure semantics before AWS deployment. Local results are not cloud evidence.

## Local tests

```powershell
python -m unittest discover -s code/scenarios/exactly-once-and-reconciliation/tests -v
```

The AWS implementation will use DynamoDB transactional writes, an idempotent provider simulator, DynamoDB Streams/EventBridge Pipes for asynchronous projection, and an explicit reconciliation run.

