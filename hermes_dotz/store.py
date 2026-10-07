"""Lightweight persistent SQLite store for Hermes Dotz bridge.

Compatible with existing drex-dotz database schemas and extensible for generic providers.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class DotzStore:
    """Thread-safe SQLite storage for dots, tasks, receipts, activities, and approvals."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._init_schema()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._get_conn() as conn:
            cur = conn.cursor()
            # 1. dots table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS dots (
                name TEXT PRIMARY KEY,
                state TEXT NOT NULL,
                created_at REAL,
                updated_at REAL,
                last_result TEXT,
                project_id TEXT,
                provider TEXT DEFAULT 'open-dotz',
                mission TEXT,
                models TEXT,
                capabilities TEXT,
                workspace TEXT
            );
            """)

            # Ensure columns exist if migrating from an older DB
            cur.execute("PRAGMA table_info(dots)")
            cols = {row["name"] for row in cur.fetchall()}
            for col, col_type in [
                ("provider", "TEXT DEFAULT 'open-dotz'"),
                ("mission", "TEXT"),
                ("models", "TEXT"),
                ("capabilities", "TEXT"),
                ("workspace", "TEXT"),
            ]:
                if col not in cols:
                    cur.execute(f"ALTER TABLE dots ADD COLUMN {col} {col_type};")

            # 2. tasks table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                dot TEXT NOT NULL,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                source TEXT NOT NULL,
                event_id TEXT,
                responsibility TEXT,
                parent_task_id TEXT,
                parent_dot TEXT,
                expected_output TEXT,
                deadline REAL,
                ceiling TEXT,
                session_id TEXT NOT NULL,
                steps INTEGER DEFAULT 0,
                obligation TEXT,
                next_action TEXT,
                result TEXT,
                created_at REAL,
                updated_at REAL
            );
            """)

            # 3. receipts table (Drex & audit)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS receipts (
                receipt_id TEXT PRIMARY KEY,
                ts REAL NOT NULL,
                who TEXT,
                dot TEXT,
                task_id TEXT,
                session_id TEXT,
                why TEXT,
                model TEXT,
                capability TEXT,
                grant_id TEXT,
                target TEXT,
                action TEXT,
                decision TEXT,
                reason TEXT,
                rule TEXT,
                drex_action_id TEXT,
                cost_usd REAL,
                input_tokens INTEGER,
                output_tokens INTEGER,
                result TEXT,
                verification TEXT,
                upstream_executed INTEGER,
                output_sha256 TEXT
            );
            """)

            # 4. generic approvals table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS approvals (
                approval_id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                dot_id TEXT NOT NULL,
                action TEXT NOT NULL,
                description TEXT NOT NULL,
                scope TEXT NOT NULL,
                payload_summary TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL,
                status TEXT NOT NULL,
                target TEXT,
                task_id TEXT,
                session_id TEXT,
                capability TEXT,
                details_json TEXT
            );
            """)

            # 5. activity events table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS activity_events (
                event_id TEXT PRIMARY KEY,
                dot_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                title TEXT NOT NULL,
                timestamp REAL NOT NULL,
                description TEXT,
                details_json TEXT
            );
            """)

            # 6. responsibilities table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS responsibilities (
                dot TEXT NOT NULL,
                name TEXT NOT NULL,
                trigger TEXT NOT NULL,
                next_due_at REAL,
                current_task TEXT,
                last_result TEXT,
                last_run_at REAL,
                PRIMARY KEY (dot, name)
            );
            """)

            # 7. grants table (for Drex)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS grants (
                grant_id TEXT PRIMARY KEY,
                dot TEXT NOT NULL,
                task_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                workspace TEXT NOT NULL,
                capability TEXT NOT NULL,
                resources TEXT NOT NULL,
                issued_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                max_uses INTEGER NOT NULL,
                uses INTEGER NOT NULL DEFAULT 0,
                approved_by TEXT,
                revoked INTEGER NOT NULL DEFAULT 0
            );
            """)

            conn.commit()

    def one(self, query: str, args: Tuple[Any, ...] = ()) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(query, args)
            row = cur.fetchone()
            return dict(row) if row else None

    def all(self, query: str, args: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(query, args)
            return [dict(row) for row in cur.fetchall()]

    def execute(self, query: str, args: Tuple[Any, ...] = ()) -> int:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(query, args)
            conn.commit()
            return cur.rowcount

    def insert(self, table: str, data: Dict[str, Any]) -> None:
        keys = list(data.keys())
        placeholders = ", ".join(["?"] * len(keys))
        columns = ", ".join(keys)
        sql = f"INSERT OR REPLACE INTO {table} ({columns}) VALUES ({placeholders})"
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, tuple(data[k] for k in keys))
            conn.commit()

    def record_activity(
        self,
        dot_id: str,
        event_type: str,
        title: str,
        description: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        event_id: Optional[str] = None,
    ) -> str:
        eid = event_id or f"evt_{int(time.time() * 1000)}_{title[:8]}"
        self.insert(
            "activity_events",
            {
                "event_id": eid,
                "dot_id": dot_id,
                "event_type": event_type,
                "title": title,
                "timestamp": time.time(),
                "description": description,
                "details_json": json.dumps(details or {}),
            },
        )
        return eid
