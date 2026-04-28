"""Provider registry + Protocol re-export for the redteam package.

Concrete providers implementing `RedTeamProvider`:
  - `OllamaProvider` — local LLM via httpx (PR-B1, this commit)
  - `AnthropicProvider` — Messages API streaming (PR-B1, follow-up)
  - `OpenAIResponsesProvider` — Responses API background mode (PR-B1, follow-up)
  - `OpenAICodexProvider` — gpt-5.3-codex Responses API (PR-B1, follow-up)
"""

from __future__ import annotations

import inspect

from aipea.redteam._types import RedTeamProvider
from aipea.redteam.providers.ollama import OllamaProvider


def _validate_provider(provider_cls: type) -> None:
    """Validate provider conforms to RedTeamProvider Protocol shape + async-ness.

    `runtime_checkable` Protocol only enforces *attribute presence*,
    not coroutine-ness. A class with a synchronous `def generate(...)`
    that returns a `list[RedTeamResult]` would pass `isinstance(p,
    RedTeamProvider)` cleanly, then fail at the call site with a
    confusing ``TypeError: object list can't be used in 'await'
    expression``. Catch that footgun at registration time instead.
    """
    if not hasattr(provider_cls, "name"):
        raise TypeError(f"{provider_cls.__name__} missing required `name` attribute")
    if not hasattr(provider_cls, "default_model"):
        raise TypeError(f"{provider_cls.__name__} missing required `default_model` attribute")
    # `getattr` rather than `provider_cls.generate` — the Protocol
    # contract guarantees the attribute, but mypy under `--strict`
    # doesn't model `type` as having arbitrary attributes. The
    # `iscoroutinefunction` check accepts any callable.
    generate = getattr(provider_cls, "generate", None)
    if generate is None:
        raise TypeError(f"{provider_cls.__name__} missing required `generate` method")
    if not inspect.iscoroutinefunction(generate):
        raise TypeError(
            f"{provider_cls.__name__}.generate must be `async def`; "
            f"runtime_checkable Protocol does not enforce this"
        )


# Provider registry — extended as later providers ship in B1.
# CLI uses this to power `aipea redteam list-providers`.
PROVIDERS: dict[str, type[RedTeamProvider]] = {
    OllamaProvider.name: OllamaProvider,
}

# Validate every registered provider at package import time. Adding a
# new provider that fails this check raises ImportError on `import
# aipea.redteam` — fail-fast at the contributor's machine rather than
# at the first user invocation.
for _provider_cls in PROVIDERS.values():
    _validate_provider(_provider_cls)


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
    "_validate_provider",
    "get_provider",
]
