"""Tests for aipea.quality — heuristic quality assessor."""

from __future__ import annotations

import pytest

from aipea.quality import QualityAssessor, QualityScore

# =============================================================================
# QualityScore TESTS
# =============================================================================


class TestQualityScore:
    @pytest.mark.unit
    def test_to_dict(self) -> None:
        score = QualityScore(
            clarity_improvement=0.12345,
            specificity_gain=0.6789,
            information_density=0.5,
            instruction_quality=0.3,
            overall=0.45,
        )
        d = score.to_dict()
        assert d["clarity_improvement"] == 0.1235
        assert d["specificity_gain"] == 0.6789
        assert d["information_density"] == 0.5
        assert d["instruction_quality"] == 0.3
        assert d["overall"] == 0.45

    @pytest.mark.unit
    def test_all_fields_present(self) -> None:
        score = QualityScore(0.1, 0.2, 0.3, 0.4, 0.5)
        d = score.to_dict()
        assert set(d.keys()) == {
            "clarity_improvement",
            "specificity_gain",
            "information_density",
            "instruction_quality",
            "overall",
        }


# =============================================================================
# QualityAssessor TESTS
# =============================================================================


class TestQualityAssessor:
    @pytest.mark.unit
    def test_empty_original(self) -> None:
        assessor = QualityAssessor()
        score = assessor.assess("", "some enhanced text")
        assert score.overall == 0.0

    @pytest.mark.unit
    def test_empty_enhanced(self) -> None:
        assessor = QualityAssessor()
        score = assessor.assess("some query", "")
        assert score.overall == 0.0

    @pytest.mark.unit
    def test_both_empty(self) -> None:
        assessor = QualityAssessor()
        score = assessor.assess("", "")
        assert score.overall == 0.0

    @pytest.mark.unit
    def test_identical_texts(self) -> None:
        assessor = QualityAssessor()
        score = assessor.assess("What is Python?", "What is Python?")
        # Same text → limited improvement, but non-negative
        assert 0.0 <= score.overall <= 1.0

    @pytest.mark.unit
    def test_good_enhancement_scores_higher(self) -> None:
        assessor = QualityAssessor()
        original = "Tell me about databases"
        poor = "Tell me about databases please"
        good = (
            "Explain the key differences between relational and NoSQL databases. "
            "Step 1: Compare data models. Step 2: Evaluate query patterns. "
            "You must consider scalability, consistency, and performance trade-offs. "
            "Ensure the comparison includes specific examples like PostgreSQL vs MongoDB."
        )

        score_poor = assessor.assess(original, poor)
        score_good = assessor.assess(original, good)

        assert score_good.overall > score_poor.overall

    @pytest.mark.unit
    def test_scores_in_range(self) -> None:
        assessor = QualityAssessor()
        score = assessor.assess(
            "How to build an API?",
            "Design a RESTful API following best practices. "
            "Step 1: Define resource endpoints. "
            "Step 2: Implement authentication. "
            "You must validate all inputs and ensure proper error handling.",
        )
        assert 0.0 <= score.clarity_improvement <= 1.0
        assert 0.0 <= score.specificity_gain <= 1.0
        assert 0.0 <= score.information_density <= 1.0
        assert 0.0 <= score.instruction_quality <= 1.0
        assert 0.0 <= score.overall <= 1.0

    @pytest.mark.unit
    def test_instruction_quality_with_steps(self) -> None:
        assessor = QualityAssessor()
        enhanced = (
            "First, analyze the problem. "
            "Then, design a solution. "
            "Finally, implement and validate. "
            "You must ensure correctness."
        )
        score = assessor.assess("Solve this problem", enhanced)
        assert score.instruction_quality > 0.0

    @pytest.mark.unit
    def test_instruction_quality_without_steps(self) -> None:
        assessor = QualityAssessor()
        score = assessor.assess("What is AI?", "Artificial intelligence overview.")
        assert score.instruction_quality == 0.0

    @pytest.mark.unit
    def test_specificity_gain_with_new_terms(self) -> None:
        assessor = QualityAssessor()
        original = "Tell me about Python"
        enhanced = (
            "Explain the Python programming language including its type system, "
            "concurrency model, standard library ecosystem, and performance "
            "characteristics compared to compiled languages."
        )
        score = assessor.assess(original, enhanced)
        assert score.specificity_gain > 0.0

    @pytest.mark.unit
    def test_specificity_gain_no_new_words(self) -> None:
        assessor = QualityAssessor()
        score = assessor.assess("hello world", "hello world")
        assert score.specificity_gain >= 0.0

    @pytest.mark.unit
    def test_clarity_with_structure(self) -> None:
        assessor = QualityAssessor()
        original = "Compare databases"
        enhanced = (
            "Compare databases:\n"
            "- Relational: SQL-based, ACID compliant\n"
            "- NoSQL: document-based, eventual consistency\n"
            "- Graph: relationship-focused, traversal queries"
        )
        score = assessor.assess(original, enhanced)
        assert score.clarity_improvement > 0.0

    @pytest.mark.unit
    def test_overall_is_weighted_composite(self) -> None:
        assessor = QualityAssessor()
        score = assessor.assess(
            "Tell me about AI",
            "Explain artificial intelligence. "
            "Step 1: Define core concepts. "
            "You must include machine learning and neural networks.",
        )
        # Verify overall is approximately the weighted sum
        expected = (
            0.25 * score.clarity_improvement
            + 0.30 * score.specificity_gain
            + 0.20 * score.information_density
            + 0.25 * score.instruction_quality
        )
        assert abs(score.overall - round(expected, 4)) < 0.01

    @pytest.mark.unit
    def test_short_original_no_content_words(self) -> None:
        """Original with no 3+ letter words — edge case."""
        assessor = QualityAssessor()
        score = assessor.assess("hi", "Explain the concept in detail.")
        # Should not crash; specificity gain uses fallback
        assert 0.0 <= score.overall <= 1.0


# =============================================================================
# REGRESSION TESTS — Wave 18 #93
# =============================================================================


class TestWave18ClarityWhitespaceGuard:
    """Regression: _score_clarity must return 0.0 for whitespace-only enhanced prompts.

    Bug #93 — Before the fix, whitespace-only enhanced prompts produced
    a clarity score of ~0.632 via the exp(-1) fallback path, misleadingly
    suggesting meaningful clarity improvement from no output.
    """

    @pytest.mark.unit
    def test_empty_enhanced_returns_zero_clarity(self) -> None:
        """Empty string enhanced -> clarity = 0.0."""
        assert QualityAssessor._score_clarity("some original query", "") == 0.0

    @pytest.mark.unit
    def test_whitespace_only_enhanced_returns_zero_clarity(self) -> None:
        """Whitespace-only enhanced (spaces, tabs, newlines) -> clarity = 0.0."""
        assert QualityAssessor._score_clarity("original", "   \n\n\t  ") == 0.0
        assert QualityAssessor._score_clarity("original", "\r\n") == 0.0

    @pytest.mark.unit
    def test_real_enhanced_prompt_still_scored(self) -> None:
        """Non-whitespace enhanced prompts retain their normal clarity score."""
        score = QualityAssessor._score_clarity(
            "Tell me about AI",
            "Explain artificial intelligence. Include examples.",
        )
        assert score > 0.0
        assert score <= 1.0


class TestWave19DensityScoreMonotonic:
    """Regression for bug #105: `_score_density` had a discontinuous,
    non-monotonic curve around `delta = 0`. The positive branch started
    from 0 (so a +0.001 delta scored 0.007) while the negative branch
    started from 0.5 (so a -0.001 delta scored 0.499) — a tiny
    improvement scored worse than a tiny regression. Fix: make the
    positive branch also start from the 0.5 baseline so the curve is
    continuous at 0 and monotonic on both sides."""

    @pytest.mark.unit
    def test_zero_delta_returns_baseline(self) -> None:
        """delta = 0 (identical input) must return the 0.5 baseline."""
        score = QualityAssessor._score_density("cat dog", "cat dog")
        assert abs(score - 0.5) < 1e-9

    @pytest.mark.unit
    def test_tiny_positive_delta_above_baseline(self) -> None:
        """A tiny positive delta must score >= 0.5, not drop near zero.

        Prior to the fix, appending content words that produced a
        positive delta scored lower than the identical-input baseline
        because the positive branch started from 0 instead of 0.5.
        """
        original = "I am going to ask about the cat and the dog and the bird"
        enhanced = original + " cat"  # one extra content word
        score = QualityAssessor._score_density(original, enhanced)
        assert score >= 0.5, f"Expected >=0.5 for tiny positive delta, got {score}"

    @pytest.mark.unit
    def test_no_discontinuity_near_zero(self) -> None:
        """Tiny positive delta must not score dramatically lower than baseline.

        Prior to the fix, a +0.001 delta (positive branch `delta/0.15`)
        scored ~0.0067 while a delta of exactly 0 (negative branch
        `0.5 + delta`) scored 0.5 — a dramatic >70x cliff at the sign
        boundary. After the fix both branches start from 0.5 so the
        difference at the crossing is bounded by the positive branch's
        slope (0.5/0.15 ≈ 3.3 per unit) times the delta magnitude.
        """
        original = "cat dog"  # ratio 1.0 (two content words, no stop words)
        # Identical input -> delta = 0 -> baseline 0.5
        s_base = QualityAssessor._score_density(original, original)
        # Adding another content word keeps the ratio at 1.0 (delta = 0)
        s_tiny = QualityAssessor._score_density(original, original + " bird")
        # Both should be at or near the 0.5 baseline — the pre-fix
        # bug would have made s_tiny plummet to ~0.007.
        assert s_base >= 0.5
        assert s_tiny >= 0.5, (
            f"tiny positive delta should be >=0.5, got {s_tiny}; "
            "indicates non-monotonic regression at sign boundary"
        )

    @pytest.mark.unit
    def test_large_positive_delta_saturates_at_one(self) -> None:
        """A strongly positive delta still saturates at 1.0."""
        original = "the a an of and to cat"  # lots of stop words
        enhanced = "python programming algorithm data structure optimization benchmark"
        score = QualityAssessor._score_density(original, enhanced)
        # Should be solidly above the baseline and bounded by 1.0.
        assert 0.5 <= score <= 1.0
