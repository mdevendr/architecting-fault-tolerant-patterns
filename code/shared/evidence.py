"""Versioned evidence records shared by reference implementations."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from typing import Any
from uuid import uuid4


SCHEMA_VERSION = "1.0"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def git_commit(repository_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository_root,
            capture_output=True,
            check=True,
            text=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "uncommitted"


@dataclass(frozen=True)
class ContractResult:
    name: str
    passed: bool
    observed: float | int | str | bool
    operator: str
    threshold: float | int | str | bool
    unit: str = ""


@dataclass
class EvidenceRun:
    scenario: str
    mode: str
    configuration: dict[str, Any]
    metrics: dict[str, Any]
    contract_results: list[ContractResult]
    limitations: list[str]
    repository_commit: str = "uncommitted"
    run_id: str = field(default_factory=lambda: str(uuid4()))
    schema_version: str = SCHEMA_VERSION
    execution_environment: str = "local-simulator"
    started_at: str = field(default_factory=utc_now)
    completed_at: str = field(default_factory=utc_now)

    @property
    def passed(self) -> bool:
        return all(result.passed for result in self.contract_results)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["passed"] = self.passed
        return value

    def write(self, output_directory: Path) -> Path:
        output_directory.mkdir(parents=True, exist_ok=True)
        path = output_directory / f"{self.mode}-{self.run_id}.json"
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return path


def write_comparison_report(
    runs: list[EvidenceRun], output_path: Path, title: str
) -> None:
    metric_names = sorted({name for run in runs for name in run.metrics})
    lines = [f"# {title}", "", "## Contract result", ""]
    lines.extend(
        [
            "| Mode | Result | Run ID |",
            "|---|---|---|",
            *[
                f"| {run.mode} | {'PASS' if run.passed else 'FAIL'} | `{run.run_id}` |"
                for run in runs
            ],
            "",
            "## Metrics",
            "",
            "| Metric | " + " | ".join(run.mode for run in runs) + " |",
            "|---|" + "---|" * len(runs),
        ]
    )
    for name in metric_names:
        lines.append(
            f"| {name} | "
            + " | ".join(str(run.metrics.get(name, "-")) for run in runs)
            + " |"
        )
    lines.extend(
        [
            "",
            "> Local simulator results validate scenario logic only. They are not AWS cloud evidence.",
            "",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")

