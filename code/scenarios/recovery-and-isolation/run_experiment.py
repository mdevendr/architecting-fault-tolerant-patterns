"""Run the local comparison and write versioned, clearly labelled evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


SCENARIO_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = SCENARIO_ROOT.parents[2]
CODE_ROOT = SCENARIO_ROOT.parents[1]
sys.path.insert(0, str(CODE_ROOT))
sys.path.insert(0, str(SCENARIO_ROOT))

from shared.evidence import (  # noqa: E402
    ContractResult,
    EvidenceRun,
    git_commit,
    write_comparison_report,
)
from src.simulator import RecoverySimulation, SimulationConfig  # noqa: E402


def evaluate(mode: str, metrics: dict, thresholds: dict) -> list[ContractResult]:
    results = [
        ContractResult(
            name="duplicate business outcomes",
            passed=metrics["duplicate_business_outcomes"]
            == thresholds["duplicate_business_outcomes"],
            observed=metrics["duplicate_business_outcomes"],
            operator="==",
            threshold=thresholds["duplicate_business_outcomes"],
        ),
        ContractResult(
            name="healthy cell oldest message age",
            passed=metrics["healthy_cell_oldest_message_age_ticks"]
            <= thresholds["healthy_cell_oldest_message_age_max_ticks"],
            observed=metrics["healthy_cell_oldest_message_age_ticks"],
            operator="<=",
            threshold=thresholds["healthy_cell_oldest_message_age_max_ticks"],
            unit="ticks",
        ),
    ]
    if mode == "protected":
        results.extend(
            [
                ContractResult(
                    name="protected peak attempts",
                    passed=metrics["peak_attempts_cell_a_per_tick"]
                    <= thresholds["protected_peak_attempts_per_tick"],
                    observed=metrics["peak_attempts_cell_a_per_tick"],
                    operator="<=",
                    threshold=thresholds["protected_peak_attempts_per_tick"],
                    unit="attempts/tick",
                ),
                ContractResult(
                    name="protected unprocessed messages",
                    passed=metrics["unprocessed_messages"]
                    == thresholds["protected_unprocessed_messages"],
                    observed=metrics["unprocessed_messages"],
                    operator="==",
                    threshold=thresholds["protected_unprocessed_messages"],
                ),
            ]
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    contract = json.loads(
        (SCENARIO_ROOT / "failure-contract.json").read_text(encoding="utf-8")
    )
    config = SimulationConfig()
    runs: list[EvidenceRun] = []
    for mode in ("naive", "protected"):
        result = RecoverySimulation(config, mode).run()
        run = EvidenceRun(
            scenario="recovery-and-isolation",
            mode=mode,
            configuration={**config.__dict__, "contract_version": contract["contract_version"]},
            metrics=result.metrics,
            contract_results=evaluate(mode, result.metrics, contract["thresholds"]),
            limitations=[
                "This run is a deterministic local simulator, not AWS cloud evidence.",
                "Network latency, Lambda polling behaviour, and service quotas require cloud validation.",
            ],
            repository_commit=git_commit(REPOSITORY_ROOT),
        )
        run.write(args.output_dir / "runs")
        runs.append(run)

    write_comparison_report(
        runs,
        args.output_dir / "comparison.md",
        "Recovery-storm containment: local scenario validation",
    )
    return 0 if runs[1].passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
