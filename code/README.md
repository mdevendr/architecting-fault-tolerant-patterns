# Reference implementations

## Layout

```text
shared/       Evidence contracts and common tooling
scenarios/    Independently executable failure scenarios
```

Each scenario contains:

- `failure-contract.json` — measurable pass/fail conditions;
- `src/` — executable scenario logic;
- `tests/` — deterministic local validation;
- `infrastructure/` — AWS deployment definition;
- `evidence/` — schemas, sanitized results, and report guidance;
- `article-placement.md` — exact document removal and insertion map.

## Local validation

From the repository root:

```powershell
python -m unittest discover -s code/scenarios/recovery-and-isolation/tests -v
python code/scenarios/recovery-and-isolation/run_experiment.py --output-dir tmp/evidence
```

The local simulator validates the failure contract before AWS resources are deployed. Cloud evidence is kept separate and must never be inferred from simulator results.

