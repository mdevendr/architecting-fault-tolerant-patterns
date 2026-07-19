# AWS implementation

The stack deploys:

- an operation ownership and canonical-result table;
- an idempotent provider-effect table;
- an outbox table with DynamoDB Streams;
- an independently committed projection table;
- a worker Lambda;
- a stream-driven projector Lambda; and
- an explicit reconciler Lambda.

The evidence runner executes this sequence:

1. acquire operation ownership;
2. commit the provider effect;
3. crash before operation completion;
4. verify that another owner is rejected before lease expiry;
5. reclaim the expired lease;
6. retrieve the existing provider result rather than repeating the effect;
7. commit operation completion and outbox atomically;
8. crash the projector after the projection commit;
9. verify stream replay is idempotent and the outbox becomes delivered;
10. replay the original request and return the canonical result;
11. corrupt the derived projection; and
12. run reconciliation and verify repair.

## Deploy and run

```powershell
./deploy.ps1 -RunId 20260719-g02 -Profile melon
./run-cloud-experiment.ps1 -RunId 20260719-g02 -Profile melon
```

The runner writes a versioned manifest containing every injected failure, state count, final source/projection comparison and contract result.
