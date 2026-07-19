import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.model import ProjectionModel, Record


class ProjectionTests(unittest.TestCase):
    def test_duplicate_and_out_of_order_events_do_not_regress_projection(self):
        model = ProjectionModel()
        v2 = Record("a", 2, "current")
        self.assertEqual("APPLIED", model.apply_event(v2, "e2"))
        self.assertEqual("DUPLICATE_OR_STALE", model.apply_event(v2, "e2-replay"))
        self.assertEqual(
            "DUPLICATE_OR_STALE",
            model.apply_event(Record("a", 1, "obsolete"), "e1-late"),
        )
        self.assertEqual(v2, model.projection["a"])

    def test_poison_event_is_quarantined_without_projection_change(self):
        model = ProjectionModel()
        outcome = model.apply_event(Record("a", 1, "bad"), "poison-1", poison=True)
        self.assertEqual("QUARANTINED", outcome)
        self.assertEqual({}, model.projection)
        self.assertEqual(["poison-1"], model.quarantined)

    def test_reconciliation_repairs_missing_extra_and_mismatch(self):
        model = ProjectionModel(
            source={
                "missing": Record("missing", 1, "source"),
                "mismatch": Record("mismatch", 3, "source-v3"),
            },
            projection={
                "mismatch": Record("mismatch", 2, "old"),
                "extra": Record("extra", 1, "orphan"),
            },
        )
        differences = model.reconcile()
        self.assertEqual(["missing"], differences["missing"])
        self.assertEqual(["extra"], differences["extra"])
        self.assertEqual(["mismatch"], differences["mismatched"])
        self.assertEqual(model.source, model.projection)


if __name__ == "__main__":
    unittest.main()

