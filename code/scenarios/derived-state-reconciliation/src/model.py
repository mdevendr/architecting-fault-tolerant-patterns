"""Deterministic model of a versioned projection and anti-entropy repair."""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class Record:
    record_id: str
    version: int
    value: str


@dataclass
class ProjectionModel:
    source: Dict[str, Record] = field(default_factory=dict)
    projection: Dict[str, Record] = field(default_factory=dict)
    quarantined: List[str] = field(default_factory=list)

    def apply_event(self, record: Record, event_id: str, poison: bool = False) -> str:
        if poison:
            self.quarantined.append(event_id)
            return "QUARANTINED"
        current = self.projection.get(record.record_id)
        if current and current.version >= record.version:
            return "DUPLICATE_OR_STALE"
        self.projection[record.record_id] = record
        return "APPLIED"

    def divergence(self):
        source_keys = set(self.source)
        projection_keys = set(self.projection)
        missing = sorted(source_keys - projection_keys)
        extra = sorted(projection_keys - source_keys)
        mismatched = sorted(
            key for key in source_keys & projection_keys
            if self.source[key] != self.projection[key]
        )
        return {"missing": missing, "extra": extra, "mismatched": mismatched}

    def reconcile(self):
        differences = self.divergence()
        for key in differences["missing"] + differences["mismatched"]:
            self.projection[key] = self.source[key]
        for key in differences["extra"]:
            del self.projection[key]
        return differences

