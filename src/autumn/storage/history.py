"""Transactional SQLite migrations and metadata-only activity."""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from autumn.controller.contracts import HistoryEvent

SCHEMA_VERSION = 1


class HistoryStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, timeout=1)
        try:
            self.migrate(path)
        except Exception:
            self.connection.close()
            raise

    def migrate(self, path: Path) -> None:
        exists = self.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_version'"
        ).fetchone()
        row = self.connection.execute("SELECT version FROM schema_version").fetchone() if exists else (0,)
        if row is None:
            raise ValueError("Incomplete history schema")
        current = row[0]
        if current > SCHEMA_VERSION:
            raise ValueError("Newer history schema")
        if current == SCHEMA_VERSION:
            return
        if path.stat().st_size:
            with sqlite3.connect(path.with_suffix(".migration-backup.sqlite")) as backup:
                self.connection.backup(backup)
        with self.connection:
            self.connection.execute("BEGIN IMMEDIATE")
            self.connection.execute("CREATE TABLE IF NOT EXISTS schema_version(version INTEGER NOT NULL)")
            self.connection.execute("DELETE FROM schema_version")
            self.connection.execute("INSERT INTO schema_version VALUES (?)", (SCHEMA_VERSION,))
            self.connection.execute("""CREATE TABLE IF NOT EXISTS action_events(
                id INTEGER PRIMARY KEY, created REAL NOT NULL, request_id TEXT NOT NULL UNIQUE,
                skill_id TEXT NOT NULL, origin TEXT NOT NULL, status TEXT NOT NULL,
                code TEXT NOT NULL, duration_ms INTEGER NOT NULL)""")
            # Later phases supply their own versioned columns and data migrations.
            for table in ("routines", "routine_steps", "app_catalog"):
                self.connection.execute(f"CREATE TABLE IF NOT EXISTS {table}(id TEXT PRIMARY KEY)")

    def add(self, event: HistoryEvent, now: float | None = None) -> None:
        with self.connection:
            self.connection.execute(
                "INSERT OR IGNORE INTO action_events(created,request_id,skill_id,origin,status,code,duration_ms) VALUES (?,?,?,?,?,?,?)",
                (time.time() if now is None else now, str(event.request_id), event.skill_id,
                 event.origin, event.status, event.code, event.duration_ms),
            )

    def list_recent(self) -> list[dict]:
        self.connection.row_factory = sqlite3.Row
        return [dict(row) for row in self.connection.execute(
            "SELECT created,skill_id,origin,status,code,duration_ms FROM action_events ORDER BY id DESC LIMIT 100"
        )]

    def prune(self, days: int, now: float | None = None) -> None:
        if not 1 <= days <= 90:
            raise ValueError("Invalid retention")
        with self.connection:
            self.connection.execute("DELETE FROM action_events WHERE created < ?", (
                (time.time() if now is None else now) - days * 86400,
            ))

    def clear(self) -> None:
        with self.connection:
            self.connection.execute("DELETE FROM action_events")

    def close(self) -> None:
        self.connection.close()
