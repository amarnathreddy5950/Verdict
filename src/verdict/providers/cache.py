"""Tiny SQLite cache so identical model calls are not paid for twice."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path


class SqliteCache:
    def __init__(self, path: str | Path = ".verdict_cache.sqlite") -> None:
        self.path = str(path)
        self._conn = sqlite3.connect(self.path)
        self._conn.execute("CREATE TABLE IF NOT EXISTS cache (k TEXT PRIMARY KEY, v TEXT)")
        self._conn.commit()

    @staticmethod
    def make_key(*parts: object) -> str:
        digest = hashlib.sha256("\x1f".join(str(p) for p in parts).encode("utf-8"))
        return digest.hexdigest()

    def get(self, key: str) -> str | None:
        row = self._conn.execute("SELECT v FROM cache WHERE k = ?", (key,)).fetchone()
        return row[0] if row else None

    def set(self, key: str, value: str) -> None:
        self._conn.execute("INSERT OR REPLACE INTO cache (k, v) VALUES (?, ?)", (key, value))
        self._conn.commit()
