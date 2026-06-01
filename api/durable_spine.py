from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

DEFAULT_DB_PATH = os.getenv("SPINE_DB_PATH", "data/operator_spine.db")


@dataclass
class SpineEventRow:
    event_type: str
    lane: str
    payload: dict[str, Any]
    timestamp: str
    height: int
    parent_event_hash: str
    evidence_hash: str
    event_hash: str


class DurableSpineStore:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or DEFAULT_DB_PATH
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;
                PRAGMA synchronous=NORMAL;

                CREATE TABLE IF NOT EXISTS spine_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    height INTEGER NOT NULL UNIQUE,
                    event_type TEXT NOT NULL,
                    lane TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    parent_event_hash TEXT NOT NULL,
                    evidence_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_spine_events_height ON spine_events(height);
                CREATE INDEX IF NOT EXISTS idx_spine_events_event_hash ON spine_events(event_hash);
                """
            )
            conn.commit()

    def get_height(self) -> int:
        with self.connect() as conn:
            row = conn.execute("SELECT COALESCE(MAX(height), -1) AS max_height FROM spine_events").fetchone()
            return int(row["max_height"]) + 1

    def get_tip_hash(self) -> str | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT event_hash FROM spine_events ORDER BY height DESC LIMIT 1"
            ).fetchone()
            return str(row["event_hash"]) if row else None

    def append_event(self, event: dict[str, Any]) -> dict[str, Any]:
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            latest = conn.execute(
                "SELECT height, event_hash FROM spine_events ORDER BY height DESC LIMIT 1"
            ).fetchone()
            next_height = (int(latest["height"]) + 1) if latest else 0
            expected_parent = str(latest["event_hash"]) if latest else ""
            actual_parent = str(event.get("parent_event_hash", "") or "")
            if actual_parent != expected_parent:
                raise ValueError(
                    f"Parent hash mismatch: expected {expected_parent!r}, got {actual_parent!r}"
                )

            event["height"] = next_height
            conn.execute(
                """
                INSERT INTO spine_events (
                    height, event_type, lane, payload_json, timestamp,
                    parent_event_hash, evidence_hash, event_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(event["height"]),
                    str(event["event_type"]),
                    str(event["lane"]),
                    json.dumps(event["payload"], ensure_ascii=False, separators=(",", ":"), sort_keys=True),
                    str(event["timestamp"]),
                    str(event["parent_event_hash"]),
                    str(event["evidence_hash"]),
                    str(event["event_hash"]),
                ),
            )
            conn.commit()
            return event

    def list_events(self, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 500))
        safe_offset = max(0, int(offset))
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT height, event_type, lane, payload_json, timestamp,
                       parent_event_hash, evidence_hash, event_hash
                FROM spine_events
                ORDER BY height ASC
                LIMIT ? OFFSET ?
                """,
                (safe_limit, safe_offset),
            ).fetchall()
            return [self._row_to_event(r) for r in rows]

    def total_events(self) -> int:
        with self.connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM spine_events").fetchone()
            return int(row["c"])

    def verify(self, from_height: int = 0) -> dict[str, Any]:
        safe_from = max(0, int(from_height))
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT height, parent_event_hash, event_hash
                FROM spine_events
                WHERE height >= ?
                ORDER BY height ASC
                """,
                (safe_from,),
            ).fetchall()
            previous_hash: str | None = None
            checked = 0
            for row in rows:
                height = int(row["height"])
                parent_hash = str(row["parent_event_hash"])
                event_hash = str(row["event_hash"])
                if checked == 0:
                    if height > 0:
                        prev = conn.execute(
                            "SELECT event_hash FROM spine_events WHERE height = ?",
                            (height - 1,),
                        ).fetchone()
                        previous_hash = str(prev["event_hash"]) if prev else None
                    else:
                        previous_hash = ""
                if parent_hash != (previous_hash or ""):
                    return {
                        "valid": False,
                        "broken_at": height,
                        "expected": previous_hash or "",
                        "got": parent_hash,
                    }
                previous_hash = event_hash
                checked += 1
            tip = previous_hash if rows else self.get_tip_hash()
            return {"valid": True, "checked": checked, "tip": tip}

    def _row_to_event(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "event_type": str(row["event_type"]),
            "lane": str(row["lane"]),
            "payload": json.loads(str(row["payload_json"])),
            "timestamp": str(row["timestamp"]),
            "height": int(row["height"]),
            "parent_event_hash": str(row["parent_event_hash"]),
            "evidence_hash": str(row["evidence_hash"]),
            "event_hash": str(row["event_hash"]),
        }
