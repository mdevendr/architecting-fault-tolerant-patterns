import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.model import GovernedToolBoundary, PolicyDenied, ToolRequest


class GovernedAgentRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.boundary = GovernedToolBoundary()

    def request(self, **changes):
        values = {
            "call_id": "call-1",
            "tenant_id": "tenant-a",
            "actor_role": "credit-operator",
            "action": "reserve_credit",
            "amount": 500,
        }
        values.update(changes)
        return ToolRequest(**values)

    def test_policy_denies_before_effect(self):
        with self.assertRaises(PolicyDenied):
            self.boundary.execute(self.request(amount=1500))
        self.assertEqual({}, self.boundary.committed_effects)

    def test_policy_denies_wrong_role_before_effect(self):
        with self.assertRaises(PolicyDenied):
            self.boundary.execute(self.request(actor_role="viewer"))
        self.assertEqual({}, self.boundary.committed_effects)

    def test_ambiguous_completion_replays_canonical_result(self):
        request = self.request()
        with self.assertRaises(TimeoutError):
            self.boundary.execute(request, fail_after_commit=True)
        replayed = self.boundary.execute(request)
        self.assertEqual("reservation:call-1:500", replayed)
        self.assertEqual(1, len(self.boundary.committed_effects))

    def test_compensation_executes_once_after_lost_response(self):
        self.boundary.execute(self.request())
        with self.assertRaises(TimeoutError):
            self.boundary.compensate("call-1", fail_after_commit=True)
        replayed = self.boundary.compensate("call-1")
        self.assertEqual("released:call-1", replayed)
        self.assertEqual(1, len(self.boundary.compensating_effects))
        self.assertEqual("COMPENSATED", self.boundary.records["call-1"].status)


if __name__ == "__main__":
    unittest.main()

