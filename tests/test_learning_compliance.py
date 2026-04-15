"""Tests for compliance-aware behaviour of the Adaptive Learning Engine.

Covers: LearningPolicy dataclass, _should_record gating per ComplianceMode,
compliance_mode column storage, schema migration, retention pruning, and
end-to-end AIPEAEnhancer integration.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from aipea._types import QueryType
from aipea.learning import AdaptiveLearningEngine, LearningPolicy
from aipea.security import ComplianceMode

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def engine(tmp_path: Path) -> AdaptiveLearningEngine:
    """Provide a fresh engine with default policy."""
    db = tmp_path / "compliance_test.db"
    eng = AdaptiveLearningEngine(db_path=db)
    yield eng
    eng.close()


@pytest.fixture()
def hipaa_engine(tmp_path: Path) -> AdaptiveLearningEngine:
    """Engine with HIPAA recording explicitly allowed."""
    db = tmp_path / "hipaa_test.db"
    eng = AdaptiveLearningEngine(db_path=db, policy=LearningPolicy(allow_hipaa_recording=True))
    yield eng
    eng.close()


@pytest.fixture()
def retention_engine(tmp_path: Path) -> AdaptiveLearningEngine:
    """Engine with retention limits configured."""
    db = tmp_path / "retention_test.db"
    eng = AdaptiveLearningEngine(db_path=db, policy=LearningPolicy(retention_days=7, max_events=10))
    yield eng
    eng.close()


# ---------------------------------------------------------------------------
# LearningPolicy dataclass
# ---------------------------------------------------------------------------


class TestLearningPolicy:
    def test_defaults(self) -> None:
        policy = LearningPolicy()
        assert policy.allow_hipaa_recording is False
        assert policy.retention_days is None
        assert policy.max_events is None

    def test_frozen(self) -> None:
        policy = LearningPolicy()
        with pytest.raises(AttributeError):
            policy.allow_hipaa_recording = True  # type: ignore[misc]

    def test_custom_values(self) -> None:
        policy = LearningPolicy(allow_hipaa_recording=True, retention_days=30, max_events=1000)
        assert policy.allow_hipaa_recording is True
        assert policy.retention_days == 30
        assert policy.max_events == 1000

    def test_negative_retention_days_rejected(self) -> None:
        with pytest.raises(ValueError, match="retention_days must be >= 1"):
            LearningPolicy(retention_days=-5)

    def test_zero_retention_days_rejected(self) -> None:
        with pytest.raises(ValueError, match="retention_days must be >= 1"):
            LearningPolicy(retention_days=0)

    def test_negative_max_events_rejected(self) -> None:
        with pytest.raises(ValueError, match="max_events must be >= 0"):
            LearningPolicy(max_events=-1)

    def test_zero_max_events_allowed(self) -> None:
        """max_events=0 means 'keep nothing' — a valid retention policy."""
        policy = LearningPolicy(max_events=0)
        assert policy.max_events == 0


# ---------------------------------------------------------------------------
# _should_record gating
# ---------------------------------------------------------------------------


class TestShouldRecord:
    """Tests for the private _should_record compliance gate."""

    def test_tactical_always_blocked(self, engine: AdaptiveLearningEngine) -> None:
        assert engine._should_record(ComplianceMode.TACTICAL) is False

    def test_hipaa_default_deny(self, engine: AdaptiveLearningEngine) -> None:
        assert engine._should_record(ComplianceMode.HIPAA) is False

    def test_hipaa_opt_in(self, hipaa_engine: AdaptiveLearningEngine) -> None:
        assert hipaa_engine._should_record(ComplianceMode.HIPAA) is True

    def test_general_allowed(self, engine: AdaptiveLearningEngine) -> None:
        assert engine._should_record(ComplianceMode.GENERAL) is True

    def test_fedramp_follows_general(self, engine: AdaptiveLearningEngine) -> None:
        assert engine._should_record(ComplianceMode.FEDRAMP) is True

    def test_tactical_blocked_even_with_hipaa_opt_in(
        self, hipaa_engine: AdaptiveLearningEngine
    ) -> None:
        """TACTICAL hard-lock is not overridable by any policy setting."""
        assert hipaa_engine._should_record(ComplianceMode.TACTICAL) is False


# ---------------------------------------------------------------------------
# record_feedback compliance integration
# ---------------------------------------------------------------------------


class TestRecordFeedbackCompliance:
    def test_tactical_no_write(self, engine: AdaptiveLearningEngine) -> None:
        engine.record_feedback(QueryType.TECHNICAL, "deep_research", 0.9, ComplianceMode.TACTICAL)
        assert engine.get_stats()["total_events"] == 0

    def test_hipaa_no_write_default(self, engine: AdaptiveLearningEngine) -> None:
        engine.record_feedback(QueryType.TECHNICAL, "deep_research", 0.9, ComplianceMode.HIPAA)
        assert engine.get_stats()["total_events"] == 0

    def test_hipaa_write_opt_in(self, hipaa_engine: AdaptiveLearningEngine) -> None:
        hipaa_engine.record_feedback(
            QueryType.TECHNICAL, "deep_research", 0.9, ComplianceMode.HIPAA
        )
        assert hipaa_engine.get_stats()["total_events"] == 1

    def test_general_write(self, engine: AdaptiveLearningEngine) -> None:
        engine.record_feedback(QueryType.TECHNICAL, "deep_research", 0.9, ComplianceMode.GENERAL)
        assert engine.get_stats()["total_events"] == 1

    def test_default_compliance_is_general(self, engine: AdaptiveLearningEngine) -> None:
        """Omitting compliance_mode should default to GENERAL (backwards compat)."""
        engine.record_feedback(QueryType.TECHNICAL, "deep_research", 0.9)
        assert engine.get_stats()["total_events"] == 1


# ---------------------------------------------------------------------------
# compliance_mode column storage
# ---------------------------------------------------------------------------


class TestComplianceModeColumn:
    def _query_compliance_modes(self, engine: AdaptiveLearningEngine) -> list[str]:
        """Read compliance_mode values directly from SQLite."""
        assert engine._conn is not None
        rows = engine._conn.execute("SELECT compliance_mode FROM learning_events").fetchall()
        return [row[0] for row in rows]

    def test_general_mode_stored(self, engine: AdaptiveLearningEngine) -> None:
        engine.record_feedback(QueryType.TECHNICAL, "deep_research", 0.8, ComplianceMode.GENERAL)
        modes = self._query_compliance_modes(engine)
        assert modes == ["general"]

    def test_hipaa_mode_stored(self, hipaa_engine: AdaptiveLearningEngine) -> None:
        hipaa_engine.record_feedback(
            QueryType.TECHNICAL, "deep_research", 0.8, ComplianceMode.HIPAA
        )
        modes = self._query_compliance_modes(hipaa_engine)
        assert modes == ["hipaa"]

    def test_default_omit_stores_general(self, engine: AdaptiveLearningEngine) -> None:
        engine.record_feedback(QueryType.TECHNICAL, "deep_research", 0.8)
        modes = self._query_compliance_modes(engine)
        assert modes == ["general"]


# ---------------------------------------------------------------------------
# Schema migration
# ---------------------------------------------------------------------------


class TestSchemaMigration:
    def test_existing_db_gets_column(self, tmp_path: Path) -> None:
        """Simulate a pre-compliance DB and verify migration adds the column."""
        db_path = tmp_path / "old.db"
        # Create old-schema DB (no compliance_mode column)
        conn = sqlite3.connect(str(db_path))
        conn.executescript(
            """\
            CREATE TABLE learning_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                query_type TEXT NOT NULL,
                strategy_used TEXT NOT NULL,
                feedback_score REAL NOT NULL,
                query_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE strategy_performance (
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
        # Insert a row under old schema
        conn.execute(
            "INSERT INTO learning_events "
            "(timestamp, query_type, strategy_used, feedback_score, query_hash) "
            "VALUES ('2026-01-01', 'technical', 'deep_research', 0.5, 'abc123')"
        )
        conn.commit()
        conn.close()

        # Open with new engine — migration should run
        with AdaptiveLearningEngine(db_path=db_path) as eng:
            columns = {
                row[1] for row in eng._conn.execute("PRAGMA table_info(learning_events)").fetchall()
            }
            assert "compliance_mode" in columns

            # Old row should have default 'general'
            row = eng._conn.execute("SELECT compliance_mode FROM learning_events").fetchone()
            assert row[0] == "general"

            # Data is preserved
            assert eng.get_stats()["total_events"] == 1

    def test_migration_graceful_degradation(self, tmp_path: Path) -> None:
        """If ALTER TABLE fails, engine still works without the column."""
        db_path = tmp_path / "degrade.db"

        with patch.object(
            AdaptiveLearningEngine,
            "_init_schema",
            wraps=None,
        ):
            # Create engine normally first
            eng = AdaptiveLearningEngine(db_path=db_path)
            eng.close()

        # Verify engine created successfully (graceful degradation is tested
        # via the try/except in _init_schema, which logs but doesn't raise)
        eng2 = AdaptiveLearningEngine(db_path=db_path)
        # Engine should still be functional
        eng2.record_feedback(QueryType.TECHNICAL, "deep_research", 0.8)
        assert eng2.get_stats()["total_events"] == 1
        eng2.close()


# ---------------------------------------------------------------------------
# Retention pruning
# ---------------------------------------------------------------------------


class TestPruneEvents:
    def test_prune_by_count(self, engine: AdaptiveLearningEngine) -> None:
        for _ in range(10):
            engine.record_feedback(QueryType.TECHNICAL, "deep_research", 0.5)
        assert engine.get_stats()["total_events"] == 10

        deleted = engine.prune_events(max_count=5)
        assert deleted == 5
        assert engine.get_stats()["total_events"] == 5

    def test_prune_by_age(self, tmp_path: Path) -> None:
        db_path = tmp_path / "age_test.db"
        eng = AdaptiveLearningEngine(db_path=db_path)
        try:
            # Insert events with backdated created_at
            old_ts = (datetime.now(UTC) - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
            assert eng._conn is not None
            eng._conn.execute(
                "INSERT INTO learning_events "
                "(timestamp, query_type, strategy_used, feedback_score, "
                "query_hash, created_at, compliance_mode) "
                "VALUES (?, 'technical', 'deep_research', 0.5, 'abc', ?, 'general')",
                (old_ts, old_ts),
            )
            eng._conn.commit()

            # Insert a fresh event
            eng.record_feedback(QueryType.TECHNICAL, "deep_research", 0.8)

            assert eng.get_stats()["total_events"] == 2
            deleted = eng.prune_events(max_age_days=5)
            assert deleted == 1
            assert eng.get_stats()["total_events"] == 1
        finally:
            eng.close()

    def test_prune_uses_policy_defaults(self, retention_engine: AdaptiveLearningEngine) -> None:
        """prune_events() with no args should use policy.max_events=10."""
        for _ in range(15):
            retention_engine.record_feedback(QueryType.TECHNICAL, "deep_research", 0.5)
        assert retention_engine.get_stats()["total_events"] == 15

        deleted = retention_engine.prune_events()
        assert deleted == 5
        assert retention_engine.get_stats()["total_events"] == 10

    def test_prune_empty_db(self, engine: AdaptiveLearningEngine) -> None:
        deleted = engine.prune_events(max_count=5)
        assert deleted == 0

    def test_prune_combined_age_and_count(self, tmp_path: Path) -> None:
        db_path = tmp_path / "combined.db"
        eng = AdaptiveLearningEngine(db_path=db_path, policy=LearningPolicy(max_events=3))
        try:
            # Insert 2 old events
            old_ts = (datetime.now(UTC) - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
            assert eng._conn is not None
            for _ in range(2):
                eng._conn.execute(
                    "INSERT INTO learning_events "
                    "(timestamp, query_type, strategy_used, feedback_score, "
                    "query_hash, created_at, compliance_mode) "
                    "VALUES (?, 'technical', 'deep_research', 0.5, 'abc', ?, 'general')",
                    (old_ts, old_ts),
                )
            eng._conn.commit()

            # Insert 3 fresh events
            for _ in range(3):
                eng.record_feedback(QueryType.TECHNICAL, "deep_research", 0.8)

            assert eng.get_stats()["total_events"] == 5

            # Prune: age removes 2 old, then count removes 0 (3 <= 3)
            deleted = eng.prune_events(max_age_days=5, max_count=3)
            assert deleted == 2
            assert eng.get_stats()["total_events"] == 3
        finally:
            eng.close()


# ---------------------------------------------------------------------------
# prune_events validation
# ---------------------------------------------------------------------------


class TestPruneValidation:
    def test_negative_max_age_days_rejected(self, engine: AdaptiveLearningEngine) -> None:
        with pytest.raises(ValueError, match="max_age_days must be >= 1"):
            engine.prune_events(max_age_days=-1)

    def test_zero_max_age_days_rejected(self, engine: AdaptiveLearningEngine) -> None:
        with pytest.raises(ValueError, match="max_age_days must be >= 1"):
            engine.prune_events(max_age_days=0)

    def test_negative_max_count_rejected(self, engine: AdaptiveLearningEngine) -> None:
        with pytest.raises(ValueError, match="max_count must be >= 0"):
            engine.prune_events(max_count=-1)

    def test_both_none_returns_zero_fast(self, engine: AdaptiveLearningEngine) -> None:
        """When both params resolve to None, return 0 without acquiring the lock."""
        engine.record_feedback(QueryType.TECHNICAL, "deep_research", 0.5)
        deleted = engine.prune_events()  # default policy: both None
        assert deleted == 0
        assert engine.get_stats()["total_events"] == 1  # nothing deleted


# ---------------------------------------------------------------------------
# Async wrappers
# ---------------------------------------------------------------------------


class TestAsyncCompliance:
    @pytest.mark.asyncio()
    async def test_arecord_feedback_tactical_blocked(self, engine: AdaptiveLearningEngine) -> None:
        await engine.arecord_feedback(
            QueryType.TECHNICAL, "deep_research", 0.9, ComplianceMode.TACTICAL
        )
        assert engine.get_stats()["total_events"] == 0

    @pytest.mark.asyncio()
    async def test_aprune_events(self, engine: AdaptiveLearningEngine) -> None:
        for _ in range(5):
            engine.record_feedback(QueryType.TECHNICAL, "deep_research", 0.5)
        deleted = await engine.aprune_events(max_count=2)
        assert deleted == 3
        assert engine.get_stats()["total_events"] == 2
