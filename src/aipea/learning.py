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
import json
import logging
import os
import sqlite3
import threading
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from aipea._types import QueryType
from aipea.security import _COMPLIANCE_TAINT_PREFIXES, ComplianceMode

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = "aipea_learning.db"
_MIN_SAMPLES = 3


@dataclass(frozen=True)
class LearningPolicy:
    """Controls compliance-aware behavior of the AdaptiveLearningEngine.

    Attributes:
        allow_hipaa_recording: If True, permit recording in HIPAA mode.
            Default False (deny). TACTICAL mode always blocks regardless.
        retention_days: Max age of learning events in days. None = no limit.
        max_events: Max total events in learning_events table. None = no limit.
        exclude_tainted_from_averaging: If True (the default), feedback
            associated with a query that fired a compliance-taint scanner flag
            is recorded to learning_events for audit but does NOT update
            strategy_performance. See ADR-004.
    """

    allow_hipaa_recording: bool = False
    retention_days: int | None = None
    max_events: int | None = None
    exclude_tainted_from_averaging: bool = True

    def __post_init__(self) -> None:
        if self.retention_days is not None and self.retention_days < 1:
            msg = f"retention_days must be >= 1 (got {self.retention_days})"
            raise ValueError(msg)
        if self.max_events is not None and self.max_events < 0:
            msg = f"max_events must be >= 0 (got {self.max_events})"
            raise ValueError(msg)


@dataclass(frozen=True)
class LearningEvent:
    """A single feedback observation recorded by the engine."""

    query_type: QueryType
    strategy_used: str
    feedback_score: float
    query_hash: str
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass(frozen=True)
class LearningRecordResult:
    """Outcome of a record_feedback call.

    Attributes:
        recorded: True if the event was persisted to learning_events.
        excluded_from_averaging: True if the event was persisted but NOT
            aggregated into strategy_performance (taint-gated).
        reason: Human-readable reason when recorded is False or when the
            event was excluded from averaging.
        taint_flags: The compliance-taint flags that fired (empty tuple = clean).
    """

    recorded: bool
    excluded_from_averaging: bool
    reason: str | None
    taint_flags: tuple[str, ...] = ()


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

    def __init__(
        self,
        db_path: str | Path | None = None,
        policy: LearningPolicy | None = None,
    ) -> None:
        self._policy = policy or LearningPolicy()
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
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    compliance_mode TEXT NOT NULL DEFAULT 'general',
                    taint_flags TEXT,
                    excluded_from_averaging INTEGER NOT NULL DEFAULT 0
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
            # Additive migration: add columns introduced in ADR-003 and ADR-004.
            # Each column is added independently so a failure in one does not
            # block the others; the engine degrades gracefully.
            columns = {
                row[1]
                for row in self._conn.execute("PRAGMA table_info(learning_events)").fetchall()
            }
            additive: list[tuple[str, str]] = [
                ("compliance_mode", "TEXT NOT NULL DEFAULT 'general'"),
                ("taint_flags", "TEXT"),
                ("excluded_from_averaging", "INTEGER NOT NULL DEFAULT 0"),
            ]
            for col, ddl in additive:
                if col not in columns:
                    try:
                        self._conn.execute(f"ALTER TABLE learning_events ADD COLUMN {col} {ddl}")
                    except sqlite3.Error:
                        logger.warning(
                            "Failed to add %s column to learning_events; "
                            "compliance auditing reduced",
                            col,
                            exc_info=True,
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
    # Compliance gating
    # ------------------------------------------------------------------

    def _should_record(self, mode: ComplianceMode) -> bool:
        """Check if recording is permitted for the given compliance mode."""
        if mode == ComplianceMode.TACTICAL:
            logger.debug("Learning record blocked: TACTICAL mode forbids persistence")
            return False
        if mode == ComplianceMode.HIPAA and not self._policy.allow_hipaa_recording:
            logger.info(
                "Learning record skipped: HIPAA mode requires explicit opt-in "
                "via LearningPolicy(allow_hipaa_recording=True)"
            )
            return False
        return True

    # ------------------------------------------------------------------
    # Public API — sync
    # ------------------------------------------------------------------

    def record_feedback(
        self,
        query_type: QueryType,
        strategy: str,
        score: float,
        compliance_mode: ComplianceMode | None = None,
        *,
        scan_flags: Sequence[str] = (),
    ) -> LearningRecordResult:
        """Record a feedback observation and update the running average.

        Parameters
        ----------
        query_type:
            The query type that was enhanced.
        strategy:
            The strategy name that was used for enhancement.
        score:
            User satisfaction score in ``[-1.0, 1.0]``.  Clamped if outside.
        compliance_mode:
            Active compliance mode.  Defaults to GENERAL.  TACTICAL always
            blocks recording; HIPAA blocks unless the engine's
            ``LearningPolicy.allow_hipaa_recording`` is True.
        scan_flags:
            Security scanner flags from the originating query's ScanResult.
            Compliance-taint flags (PII/PHI/classified/injection) gate
            strategy_performance averaging per ADR-004.
        """
        mode = compliance_mode or ComplianceMode.GENERAL
        if not self._should_record(mode):
            return LearningRecordResult(
                recorded=False,
                excluded_from_averaging=False,
                reason=f"{mode.value}_blocked",
            )

        # Compute taint from scan flags
        taint = tuple(
            f for f in scan_flags if any(f.startswith(p) for p in _COMPLIANCE_TAINT_PREFIXES)
        )
        exclude = bool(taint) and self._policy.exclude_tainted_from_averaging

        clamped = max(-1.0, min(1.0, score))
        qtype = query_type.value
        qhash = hashlib.sha256(qtype.encode()).hexdigest()[:16]
        ts = datetime.now(UTC).isoformat()
        taint_json = json.dumps(list(taint)) if taint else None

        try:
            with self._with_db_lock() as conn:
                conn.execute(
                    "INSERT INTO learning_events "
                    "(timestamp, query_type, strategy_used, feedback_score, query_hash, "
                    "compliance_mode, taint_flags, excluded_from_averaging) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (ts, qtype, strategy, clamped, qhash, mode.value, taint_json, int(exclude)),
                )
                if not exclude:
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
            return LearningRecordResult(
                recorded=False, excluded_from_averaging=False, reason="db_error"
            )

        if taint:
            logger.info(
                "Learning feedback recorded with compliance taint: flags=%s excluded=%s",
                taint,
                exclude,
            )

        return LearningRecordResult(
            recorded=True,
            excluded_from_averaging=exclude,
            reason="tainted" if taint else None,
            taint_flags=taint,
        )

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
        compliance_mode: ComplianceMode | None = None,
        *,
        scan_flags: Sequence[str] = (),
    ) -> LearningRecordResult:
        """Async wrapper around :meth:`record_feedback`."""
        return await asyncio.to_thread(
            self.record_feedback,
            query_type,
            strategy,
            score,
            compliance_mode,
            scan_flags=scan_flags,
        )

    async def aget_best_strategy(
        self,
        query_type: QueryType,
        min_samples: int = _MIN_SAMPLES,
    ) -> str | None:
        """Async wrapper around :meth:`get_best_strategy`."""
        return await asyncio.to_thread(self.get_best_strategy, query_type, min_samples)

    # ------------------------------------------------------------------
    # Retention
    # ------------------------------------------------------------------

    def prune_events(
        self,
        max_age_days: int | None = None,
        max_count: int | None = None,
    ) -> int:
        """Remove old or excess learning events.

        Falls back to ``LearningPolicy`` defaults when parameters are ``None``.

        Parameters
        ----------
        max_age_days:
            Delete events older than this many days.
        max_count:
            Keep at most this many events (FIFO by ``created_at``).

        Returns
        -------
        int
            Number of events deleted.
        """
        age = max_age_days if max_age_days is not None else self._policy.retention_days
        count = max_count if max_count is not None else self._policy.max_events

        if age is not None and age < 1:
            msg = f"max_age_days must be >= 1 (got {age})"
            raise ValueError(msg)
        if count is not None and count < 0:
            msg = f"max_count must be >= 0 (got {count})"
            raise ValueError(msg)

        if age is None and count is None:
            return 0

        deleted = 0
        try:
            with self._with_db_lock() as conn:
                if age is not None:
                    cutoff = (datetime.now(UTC) - timedelta(days=age)).isoformat()
                    cursor = conn.execute(
                        "DELETE FROM learning_events WHERE created_at < ?",
                        (cutoff,),
                    )
                    deleted += cursor.rowcount
                if count is not None:
                    total = conn.execute("SELECT COUNT(*) FROM learning_events").fetchone()[0]
                    excess = total - count
                    if excess > 0:
                        cursor = conn.execute(
                            "DELETE FROM learning_events WHERE id IN "
                            "(SELECT id FROM learning_events "
                            "ORDER BY created_at ASC LIMIT ?)",
                            (excess,),
                        )
                        deleted += cursor.rowcount
                if deleted > 0:
                    conn.commit()
        except sqlite3.Error:
            logger.warning("Failed to prune learning events", exc_info=True)
        return deleted

    async def aprune_events(
        self,
        max_age_days: int | None = None,
        max_count: int | None = None,
    ) -> int:
        """Async wrapper around :meth:`prune_events`."""
        return await asyncio.to_thread(self.prune_events, max_age_days, max_count)

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
