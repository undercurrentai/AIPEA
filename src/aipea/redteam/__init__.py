"""AIPEA redteam package — adversarial-payload generation for SecurityScanner evaluation.

Implements ADR-009 (LLM-Driven Red Team Engine). Public surface kept
deliberately minimal at the package level; deeper imports
(`aipea.redteam.providers.ollama.OllamaProvider`) are stable for
power-users + tests.

Status (2026-04-28):
  - PR-B1 in progress: skeleton + types + Ollama provider + basic CLI.
  - PR-B1 follow-ups: AnthropicProvider, OpenAIResponsesProvider,
    OpenAICodexProvider, generator iterative refinement, evaluator,
    reporter.
  - PR-B2 (next): budget ledger + circuit breaker + daemon mode.
  - PR-B3 (next): Council Mode + AgenticRed archive + CI cron.

See ~/.claude/plans/review-and-orient-yourself-jazzy-dragon.md for the
full multi-PR plan.
"""

from __future__ import annotations

from aipea.redteam._polling import (
    DEFAULT_POLL_INTERVAL_SECONDS,
    DEFAULT_POLL_TIMEOUT_SECONDS,
    TERMINAL_STATES,
    PollTimeoutError,
    poll_until_terminal,
)
from aipea.redteam._resolve import resolve_api_key, resolve_provider_url
from aipea.redteam._types import RedTeamProvider, RedTeamResult, Technique
from aipea.redteam.providers import PROVIDERS, OllamaProvider, get_provider

__all__ = [
    "DEFAULT_POLL_INTERVAL_SECONDS",
    "DEFAULT_POLL_TIMEOUT_SECONDS",
    "PROVIDERS",
    "TERMINAL_STATES",
    "OllamaProvider",
    "PollTimeoutError",
    "RedTeamProvider",
    "RedTeamResult",
    "Technique",
    "get_provider",
    "poll_until_terminal",
    "resolve_api_key",
    "resolve_provider_url",
]
