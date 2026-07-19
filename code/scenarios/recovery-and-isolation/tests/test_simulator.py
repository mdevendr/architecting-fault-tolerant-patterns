from pathlib import Path
import sys
import unittest


SCENARIO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCENARIO_ROOT))

from src.simulator import RecoverySimulation, SimulationConfig


class RecoverySimulationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = SimulationConfig()

    def test_protected_mode_caps_recovery_attempt_rate(self) -> None:
        result = RecoverySimulation(self.config, "protected").run()
        self.assertLessEqual(
            result.metrics["peak_attempts_cell_a_per_tick"],
            self.config.downstream_capacity_per_tick,
        )

    def test_naive_mode_creates_recovery_spike(self) -> None:
        result = RecoverySimulation(self.config, "naive").run()
        self.assertGreater(
            result.metrics["peak_attempts_cell_a_per_tick"],
            self.config.downstream_capacity_per_tick,
        )

    def test_faulted_cell_does_not_delay_healthy_cell(self) -> None:
        result = RecoverySimulation(self.config, "protected").run()
        self.assertEqual(
            result.metrics["healthy_cell_oldest_message_age_ticks"], 0
        )

    def test_business_outcome_is_not_duplicated(self) -> None:
        result = RecoverySimulation(self.config, "protected").run()
        self.assertEqual(result.metrics["duplicate_business_outcomes"], 0)


if __name__ == "__main__":
    unittest.main()

