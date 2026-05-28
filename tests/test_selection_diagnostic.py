"""Tests for the public ALIG surface + ``AIPEAEnhancer.selection_diagnostic`` wiring.

Covers increment 2: the certificate exports, the ``AdaptiveLearningEngine``
score-reader, and the read-only enhancer diagnostic (diagnostic-only, score range
[-1, 1], never authorizing strategy switching — ADR-011).
"""

from __future__ import annotations

from pathlib import Path

import pytest

import aipea
from aipea import AIPEAEnhancer, CertificateStatus
from aipea._types import QueryType
from aipea.learning import AdaptiveLearningEngine


def test_public_exports_importable() -> None:
    for name in (
        "CertificateStatus",
        "PerturbationModel",
        "InfluenceCertificate",
        "compute_influence_certificate",
    ):
        assert name in aipea.__all__, f"{name} missing from __all__"
        assert hasattr(aipea, name), f"{name} not importable from aipea"


def test_scores_by_strategy_excludes_tainted(tmp_path: Path) -> None:
    eng = AdaptiveLearningEngine(db_path=tmp_path / "learn.db")
    try:
        for _ in range(4):
            eng.record_feedback(QueryType.TECHNICAL, "alpha", 0.9)
        # A taint-flagged event is recorded for audit but excluded from averaging
        # (ADR-004); the diagnostic must not see it.
        eng.record_feedback(QueryType.TECHNICAL, "beta", 0.8, scan_flags=["injection_attempt"])
        scores = eng.scores_by_strategy(QueryType.TECHNICAL)
        assert scores.get("alpha") == [0.9, 0.9, 0.9, 0.9]
        assert "beta" not in scores  # its only event was tainted/excluded
    finally:
        eng.close()


def test_selection_diagnostic_none_when_learning_disabled() -> None:
    enh = AIPEAEnhancer(enable_learning=False)
    try:
        assert enh.selection_diagnostic(QueryType.TECHNICAL) is None
    finally:
        enh.close()


def test_selection_diagnostic_over_seeded_feedback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AIPEA_LEARNING_DB_PATH", str(tmp_path / "learn.db"))
    enh = AIPEAEnhancer(enable_learning=True)
    try:
        eng = enh._learning_engine
        assert eng is not None
        for _ in range(5):
            eng.record_feedback(QueryType.TECHNICAL, "alpha", 0.9)
            eng.record_feedback(QueryType.TECHNICAL, "beta", 0.4)
        cert = enh.selection_diagnostic(QueryType.TECHNICAL, min_samples=3)
        assert cert is not None
        # Diagnostic-only invariants (ADR-011).
        assert cert.status is CertificateStatus.RAW_EVENT_EDIT_DIAGNOSTIC
        assert cert.certified_k is None
        # Wiring: learning score range is [-1, 1], not the engine default [0, 1].
        assert cert.score_bounds == (-1.0, 1.0)
        # alpha (0.9) dominates beta (0.4) and is robust to >=1 adversarial event.
        assert cert.selected_strategy == "alpha"
        assert cert.diagnostic_event_k >= 1
    finally:
        enh.close()
