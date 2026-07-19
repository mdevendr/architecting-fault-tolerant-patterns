import sqlite3
from pathlib import Path
import sys
import unittest


SCENARIO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCENARIO_ROOT))

from src.model import ExactlyOnceModel, ExecutionBusy, InjectedCrash


class ExactlyOnceModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = sqlite3.connect(":memory:")
        self.model = ExactlyOnceModel(self.db)
        self.model.create_schema()

    def tearDown(self) -> None:
        self.db.close()

    def test_duplicate_delivery_returns_canonical_result(self) -> None:
        first = self.model.execute("payment-1", "worker-a", now=100)
        replay = self.model.execute("payment-1", "worker-b", now=101)
        self.assertFalse(first.replayed)
        self.assertTrue(replay.replayed)
        self.assertEqual(first.result, replay.result)
        self.assertEqual(self.model.count("provider_effects"), 1)

    def test_crash_after_provider_does_not_repeat_effect(self) -> None:
        with self.assertRaises(InjectedCrash):
            self.model.execute(
                "payment-2", "worker-a", now=100, lease_seconds=5, crash_after_provider=True
            )
        with self.assertRaises(ExecutionBusy):
            self.model.execute("payment-2", "worker-b", now=103, lease_seconds=5)
        recovered = self.model.execute("payment-2", "worker-b", now=106, lease_seconds=5)
        self.assertFalse(recovered.replayed)
        self.assertEqual(self.model.count("provider_effects"), 1)
        self.assertEqual(self.model.count("outbox"), 1)

    def test_completion_and_outbox_are_atomic(self) -> None:
        self.model.execute("payment-3", "worker-a", now=100)
        self.assertEqual(self.model.count("operations"), 1)
        self.assertEqual(self.model.count("outbox"), 1)

    def test_outbox_replay_is_projection_idempotent(self) -> None:
        self.model.execute("payment-4", "worker-a", now=100)
        with self.assertRaises(InjectedCrash):
            self.model.publish_outbox(fail_before_marking=True)
        self.assertEqual(self.model.count("projection"), 1)
        self.model.publish_outbox()
        self.assertEqual(self.model.count("projection"), 1)

    def test_reconciliation_detects_and_repairs_corruption(self) -> None:
        self.model.execute("payment-5", "worker-a", now=100)
        self.model.publish_outbox()
        with self.db:
            self.db.execute(
                "UPDATE projection SET result='corrupt', source_version=0 WHERE operation_key='payment-5'"
            )
        self.assertEqual(self.model.reconciliation_counts()["mismatched"], 1)
        self.assertEqual(self.model.repair_projection(), 1)
        self.assertEqual(
            self.model.reconciliation_counts(),
            {"missing": 0, "mismatched": 0, "extra": 0},
        )


if __name__ == "__main__":
    unittest.main()

