"""Long-running response polling helper for frontier-model providers.

Extracted from `.github/scripts/gpt_review.py:219-253` so the library and
CI workflow share one canonical polling implementation. The library
version is provider-agnostic — callers pass `retrieve` and `cancel` as
callables, so the helper stays within AIPEA's stdlib + httpx core
constraint (no OpenAI SDK as a runtime dep).

Used by:
  - `src/aipea/redteam/providers/openai_responses.py` (PR-B1, future)
  - `src/aipea/redteam/providers/openai_codex.py` (PR-B1, future)
  - `.github/scripts/gpt_review.py` (refactored to import this helper)

Terminal states mirror the OpenAI Responses API:
`completed`, `failed`, `cancelled`, `incomplete`.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


TERMINAL_STATES: frozenset[str] = frozenset({"completed", "failed", "cancelled", "incomplete"})
"""Default terminal status values for a polled response."""

DEFAULT_POLL_TIMEOUT_SECONDS: int = 1500
"""Default 25-minute polling cap. Mirrors `.github/workflows/ai-second-review.yml`
`AIPEA_REVIEW_POLL_TIMEOUT_SECONDS` env default; leaves 5-min overhead inside
a 30-min CI job timeout."""

DEFAULT_POLL_INTERVAL_SECONDS: int = 5
"""Default 5s between polls. Mirrors `gpt_review.py` cadence."""


class PollTimeoutError(Exception):
    """Raised when a polled response does not reach a terminal state in time.

    Carries the response_id and last observed status for caller-side
    structured logging.
    """

    def __init__(self, response_id: str, last_status: str, timeout_s: int) -> None:
        self.response_id = response_id
        self.last_status = last_status
        self.timeout_s = timeout_s
        super().__init__(
            f"response {response_id} did not reach a terminal state within "
            f"{timeout_s}s (last status: {last_status})"
        )


def _extract_status(response: Any) -> str | None:
    """Read `status` from either an attribute (SDK object) or a dict (raw httpx)."""
    status = getattr(response, "status", None)
    if status is not None:
        return str(status)
    if isinstance(response, dict):
        s = response.get("status")
        return str(s) if s is not None else None
    return None


def poll_until_terminal(
    response_id: str,
    *,
    retrieve: Callable[[str], Any],
    cancel: Callable[[str], None] | None = None,
    poll_timeout_seconds: int = DEFAULT_POLL_TIMEOUT_SECONDS,
    poll_interval_seconds: int = DEFAULT_POLL_INTERVAL_SECONDS,
    terminal_states: frozenset[str] = TERMINAL_STATES,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> Any:
    """Poll a long-running background response until terminal state.

    Args:
        response_id: ID of the background response (provider-specific).
        retrieve: callable that fetches the current response object given an ID.
                  Returns either an SDK object with `.status` or a dict
                  with `"status"`. Exceptions during retrieve are logged
                  and the loop retries; only timeout breaks out.
        cancel: optional callable that cancels the response. Called
                best-effort on timeout to free the server-side slot.
        poll_timeout_seconds: hard deadline; default 1500s (25 min).
        poll_interval_seconds: sleep between polls; default 5s.
        terminal_states: status strings considered terminal.
        sleep: injectable for tests (default `time.sleep`).
        monotonic: injectable for tests (default `time.monotonic`).

    Returns:
        The final response object (whatever `retrieve` returned at the
        terminal poll).

    Raises:
        PollTimeoutError: if no terminal state reached within the deadline.
    """
    deadline = monotonic() + poll_timeout_seconds
    last_status = "queued"
    while True:
        if monotonic() > deadline:
            if cancel is not None:
                try:
                    cancel(response_id)
                except Exception:
                    logger.debug("cancel() failed during timeout cleanup; ignoring")
            raise PollTimeoutError(response_id, last_status, poll_timeout_seconds)
        try:
            current = retrieve(response_id)
        except Exception as exc:
            logger.warning("retrieve failed (%s); retrying...", exc)
            sleep(poll_interval_seconds)
            continue
        status = _extract_status(current)
        if status != last_status:
            logger.info("response status: %s -> %s", last_status, status)
            last_status = status or "unknown"
        if status in terminal_states:
            return current
        sleep(poll_interval_seconds)
