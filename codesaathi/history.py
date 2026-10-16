"""SQLite persistence for previous analyses."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path


def _connect(db_path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path), timeout=5)
    connection.row_factory = sqlite3.Row
    return connection


def initialize(db_path: str | Path) -> None:
    with closing(_connect(db_path)) as db:
        with db:
            db.execute("""CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            title TEXT NOT NULL,
            code TEXT NOT NULL,
            result_json TEXT NOT NULL
        )""")


def save(db_path: str | Path, title: str, code: str, result: dict) -> int:
    initialize(db_path)
    with closing(_connect(db_path)) as db:
        with db:
            cursor = db.execute("INSERT INTO analyses(title, code, result_json) VALUES (?, ?, ?)", (title[:100], code, json.dumps(result)))
            return int(cursor.lastrowid)


def list_recent(db_path: str | Path, limit: int = 50) -> list[dict]:
    initialize(db_path)
    with closing(_connect(db_path)) as db:
        rows = db.execute("SELECT id, created_at, title, code, result_json FROM analyses ORDER BY id DESC LIMIT ?", (max(1, min(limit, 100)),)).fetchall()
    return [{**dict(row), "result": json.loads(row["result_json"])} for row in rows]
