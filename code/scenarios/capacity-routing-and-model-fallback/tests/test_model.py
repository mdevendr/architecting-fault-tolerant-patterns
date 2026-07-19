import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.model import ModelContract, recovery_decision


class RecoveryDecisionTests(unittest.TestCase):
    def contract(self, **changes):
        values = dict(
            model_id="fallback-model",
            evaluation_score=0.93,
            minimum_score=0.90,
            approved_geographies=("EU",),
            degraded=True,
        )
        values.update(changes)
        return ModelContract(**values)

    def test_transient_failure_can_use_evaluated_fallback(self):
        decision = recovery_decision(503, "CAPACITY", self.contract(), "EU")
        self.assertEqual("SEMANTIC_FALLBACK", decision["action"])
        self.assertTrue(decision["degraded"])

    def test_invalid_request_never_falls_back(self):
        self.assertEqual(
            "RETURN_ERROR",
            recovery_decision(400, "INVALID_REQUEST", self.contract(), "EU")["action"],
        )

    def test_policy_denial_never_falls_back(self):
        self.assertEqual(
            "FAIL_CLOSED",
            recovery_decision(403, "POLICY_DENIED", self.contract(), "EU")["action"],
        )

    def test_unevaluated_model_is_not_a_fallback(self):
        decision = recovery_decision(
            429, "THROTTLED", self.contract(evaluation_score=0.70), "EU"
        )
        self.assertEqual("CAPACITY_ROUTE_ONLY", decision["action"])

    def test_geography_constraint_blocks_semantic_fallback(self):
        decision = recovery_decision(503, "CAPACITY", self.contract(), "US")
        self.assertEqual("CAPACITY_ROUTE_ONLY", decision["action"])


if __name__ == "__main__":
    unittest.main()

