"""Tests for pcw_query_analyzer.py - Query complexity analysis."""

import pytest

from aipea._types import ProcessingTier
from aipea.analyzer import QueryRouter
from aipea.security import SecurityContext

pytestmark = [pytest.mark.unit]


class TestQueryRouterComplexity:
    """Tests for QueryRouter complexity calculation."""

    @pytest.fixture
    def router(self):
        """Create a QueryRouter instance."""
        return QueryRouter()

    def test_word_count_over_100_gets_higher_boost(self, router):
        """Queries with >100 words should get 0.2 complexity boost, not 0.1.

        This tests the fix for conditional ordering: >100 must be checked
        before >50, otherwise long queries only get the smaller boost.
        """
        # Query with exactly 101 words
        long_query = "word " * 101
        complexity = router._calculate_complexity(long_query.strip())

        # Base complexity (0.1) + word count boost (0.2 for >100 words) = 0.3
        assert complexity == pytest.approx(0.3)

    def test_word_count_over_50_gets_smaller_boost(self, router):
        """Queries with 51-100 words should get 0.1 complexity boost."""
        medium_query = "word " * 55
        complexity = router._calculate_complexity(medium_query.strip())

        # Base complexity (0.1) + word count boost (0.1 for >50 words) = 0.2
        assert complexity == pytest.approx(0.2)

    def test_word_count_under_50_no_boost(self, router):
        """Queries with <=50 words should get no word count boost."""
        short_query = "word " * 10
        complexity = router._calculate_complexity(short_query.strip())

        # Base complexity only (0.1), no word count boost
        assert complexity == pytest.approx(0.1)

    def test_conditional_ordering_boundary(self, router):
        """Test boundary conditions at exactly 50 and 100 words."""
        # Exactly 50 words - no boost
        query_50 = "word " * 50
        complexity_50 = router._calculate_complexity(query_50.strip())
        assert complexity_50 == pytest.approx(0.1)

        # Exactly 100 words - gets 0.1 boost (>50 condition)
        query_100 = "word " * 100
        complexity_100 = router._calculate_complexity(query_100.strip())
        assert complexity_100 == pytest.approx(0.2)


class TestQueryRouterRouting:
    """Tests for QueryRouter routing decisions."""

    @pytest.fixture
    def router(self):
        """Create a QueryRouter instance."""
        return QueryRouter()

    def test_simple_query_routes_offline(self, router):
        """Simple, non-temporal queries should stay in OFFLINE tier."""
        tier = router.route("hello", SecurityContext())
        assert tier == ProcessingTier.OFFLINE
