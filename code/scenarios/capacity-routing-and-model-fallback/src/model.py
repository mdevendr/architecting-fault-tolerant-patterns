"""Fault classification and independently governed semantic fallback."""

from dataclasses import dataclass


TRANSIENT = {429, 500, 502, 503, 504}
NON_RETRYABLE = {400, 401, 403, 404}


@dataclass(frozen=True)
class ModelContract:
    model_id: str
    evaluation_score: float
    minimum_score: float
    approved_geographies: tuple[str, ...]
    degraded: bool = False

    @property
    def eligible(self) -> bool:
        return self.evaluation_score >= self.minimum_score


def recovery_decision(status_code: int, reason: str, fallback: ModelContract, geography: str):
    if reason == "POLICY_DENIED":
        return {"action": "FAIL_CLOSED", "fallback": False}
    if status_code in NON_RETRYABLE:
        return {"action": "RETURN_ERROR", "fallback": False}
    if status_code not in TRANSIENT:
        return {"action": "RETURN_ERROR", "fallback": False}
    if geography not in fallback.approved_geographies:
        return {"action": "CAPACITY_ROUTE_ONLY", "fallback": False}
    if not fallback.eligible:
        return {"action": "CAPACITY_ROUTE_ONLY", "fallback": False}
    return {
        "action": "SEMANTIC_FALLBACK",
        "fallback": True,
        "model_id": fallback.model_id,
        "degraded": fallback.degraded,
    }

