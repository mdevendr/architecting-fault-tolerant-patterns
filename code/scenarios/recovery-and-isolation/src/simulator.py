"""Deterministic recovery-storm and cell-isolation simulator.

The simulator is deliberately independent of AWS. It proves the scenario and
evidence logic before deployment; it does not represent cloud evidence.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Deque, Iterable


@dataclass
class Message:
    message_id: str
    tenant: str
    cell: str
    created_tick: int
    attempts: int = 0
    next_attempt_tick: int = 0


@dataclass(frozen=True)
class SimulationConfig:
    duration_ticks: int = 90
    outage_start: int = 15
    outage_end: int = 35
    downstream_capacity_per_tick: int = 12
    normal_arrivals_per_tick: int = 4
    noisy_arrivals_per_tick: int = 10
    noisy_start: int = 8
    noisy_end: int = 42
    max_attempts_per_tick_naive: int = 200
    protected_initial_rate: int = 3
    protected_ramp_per_tick: int = 1
    protected_max_rate: int = 12
    retry_delay_ticks: int = 1


@dataclass
class SimulationResult:
    mode: str
    metrics: dict[str, float | int]
    timeline: list[dict[str, int]] = field(default_factory=list)


class RecoverySimulation:
    def __init__(self, config: SimulationConfig, mode: str) -> None:
        if mode not in {"naive", "protected"}:
            raise ValueError("mode must be naive or protected")
        self.config = config
        self.mode = mode
        self.queues: dict[str, Deque[Message]] = {
            "cell-a": deque(),
            "cell-b": deque(),
        }
        self.completed: set[str] = set()
        self.business_outcomes: defaultdict[str, int] = defaultdict(int)
        self.total_attempts = 0
        self.total_retries = 0
        self.total_throttled = 0
        self.peak_attempts = 0
        self.max_healthy_cell_age = 0
        self.timeline: list[dict[str, int]] = []

    def _arrivals(self, tick: int) -> Iterable[Message]:
        for index in range(self.config.normal_arrivals_per_tick):
            yield Message(
                message_id=f"normal-{tick}-{index}",
                tenant="tenant-normal",
                cell="cell-b",
                created_tick=tick,
            )
        noisy_count = (
            self.config.noisy_arrivals_per_tick
            if self.config.noisy_start <= tick < self.config.noisy_end
            else 1
        )
        for index in range(noisy_count):
            yield Message(
                message_id=f"noisy-{tick}-{index}",
                tenant="tenant-noisy",
                cell="cell-a",
                created_tick=tick,
            )

    def _attempt_budget(self, tick: int, cell: str) -> int:
        if self.mode == "naive":
            return self.config.max_attempts_per_tick_naive
        if cell == "cell-b":
            return self.config.downstream_capacity_per_tick
        ticks_since_recovery = max(0, tick - self.config.outage_end)
        return min(
            self.config.protected_max_rate,
            self.config.protected_initial_rate
            + ticks_since_recovery * self.config.protected_ramp_per_tick,
        )

    def _dependency_available(self, tick: int, cell: str) -> bool:
        return not (
            cell == "cell-a"
            and self.config.outage_start <= tick < self.config.outage_end
        )

    def _process_cell(self, tick: int, cell: str) -> tuple[int, int]:
        queue = self.queues[cell]
        budget = self._attempt_budget(tick, cell)
        capacity = self.config.downstream_capacity_per_tick
        attempts = successes = 0
        initial_length = len(queue)

        for _ in range(initial_length):
            if attempts >= budget:
                break
            message = queue.popleft()
            if message.next_attempt_tick > tick:
                queue.append(message)
                continue

            attempts += 1
            self.total_attempts += 1
            if message.attempts:
                self.total_retries += 1
            message.attempts += 1

            available = self._dependency_available(tick, cell)
            accepted = available and successes < capacity
            if accepted:
                successes += 1
                if message.message_id not in self.completed:
                    self.completed.add(message.message_id)
                    self.business_outcomes[message.message_id] += 1
            else:
                self.total_throttled += 1
                message.next_attempt_tick = tick + self.config.retry_delay_ticks
                queue.append(message)

        return attempts, successes

    def run(self) -> SimulationResult:
        total_arrivals = 0
        for tick in range(self.config.duration_ticks):
            for message in self._arrivals(tick):
                self.queues[message.cell].append(message)
                total_arrivals += 1

            attempts_a, completed_a = self._process_cell(tick, "cell-a")
            attempts_b, completed_b = self._process_cell(tick, "cell-b")
            attempts = attempts_a + attempts_b
            self.peak_attempts = max(self.peak_attempts, attempts_a)

            healthy_age = (
                tick - self.queues["cell-b"][0].created_tick
                if self.queues["cell-b"]
                else 0
            )
            self.max_healthy_cell_age = max(self.max_healthy_cell_age, healthy_age)
            self.timeline.append(
                {
                    "tick": tick,
                    "attempts": attempts,
                    "attempts_cell_a": attempts_a,
                    "attempts_cell_b": attempts_b,
                    "completed_cell_a": completed_a,
                    "completed_cell_b": completed_b,
                    "queue_cell_a": len(self.queues["cell-a"]),
                    "queue_cell_b": len(self.queues["cell-b"]),
                }
            )

        unprocessed = sum(len(queue) for queue in self.queues.values())
        duplicate_outcomes = sum(
            max(0, count - 1) for count in self.business_outcomes.values()
        )
        retry_amplification = (
            round(self.total_attempts / len(self.completed), 3)
            if self.completed
            else 0
        )
        metrics: dict[str, float | int] = {
            "total_arrivals": total_arrivals,
            "completed_messages": len(self.completed),
            "unprocessed_messages": unprocessed,
            "total_attempts": self.total_attempts,
            "retry_attempts": self.total_retries,
            "throttled_attempts": self.total_throttled,
            "retry_amplification": retry_amplification,
            "peak_attempts_cell_a_per_tick": self.peak_attempts,
            "healthy_cell_oldest_message_age_ticks": self.max_healthy_cell_age,
            "duplicate_business_outcomes": duplicate_outcomes,
        }
        return SimulationResult(mode=self.mode, metrics=metrics, timeline=self.timeline)

