"""Deterministic trust-gateway model used before AWS deployment."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PolicyFinding(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    AMBIGUOUS = "AMBIGUOUS"


@dataclass(frozen=True)
class SourceLedger:
    document_id: str
    tenant_id: str
    authoritative_version: int
    indexed_version: int
    ingestion_status: str
    policy_version: str


@dataclass(frozen=True)
class VectorHit:
    document_id: str
    tenant_id: str
    source_version: int
    source_uri: str | None
    text: str


@dataclass(frozen=True)
class GatewayResult:
    status: str
    reason: str
    answer: str | None = None
    citations: tuple[str, ...] = ()


class TrustGateway:
    def evaluate(
        self,
        caller_tenant: str,
        ledger: SourceLedger,
        hits: list[VectorHit],
        generated_answer: str,
        policy_finding: PolicyFinding,
    ) -> GatewayResult:
        if caller_tenant != ledger.tenant_id:
            return GatewayResult("SAFE_NON_ANSWER", "CALLER_NOT_AUTHORIZED")
        if ledger.ingestion_status != "COMPLETE":
            return GatewayResult("SAFE_NON_ANSWER", "INGESTION_NOT_COMPLETE")
        if ledger.indexed_version != ledger.authoritative_version:
            return GatewayResult("SAFE_NON_ANSWER", "INDEX_VERSION_STALE")
        if not hits:
            return GatewayResult("SAFE_NON_ANSWER", "NO_AUTHORIZED_CONTEXT")

        citations: list[str] = []
        for hit in hits:
            if hit.tenant_id != caller_tenant:
                return GatewayResult("SAFE_NON_ANSWER", "CROSS_TENANT_CONTEXT")
            if hit.document_id != ledger.document_id:
                return GatewayResult("SAFE_NON_ANSWER", "UNEXPECTED_DOCUMENT")
            if hit.source_version != ledger.authoritative_version:
                return GatewayResult("SAFE_NON_ANSWER", "RETRIEVED_VERSION_STALE")
            if not hit.source_uri:
                return GatewayResult("SAFE_NON_ANSWER", "PROVENANCE_MISSING")
            citations.append(
                f"{hit.source_uri}#document={hit.document_id}&version={hit.source_version}"
            )

        if policy_finding == PolicyFinding.INVALID:
            return GatewayResult("SAFE_NON_ANSWER", "POLICY_CONFLICT")
        if policy_finding == PolicyFinding.AMBIGUOUS:
            return GatewayResult("HUMAN_REVIEW", "POLICY_AMBIGUOUS")
        return GatewayResult(
            "ANSWER",
            "TRUST_CONTRACT_SATISFIED",
            answer=generated_answer,
            citations=tuple(citations),
        )

