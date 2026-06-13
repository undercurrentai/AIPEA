"""Tests for the AIPEAEnhancer trust-boundary wiring (ALIG B1.1, ADR-011).

Covers the opt-in request-bound feedback path: ``issue_feedback_token`` +
``record_end_user_feedback``. The key security property under test is
forge-resistance — the untrusted ``record_end_user_feedback(request_id, score)``
records against the strategy/query type resolved from the *token*, never from
caller-supplied values.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aipea import (
    AIPEAEnhancer,
    ComplianceMode,
    EnhancementResult,
    ProcessingTier,
    QueryAnalysis,
    QueryType,
    SecurityContext,
    SecurityLevel,
)


def _result(
    strategy: str = "alpha", compliance: ComplianceMode = ComplianceMode.GENERAL
) -> EnhancementResult:
    return EnhancementResult(
        original_query="q",
        enhanced_prompt="enhanced",
        processing_tier=ProcessingTier.TACTICAL,
        security_context=SecurityContext(
            security_level=SecurityLevel.UNCLASSIFIED, compliance_mode=compliance
        ),
        query_analysis=QueryAnalysis(
            query="q",
            query_type=QueryType.TECHNICAL,
            complexity=0.5,
            confidence=0.9,
            needs_current_info=False,
        ),
        strategy_used=strategy,
    )


def test_issue_token_none_when_trust_boundary_disabled() -> None:
    enh = AIPEAEnhancer(enable_trust_boundary=False)
    try:
        assert enh.issue_feedback_token(_result(), tenant_id="t1") is None
    finally:
        enh.close()


async def test_record_end_user_feedback_noop_when_disabled() -> None:
    enh = AIPEAEnhancer(enable_trust_boundary=False)
    try:
        await enh.record_end_user_feedback("x", 0.5)  # must not raise
    finally:
        enh.close()


def test_issue_none_without_strategy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIPEA_LEARNING_DB_PATH", str(tmp_path / "learn.db"))
    enh = AIPEAEnhancer(enable_trust_boundary=True)
    try:
        assert enh.issue_feedback_token(_result(strategy=""), tenant_id="t1") is None
    finally:
        enh.close()


async def test_issue_and_record_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIPEA_LEARNING_DB_PATH", str(tmp_path / "learn.db"))
    enh = AIPEAEnhancer(enable_learning=True, enable_trust_boundary=True)
    try:
        token = enh.issue_feedback_token(_result(strategy="alpha"), tenant_id="t1")
        assert token is not None
        await enh.record_end_user_feedback(token, 0.9)
        eng = enh._learning_engine
        assert eng is not None
        # Forge-resistance: the recorded strategy/query type come from the TOKEN,
        # not from anything the untrusted feedback caller supplied.
        assert eng.scores_by_strategy(QueryType.TECHNICAL) == {"alpha": [0.9]}
    finally:
        enh.close()


async def test_replayed_token_records_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIPEA_LEARNING_DB_PATH", str(tmp_path / "learn.db"))
    enh = AIPEAEnhancer(enable_learning=True, enable_trust_boundary=True)
    try:
        token = enh.issue_feedback_token(_result(strategy="alpha"), tenant_id="t1")
        assert token is not None
        await enh.record_end_user_feedback(token, 0.9)
        await enh.record_end_user_feedback(token, -1.0)  # single-use replay -> ignored
        eng = enh._learning_engine
        assert eng is not None
        assert eng.scores_by_strategy(QueryType.TECHNICAL) == {"alpha": [0.9]}
    finally:
        enh.close()


async def test_invalid_token_noop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIPEA_LEARNING_DB_PATH", str(tmp_path / "learn.db"))
    enh = AIPEAEnhancer(enable_learning=True, enable_trust_boundary=True)
    try:
        await enh.record_end_user_feedback("bogus-token", 0.9)
        eng = enh._learning_engine
        assert eng is not None
        assert eng.scores_by_strategy(QueryType.TECHNICAL) == {}
    finally:
        enh.close()


def test_source_id_with_hmac_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIPEA_LEARNING_DB_PATH", str(tmp_path / "learn.db"))
    enh = AIPEAEnhancer(enable_trust_boundary=True, learning_hmac_key="k")
    try:
        token = enh.issue_feedback_token(_result(), tenant_id="t1", source_id="user-9")
        assert token is not None
    finally:
        enh.close()
