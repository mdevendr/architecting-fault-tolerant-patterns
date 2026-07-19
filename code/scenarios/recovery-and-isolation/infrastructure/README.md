# AWS deployment

The template deploys two independently consumed SQS cells, DynamoDB control/counter/outcome tables, per-cell Lambda consumers, alarms, and a CloudWatch evidence dashboard.

The current evidence account has a Regional Lambda concurrency quota of 10. Each SQS event source is therefore capped at five concurrent executions. This is an experiment constraint, not a recommended production capacity value; production limits must be derived from the downstream capacity contract and account quotas.

Deployments are intentionally batched. One authentication session should be used to deploy both modes, run the fault experiment, collect evidence, and tear down both stacks.

## Deployment

```powershell
./deploy.ps1 -RunId 20260719-g01 -Mode naive -Profile your-profile
./deploy.ps1 -RunId 20260719-g01 -Mode protected -Profile your-profile
```

The current environment has no configured AWS CLI profile. Local validation can continue without AWS credentials; do not label local simulator results as cloud evidence.

## Batched experiment

After both modes have been deployed in one authenticated session, run:

```powershell
./run-cloud-experiment.ps1 -RunId 20260719-g01 -Mode naive -Profile your-profile
./run-cloud-experiment.ps1 -RunId 20260719-g01 -Mode protected -Profile your-profile
```

The runner performs the full sequence without interactive AWS prompts: it initializes cell state, publishes the workload, holds the cell-A fault, restores the cell, samples both queues, counts committed outcomes, and writes a run manifest. Authentication is intentionally outside the script so one existing CLI session can be reused.

After CloudWatch has ingested both runs:

```powershell
./collect-cloud-evidence.ps1 -RunId 20260719-g01 -Profile your-profile
```

The collector calculates downstream attempts, attempt amplification, peak per-minute request rate, completed outcomes, healthy-cell outcomes and recovery duration. It fails if the protected contract is not satisfied.

## Fault control

The `ControlTable` holds one item per cell:

```json
{"cell_id":"cell-a","state":"RUNNING"}
```

Changing `cell-a` to `IMPAIRED` rejects its dependency calls while `cell-b` remains independently operational. The experiment runner will automate this transition, workload publication, CloudWatch export, and restoration in the next implementation step.
