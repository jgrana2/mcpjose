"""Simple daily rate limiting utilities."""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone, tzinfo
from pathlib import Path
from typing import Optional


def _day_key(now: Optional[datetime] = None, tz: Optional[tzinfo] = None) -> str:
    if now is None:
        if tz is None:
            current = datetime.now().astimezone()
        else:
            current = datetime.now(tz)
    else:
        current = now
        if tz is not None:
            current = current.astimezone(tz)
        elif current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)

    return current.date().isoformat()


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    day: str
    used: int
    limit: int
    remaining: int


class DailyRateLimiter:
    """Process-local daily counter backed by SQLite.

    This is designed for a single-user MCP server process. If multiple processes
    share the same DB file concurrently, SQLite still provides basic safety,
    but correctness under high concurrency is not guaranteed.
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @classmethod
    def from_env(cls, default_path: Path) -> "DailyRateLimiter":
        configured = os.getenv("MCPJOSE_RATE_LIMIT_DB")
        return cls(Path(configured) if configured else default_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS daily_usage (
                  day TEXT NOT NULL,
                  scope TEXT NOT NULL,
                  used INTEGER NOT NULL,
                  PRIMARY KEY (day, scope)
                );
                """
            )

    def check(
        self,
        scope: str,
        limit: int,
        now: Optional[datetime] = None,
        tz: Optional[tzinfo] = None,
    ) -> RateLimitResult:
        day = _day_key(now, tz=tz)
        used = self._get_used(day, scope)
        remaining = max(0, limit - used)
        return RateLimitResult(
            allowed=used < limit,
            day=day,
            used=used,
            limit=limit,
            remaining=remaining,
        )

    def consume(
        self,
        scope: str,
        limit: int,
        amount: int = 1,
        now: Optional[datetime] = None,
        tz: Optional[tzinfo] = None,
    ) -> RateLimitResult:
        if amount <= 0:
            raise ValueError("amount must be >= 1")

        day = _day_key(now, tz=tz)
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE;")
            row = conn.execute(
                "SELECT used FROM daily_usage WHERE day=? AND scope=?;",
                (day, scope),
            ).fetchone()
            used = int(row[0]) if row else 0

            if used + amount > limit:
                remaining = max(0, limit - used)
                conn.execute("ROLLBACK;")
                return RateLimitResult(
                    allowed=False,
                    day=day,
                    used=used,
                    limit=limit,
                    remaining=remaining,
                )

            new_used = used + amount
            conn.execute(
                """
                INSERT INTO daily_usage(day, scope, used)
                VALUES(?, ?, ?)
                ON CONFLICT(day, scope) DO UPDATE SET used=excluded.used;
                """,
                (day, scope, new_used),
            )
            conn.execute("COMMIT;")

        remaining = max(0, limit - new_used)
        return RateLimitResult(
            allowed=True,
            day=day,
            used=new_used,
            limit=limit,
            remaining=remaining,
        )

    def _get_used(self, day: str, scope: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT used FROM daily_usage WHERE day=? AND scope=?;",
                (day, scope),
            ).fetchone()
            return int(row[0]) if row else 0
