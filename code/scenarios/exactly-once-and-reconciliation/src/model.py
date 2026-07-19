"""SQLite reference model for exactly-once outcomes and derived-state repair.

This model validates failure semantics locally. It is not AWS evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import sqlite3
import time
from uuid import uuid4


class ExecutionBusy(Exception):
    pass


class InjectedCrash(Exception):
    pass


@dataclass(frozen=True)
class ExecutionResult:
    operation_key: str
    result: str
    replayed: bool


class ExactlyOnceModel:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.db = connection
        self.db.row_factory = sqlite3.Row

    def create_schema(self) -> None:
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS operations (
                operation_key TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                owner TEXT NOT NULL,
                lease_expires INTEGER NOT NULL,
                result TEXT,
                version INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS provider_effects (
                operation_key TEXT PRIMARY KEY,
                provider_reference TEXT NOT NULL,
                result TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS outbox (
                event_id TEXT PRIMARY KEY,
                operation_key TEXT NOT NULL UNIQUE,
                source_version INTEGER NOT NULL,
                payload TEXT NOT NULL,
                published INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS projection (
                operation_key TEXT PRIMARY KEY,
                source_version INTEGER NOT NULL,
                result TEXT NOT NULL
            );
            """
        )

    def acquire(
        self, operation_key: str, owner: str, now: int, lease_seconds: int
    ) -> ExecutionResult | None:
        with self.db:
            row = self.db.execute(
                "SELECT * FROM operations WHERE operation_key = ?",
                (operation_key,),
            ).fetchone()
            if row is None:
                self.db.execute(
                    "INSERT INTO operations(operation_key,status,owner,lease_expires) VALUES(?,?,?,?)",
                    (operation_key, "IN_PROGRESS", owner, now + lease_seconds),
                )
                return None
            if row["status"] == "COMPLETE":
                return ExecutionResult(operation_key, row["result"], replayed=True)
            if row["lease_expires"] > now and row["owner"] != owner:
                raise ExecutionBusy(operation_key)
            self.db.execute(
                "UPDATE operations SET owner = ?, lease_expires = ? WHERE operation_key = ?",
                (owner, now + lease_seconds, operation_key),
            )
            return None

    def invoke_provider(self, operation_key: str) -> str:
        """Provider uses the business operation key as its idempotency key."""
        row = self.db.execute(
            "SELECT result FROM provider_effects WHERE operation_key = ?",
            (operation_key,),
        ).fetchone()
        if row:
            return row["result"]
        result = json.dumps(
            {
                "status": "APPROVED",
                "provider_reference": f"provider-{uuid4()}",
            },
            sort_keys=True,
        )
        with self.db:
            self.db.execute(
                "INSERT INTO provider_effects(operation_key,provider_reference,result) VALUES(?,?,?)",
                (operation_key, json.loads(result)["provider_reference"], result),
            )
        return result

    def complete(self, operation_key: str, owner: str, result: str) -> None:
        """Completion and outbox creation share one transaction boundary."""
        with self.db:
            row = self.db.execute(
                "SELECT status, owner, version FROM operations WHERE operation_key = ?",
                (operation_key,),
            ).fetchone()
            if row is None or row["status"] != "IN_PROGRESS" or row["owner"] != owner:
                raise ExecutionBusy(operation_key)
            version = row["version"] + 1
            self.db.execute(
                "UPDATE operations SET status='COMPLETE', result=?, version=? WHERE operation_key=?",
                (result, version, operation_key),
            )
            self.db.execute(
                "INSERT OR IGNORE INTO outbox(event_id,operation_key,source_version,payload) VALUES(?,?,?,?)",
                (str(uuid4()), operation_key, version, result),
            )

    def execute(
        self,
        operation_key: str,
        owner: str,
        now: int | None = None,
        lease_seconds: int = 30,
        crash_after_provider: bool = False,
    ) -> ExecutionResult:
        now = int(time.time()) if now is None else now
        completed = self.acquire(operation_key, owner, now, lease_seconds)
        if completed:
            return completed
        result = self.invoke_provider(operation_key)
        if crash_after_provider:
            raise InjectedCrash(operation_key)
        self.complete(operation_key, owner, result)
        return ExecutionResult(operation_key, result, replayed=False)

    def publish_outbox(self, fail_before_marking: bool = False) -> int:
        records = self.db.execute(
            "SELECT * FROM outbox WHERE published = 0 ORDER BY operation_key"
        ).fetchall()
        published = 0
        for row in records:
            # The projection represents an independently committed destination.
            # It cannot share a transaction with the source outbox acknowledgement.
            with self.db:
                current = self.db.execute(
                    "SELECT source_version FROM projection WHERE operation_key = ?",
                    (row["operation_key"],),
                ).fetchone()
                if current is None or current["source_version"] < row["source_version"]:
                    self.db.execute(
                        "INSERT INTO projection(operation_key,source_version,result) VALUES(?,?,?) "
                        "ON CONFLICT(operation_key) DO UPDATE SET source_version=excluded.source_version,result=excluded.result",
                        (row["operation_key"], row["source_version"], row["payload"]),
                    )
            if fail_before_marking:
                raise InjectedCrash(row["operation_key"])
            with self.db:
                self.db.execute(
                    "UPDATE outbox SET published = 1 WHERE event_id = ?",
                    (row["event_id"],),
                )
                published += 1
        return published

    def reconciliation_counts(self) -> dict[str, int]:
        missing = self.db.execute(
            """
            SELECT COUNT(*) FROM operations o
            LEFT JOIN projection p ON p.operation_key=o.operation_key
            WHERE o.status='COMPLETE' AND p.operation_key IS NULL
            """
        ).fetchone()[0]
        mismatched = self.db.execute(
            """
            SELECT COUNT(*) FROM operations o
            JOIN projection p ON p.operation_key=o.operation_key
            WHERE o.status='COMPLETE' AND (p.source_version != o.version OR p.result != o.result)
            """
        ).fetchone()[0]
        extra = self.db.execute(
            """
            SELECT COUNT(*) FROM projection p
            LEFT JOIN operations o ON o.operation_key=p.operation_key
            WHERE o.operation_key IS NULL
            """
        ).fetchone()[0]
        return {"missing": missing, "mismatched": mismatched, "extra": extra}

    def repair_projection(self) -> int:
        rows = self.db.execute(
            "SELECT operation_key,version,result FROM operations WHERE status='COMPLETE'"
        ).fetchall()
        repaired = 0
        with self.db:
            for row in rows:
                projection = self.db.execute(
                    "SELECT source_version,result FROM projection WHERE operation_key=?",
                    (row["operation_key"],),
                ).fetchone()
                if (
                    projection is None
                    or projection["source_version"] != row["version"]
                    or projection["result"] != row["result"]
                ):
                    self.db.execute(
                        "INSERT INTO projection(operation_key,source_version,result) VALUES(?,?,?) "
                        "ON CONFLICT(operation_key) DO UPDATE SET source_version=excluded.source_version,result=excluded.result",
                        (row["operation_key"], row["version"], row["result"]),
                    )
                    repaired += 1
        return repaired

    def count(self, table: str) -> int:
        if table not in {"operations", "provider_effects", "outbox", "projection"}:
            raise ValueError(table)
        return self.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
