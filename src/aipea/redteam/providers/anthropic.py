"""Anthropic provider — Messages API with adaptive thinking + SSE streaming.

Pure-httpx implementation (no `anthropic` SDK as runtime dep) targeting
Claude Opus 4.7 (released 2026-04-16). Per the official streaming docs
(`docs.anthropic.com/en/api/streaming`):

- `stream: true` returns SSE events with named types: `message_start`,
  `content_block_start`, `content_block_delta`, `content_block_stop`,
  `message_delta`, `message_stop`.
- Adaptive thinking (`thinking: {type: "adaptive"}`) is REQUIRED on Opus
  4.7 — manual `{type: "enabled", budget_tokens: N}` returns HTTP 400.
- `thinking_delta` events carry the model's chain-of-thought; we
  discard them (only the final text content is the adversarial payload).
- Streaming avoids the "long-call HTTP timeout before first token"
  failure mode that plain POST+wait would hit on extended-thinking
  requests.

Headers required:
- ``x-api-key``: the Anthropic API key
- ``anthropic-version: 2023-06-01``: the stable version pin
- ``content-type: application/json``

Refs:
- https://www.anthropic.com/news/claude-opus-4-7
- https://docs.anthropic.com/en/api/streaming
- https://docs.anthropic.com/en/build-with-claude/extended-thinking
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from aipea.redteam._resolve import resolve_api_key
from aipea.redteam._types import RedTeamResult, Technique

logger = logging.getLogger(__name__)

DEFAULT_ANTHROPIC_API_URL: str = "https://api.anthropic.com/v1/messages"
DEFAULT_ANTHROPIC_MODEL: str = "claude-opus-4-7"
DEFAULT_ANTHROPIC_TIMEOUT: float = 1500.0  # 25 min — same cap as poll_until_terminal
DEFAULT_ANTHROPIC_MAX_TOKENS: int = 4096
ANTHROPIC_VERSION_HEADER: str = "2023-06-01"

# Cost per million tokens for Opus 4.7 (USD). Pricing per
# https://www.anthropic.com/news/claude-opus-4-7 (2026-04-16).
_OPUS_47_INPUT_COST_PER_MTOK: float = 5.0
_OPUS_47_OUTPUT_COST_PER_MTOK: float = 25.0


class AnthropicProvider:
    """Anthropic Messages-API provider with adaptive-thinking SSE streaming."""

    name: str = "anthropic"
    default_model: str = DEFAULT_ANTHROPIC_MODEL

    def __init__(
        self,
        *,
        api_key: str | None = None,
        api_url: str | None = None,
        timeout: float | None = None,
        max_tokens: int = DEFAULT_ANTHROPIC_MAX_TOKENS,
        model: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = resolve_api_key("ANTHROPIC_API_KEY", api_key)
        self.api_url = api_url or DEFAULT_ANTHROPIC_API_URL
        self.timeout = timeout if timeout is not None else DEFAULT_ANTHROPIC_TIMEOUT
        self.max_tokens = max_tokens
        if model:
            self.default_model = model
        self._client = client

    async def generate(
        self,
        *,
        technique: Technique,
        prompt: str,
        num: int = 1,
        model: str | None = None,
    ) -> list[RedTeamResult]:
        """Generate ``num`` payloads via Anthropic Messages streaming.

        Each iteration is a separate /v1/messages call — adaptive
        thinking + SSE means we read the full stream before producing
        the RedTeamResult. Connection-pooling: ONE client for the
        whole batch (mirrors Ollama pattern).
        """
        if num <= 0:
            return []
        if not self.api_key:
            return [
                self._error_result(
                    technique=technique, model=model or self.default_model, error="missing_api_key"
                )
                for _ in range(num)
            ]
        chosen_model = model or self.default_model
        results: list[RedTeamResult] = []
        if self._client is not None:
            for _ in range(num):
                results.append(
                    await self._one_generation(
                        client=self._client,
                        technique=technique,
                        prompt=prompt,
                        model=chosen_model,
                    )
                )
        else:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                for _ in range(num):
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
        body = {
            "model": model,
            "max_tokens": self.max_tokens,
            "stream": True,
            "thinking": {"type": "adaptive"},
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION_HEADER,
            "content-type": "application/json",
        }
        started = time.perf_counter()
        text_chunks: list[str] = []
        usage_in, usage_out = 0, 0
        error: str | None = None
        try:
            async with client.stream(
                "POST", self.api_url, json=body, headers=headers, timeout=self.timeout
            ) as response:
                if response.status_code >= 400:
                    body_text = await response.aread()
                    logger.warning("Anthropic HTTP %s: %s", response.status_code, body_text[:500])
                    error = "http_error"
                else:
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        try:
                            event = json.loads(line[6:])
                        except json.JSONDecodeError:
                            continue
                        evt_type = event.get("type")
                        if evt_type == "content_block_delta":
                            delta = event.get("delta", {})
                            # text_delta is the adversarial payload; thinking_delta is
                            # discarded (CoT is not the attack candidate)
                            if delta.get("type") == "text_delta":
                                text_chunks.append(delta.get("text", ""))
                        elif evt_type == "message_delta":
                            usage = event.get("usage", {}) or {}
                            usage_out = max(usage_out, int(usage.get("output_tokens", 0) or 0))
                        elif evt_type == "message_start":
                            msg = event.get("message", {}) or {}
                            usage = msg.get("usage", {}) or {}
                            usage_in = int(usage.get("input_tokens", 0) or 0)
        except httpx.HTTPError as exc:
            logger.warning("Anthropic network error: %s", exc)
            error = "network"

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        text = "".join(text_chunks)
        if error is None and text == "":
            error = "empty_response"
        cost_usd = (
            usage_in * _OPUS_47_INPUT_COST_PER_MTOK / 1_000_000
            + usage_out * _OPUS_47_OUTPUT_COST_PER_MTOK / 1_000_000
        )
        return RedTeamResult(
            payload=text,
            technique=technique,
            intent=f"technique={technique.value}; model={model}",
            detected=False,
            flags=(),
            generated_by=f"anthropic/{model}",
            generated_at=RedTeamResult.now_iso(),
            novelty_score=0.0,
            refinement_round=0,
            cost_usd=cost_usd,
            latency_ms=elapsed_ms,
            error=error,
        )

    def _error_result(self, *, technique: Technique, model: str, error: str) -> RedTeamResult:
        return RedTeamResult(
            payload="",
            technique=technique,
            intent=f"technique={technique.value}; model={model}",
            detected=False,
            flags=(),
            generated_by=f"anthropic/{model}",
            generated_at=RedTeamResult.now_iso(),
            novelty_score=0.0,
            refinement_round=0,
            cost_usd=0.0,
            latency_ms=0,
            error=error,
        )

    def _post(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        """Test-introspection helper — Anthropic uses streaming, not POST."""
        raise NotImplementedError("AnthropicProvider streams; no _post() entry point")
