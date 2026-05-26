"""Regression tests for Phase 2 bug-hunt cycle-2 analyzer findings.

Three term-matching sites in `aipea.analyzer` used plain `str.in` /
`str.find` substring matching, producing false hits where one English
word contains another as a substring:

- FINDING #8 (LOW C3) — `QueryRouter.calculate_confidence`: the term
  "might" wrongly fired on "mighty", subtracting 0.1 from confidence on
  perfectly clear queries containing "mighty river" etc.
- FINDING #9 (LOW C3) — `QueryAnalyzer._calculate_ambiguity`: same
  "might"-in-"mighty" hit, adding +0.15 ambiguity on clear queries. The
  two findings COMPOUND (a "mighty" query gets both lower confidence
  and higher ambiguity), which can flip tier-escalation downstream.
- FINDING #10 (LOW C3) — `QueryAnalyzer._determine_search_strategy`:
  "best" inside "asbestos" / "bestselling", "true" inside "construe" /
  "truest", "better" inside "betterment" all misrouted non-comparative
  queries to `SearchStrategy.MULTI_SOURCE`.

All three are fixed by anchoring the term-matching at word boundaries
via the module-level compiled regexes (`_AMBIGUITY_CONFIDENCE_RE`,
`_AMBIGUITY_RE`, `_COMPARATIVE_RE`, `_VERIFICATION_RE`) in
`src/aipea/analyzer.py`.
"""

from __future__ import annotations

import pytest

from aipea._types import QueryType, SearchStrategy
from aipea.analyzer import QueryAnalyzer, QueryRouter
from aipea.models import QueryAnalysis


def _make_analysis(query: str, query_type: QueryType = QueryType.RESEARCH) -> QueryAnalysis:
    """Build a minimal QueryAnalysis for the search-strategy tests."""
    return QueryAnalysis(
        query=query,
        query_type=query_type,
        complexity=0.8,
        confidence=0.9,
        needs_current_info=True,
        ambiguity_score=0.0,
        search_strategy=SearchStrategy.QUICK_FACTS,
    )


# =============================================================================
# F8: QueryRouter.calculate_confidence — word boundary for ambiguous terms
# =============================================================================


class TestCalculateConfidenceWordBoundary:
    """FINDING #8 (LOW C3): "might" inside "mighty" wrongly subtracted 0.1."""

    def test_mighty_does_not_trigger_might_ambiguous_penalty(self) -> None:
        router = QueryRouter()
        # Two queries identical except for one word; should yield equal
        # confidence (pre-fix: "mighty" was 0.1 lower than "grand").
        conf_mighty = router.calculate_confidence(
            "Describe the mighty river system", 0.2, ["geography"]
        )
        conf_grand = router.calculate_confidence(
            "Describe the grand river system", 0.2, ["geography"]
        )
        assert conf_mighty == pytest.approx(conf_grand, abs=1e-9)

    def test_genuine_might_still_triggers_penalty(self) -> None:
        # Positive control: a real "might" usage MUST still subtract.
        router = QueryRouter()
        conf_with_might = router.calculate_confidence(
            "This might be the answer to the question", 0.2, ["general"]
        )
        conf_without = router.calculate_confidence(
            "This is the answer to the question", 0.2, ["general"]
        )
        # Both queries are the same length so the short-query penalty
        # does not differ; the difference is exactly the ambiguous-term
        # penalty of 0.1.
        assert conf_with_might < conf_without
        assert (conf_without - conf_with_might) == pytest.approx(0.1, abs=1e-9)


# =============================================================================
# F9: QueryAnalyzer._calculate_ambiguity — word boundary for ambiguous terms
# =============================================================================


class TestCalculateAmbiguityWordBoundary:
    """FINDING #9 (LOW C3): "mighty" wrongly added +0.15 ambiguity."""

    def test_mighty_does_not_trigger_might_ambiguity_bump(self) -> None:
        analyzer = QueryAnalyzer()
        # Two long enough queries (≥5 words) so the short-query bumps
        # don't differ. The only difference is "mighty" vs "grand".
        amb_mighty = analyzer._calculate_ambiguity(
            "Render the mighty waterfall scene in great detail with physics"
        )
        amb_grand = analyzer._calculate_ambiguity(
            "Render the grand waterfall scene in great detail with physics"
        )
        assert amb_mighty == pytest.approx(amb_grand, abs=1e-9)

    def test_could_inside_couldnt_does_not_trigger(self) -> None:
        # "couldn't" — `\bcould\b` requires a word boundary AFTER
        # "could". In "couldn't" the next char is 'n' (also a word
        # character), so NO boundary exists between 'd' and 'n' and the
        # regex correctly does NOT match. This is a strict improvement
        # over the pre-fix substring scan, which DID match "could"
        # inside "couldn't" and added a spurious +0.15. Pin the
        # post-fix behavior so a future regex relaxation doesn't
        # silently re-introduce the false hit.
        analyzer = QueryAnalyzer()
        score = analyzer._calculate_ambiguity("This couldn't be more clear")
        # 5 words → no short-query bump. No "?", no interrogative
        # keyword in the (out-of-scope) substring check → +0.1.
        # NO ambiguous-term match. Total = 0.1.
        assert score == pytest.approx(0.1, abs=1e-9)

    def test_multi_word_term_matches_as_a_whole(self) -> None:
        # Positive control: "it depends" matches once (not twice via
        # the standalone "depends" alternative). Longest-first
        # alternation handles this.
        analyzer = QueryAnalyzer()
        score = analyzer._calculate_ambiguity("Well, it depends on the context here")
        # Exactly ONE ambiguous match. 7 words → no short bump. "context"
        # alone is no interrogative keyword (the test query has no "?"
        # and no how/what/why keyword), so +0.1 interrogative-absence.
        # Total = 0.15 + 0.1 = 0.25.
        assert score == pytest.approx(0.25, abs=1e-9)

    def test_genuine_might_still_counts(self) -> None:
        analyzer = QueryAnalyzer()
        score = analyzer._calculate_ambiguity("I might be wrong but that seems incorrect here")
        # "might" counted once. 8 words → no short bump. No "?" and no
        # interrogative keyword → +0.1.
        assert score == pytest.approx(0.25, abs=1e-9)


# =============================================================================
# F10: QueryAnalyzer._determine_search_strategy — word boundary
# =============================================================================


class TestDetermineSearchStrategyWordBoundary:
    """FINDING #10 (LOW C3): substring "best" in "asbestos" / "bestselling"
    and "true" in "construe" misrouted to MULTI_SOURCE.
    """

    def test_asbestos_does_not_route_to_multi_source(self) -> None:
        analyzer = QueryAnalyzer()
        result = analyzer._determine_search_strategy(
            _make_analysis("Research the health effects of asbestos exposure in older buildings")
        )
        # Should NOT be MULTI_SOURCE (the comparative strategy) just
        # because "asbestos" contains "best".
        assert result != SearchStrategy.MULTI_SOURCE

    def test_bestselling_does_not_route_to_multi_source(self) -> None:
        analyzer = QueryAnalyzer()
        result = analyzer._determine_search_strategy(
            _make_analysis("Analyze bestselling book trends in 2026")
        )
        assert result != SearchStrategy.MULTI_SOURCE

    def test_construe_does_not_route_to_multi_source_via_true(self) -> None:
        analyzer = QueryAnalyzer()
        result = analyzer._determine_search_strategy(
            _make_analysis("Discuss how some critics construe this passage")
        )
        assert result != SearchStrategy.MULTI_SOURCE

    def test_genuine_comparative_still_routes_to_multi_source(self) -> None:
        # Positive control: a real comparative query.
        analyzer = QueryAnalyzer()
        result = analyzer._determine_search_strategy(
            _make_analysis("Compare PostgreSQL versus MongoDB performance under load")
        )
        assert result == SearchStrategy.MULTI_SOURCE

    def test_genuine_verification_still_routes_to_multi_source(self) -> None:
        # Positive control: a real verification query.
        analyzer = QueryAnalyzer()
        result = analyzer._determine_search_strategy(
            _make_analysis("Verify the claim that the 2026 election results are accurate")
        )
        assert result == SearchStrategy.MULTI_SOURCE
