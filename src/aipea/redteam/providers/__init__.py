"""Provider registry + Protocol re-export for the redteam package.

Concrete providers implementing `RedTeamProvider`:
  - `OllamaProvider` — local LLM via httpx (PR-B1, this commit)
  - `AnthropicProvider` — Messages API streaming (PR-B1, follow-up)
  - `OpenAIResponsesProvider` — Responses API background mode (PR-B1, follow-up)
  - `OpenAICodexProvider` — gpt-5.3-codex Responses API (PR-B1, follow-up)
"""

from __future__ import annotations

from aipea.redteam._types import RedTeamProvider
from aipea.redteam.providers.ollama import OllamaProvider

# Provider registry — extended as later providers ship in B1.
# CLI uses this to power `aipea redteam list-providers`.
PROVIDERS: dict[str, type[RedTeamProvider]] = {
    OllamaProvider.name: OllamaProvider,
}


def get_provider(name: str) -> type[RedTeamProvider]:
    """Look up a provider class by name.

    Raises:
        KeyError: if `name` is not registered. Caller (CLI) translates
            into a user-friendly error message.
    """
    if name not in PROVIDERS:
        raise KeyError(f"unknown provider {name!r}; available: {sorted(PROVIDERS)}")
    return PROVIDERS[name]


__all__ = [
    "PROVIDERS",
    "OllamaProvider",
    "RedTeamProvider",
    "get_provider",
]
