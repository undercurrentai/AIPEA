"""Public types for the redteam package.

Defines the `RedTeamProvider` Protocol every provider implements, the
`RedTeamResult` frozen dataclass each generation emits, and the
`Technique` enum that classifies an attack vector.

Kept in a private module (`_types`) so the public package `__init__.py`
can re-export selectively without circular imports between providers
and the generator.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol, runtime_checkable


class Technique(StrEnum):
    """OWASP-aligned attack-vector categories the generator targets.

    String-valued for clean serialization to/from corpus JSON.
    Eight categories cover the bulk of LLM-injection attack surface
    documented in OWASP LLM Top-10 2026 + ClawGuard 2026 + Garak v0.14.1
    probe families.
    """

    ENCODING_BYPASS = "encoding_bypass"
    """Base64 / ROT13 / hex / Unicode-encoded payload to evade pattern match."""

    PARAPHRASE = "paraphrase"
    """Verb-substituted instruction-override (bypass/reset/cancel/...)."""

    ROLE_PLAY = "role_play"
    """Character or persona switch (DAN, jailbreak, unrestricted AI)."""

    MULTI_LANGUAGE = "multi_language"
    """Cross-language verb + noun pair to evade English-only regex."""

    INDIRECT_INJECTION = "indirect_injection"
    """Hidden instruction inside a document, tool output, or retrieval."""

    DELIMITER_ABUSE = "delimiter_abuse"
    """Bracket/XML/JSON tag injection (`</system>`, `[/assistant]`, etc.)."""

    UNICODE_EVASION = "unicode_evasion"
    """Homoglyph / zero-width / RLO / combining-mark obfuscation."""

    INSTRUCTION_SMUGGLING = "instruction_smuggling"
    """Adversarial intent embedded in benign-looking task wrapper."""


@dataclass(frozen=True)
class RedTeamResult:
    """One generated payload + its evaluation against `SecurityScanner`.

    Frozen to make instances hashable + safe to pass between async
    contexts. `flags` is a tuple (not list) for the same reason.

    The `cost_usd` and `latency_ms` fields are populated by the
    provider's wrapper around its httpx call; B2 wires these through to
    the budget ledger (`src/aipea/redteam/budget/ledger.py`).
    """

    payload: str
    """The adversarial input string the generator produced."""

    technique: Technique
    """Which attack-vector category the prompt seeded."""

    intent: str
    """One-sentence description of the attacker objective."""

    detected: bool
    """Whether `SecurityScanner.scan(payload)` set any blocking flag."""

    flags: tuple[str, ...]
    """Flags the scanner emitted (empty tuple if not detected)."""

    generated_by: str
    """Provider + model identifier (e.g. ``ollama/gemma3:1b``,
    ``anthropic/claude-opus-4-7``, ``openai/gpt-5.5-pro``)."""

    generated_at: str
    """ISO-8601 UTC timestamp of generation. Use `RedTeamResult.now_iso()`
    when constructing from inside a provider."""

    novelty_score: float = 0.0
    """0.0-1.0 cosine distance to the existing corpus (TF-IDF on
    payload tokens). 1.0 = highly novel; 0.0 = duplicate. Computed by
    the evaluator, not the provider."""

    refinement_round: int = 0
    """0 = first generation; 1-3 = post-refinement variants."""

    cost_usd: float = 0.0
    """Estimated cost of the LLM call that produced this result.
    Provider-supplied; 0.0 for Ollama/local."""

    latency_ms: int = 0
    """Wall-clock latency of the generation call in milliseconds."""

    error: str | None = None
    """Provider-side error category, or ``None`` on success.

    When set, ``payload`` is empty (or partial) due to an upstream
    failure: HTTP non-2xx, non-JSON response, missing expected field,
    network error, etc. The downstream evaluator MUST skip results
    with non-None ``error`` rather than scoring them as benign
    generations — otherwise an HTTP 500 from a provider produces a
    corpus row indistinguishable from a successful, undetected attack.
    Suggested vocabulary: ``"http_error"``, ``"non_json"``,
    ``"missing_field"``, ``"network"``, ``"timeout"``,
    ``"empty_response"``."""

    @staticmethod
    def now_iso() -> str:
        """Return current UTC time as an ISO-8601 string with seconds precision."""
        return datetime.now(UTC).replace(microsecond=0).isoformat()


@runtime_checkable
class RedTeamProvider(Protocol):
    """Provider Protocol: every concrete provider implements `generate`.

    The Protocol is `runtime_checkable` so `isinstance(p, RedTeamProvider)`
    works at provider-registry time. Implementations live in
    `src/aipea/redteam/providers/`.

    Implementations MUST:
    - Use httpx only (no provider SDK as a runtime dep)
    - Honor an injectable `httpx.AsyncClient` for tests via pytest-httpx
    - Emit `RedTeamResult` instances with `generated_by` set to a
      stable identifier of form ``<provider>/<model>``
    - For long-call providers (gpt-5.5-pro background mode, Opus 4.7
      streaming), use `aipea.redteam._polling.poll_until_terminal()` or
      Anthropic's `client.messages.stream(...)` respectively — never
      block on a sync HTTP request that may exceed 5 minutes.
    """

    name: str
    """Provider name (lower-case, e.g. ``ollama``, ``anthropic``,
    ``openai``, ``codex``). Used by the CLI's ``--provider`` flag."""

    default_model: str
    """The model identifier used when the caller doesn't pass ``--model``."""

    async def generate(
        self,
        *,
        technique: Technique,
        prompt: str,
        num: int = 1,
        model: str | None = None,
    ) -> list[RedTeamResult]:
        """Generate ``num`` candidate payloads in the given technique class.

        Args:
            technique: Attack-vector category; provider seeds the prompt
                with the technique-specific framing.
            prompt: The render-ready prompt text. The generator (caller)
                does the technique seeding; provider just relays.
            num: Number of payloads to produce in this call.
            model: Override the provider's `default_model`.

        Returns:
            List of `RedTeamResult`. The provider does NOT run the
            evaluator (that's the generator's job); `detected` and
            `flags` are populated downstream.
        """
        ...
