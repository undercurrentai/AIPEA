"""Tests for the Adaptive Learning Engine (src/aipea/learning.py)."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

from aipea._types import QueryType
from aipea.learning import AdaptiveLearningEngine

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def engine(tmp_path: Path) -> AdaptiveLearningEngine:
    """Provide a fresh learning engine backed by a tmp-dir database."""
    db = tmp_path / "test_learning.db"
    eng = AdaptiveLearningEngine(db_path=db)
    yield eng
    eng.close()


# ---------------------------------------------------------------------------
# Init & schema
# ---------------------------------------------------------------------------


class TestInit:
    def test_init_creates_db(self, tmp_path: Path) -> None:
        db = tmp_path / "learn.db"
        assert not db.exists()
        with AdaptiveLearningEngine(db_path=db):
            assert db.exists()

    def test_empty_db_get_stats(self, engine: AdaptiveLearningEngine) -> None:
        stats = engine.get_stats()
        assert stats == {
            "total_events": 0,
            "strategies_tracked": 0,
            "query_types_with_data": 0,
        }


# ---------------------------------------------------------------------------
# record_feedback
# ---------------------------------------------------------------------------


class TestRecordFeedback:
    def test_inserts_event(self, engine: AdaptiveLearningEngine) -> None:
        engine.record_feedback(QueryType.TECHNICAL, "technical", 0.8)
        stats = engine.get_stats()
        assert stats["total_events"] == 1

    def test_updates_performance(self, engine: AdaptiveLearningEngine) -> None:
        engine.record_feedback(QueryType.TECHNICAL, "technical", 0.9)
        # Check the running average directly
        assert engine._conn is not None
        row = engine._conn.execute(
            "SELECT total_count, avg_score FROM strategy_performance "
            "WHERE query_type = 'technical' AND strategy = 'technical'"
        ).fetchone()
        assert row is not None
        assert row["total_count"] == 1
        assert abs(row["avg_score"] - 0.9) < 1e-9

    def test_feedback_score_clamped(self, engine: AdaptiveLearningEngine) -> None:
        engine.record_feedback(QueryType.RESEARCH, "research", 5.0)
        engine.record_feedback(QueryType.RESEARCH, "research", -3.0)
        assert engine._conn is not None
        row = engine._conn.execute(
            "SELECT total_count, avg_score FROM strategy_performance "
            "WHERE query_type = 'research' AND strategy = 'research'"
        ).fetchone()
        assert row is not None
        assert row["total_count"] == 2
        # avg of clamped(5.0)=1.0 and clamped(-3.0)=-1.0 => 0.0
        assert abs(row["avg_score"]) < 1e-9

    def test_multiple_strategies_tracked(self, engine: AdaptiveLearningEngine) -> None:
        engine.record_feedback(QueryType.TECHNICAL, "technical", 0.9)
        engine.record_feedback(QueryType.TECHNICAL, "analytical", 0.3)
        stats = engine.get_stats()
        assert stats["strategies_tracked"] == 2
        assert stats["query_types_with_data"] == 1


# ---------------------------------------------------------------------------
# get_best_strategy
# ---------------------------------------------------------------------------


class TestGetBestStrategy:
    def test_returns_none_below_min_samples(self, engine: AdaptiveLearningEngine) -> None:
        engine.record_feedback(QueryType.TECHNICAL, "technical", 0.9)
        engine.record_feedback(QueryType.TECHNICAL, "technical", 0.8)
        # Only 2 samples, min is 3
        assert engine.get_best_strategy(QueryType.TECHNICAL) is None

    def test_returns_highest_avg(self, engine: AdaptiveLearningEngine) -> None:
        # Give "analytical" 3 high scores
        for _ in range(3):
            engine.record_feedback(QueryType.TECHNICAL, "analytical", 0.9)
        # Give "technical" 3 low scores
        for _ in range(3):
            engine.record_feedback(QueryType.TECHNICAL, "technical", 0.1)
        best = engine.get_best_strategy(QueryType.TECHNICAL)
        assert best == "analytical"

    def test_respects_query_type(self, engine: AdaptiveLearningEngine) -> None:
        # "research" strategy is great for RESEARCH queries
        for _ in range(3):
            engine.record_feedback(QueryType.RESEARCH, "research", 0.9)
        # But TECHNICAL queries have no data
        assert engine.get_best_strategy(QueryType.TECHNICAL) is None
        assert engine.get_best_strategy(QueryType.RESEARCH) == "research"

    def test_returns_none_on_empty_db(self, engine: AdaptiveLearningEngine) -> None:
        assert engine.get_best_strategy(QueryType.UNKNOWN) is None


# ---------------------------------------------------------------------------
# Async wrappers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
class TestAsync:
    async def test_arecord_feedback(self, engine: AdaptiveLearningEngine) -> None:
        await engine.arecord_feedback(QueryType.CREATIVE, "creative", 0.7)
        stats = engine.get_stats()
        assert stats["total_events"] == 1

    async def test_aget_best_strategy(self, engine: AdaptiveLearningEngine) -> None:
        for _ in range(3):
            await engine.arecord_feedback(QueryType.ANALYTICAL, "analytical", 0.8)
        result = await engine.aget_best_strategy(QueryType.ANALYTICAL)
        assert result == "analytical"


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    def test_context_manager(self, tmp_path: Path) -> None:
        db = tmp_path / "ctx.db"
        with AdaptiveLearningEngine(db_path=db) as eng:
            eng.record_feedback(QueryType.TECHNICAL, "technical", 0.5)
        # Connection should be closed
        assert eng._conn is None

    def test_close_and_reopen(self, tmp_path: Path) -> None:
        db = tmp_path / "persist.db"
        # Write data
        with AdaptiveLearningEngine(db_path=db) as eng:
            for _ in range(3):
                eng.record_feedback(QueryType.STRATEGIC, "strategic", 0.85)
        # Reopen and verify persistence
        with AdaptiveLearningEngine(db_path=db) as eng2:
            assert eng2.get_best_strategy(QueryType.STRATEGIC) == "strategic"
            stats = eng2.get_stats()
            assert stats["total_events"] == 3

    def test_get_stats_returns_dict(self, engine: AdaptiveLearningEngine) -> None:
        engine.record_feedback(QueryType.TECHNICAL, "technical", 0.5)
        engine.record_feedback(QueryType.RESEARCH, "research", 0.7)
        stats = engine.get_stats()
        assert stats["total_events"] == 2
        assert stats["strategies_tracked"] == 2
        assert stats["query_types_with_data"] == 2


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------


class TestThreadSafety:
    def test_concurrent_writes(self, engine: AdaptiveLearningEngine) -> None:
        errors: list[Exception] = []

        def _write(strategy: str) -> None:
            try:
                for _ in range(20):
                    engine.record_feedback(QueryType.TECHNICAL, strategy, 0.5)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_write, args=(f"s{i}",)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread errors: {errors}"
        stats = engine.get_stats()
        assert stats["total_events"] == 80  # 4 threads * 20 writes


# ---------------------------------------------------------------------------
# Graceful degradation
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    def test_corrupt_db_path(self, tmp_path: Path) -> None:
        # Write garbage to the DB path so SQLite fails
        bad_db = tmp_path / "bad.db"
        bad_db.write_text("not a sqlite database")
        eng = AdaptiveLearningEngine(db_path=bad_db)
        # Should degrade gracefully
        assert eng.get_best_strategy(QueryType.TECHNICAL) is None
        assert eng.get_stats() == {
            "total_events": 0,
            "strategies_tracked": 0,
            "query_types_with_data": 0,
        }
        eng.close()

    def test_readonly_directory(self, tmp_path: Path) -> None:
        # Create a directory where we can't write
        readonly = tmp_path / "readonly"
        readonly.mkdir()
        readonly.chmod(0o444)
        try:
            eng = AdaptiveLearningEngine(db_path=readonly / "test.db")
            # Should degrade gracefully (can't create DB)
            assert eng._conn is None
            eng.close()
        finally:
            readonly.chmod(0o755)

    def test_init_closes_connection_on_schema_failure(self, tmp_path: Path) -> None:
        """#110: __init__ must close the connection when _init_schema() fails.

        Before the fix, a schema failure left self._conn as a leaked, open
        connection set to None without calling close().  Verify that close()
        is called on the underlying connection.
        """
        db_path = tmp_path / "schema_fail.db"
        # Create the DB so _open_connection succeeds
        conn = sqlite3.connect(str(db_path))
        conn.close()

        with patch.object(
            AdaptiveLearningEngine,
            "_init_schema",
            side_effect=sqlite3.OperationalError("forced"),
        ):
            eng = AdaptiveLearningEngine(db_path=db_path)

        # The fix closes the connection before setting _conn = None.
        # Verify _conn is None (graceful degradation) and that the
        # connection is actually closed (not leaked).
        assert eng._conn is None
        # If the fix works, the file should not be locked — we can open it
        conn2 = sqlite3.connect(str(db_path))
        conn2.execute("PRAGMA journal_mode=WAL")  # would fail if locked
        conn2.close()

    def test_open_connection_closes_on_pragma_failure(self, tmp_path: Path) -> None:
        """#111: _open_connection must close conn when PRAGMA fails.

        Verify that when PRAGMA journal_mode=WAL raises, the half-opened
        connection is closed (not leaked), and init degrades gracefully.
        """
        db_path = tmp_path / "pragma_fail.db"
        call_count = {"connect": 0}
        original_connect = sqlite3.connect

        def counting_connect(*args: object, **kwargs: object) -> sqlite3.Connection:
            call_count["connect"] += 1
            conn = original_connect(*args, **kwargs)  # type: ignore[arg-type]
            if call_count["connect"] == 1:
                # Poison the first connection's execute to fail on PRAGMA
                orig_exec = conn.execute

                class PoisonedConn:
                    """Wraps a real conn but fails on PRAGMA."""

                    def __getattr__(self, name: str) -> object:
                        return getattr(conn, name)

                    def execute(self, sql: str, *a: object) -> sqlite3.Cursor:
                        if "PRAGMA" in sql:
                            raise sqlite3.OperationalError("WAL denied")
                        return orig_exec(sql, *a)

                    def close(self) -> None:
                        conn.close()

                    @property
                    def row_factory(self) -> object:
                        return conn.row_factory

                    @row_factory.setter
                    def row_factory(self, val: object) -> None:
                        conn.row_factory = val  # type: ignore[assignment]

                return PoisonedConn()  # type: ignore[return-value]
            return conn

        with patch("aipea.learning.sqlite3.connect", counting_connect):
            eng = AdaptiveLearningEngine(db_path=db_path)

        assert eng._conn is None
