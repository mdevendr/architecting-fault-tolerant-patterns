from pathlib import Path
import sys
import unittest


SCENARIO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCENARIO_ROOT))

from src.routing import assign_cell, ordering_key


class RoutingTests(unittest.TestCase):
    def test_assignment_is_stable(self) -> None:
        cells = ("cell-a", "cell-b", "cell-c")
        first = assign_cell("tenant-42", cells)
        self.assertEqual(first, assign_cell("tenant-42", cells))

    def test_dedicated_assignment_overrides_hash(self) -> None:
        self.assertEqual(
            "cell-dedicated",
            assign_cell(
                "tenant-large",
                ("cell-a", "cell-b", "cell-dedicated"),
                {"tenant-large": "cell-dedicated"},
            ),
        )

    def test_ordering_key_excludes_random_event_identity(self) -> None:
        self.assertEqual(
            "tenant-42#account-7", ordering_key("tenant-42", "account-7")
        )


if __name__ == "__main__":
    unittest.main()

