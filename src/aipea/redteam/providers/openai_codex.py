"""OpenAI Codex provider — gpt-5.3-codex via Responses API background mode.

Thin variant of OpenAIResponsesProvider with a Codex-tuned default
model. Reuses the same Responses-API background-mode pattern + polling
helper so frontier-model API drift only needs to be fixed in one
place.
"""

from __future__ import annotations

from typing import Any

import httpx

from aipea.redteam.providers.openai_responses import OpenAIResponsesProvider

DEFAULT_CODEX_MODEL: str = "gpt-5.3-codex"


class OpenAICodexProvider(OpenAIResponsesProvider):
    """gpt-5.3-codex via OpenAI Responses API background mode.

    Inherits the full Responses-API + polling implementation from
    ``OpenAIResponsesProvider``; overrides only the default model and
    the public name.
    """

    name: str = "codex"
    default_model: str = DEFAULT_CODEX_MODEL

    def __init__(
        self,
        *,
        api_key: str | None = None,
        api_base: str | None = None,
        timeout: float | None = None,
        poll_timeout_seconds: int = 1500,
        poll_interval_seconds: int = 5,
        reasoning_effort: str = "high",
        model: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            api_base=api_base,
            timeout=timeout,
            poll_timeout_seconds=poll_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
            reasoning_effort=reasoning_effort,
            model=model or DEFAULT_CODEX_MODEL,
            client=client,
        )

    def __repr__(self) -> str:
        return f"OpenAICodexProvider(model={self.default_model!r})"

    def _ensure_codex(self) -> None:  # pragma: no cover - documentation hook
        """Validates default_model is a Codex variant; called from tests."""
        if "codex" not in self.default_model.lower():
            raise ValueError(
                f"OpenAICodexProvider configured with non-Codex model {self.default_model!r}"
            )

    @classmethod
    def supports_model(cls, model: str) -> bool:
        """Heuristic: Codex models contain 'codex' in their identifier.

        Returns True for ``gpt-5.3-codex``, ``gpt-5.2-codex``, etc.
        """
        return "codex" in model.lower()

    @staticmethod
    def _internal_marker() -> dict[str, Any]:
        return {"provider": "codex", "subclass_of": "openai_responses"}
