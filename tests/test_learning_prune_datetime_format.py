"""Regression test for Phase 2 bug-hunt cycle-2 finding F4.

`AdaptiveLearningEngine.prune_events(max_age_days=N)` produced a
data-loss bug at the calendar-day boundary because the cutoff and the
stored `created_at` used different string formats:

- `created_at` is stored by the schema DEFAULT `datetime('now')` in
  SQLite format: ``"YYYY-MM-DD HH:MM:SS"`` (space-separated, second
  precision, no timezone offset).
- The pre-fix cutoff was ``datetime.now(UTC).isoformat()``:
  ``"YYYY-MM-DDTHH:MM:SS.ffffff+00:00"`` (T-separated, microseconds,
  "+00:00" offset).

Lexicographic string comparison of these two formats is wrong at the
boundary: position 10 is ``' '`` (0x20) on the stored side vs ``'T'``
(0x54) on the cutoff side. ``' '`` < ``'T'``, so EVERY row created on
the cutoff's calendar day — at ANY time of day, even hours AFTER the
cutoff time — compared as less-than the cutoff via ``created_at <
cutoff`` and was wrongly deleted.

The fix formats the cutoff with ``strftime("%Y-%m-%d %H:%M:%S")`` so
both sides of the comparison use the same canonical SQLite format and
lexicographic order coincides with chronological order.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

from aipea._types import QueryType
from aipea.learning import AdaptiveLearningEngine


def _insert_event_with_created_at(eng: AdaptiveLearningEngine, created_at: str) -> None:
    """Insert one learning_events row with a specific `created_at`."""
    assert eng._conn is not None
    eng._conn.execute(
        "INSERT INTO learning_events "
        "(timestamp, query_type, strategy_used, feedback_score, "
        "query_hash, created_at, compliance_mode) "
        "VALUES (?, 'technical', 'deep_research', 0.5, 'abc', ?, 'general')",
        (created_at, created_at),
    )
    eng._conn.commit()


class TestPruneDatetimeFormatBoundary:
    """FINDING #4 (MEDIUM C3): pre-fix isoformat cutoff vs SQLite-format
    `created_at` made any same-calendar-day row lex-compare less-than
    the cutoff and get wrongly deleted.
    """

    def test_same_date_row_newer_than_cutoff_is_retained(self, tmp_path: Path) -> None:
        db_path = tmp_path / "fmt_newer.db"
        eng = AdaptiveLearningEngine(db_path=db_path)
        try:
            # Row at 2026-05-24 16:30 UTC — same date as cutoff, but
            # 1 hour LATER → row is genuinely newer than cutoff → MUST
            # be retained. Pre-fix wrongly deleted this row because the
            # isoformat cutoff (with 'T' at position 10) lex-compared
            # greater than the row's space at position 10.
            _insert_event_with_created_at(eng, "2026-05-24 16:30:00")
            assert eng.get_stats()["total_events"] == 1

            fixed_now = datetime(2026, 5, 25, 15, 30, 0, tzinfo=UTC)
            # cutoff at max_age_days=1 = 2026-05-24 15:30:00 UTC.

            class _MockDT:
                @staticmethod
                def now(tz: Any = None) -> datetime:
                    return fixed_now

            with patch("aipea.learning.datetime", _MockDT):
                deleted = eng.prune_events(max_age_days=1)

            assert deleted == 0, (
                "regression — same-date row newer than cutoff was wrongly "
                "deleted via the isoformat-vs-SQLite-format mismatch"
            )
            assert eng.get_stats()["total_events"] == 1
        finally:
            eng.close()

    def test_same_date_row_older_than_cutoff_is_deleted(self, tmp_path: Path) -> None:
        # Positive control on the same date — a row genuinely OLDER
        # than the cutoff (still on the cutoff's date) must still be
        # deleted, so the fix doesn't accidentally retain everything.
        db_path = tmp_path / "fmt_older.db"
        eng = AdaptiveLearningEngine(db_path=db_path)
        try:
            _insert_event_with_created_at(eng, "2026-05-24 14:30:00")
            assert eng.get_stats()["total_events"] == 1

            fixed_now = datetime(2026, 5, 25, 15, 30, 0, tzinfo=UTC)
            # cutoff at max_age_days=1 = 2026-05-24 15:30:00 UTC.

            class _MockDT:
                @staticmethod
                def now(tz: Any = None) -> datetime:
                    return fixed_now

            with patch("aipea.learning.datetime", _MockDT):
                deleted = eng.prune_events(max_age_days=1)

            assert deleted == 1
            assert eng.get_stats()["total_events"] == 0
        finally:
            eng.close()

    def test_clearly_older_row_still_deleted_no_regression(self, tmp_path: Path) -> None:
        # Regression on the original happy path (rows much older than
        # cutoff get deleted) — mirrors the existing `test_prune_by_age`
        # but uses a freshly minted engine + the real wall clock so the
        # fix doesn't break the common case.
        db_path = tmp_path / "fmt_old.db"
        eng = AdaptiveLearningEngine(db_path=db_path)
        try:
            old_ts = (datetime.now(UTC) - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
            _insert_event_with_created_at(eng, old_ts)
            # Also a fresh row via record_feedback so we have a mix.
            eng.record_feedback(QueryType.TECHNICAL, "deep_research", 0.8)
            assert eng.get_stats()["total_events"] == 2

            deleted = eng.prune_events(max_age_days=5)
            assert deleted == 1
            assert eng.get_stats()["total_events"] == 1
        finally:
            eng.close()
