import sqlite3
from unittest.mock import patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

from autumn.controller.contracts import HistoryEvent
from autumn.storage.history import HistoryStore


def event(status="unverified"):
    return HistoryEvent(request_id=uuid4(), origin="typed", status=status, code="SIMULATED", duration_ms=20)


def test_metadata_only_retention_and_clear(tmp_path):
    path = tmp_path / "history é" / "jarvis.db"
    store = HistoryStore(path)
    store.add(event(), now=1)
    for status in ("succeeded", "failed", "unverified", "cancelled", "partial"):
        store.add(event(status), now=900000)
    store.prune(7, now=900000)
    rows = store.list_recent()
    assert len(rows) == 5
    assert {row["status"] for row in rows} == {"succeeded", "failed", "unverified", "cancelled", "partial"}
    assert set(rows[0]) == {"created", "skill_id", "origin", "status", "code", "duration_ms"}
    store.close()
    reopened = HistoryStore(path)
    assert len(reopened.list_recent()) == 5
    reopened.clear()
    assert reopened.list_recent() == []
    reopened.close()


def test_schema_migration_backups_and_future_refusal(tmp_path):
    path = tmp_path / "jarvis.db"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE placeholder(id INTEGER)")
    store = HistoryStore(path)
    assert path.with_suffix(".migration-backup.sqlite").is_file()
    store.connection.execute("UPDATE schema_version SET version=99")
    store.connection.commit()
    store.close()
    with pytest.raises(ValueError):
        HistoryStore(path)


def test_transcript_cannot_enter_history():
    with pytest.raises(ValidationError):
        HistoryEvent(**event().model_dump(), transcript="private text")


def test_failed_migration_rolls_back_ddl(tmp_path):
    path = tmp_path / "jarvis.db"
    connection = sqlite3.connect(path)

    def authorizer(action, table, *_):
        return sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_CREATE_TABLE and table == "routines" else sqlite3.SQLITE_OK

    connection.set_authorizer(authorizer)
    with patch("autumn.storage.history.sqlite3.connect", return_value=connection):
        with pytest.raises(sqlite3.DatabaseError):
            HistoryStore(path)
    with sqlite3.connect(path) as fresh:
        assert fresh.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == []
