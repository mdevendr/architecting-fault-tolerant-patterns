from pathlib import Path
import sys
import unittest


SCENARIO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCENARIO_ROOT))

from src.model import PolicyFinding, SourceLedger, TrustGateway, VectorHit


class TrustGatewayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.gateway = TrustGateway()
        self.ledger = SourceLedger(
            document_id="policy-1",
            tenant_id="tenant-a",
            authoritative_version=2,
            indexed_version=2,
            ingestion_status="COMPLETE",
            policy_version="policy-v3",
        )
        self.hit = VectorHit(
            document_id="policy-1",
            tenant_id="tenant-a",
            source_version=2,
            source_uri="s3://authoritative/tenant-a/policy-1.txt",
            text="The approved limit is 5000.",
        )

    def evaluate(self, **overrides):
        values = {
            "caller_tenant": "tenant-a",
            "ledger": self.ledger,
            "hits": [self.hit],
            "generated_answer": "The approved limit is 5000.",
            "policy_finding": PolicyFinding.VALID,
        }
        values.update(overrides)
        return self.gateway.evaluate(**values)

    def test_stale_index_returns_safe_non_answer(self) -> None:
        stale = SourceLedger(
            **{**self.ledger.__dict__, "authoritative_version": 3, "indexed_version": 2}
        )
        result = self.evaluate(ledger=stale)
        self.assertEqual((result.status, result.reason), ("SAFE_NON_ANSWER", "INDEX_VERSION_STALE"))

    def test_cross_tenant_context_is_rejected(self) -> None:
        unauthorized = VectorHit(**{**self.hit.__dict__, "tenant_id": "tenant-b"})
        result = self.evaluate(hits=[unauthorized])
        self.assertEqual(result.reason, "CROSS_TENANT_CONTEXT")

    def test_missing_provenance_is_rejected(self) -> None:
        no_source = VectorHit(**{**self.hit.__dict__, "source_uri": None})
        result = self.evaluate(hits=[no_source])
        self.assertEqual(result.reason, "PROVENANCE_MISSING")

    def test_policy_conflict_returns_safe_non_answer(self) -> None:
        result = self.evaluate(policy_finding=PolicyFinding.INVALID)
        self.assertEqual((result.status, result.reason), ("SAFE_NON_ANSWER", "POLICY_CONFLICT"))

    def test_policy_ambiguity_routes_to_human(self) -> None:
        result = self.evaluate(policy_finding=PolicyFinding.AMBIGUOUS)
        self.assertEqual((result.status, result.reason), ("HUMAN_REVIEW", "POLICY_AMBIGUOUS"))

    def test_current_authorized_response_contains_versioned_citation(self) -> None:
        result = self.evaluate()
        self.assertEqual(result.status, "ANSWER")
        self.assertIn("version=2", result.citations[0])


if __name__ == "__main__":
    unittest.main()

