"""Tests for aipea.models.QueryAnalysis (TODO §H — dedicated edge-case coverage).

Exercises `__post_init__` score handling (type coercion, NaN, clamping) and
`to_dict()` serialization directly, rather than only indirectly via the analyzer.
"""

from __future__ import annotations

import math

import pytest

from aipea._types import ProcessingTier, QueryType, SearchStrategy
from aipea.models import QueryAnalysis


def _make(**overrides: object) -> QueryAnalysis:
    """Construct a QueryAnalysis with sensible defaults, overriding as needed."""
    params: dict[str, object] = {
        "query": "test query",
        "query_type": QueryType.TECHNICAL,
        "complexity": 0.5,
        "confidence": 0.8,
        "needs_current_info": False,
    }
    params.update(overrides)
    return QueryAnalysis(**params)  # type: ignore[arg-type]


class TestQueryAnalysisScoreCoercion:
    @pytest.mark.unit
    def test_valid_floats_preserved(self) -> None:
        qa = _make(complexity=0.3, confidence=0.6, ambiguity_score=0.9)
        assert qa.complexity == 0.3
        assert qa.confidence == 0.6
        assert qa.ambiguity_score == 0.9

    @pytest.mark.unit
    def test_string_score_coerced_to_float(self) -> None:
        qa = _make(complexity="0.5", confidence="0.7")  # numeric strings
        assert qa.complexity == 0.5
        assert isinstance(qa.complexity, float)
        assert qa.confidence == 0.7

    @pytest.mark.unit
    def test_int_score_coerced_to_float(self) -> None:
        qa = _make(complexity=1, confidence=0)
        assert qa.complexity == 1.0
        assert isinstance(qa.complexity, float)
        assert qa.confidence == 0.0

    @pytest.mark.unit
    def test_uncoercible_score_defaults_to_zero(self) -> None:
        # object() and None raise TypeError on float() → defaults to 0.0
        qa = _make(complexity=object(), confidence=None, ambiguity_score="not-a-number")
        assert qa.complexity == 0.0
        assert qa.confidence == 0.0
        assert qa.ambiguity_score == 0.0


class TestQueryAnalysisNaNHandling:
    @pytest.mark.unit
    def test_nan_scores_default_to_zero(self) -> None:
        nan = float("nan")
        qa = _make(complexity=nan, confidence=nan, ambiguity_score=nan)
        assert qa.complexity == 0.0
        assert qa.confidence == 0.0
        assert qa.ambiguity_score == 0.0
        assert not math.isnan(qa.complexity)


class TestQueryAnalysisClamping:
    @pytest.mark.unit
    @pytest.mark.parametrize(
        ("raw", "clamped"),
        [(1.5, 1.0), (2.0, 1.0), (-0.3, 0.0), (-100.0, 0.0), (1.0, 1.0), (0.0, 0.0)],
    )
    def test_complexity_clamped(self, raw: float, clamped: float) -> None:
        assert _make(complexity=raw).complexity == clamped

    @pytest.mark.unit
    @pytest.mark.parametrize(("raw", "clamped"), [(1.5, 1.0), (-0.3, 0.0)])
    def test_confidence_clamped(self, raw: float, clamped: float) -> None:
        assert _make(confidence=raw).confidence == clamped

    @pytest.mark.unit
    @pytest.mark.parametrize(("raw", "clamped"), [(2.0, 1.0), (-1.0, 0.0)])
    def test_ambiguity_score_clamped(self, raw: float, clamped: float) -> None:
        # Covers the previously-uncovered ambiguity_score clamp branch (models.py:78-84).
        assert _make(ambiguity_score=raw).ambiguity_score == clamped


class TestQueryAnalysisToDict:
    @pytest.mark.unit
    def test_to_dict_serializes_enums_and_fields(self) -> None:
        qa = _make(
            query_type=QueryType.RESEARCH,
            temporal_markers=["2026"],
            domain_indicators=["ai"],
            detected_entities=["AIPEA"],
            suggested_tier=ProcessingTier.STRATEGIC,
            search_strategy=SearchStrategy.DEEP_RESEARCH,
        )
        d = qa.to_dict()
        assert d["query_type"] == "research"  # enum → .value
        assert d["suggested_tier"] == "strategic"
        assert d["search_strategy"] == "deep_research"
        assert d["temporal_markers"] == ["2026"]
        assert d["detected_entities"] == ["AIPEA"]
        # full public surface is present
        assert set(d) == {
            "query",
            "query_type",
            "complexity",
            "confidence",
            "needs_current_info",
            "temporal_markers",
            "domain_indicators",
            "ambiguity_score",
            "detected_entities",
            "suggested_tier",
            "search_strategy",
        }

    @pytest.mark.unit
    def test_to_dict_suggested_tier_none(self) -> None:
        # default suggested_tier is None → serializes to None (not an enum access error)
        assert _make().to_dict()["suggested_tier"] is None
