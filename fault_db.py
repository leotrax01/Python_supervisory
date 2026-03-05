"""Persistência SQLite para cadastro de falhas do supervisório."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Dict


class FaultRepository:
    def __init__(self, db_path: str = "faults.db") -> None:
        self.db_path = str(Path(db_path))
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        columns = self._table_columns("faults")
        if not columns:
            self._create_schema()
            return

        required = {"point_key", "word_address", "bit_index", "description"}
        if required.issubset(set(columns)):
            return

        # Migração do esquema antigo (d_address, description) para o novo
        if {"d_address", "description"}.issubset(set(columns)):
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS faults_new (
                    point_key TEXT PRIMARY KEY,
                    word_address INTEGER NOT NULL,
                    bit_index INTEGER,
                    description TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                INSERT OR IGNORE INTO faults_new (point_key, word_address, bit_index, description)
                SELECT 'D' || d_address, d_address, NULL, description
                FROM faults
                """
            )
            self._conn.execute("DROP TABLE faults")
            self._conn.execute("ALTER TABLE faults_new RENAME TO faults")
            self._conn.commit()
            return

        self._conn.execute("DROP TABLE faults")
        self._create_schema()

    def _create_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS faults (
                point_key TEXT PRIMARY KEY,
                word_address INTEGER NOT NULL,
                bit_index INTEGER,
                description TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def _table_columns(self, table_name: str) -> list[str]:
        rows = self._conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        return [str(row[1]) for row in rows]

    def seed_defaults(self, default_faults: Dict[str, tuple[int, int | None, str]]) -> None:
        with self._lock:
            self._conn.executemany(
                """
                INSERT OR IGNORE INTO faults (point_key, word_address, bit_index, description)
                VALUES (?, ?, ?, ?)
                """,
                [(key, word, bit, desc) for key, (word, bit, desc) in default_faults.items()],
            )
            self._conn.commit()

    def upsert_fault(self, point_key: str, word_address: int, bit_index: int | None, description: str) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO faults (point_key, word_address, bit_index, description)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(point_key)
                DO UPDATE SET word_address=excluded.word_address,
                              bit_index=excluded.bit_index,
                              description=excluded.description
                """,
                (point_key, word_address, bit_index, description),
            )
            self._conn.commit()

    def delete_fault(self, point_key: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM faults WHERE point_key = ?", (point_key,))
            self._conn.commit()

    def list_faults(self) -> list[tuple[str, str]]:
        with self._lock:
            cursor = self._conn.execute(
                "SELECT point_key, description FROM faults ORDER BY word_address, bit_index"
            )
            return [(str(row[0]), str(row[1])) for row in cursor.fetchall()]

    def list_points(self) -> list[tuple[str, int, int | None, str]]:
        with self._lock:
            cursor = self._conn.execute(
                "SELECT point_key, word_address, bit_index, description FROM faults ORDER BY word_address, bit_index"
            )
            return [
                (str(row[0]), int(row[1]), None if row[2] is None else int(row[2]), str(row[3]))
                for row in cursor.fetchall()
            ]

    def faults_map(self) -> Dict[str, str]:
        return {key: desc for key, desc in self.list_faults()}

    def close(self) -> None:
        with self._lock:
            self._conn.close()
