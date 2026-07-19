# Validated AWS evidence: 20260719-g01

## Scope

- Region: `eu-west-2`
- Execution environment: AWS
- Faulted cell workload: 300 messages
- Healthy cell workload: 100 messages
- Fault hold: 30 seconds
- Regional Lambda concurrency quota during the experiment: 10
- Per-cell SQS event-source maximum concurrency: 5

The experiment impaired the dependency state for cell A while cell B remained healthy. The same workload was executed against naive and protected worker policies.

## Results

| Metric | Naive | Protected |
|---|---:|---:|
| Downstream attempts | 850 | 400 |
| Circuit-open rejections | 0 | 440 |
| Attempt amplification | 2.125x | 1.0x |
| Cell A peak attempts/minute | 300 | 160 |
| Completed outcomes | 400 | 400 |
| Healthy cell outcomes | 100 | 100 |
| Recovery time | 63.746 s | 63.422 s |

Contract result: **PASS**

## What the run demonstrates

- The fault in cell A did not prevent cell B from completing all 100 accepted outcomes.
- The naive path repeatedly called the impaired dependency.
- The protected path evaluated the shared circuit state before invoking the dependency.
- The protected path suppressed 440 outage-period calls at the circuit boundary.
- Admission control preserved all accepted work and allowed the queue to drain after recovery.
- Conditional outcome writes prevented duplicate committed outcomes in this scenario.

## Defect discovered during validation

The first protected run applied admission control before checking the shared circuit state. It limited calls per second but still invoked the dependency during the declared impairment. The evidence contract failed because protected attempt amplification was not lower than the naive path.

The worker was corrected to evaluate the circuit state before consuming an admission token or recording a downstream attempt. Both stacks were updated to the same code version and the complete comparison was rerun.

## Limitations

- This is a controlled evidence workload, not a production capacity benchmark.
- The downstream dependency is represented by a DynamoDB-backed state and rate boundary; it is not an induced outage of an AWS managed service.
- The open circuit is an externally controlled shared state for deterministic testing. A production design requires health-based state transitions, ownership and stale-state handling.
- CloudWatch peak values use one-minute aggregation and do not expose sub-second burst shape.
- SQS queue attributes are approximate and the Lambda/SQS integration has visibility and polling behaviour that affects the recovery curve.
- The account concurrency quota constrained both cells to five concurrent event-source executions.

## Reproduction

The deployment, workload, fault transition, recovery sampling, contract evaluation and teardown commands are documented in the scenario infrastructure README. Raw generated evidence is excluded from Git until it has been reviewed and sanitized.

