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
