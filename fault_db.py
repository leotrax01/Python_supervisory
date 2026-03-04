"""Persistência SQLite para cadastro de falhas do supervisório."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Dict, Iterable


class FaultRepository:
    def __init__(self, db_path: str = "faults.db") -> None:
        self.db_path = str(Path(db_path))
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS faults (
                d_address INTEGER PRIMARY KEY,
                description TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def seed_defaults(self, default_faults: Dict[int, str]) -> None:
        with self._lock:
            self._conn.executemany(
                "INSERT OR IGNORE INTO faults (d_address, description) VALUES (?, ?)",
                [(addr, desc) for addr, desc in default_faults.items()],
            )
            self._conn.commit()

    def upsert_fault(self, d_address: int, description: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO faults (d_address, description) VALUES (?, ?) "
                "ON CONFLICT(d_address) DO UPDATE SET description=excluded.description",
                (d_address, description),
            )
            self._conn.commit()

    def delete_fault(self, d_address: int) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM faults WHERE d_address = ?", (d_address,))
            self._conn.commit()

    def list_faults(self) -> list[tuple[int, str]]:
        with self._lock:
            cursor = self._conn.execute(
                "SELECT d_address, description FROM faults ORDER BY d_address"
            )
            return [(int(row[0]), str(row[1])) for row in cursor.fetchall()]

    def faults_map(self) -> Dict[int, str]:
        return {addr: desc for addr, desc in self.list_faults()}

    def close(self) -> None:
        with self._lock:
            self._conn.close()
