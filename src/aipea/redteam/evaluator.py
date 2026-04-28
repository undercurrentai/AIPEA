"""RedTeamEvaluator — runs SecurityScanner + computes TF-IDF novelty.

Stdlib-only TF-IDF + cosine similarity (no sklearn/numpy dep) per the
zero-external-deps constraint. The implementation mirrors the
canonical pattern documented at
https://codingtechroom.com/question/-tf-idf-similarity (April 2026):
- Term frequency via collections.Counter
- IDF: log(N / df) where df is documents-containing-term count
- Cosine: dot(v1, v2) / (||v1|| * ||v2||)
"""

from __future__ import annotations

import dataclasses
import json
import logging
import math
import re
from collections import Counter
from pathlib import Path

from aipea.redteam._types import RedTeamResult, Technique  # noqa: F401  (Technique reserved for B3)
from aipea.security import SecurityContext, SecurityScanner

logger = logging.getLogger(__name__)

# Default OWASP corpus path (the existing canonical fixture).
_CORPUS_PATH: Path = (
    Path(__file__).resolve().parents[3]
    / "tests"
    / "fixtures"
    / "adversarial"
    / "owasp_llm_top10.json"
)

_TOKEN_RE = re.compile(r"[A-Za-z]+")


def _tokenize(text: str) -> list[str]:
    """Lowercase ASCII-letter tokenization. Stdlib-only; sufficient for
    the redteam novelty heuristic — we don't need NLP-grade
    preprocessing here."""
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(text)]


def _tf_idf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    """Compute the TF-IDF vector for a single document."""
    tf = Counter(tokens)
    n = max(1, len(tokens))
    return {t: (count / n) * idf.get(t, 0.0) for t, count in tf.items()}


def _cosine(v1: dict[str, float], v2: dict[str, float]) -> float:
    """Cosine similarity between two sparse TF-IDF dicts."""
    if not v1 or not v2:
        return 0.0
    dot = sum(v1[t] * v2.get(t, 0.0) for t in v1)
    mag1 = math.sqrt(sum(v * v for v in v1.values()))
    mag2 = math.sqrt(sum(v * v for v in v2.values()))
    if mag1 == 0.0 or mag2 == 0.0:
        return 0.0
    return dot / (mag1 * mag2)


class RedTeamEvaluator:
    """Scores generated payloads against SecurityScanner + computes novelty."""

    def __init__(
        self,
        *,
        scanner: SecurityScanner | None = None,
        corpus_path: Path | None = None,
    ) -> None:
        self.scanner = scanner or SecurityScanner()
        self._corpus_idf: dict[str, float] | None = None
        self._corpus_vectors: list[dict[str, float]] | None = None
        self._corpus_path = corpus_path or _CORPUS_PATH

    def evaluate(self, results: list[RedTeamResult]) -> list[RedTeamResult]:
        """Run SecurityScanner + novelty score on each result.

        Skips results where ``error`` is not None (provider failure
        rows must not contaminate the corpus or skew detection
        statistics).

        Returns a new list of RedTeamResult with ``detected``,
        ``flags``, and ``novelty_score`` populated. The original
        instances are untouched (frozen dataclass guarantees).
        """
        ctx = SecurityContext()
        out: list[RedTeamResult] = []
        for r in results:
            if r.error is not None or r.payload == "":
                out.append(r)
                continue
            scan = self.scanner.scan(r.payload, ctx)
            novelty = self._compute_novelty(r.payload)
            out.append(
                dataclasses.replace(
                    r,
                    detected=bool(scan.flags),
                    flags=tuple(scan.flags),
                    novelty_score=novelty,
                )
            )
        return out

    def _compute_novelty(self, payload: str) -> float:
        """Return ``1.0 - max_cosine_similarity`` against the OWASP corpus.

        1.0 = highly novel (no overlap with any corpus payload);
        0.0 = duplicate of an existing entry.
        """
        if self._corpus_vectors is None or self._corpus_idf is None:
            self._load_corpus()
        if self._corpus_vectors is None or self._corpus_idf is None:
            # Corpus unloadable — return neutral novelty.
            return 0.5
        tokens = _tokenize(payload)
        if not tokens:
            return 0.0
        v = _tf_idf_vector(tokens, self._corpus_idf)
        if not v:
            return 1.0
        max_sim = max((_cosine(v, cv) for cv in self._corpus_vectors), default=0.0)
        return max(0.0, 1.0 - max_sim)

    def _load_corpus(self) -> None:
        """Lazy-load + index the OWASP corpus on first use."""
        try:
            data = json.loads(self._corpus_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not load adversarial corpus from %s: %s", self._corpus_path, exc)
            return
        docs = [_tokenize(entry.get("payload", "")) for entry in data if isinstance(entry, dict)]
        docs = [d for d in docs if d]
        if not docs:
            return
        n_docs = len(docs)
        # Document frequency
        df: Counter[str] = Counter()
        for d in docs:
            df.update(set(d))
        idf = {term: math.log(n_docs / max(1, count)) for term, count in df.items()}
        vectors = [_tf_idf_vector(d, idf) for d in docs]
        self._corpus_idf = idf
        self._corpus_vectors = vectors
