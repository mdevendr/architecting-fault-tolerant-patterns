"""Deterministic model for governed agent tool execution and compensation."""

from dataclasses import dataclass, field
from typing import Dict, Optional


class PolicyDenied(RuntimeError):
    pass


@dataclass(frozen=True)
class ToolRequest:
    call_id: str
    tenant_id: str
    actor_role: str
    action: str
    amount: int


@dataclass
class ToolRecord:
    status: str
    result: Optional[str] = None
    compensation_status: str = "NOT_REQUIRED"


@dataclass
class GovernedToolBoundary:
    records: Dict[str, ToolRecord] = field(default_factory=dict)
    committed_effects: Dict[str, str] = field(default_factory=dict)
    compensating_effects: Dict[str, str] = field(default_factory=dict)

    def policy_allows(self, request: ToolRequest) -> bool:
        return (
            request.action == "reserve_credit"
            and request.actor_role == "credit-operator"
            and 0 < request.amount <= 1000
        )

    def execute(self, request: ToolRequest, *, fail_after_commit: bool = False) -> str:
        if not self.policy_allows(request):
            raise PolicyDenied(request.call_id)

        existing = self.records.get(request.call_id)
        if existing and existing.status == "COMMITTED":
            return existing.result or ""

        result = self.committed_effects.setdefault(
            request.call_id, f"reservation:{request.call_id}:{request.amount}"
        )
        self.records[request.call_id] = ToolRecord(status="COMMITTED", result=result)
        if fail_after_commit:
            raise TimeoutError("response lost after tool commit")
        return result

    def compensate(self, call_id: str, *, fail_after_commit: bool = False) -> str:
        record = self.records[call_id]
        if record.compensation_status == "COMPENSATED":
            return self.compensating_effects[call_id]

        result = self.compensating_effects.setdefault(call_id, f"released:{call_id}")
        record.compensation_status = "COMPENSATED"
        record.status = "COMPENSATED"
        if fail_after_commit:
            raise TimeoutError("response lost after compensation commit")
        return result

