# Architecture Assurance Evidence

This directory is reserved for evidence that supports or challenges architectural claims made in the article and architecture catalogue.

Evidence is included only when it helps an architecture audience evaluate whether a resilience mechanism behaves as intended under a defined failure condition.

## Evidence Categories

```text
cloudwatch/        Operational metrics, alarms, and dashboards
logs/              Relevant diagnostic or audit extracts
sample-responses/  Representative normal, degraded, and recovery outcomes
screenshots/       Architecture assurance and recovery observations
step-functions/    Workflow execution and recovery-state evidence
```

## Evidence Standard

Every retained artefact should identify:

- the architectural claim being evaluated
- the failure or degradation condition
- the expected system behaviour
- the observed behaviour
- the relevant time, Region, account boundary, and configuration context
- any limitations that prevent the result from being generalized

This directory is not intended to accumulate raw operational data. Evidence should be curated, sanitized, reproducible where practical, and directly traceable to an architectural decision or article claim.
