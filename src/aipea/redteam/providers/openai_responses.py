"""OpenAI Responses-API provider — gpt-5.5-pro background mode + 25-min poll.

Pure-httpx implementation (no `openai` SDK as runtime dep) targeting
gpt-5.5-pro (released 2026-04-23, snapshot ``gpt-5.5-pro-2026-04-23``).

Per `developers.openai.com/docs/guides/background`:
- POST /v1/responses with ``background: true, store: true``
- GET /v1/responses/{id} to retrieve (long-poll until terminal)
- POST /v1/responses/{id}/cancel to release server-side slot on timeout
- Background mode retains state for ~10 min — NOT ZDR-compatible

Reuses ``aipea.redteam._polling.poll_until_terminal`` (extracted from
the original ``gpt_review.py`` polling loop) for the deadline +
cancel + retry logic.

Refs:
- https://developers.openai.com/api/docs/models/gpt-5.5-pro
- https://developers.openai.com/docs/guides/background
- https://openai.com/index/introducing-gpt-5-5/ (2026-04-23)
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from aipea.redteam._polling import (
    DEFAULT_POLL_INTERVAL_SECONDS,
    DEFAULT_POLL_TIMEOUT_SECONDS,
    PollTimeoutError,
    poll_until_terminal,
)
from aipea.redteam._resolve import resolve_api_key
from aipea.redteam._types import RedTeamResult, Technique

logger = logging.getLogger(__name__)

DEFAULT_OPENAI_API_BASE: str = "https://api.openai.com/v1"
DEFAULT_OPENAI_RESPONSES_MODEL: str = "gpt-5.5-pro"
DEFAULT_OPENAI_TIMEOUT: float = 60.0  # per individual HTTP call; not the poll deadline

# Approximate gpt-5.5-pro pricing (USD per million tokens). Update when
# OpenAI publishes official pricing if not already in their docs.
_OPENAI_INPUT_COST_PER_MTOK: float = 15.0
_OPENAI_OUTPUT_COST_PER_MTOK: float = 60.0


class OpenAIResponsesProvider:
    """OpenAI Responses-API provider using background mode + polling."""

    name: str = "openai"
    default_model: str = DEFAULT_OPENAI_RESPONSES_MODEL

    def __init__(
        self,
        *,
        api_key: str | None = None,
        api_base: str | None = None,
        timeout: float | None = None,
        poll_timeout_seconds: int = DEFAULT_POLL_TIMEOUT_SECONDS,
        poll_interval_seconds: int = DEFAULT_POLL_INTERVAL_SECONDS,
        reasoning_effort: str = "high",
        model: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = resolve_api_key("OPENAI_API_KEY", api_key)
        self.api_base = (api_base or DEFAULT_OPENAI_API_BASE).rstrip("/")
        self.timeout = timeout if timeout is not None else DEFAULT_OPENAI_TIMEOUT
        self.poll_timeout_seconds = poll_timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self.reasoning_effort = reasoning_effort
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
            "input": prompt,
            "background": True,
            "store": True,
            "reasoning": {"effort": self.reasoning_effort},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        started = time.perf_counter()
        text = ""
        usage_in, usage_out = 0, 0
        error: str | None = None
        response_id: str | None = None
        try:
            create_resp = await client.post(
                f"{self.api_base}/responses",
                json=body,
                headers=headers,
                timeout=self.timeout,
            )
            if create_resp.status_code >= 400:
                logger.warning(
                    "OpenAI Responses HTTP %s: %s",
                    create_resp.status_code,
                    create_resp.text[:500],
                )
                error = "http_error"
            else:
                created = create_resp.json()
                response_id = created.get("id")
                if not response_id:
                    error = "missing_field"
                else:
                    # Reuse ONE sync httpx.Client across all poll iterations
                    # (was: per-iteration TLS+TCP handshake — up to 300/run
                    # at the default 5s interval x 1500s deadline).
                    sync_client = httpx.Client(timeout=self.timeout)

                    def _retrieve(rid: str) -> dict[str, Any]:
                        r = sync_client.get(
                            f"{self.api_base}/responses/{rid}",
                            headers=headers,
                        )
                        # Classify retrieve errors:
                        # - 4xx (except 429): permanent — synthesize a
                        #   terminal "failed" status so poll_until_terminal
                        #   exits the retry loop instead of spinning to the
                        #   25-min deadline on a 401/404
                        # - 5xx / 429 / network: transient — re-raise so the
                        #   polling helper catches and retries with backoff
                        if 400 <= r.status_code < 500 and r.status_code != 429:
                            logger.warning(
                                "OpenAI retrieve permanent error %s: %s",
                                r.status_code,
                                r.text[:500],
                            )
                            return {"status": "failed", "_retrieve_http_status": r.status_code}
                        r.raise_for_status()
                        return r.json()  # type: ignore[no-any-return]

                    def _cancel(rid: str) -> None:
                        sync_client.post(
                            f"{self.api_base}/responses/{rid}/cancel",
                            headers=headers,
                        )

                    try:
                        # poll_until_terminal is sync (uses time.sleep);
                        # off-load to a worker thread so we don't block
                        # the asyncio event loop for up to 25 min.
                        final = await asyncio.to_thread(
                            poll_until_terminal,
                            response_id,
                            retrieve=_retrieve,
                            cancel=_cancel,
                            poll_timeout_seconds=self.poll_timeout_seconds,
                            poll_interval_seconds=self.poll_interval_seconds,
                        )
                    except PollTimeoutError:
                        error = "timeout"
                        final = None
                    finally:
                        sync_client.close()
                    if final is not None:
                        status = final.get("status")
                        if status == "completed":
                            text = _extract_output_text(final)
                            usage = final.get("usage", {}) or {}
                            usage_in = int(usage.get("input_tokens", 0) or 0)
                            usage_out = int(usage.get("output_tokens", 0) or 0)
                        elif status in ("failed", "cancelled", "incomplete"):
                            error = "http_error"  # treat non-success terminal as failure
        except httpx.HTTPError as exc:
            logger.warning("OpenAI Responses network error: %s", exc)
            error = "network"

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        if error is None and text == "":
            error = "empty_response"
        cost_usd = (
            usage_in * _OPENAI_INPUT_COST_PER_MTOK / 1_000_000
            + usage_out * _OPENAI_OUTPUT_COST_PER_MTOK / 1_000_000
        )
        return RedTeamResult(
            payload=text,
            technique=technique,
            intent=f"technique={technique.value}; model={model}",
            detected=False,
            flags=(),
            generated_by=f"openai/{model}",
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
            generated_by=f"openai/{model}",
            generated_at=RedTeamResult.now_iso(),
            novelty_score=0.0,
            refinement_round=0,
            cost_usd=0.0,
            latency_ms=0,
            error=error,
        )


def _extract_output_text(response: dict[str, Any]) -> str:
    """Pull the assistant text out of a Responses-API completed response.

    Mirrors ``.github/scripts/gpt_review.py:_extract_text`` shape but
    works on raw dicts (no SDK objects). The Responses API may put
    text in ``output_text`` (top-level convenience) or in
    ``output[].content[].text`` (canonical structure).
    """
    if isinstance(response.get("output_text"), str):
        return response["output_text"]  # type: ignore[no-any-return]
    parts: list[str] = []
    for item in response.get("output", []) or []:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")
        if item_type in (None, "message"):
            for c in item.get("content", []) or []:
                if isinstance(c, dict) and isinstance(c.get("text"), str):
                    parts.append(c["text"])
        elif item_type == "output_text":
            text = item.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "\n".join(p for p in parts if p).strip()
