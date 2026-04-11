"""AIPEA Quality Assessor — heuristic scoring for prompt enhancements.

Measures quality improvement between an original query and its enhanced
version using purely heuristic techniques (no ML dependencies).

Scores are in the range [0.0, 1.0] where higher is better.

Design principles:
- Zero external dependencies (stdlib only)
- Deterministic scoring (same inputs → same outputs)
- Lightweight: suitable for real-time enhancement pipelines
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CONTENT_WORD_RE = re.compile(r"\b[a-zA-Z]{3,}\b")
_SENTENCE_RE = re.compile(r"[.!?]+")
_STEP_MARKERS_RE = re.compile(
    r"\b(step\s+\d|first|second|third|finally|next|then)\b",
    re.IGNORECASE,
)
_CONSTRAINT_KW_RE = re.compile(
    r"\b(must|should|require|ensure|constraint|limit|restrict|validate)\b",
    re.IGNORECASE,
)
_QUESTION_RE = re.compile(r"\?")
_STRUCTURE_MARKERS_RE = re.compile(
    r"(\n[-*]\s|\n\d+[.)]\s|\[.+?\]|\n#{1,3}\s)",
)


def _content_words(text: str) -> list[str]:
    """Return content words (>=3 letters) from *text*."""
    return _CONTENT_WORD_RE.findall(text)


def _sentence_count(text: str) -> int:
    """Rough sentence count via terminal-punctuation splits."""
    parts = _SENTENCE_RE.split(text.strip())
    return max(1, len([p for p in parts if p.strip()]))


def _avg_sentence_length(text: str) -> float:
    """Average words per sentence."""
    words = len(text.split())
    sentences = _sentence_count(text)
    return words / sentences if sentences else float(words)


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# QualityScore dataclass
# ---------------------------------------------------------------------------


@dataclass
class QualityScore:
    """Quality assessment of a prompt enhancement.

    All sub-scores are in [0.0, 1.0].  ``overall`` is a weighted composite.

    Attributes:
        clarity_improvement: Readability delta (sentence length, questions).
        specificity_gain: Unique content-word count gain.
        information_density: Content-word ratio delta.
        instruction_quality: Presence of step markers, constraints.
        overall: Weighted composite score.
    """

    clarity_improvement: float
    specificity_gain: float
    information_density: float
    instruction_quality: float
    overall: float

    def to_dict(self) -> dict[str, float]:
        """Serialize to dictionary."""
        return {
            "clarity_improvement": round(self.clarity_improvement, 4),
            "specificity_gain": round(self.specificity_gain, 4),
            "information_density": round(self.information_density, 4),
            "instruction_quality": round(self.instruction_quality, 4),
            "overall": round(self.overall, 4),
        }


# ---------------------------------------------------------------------------
# QualityAssessor
# ---------------------------------------------------------------------------

# Default weights for the composite score
_WEIGHTS = {
    "clarity": 0.25,
    "specificity": 0.30,
    "density": 0.20,
    "instruction": 0.25,
}


class QualityAssessor:
    """Heuristic quality assessor for prompt enhancements.

    Compares an *original* query to its *enhanced* version and produces a
    :class:`QualityScore` capturing clarity, specificity, information density,
    and instruction quality improvements.

    Usage::

        assessor = QualityAssessor()
        score = assessor.assess("What is AI?", "Explain artificial intelligence ...")
        print(score.overall)
    """

    def assess(self, original: str, enhanced: str) -> QualityScore:
        """Score the quality improvement from *original* to *enhanced*.

        Args:
            original: The original user query.
            enhanced: The enhanced prompt.

        Returns:
            A :class:`QualityScore` with sub-scores and composite.
        """
        if not original or not enhanced:
            return QualityScore(
                clarity_improvement=0.0,
                specificity_gain=0.0,
                information_density=0.0,
                instruction_quality=0.0,
                overall=0.0,
            )

        clarity = self._score_clarity(original, enhanced)
        specificity = self._score_specificity(original, enhanced)
        density = self._score_density(original, enhanced)
        instruction = self._score_instruction(enhanced)

        overall = (
            _WEIGHTS["clarity"] * clarity
            + _WEIGHTS["specificity"] * specificity
            + _WEIGHTS["density"] * density
            + _WEIGHTS["instruction"] * instruction
        )

        return QualityScore(
            clarity_improvement=round(clarity, 4),
            specificity_gain=round(specificity, 4),
            information_density=round(density, 4),
            instruction_quality=round(instruction, 4),
            overall=round(overall, 4),
        )

    # -- Sub-score methods --------------------------------------------------

    @staticmethod
    def _score_clarity(original: str, enhanced: str) -> float:
        """Clarity improvement via readability delta.

        Rewards shorter average sentence length in the enhanced prompt
        (more readable) and rewards added question marks (clarifying).
        Also rewards structural markers (bullets, numbered lists, headings).
        """
        # Whitespace-only or empty enhanced prompts contribute no clarity. (#93)
        if not enhanced.strip():
            return 0.0

        orig_avg = _avg_sentence_length(original)
        enh_avg = _avg_sentence_length(enhanced)

        # Improvement when enhanced has shorter or similar sentences
        # despite being longer overall.  Use sigmoid-like scaling.
        len_ratio = orig_avg / enh_avg if enh_avg > 0 else 1.0
        readability = _clamp(1 - math.exp(-len_ratio), 0.0, 1.0)

        # Bonus for added structure
        orig_struct = len(_STRUCTURE_MARKERS_RE.findall(original))
        enh_struct = len(_STRUCTURE_MARKERS_RE.findall(enhanced))
        structure_bonus = _clamp((enh_struct - orig_struct) * 0.1)

        # Bonus for clarifying questions
        orig_q = len(_QUESTION_RE.findall(original))
        enh_q = len(_QUESTION_RE.findall(enhanced))
        question_bonus = _clamp((enh_q - orig_q) * 0.05)

        return _clamp(readability + structure_bonus + question_bonus)

    @staticmethod
    def _score_specificity(original: str, enhanced: str) -> float:
        """Specificity gain via unique content-word growth.

        Measures the ratio of *new* unique content words introduced
        by the enhancement.
        """
        orig_words = set(w.lower() for w in _content_words(original))
        enh_words = set(w.lower() for w in _content_words(enhanced))

        if not orig_words:
            # Original had no content words; any addition is a big gain
            return _clamp(len(enh_words) * 0.1)

        new_words = enh_words - orig_words
        gain_ratio = len(new_words) / len(orig_words)
        # Sigmoid scaling so diminishing returns kick in
        return _clamp(1 - math.exp(-gain_ratio * 0.5))

    @staticmethod
    def _score_density(original: str, enhanced: str) -> float:
        """Information density improvement.

        Compares the ratio of content words to total words before and
        after enhancement.
        """

        def _ratio(text: str) -> float:
            total = len(text.split())
            content = len(_content_words(text))
            return content / total if total else 0.0

        orig_r = _ratio(original)
        enh_r = _ratio(enhanced)

        # Delta in content-word ratio.  Positive = denser.
        delta = enh_r - orig_r
        # Score continuously around a 0.5 baseline so a tiny positive delta
        # doesn't drop below a tiny negative delta. Previously the two
        # branches crossed discontinuously at delta=0 (delta=+0.001 scored
        # 0.007 while delta=-0.001 scored 0.499), producing non-monotonic
        # quality scores on near-neutral density changes. (#105)
        #
        # - delta = +0.15 (docstring "excellent")  ->  1.0
        # - delta = 0     (no change)              ->  0.5
        # - delta = -0.5  (worst realistic drop)   ->  0.0
        if delta >= 0:
            return _clamp(0.5 + (delta / 0.15) * 0.5)
        # No penalty for slight drop when the enhanced prompt is much longer
        # (longer prompts naturally dilute ratio a bit)
        return _clamp(0.5 + delta)

    @staticmethod
    def _score_instruction(enhanced: str) -> float:
        """Instruction quality of the enhanced prompt.

        Looks for step markers ("Step 1", "First", "Then") and
        constraint keywords ("must", "should", "ensure").
        """
        steps = len(_STEP_MARKERS_RE.findall(enhanced))
        constraints = len(_CONSTRAINT_KW_RE.findall(enhanced))

        step_score = _clamp(steps * 0.15)
        constraint_score = _clamp(constraints * 0.12)

        return _clamp(step_score + constraint_score)


__all__ = [
    "QualityAssessor",
    "QualityScore",
]
