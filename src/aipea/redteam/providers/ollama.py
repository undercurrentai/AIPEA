"""Ollama provider — local LLM via httpx → /api/generate.

Reference / smoke-test provider for the redteam package: zero hosted
cost, zero BAA exposure, runs entirely against a local Ollama server.
HIPAA/TACTICAL compliance modes default to this provider per
`ComplianceHandler.force_offline` precedent.

Mirrors the env-var conventions established by
`src/aipea/engine.py:131-147` (`AIPEA_OLLAMA_HOST`,
`AIPEA_OLLAMA_TIMEOUT`).
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import httpx

from aipea.redteam._types import RedTeamResult, Technique

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_HOST: str = "http://localhost:11434"
DEFAULT_OLLAMA_TIMEOUT: float = 120.0
DEFAULT_OLLAMA_MODEL: str = "gemma3:1b"


class OllamaProvider:
    """Local-Ollama provider implementing `RedTeamProvider`.

    Constructor + env precedence mirrors search.py providers: explicit
    constructor arg > env var > default.
    """

    name: str = "ollama"
    default_model: str = DEFAULT_OLLAMA_MODEL

    def __init__(
        self,
        *,
        host: str | None = None,
        timeout: float | None = None,
        model: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.host = host or os.environ.get("AIPEA_OLLAMA_HOST", DEFAULT_OLLAMA_HOST)
        self.timeout = (
            timeout
            if timeout is not None
            else float(os.environ.get("AIPEA_OLLAMA_TIMEOUT", DEFAULT_OLLAMA_TIMEOUT))
        )
        if model:
            self.default_model = model
        # Caller-injectable client for tests (pytest-httpx); when None,
        # `generate()` constructs a per-call client.
        self._client = client

    async def generate(
        self,
        *,
        technique: Technique,
        prompt: str,
        num: int = 1,
        model: str | None = None,
    ) -> list[RedTeamResult]:
        """Generate `num` payloads via local Ollama.

        Ollama doesn't natively support `n=` like OpenAI; this method
        loops `num` times with the same prompt. For larger batches the
        caller is expected to use a frontier provider.

        Connection-pooling note (load-bearing for B1 follow-up frontier
        providers): when `self._client` is None we open ONE
        `httpx.AsyncClient` for the whole batch via `async with`, then
        let it close cleanly. Frontier providers (Anthropic /
        OpenAI Responses / Codex) SHOULD copy this pattern rather than
        the per-call construction the original draft used — TLS+TCP
        handshake amortization + HTTP/2 reuse + keep-alive matter for
        remote endpoints. Local-Ollama doesn't care, but the canonical
        pattern matters.
        """
        chosen_model = model or self.default_model
        results: list[RedTeamResult] = []
        if self._client is not None:
            # Caller-owned client: reuse for all `num` iterations.
            for _ in range(max(1, num)):
                results.append(
                    await self._one_generation(
                        client=self._client,
                        technique=technique,
                        prompt=prompt,
                        model=chosen_model,
                    )
                )
        else:
            # Self-managed: ONE client for the whole batch.
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                for _ in range(max(1, num)):
                    results.append(
                        await self._one_generation(
                            client=client,
                            technique=technique,
                            prompt=prompt,
                            model=chosen_model,
                        )
                    )
        return results

    async def _one_generation(
        self,
        *,
        client: httpx.AsyncClient,
        technique: Technique,
        prompt: str,
        model: str,
    ) -> RedTeamResult:
        """Single Ollama call. Returns a `RedTeamResult` (detected=False;
        evaluator runs `SecurityScanner.scan()` later).

        On provider error (HTTP non-2xx, non-JSON, missing field), the
        returned RedTeamResult has empty `payload` AND `error` set to
        a non-None category string. Downstream evaluator MUST check
        `error` to distinguish "successful but undetected" from
        "provider-side failure"."""
        url = f"{self.host.rstrip('/')}/api/generate"
        body = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        started = time.perf_counter()
        payload_text, error = await self._post(client, url, body)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return RedTeamResult(
            payload=payload_text,
            technique=technique,
            intent=f"technique={technique.value}; model={model}",
            detected=False,
            flags=(),
            generated_by=f"ollama/{model}",
            generated_at=RedTeamResult.now_iso(),
            novelty_score=0.0,
            refinement_round=0,
            cost_usd=0.0,
            latency_ms=elapsed_ms,
            error=error,
        )

    async def _post(
        self,
        client: httpx.AsyncClient,
        url: str,
        body: dict[str, Any],
    ) -> tuple[str, str | None]:
        """Issue the POST and extract the `response` field.

        Returns ``(text, error)`` — ``error`` is ``None`` on success or
        a category string on failure. Empty ``text`` always pairs with
        a non-None ``error`` so the evaluator can distinguish a real
        empty completion from a provider failure.

        Ollama returns:
            {"model": "...", "response": "<generated text>", "done": true, ...}
        """
        try:
            response = await client.post(url, json=body, timeout=self.timeout)
        except httpx.HTTPError as exc:
            logger.warning("Ollama network error: %s", exc)
            return "", "network"
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning("Ollama HTTP %s: %s", exc.response.status_code, exc)
            return "", "http_error"
        try:
            data = response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            logger.warning("Ollama returned non-JSON: %s", exc)
            return "", "non_json"
        text = data.get("response")
        if not isinstance(text, str):
            logger.warning("Ollama response missing 'response' field: %s", data)
            return "", "missing_field"
        return text, None
