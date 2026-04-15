"""AIPEA Adaptive Learning Engine — learns from user feedback to improve strategy selection.

Records enhancement feedback in SQLite, tracks per-strategy performance as
running averages, and suggests the historically best-performing strategy for
each query type.  Opt-in via ``AIPEAEnhancer(enable_learning=True)``.

Design origin: ``docs/design-reference/aipea-offline-knowledge.py:632-747``.
Reimplemented with stdlib only (sqlite3, threading, hashlib) to preserve the
zero-external-deps-in-core principle.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import logging
import os
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aipea._types import QueryType

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = "aipea_learning.db"
_MIN_SAMPLES = 3


@dataclass(frozen=True)
class LearningEvent:
    """A single feedback observation recorded by the engine."""

    query_type: QueryType
    strategy_used: str
    feedback_score: float
    query_hash: str
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class AdaptiveLearningEngine:
    """SQLite-backed learning engine for strategy performance tracking.

    Thread-safe via ``threading.RLock`` (same pattern as
    ``OfflineKnowledgeBase`` in ``knowledge.py``).

    Parameters
    ----------
    db_path:
        Path to the SQLite database file.  Defaults to the value of
        ``AIPEA_LEARNING_DB_PATH`` env var, or ``aipea_learning.db``.
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        resolved = db_path or os.environ.get("AIPEA_LEARNING_DB_PATH", _DEFAULT_DB_PATH)
        self._db_path = Path(resolved)
        self._db_lock = threading.RLock()
        self._conn: sqlite3.Connection | None = None
        try:
            self._conn = self._open_connection()
            self._init_schema()
        except sqlite3.Error:
            logger.warning(
                "Failed to initialise learning DB at %s; learning disabled",
                self._db_path,
                exc_info=True,
            )
            if self._conn is not None:  # (#110)
                with contextlib.suppress(sqlite3.Error):
                    self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------

    def _open_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.Error:  # (#111)
            with contextlib.suppress(sqlite3.Error):
                conn.close()
            raise
        return conn

    def _init_schema(self) -> None:
        assert self._conn is not None  # noqa: S101 — internal invariant
        with self._db_lock:
            self._conn.executescript(
                """\
                CREATE TABLE IF NOT EXISTS learning_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    query_type TEXT NOT NULL,
                    strategy_used TEXT NOT NULL,
                    feedback_score REAL NOT NULL,
                    query_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS strategy_performance (
                    query_type TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    total_count INTEGER NOT NULL DEFAULT 0,
                    success_count INTEGER NOT NULL DEFAULT 0,
                    avg_score REAL NOT NULL DEFAULT 0.0,
                    last_updated TEXT NOT NULL DEFAULT (datetime('now')),
                    PRIMARY KEY (query_type, strategy)
                );
                """
            )

    @contextmanager
    def _with_db_lock(self) -> Iterator[sqlite3.Connection]:
        """Acquire the lock and yield the connection (mirrors knowledge.py)."""
        with self._db_lock:
            if self._conn is None:
                msg = "Learning DB is not initialised"
                raise sqlite3.OperationalError(msg)
            yield self._conn

    # ------------------------------------------------------------------
    # Public API — sync
    # ------------------------------------------------------------------

    def record_feedback(
        self,
        query_type: QueryType,
        strategy: str,
        score: float,
    ) -> None:
        """Record a feedback observation and update the running average.

        Parameters
        ----------
        query_type:
            The query type that was enhanced.
        strategy:
            The strategy name that was used for enhancement.
        score:
            User satisfaction score in ``[-1.0, 1.0]``.  Clamped if outside.
        """
        clamped = max(-1.0, min(1.0, score))
        qtype = query_type.value
        qhash = hashlib.sha256(qtype.encode()).hexdigest()[:16]
        ts = datetime.now(UTC).isoformat()

        try:
            with self._with_db_lock() as conn:
                conn.execute(
                    "INSERT INTO learning_events "
                    "(timestamp, query_type, strategy_used, feedback_score, query_hash) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (ts, qtype, strategy, clamped, qhash),
                )
                # Upsert running average in strategy_performance
                conn.execute(
                    """\
                    INSERT INTO strategy_performance
                        (query_type, strategy, total_count, success_count,
                         avg_score, last_updated)
                    VALUES (?, ?, 1, ?, ?, ?)
                    ON CONFLICT(query_type, strategy) DO UPDATE SET
                        total_count = total_count + 1,
                        success_count = success_count + CASE WHEN ? > 0.0 THEN 1 ELSE 0 END,
                        avg_score = (avg_score * total_count + ?) / (total_count + 1),
                        last_updated = ?
                    """,
                    (
                        qtype,
                        strategy,
                        1 if clamped > 0.0 else 0,
                        clamped,
                        ts,
                        # ON CONFLICT params:
                        clamped,  # success_count CASE
                        clamped,  # avg_score numerator
                        ts,  # last_updated
                    ),
                )
                conn.commit()
        except sqlite3.Error:
            logger.warning("Failed to record learning feedback", exc_info=True)

    def get_best_strategy(
        self,
        query_type: QueryType,
        min_samples: int = _MIN_SAMPLES,
    ) -> str | None:
        """Return the strategy with the highest avg score for *query_type*.

        Returns ``None`` if no strategy has at least *min_samples* observations
        or if the learning DB is unavailable.
        """
        try:
            with self._with_db_lock() as conn:
                row = conn.execute(
                    "SELECT strategy FROM strategy_performance "
                    "WHERE query_type = ? AND total_count >= ? "
                    "ORDER BY avg_score DESC LIMIT 1",
                    (query_type.value, min_samples),
                ).fetchone()
                return row["strategy"] if row else None
        except sqlite3.Error:
            logger.warning("Failed to query learning DB", exc_info=True)
            return None

    def get_stats(self) -> dict[str, Any]:
        """Return summary statistics about the learning database."""
        try:
            with self._with_db_lock() as conn:
                total_events = conn.execute("SELECT COUNT(*) FROM learning_events").fetchone()[0]
                strategies_tracked = conn.execute(
                    "SELECT COUNT(*) FROM strategy_performance"
                ).fetchone()[0]
                query_types_with_data = conn.execute(
                    "SELECT COUNT(DISTINCT query_type) FROM strategy_performance"
                ).fetchone()[0]
                return {
                    "total_events": total_events,
                    "strategies_tracked": strategies_tracked,
                    "query_types_with_data": query_types_with_data,
                }
        except sqlite3.Error:
            logger.warning("Failed to read learning stats", exc_info=True)
            return {"total_events": 0, "strategies_tracked": 0, "query_types_with_data": 0}

    # ------------------------------------------------------------------
    # Public API — async wrappers
    # ------------------------------------------------------------------

    async def arecord_feedback(
        self,
        query_type: QueryType,
        strategy: str,
        score: float,
    ) -> None:
        """Async wrapper around :meth:`record_feedback`."""
        await asyncio.to_thread(self.record_feedback, query_type, strategy, score)

    async def aget_best_strategy(
        self,
        query_type: QueryType,
        min_samples: int = _MIN_SAMPLES,
    ) -> str | None:
        """Async wrapper around :meth:`get_best_strategy`."""
        return await asyncio.to_thread(self.get_best_strategy, query_type, min_samples)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        import contextlib

        with self._db_lock:
            if self._conn is not None:
                with contextlib.suppress(sqlite3.Error):
                    self._conn.close()
                self._conn = None

    def __enter__(self) -> AdaptiveLearningEngine:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def __del__(self) -> None:
        self.close()
