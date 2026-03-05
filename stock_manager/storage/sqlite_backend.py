"""SQLite-backed state storage replacing JSON files.

Migration strategy: new writes go to SQLite, reads fall back to JSON.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SQLiteStateBackend:
    """Key-value state storage backed by SQLite."""

    def __init__(self, db_path: str | Path = "data/state.db") -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._init_schema()

    def _init_schema(self) -> None:
        """Create the state table if it does not exist."""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        self._conn.commit()

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value by key, returning default if not found."""
        row = self._conn.execute(
            "SELECT value FROM state WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return default
        return json.loads(row[0])

    def set(self, key: str, value: Any) -> None:
        """Store a value by key, replacing any existing entry."""
        self._conn.execute(
            "INSERT OR REPLACE INTO state (key, value, updated_at) VALUES (?, ?, datetime('now'))",
            (key, json.dumps(value)),
        )
        self._conn.commit()

    def delete(self, key: str) -> bool:
        """Delete a key. Returns True if the key existed."""
        cursor = self._conn.execute("DELETE FROM state WHERE key = ?", (key,))
        self._conn.commit()
        return cursor.rowcount > 0

    def keys(self) -> list[str]:
        """Return all stored keys."""
        rows = self._conn.execute("SELECT key FROM state").fetchall()
        return [r[0] for r in rows]

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()
