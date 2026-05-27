"""Regression tests for Phase 2 bug-hunt cycle-2 redteam findings.

Each test pins a fixed behavior so the bug cannot silently recur.

Findings indexed below correspond to the Phase 2 cycle-2 commit body
(see `.quality-gate/cycle2-findings.md` for the full ledger):

- F1, F2 (HIGH): openai_responses create-response unguarded JSON parse.
- F5 (LOW):     _polling deadline strict `>` allowed infinite loop with
                a frozen `monotonic` + `poll_timeout_seconds=0`.
- F6 (LOW):     _polling `_extract_status` stringified non-str/non-enum
                values (e.g. `0` → `"0"`) that never match terminal.
- F7 (LOW):     reporter summary reported `len(novel)` (capped at 10)
                instead of the true undetected count.
"""

from __future__ import annotations

import asyncio
import enum
from pathlib import Path
from typing import Any

import httpx
import pytest

from aipea.redteam import (
    OpenAIResponsesProvider,
    RedTeamReporter,
    RedTeamResult,
    Technique,
)
from aipea.redteam._polling import (
    PollTimeoutError,
    _extract_status,
    poll_until_terminal,
)

# =============================================================================
# Cluster 1: openai_responses.py — create-response parse guards
# =============================================================================


def _async_post_stub(response_factory: Any) -> Any:
    """Build an httpx.AsyncClient stub whose `.post()` returns whatever
    `response_factory(url)` produces. Used for the create-response tests.
    """

    class _Stub:
        async def __aenter__(self) -> _Stub:
            return self

        async def __aexit__(self, *_a: Any) -> None:
            return None

        async def post(self, url: str, *_a: Any, **_k: Any) -> httpx.Response:
            return response_factory(url)

    return _Stub


class TestOpenAIResponsesCreateNonJsonGuard:
    """FINDING #1 (HIGH C3): `create_resp.json()` raised JSONDecodeError
    (a ValueError subclass, NOT httpx.HTTPError) on a 200 + non-JSON
    body → escaped `_one_generation` → crashed the whole batch.
    """

    def test_non_json_create_body_returns_non_json_error_no_raise(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def make_response(url: str) -> httpx.Response:
            return httpx.Response(
                200,
                text="<html><body>nginx error</body></html>",
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr(
            "aipea.redteam.providers.openai_responses.httpx.AsyncClient",
            lambda **_k: _async_post_stub(make_response)(),
        )

        provider = OpenAIResponsesProvider(
            api_key="sk-test", poll_timeout_seconds=5, poll_interval_seconds=0
        )
        # Must NOT raise. Must produce one error-tagged result.
        results = asyncio.run(provider.generate(technique=Technique.PARAPHRASE, prompt="x", num=1))
        assert len(results) == 1
        assert results[0].error == "non_json"
        assert results[0].payload == ""


class TestOpenAIResponsesCreateNonDictGuard:
    """FINDING #2 (HIGH C3): `created.get("id")` assumed dict shape; a
    top-level list/null/number raised AttributeError → escaped → crashed
    the batch.
    """

    def test_top_level_list_create_body_returns_non_json_error_no_raise(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def make_response(url: str) -> httpx.Response:
            return httpx.Response(200, json=[1, 2, 3], request=httpx.Request("POST", url))

        monkeypatch.setattr(
            "aipea.redteam.providers.openai_responses.httpx.AsyncClient",
            lambda **_k: _async_post_stub(make_response)(),
        )

        provider = OpenAIResponsesProvider(
            api_key="sk-test", poll_timeout_seconds=5, poll_interval_seconds=0
        )
        results = asyncio.run(provider.generate(technique=Technique.PARAPHRASE, prompt="x", num=1))
        assert len(results) == 1
        assert results[0].error == "non_json"

    def test_null_create_body_returns_non_json_error_no_raise(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def make_response(url: str) -> httpx.Response:
            return httpx.Response(200, json=None, request=httpx.Request("POST", url))

        monkeypatch.setattr(
            "aipea.redteam.providers.openai_responses.httpx.AsyncClient",
            lambda **_k: _async_post_stub(make_response)(),
        )

        provider = OpenAIResponsesProvider(
            api_key="sk-test", poll_timeout_seconds=5, poll_interval_seconds=0
        )
        results = asyncio.run(provider.generate(technique=Technique.PARAPHRASE, prompt="x", num=1))
        assert len(results) == 1
        assert results[0].error == "non_json"

    def test_dict_without_id_still_returns_missing_field(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Regression: the dict-shape happy-path with no "id" key MUST keep
        # tagging "missing_field" (not get overwritten to "non_json").
        def make_response(url: str) -> httpx.Response:
            return httpx.Response(
                200,
                json={"foo": "bar"},
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr(
            "aipea.redteam.providers.openai_responses.httpx.AsyncClient",
            lambda **_k: _async_post_stub(make_response)(),
        )

        provider = OpenAIResponsesProvider(
            api_key="sk-test", poll_timeout_seconds=5, poll_interval_seconds=0
        )
        results = asyncio.run(provider.generate(technique=Technique.PARAPHRASE, prompt="x", num=1))
        assert len(results) == 1
        assert results[0].error == "missing_field"


# =============================================================================
# Cluster 2: _polling.py — deadline >= and strict-string status
# =============================================================================


class TestPollingDeadlineInclusive:
    """FINDING #5 (LOW C3): `monotonic() > deadline` (strict) allowed an
    infinite loop when `poll_timeout_seconds=0` AND `monotonic` was
    injected as a frozen clock (test seam). Now `>=` so the first
    iteration times out.
    """

    def test_zero_timeout_frozen_clock_raises_immediately(self) -> None:
        # Frozen clock + 0s timeout + non-terminal retrieve: the loop
        # MUST raise PollTimeoutError on the first iteration (was: spin
        # forever). Guard the test with a wall-clock cap via threading
        # so a regression fails fast instead of hanging CI.
        import threading

        result: dict[str, Any] = {}

        def driver() -> None:
            try:
                poll_until_terminal(
                    "rid",
                    retrieve=lambda _rid: {"status": "queued"},
                    poll_timeout_seconds=0,
                    poll_interval_seconds=0,
                    sleep=lambda _s: None,
                    monotonic=lambda: 0.0,  # frozen
                )
            except PollTimeoutError as exc:
                result["raised"] = exc

        t = threading.Thread(target=driver, daemon=True)
        t.start()
        t.join(timeout=5.0)
        assert not t.is_alive(), "regression — poll_until_terminal busy-looped"
        assert "raised" in result, "PollTimeoutError was not raised"
        assert result["raised"].last_status == "queued"


class TestExtractStatusStrictTypes:
    """FINDING #6 (LOW C2): `_extract_status` stringified non-str / non-
    enum values (e.g. `0` → `"0"`, `True` → `"True"`), which never match
    `TERMINAL_STATES` and produce misleading operator-log lines. Now
    coerced to None (the loop maps to "unknown").
    """

    def test_numeric_status_dict_returns_none(self) -> None:
        assert _extract_status({"status": 0}) is None
        assert _extract_status({"status": 42}) is None

    def test_bool_status_dict_returns_none(self) -> None:
        # bool is a subclass of int in Python — the strict-string coercion
        # must reject it here too.
        assert _extract_status({"status": True}) is None
        assert _extract_status({"status": False}) is None

    def test_string_status_dict_still_returned_as_is(self) -> None:
        assert _extract_status({"status": "queued"}) == "queued"
        assert _extract_status({"status": "completed"}) == "completed"

    def test_none_status_dict_returns_none(self) -> None:
        # Regression — None must still return None (not "None" via str()).
        assert _extract_status({"status": None}) is None

    def test_enum_status_returns_value(self) -> None:
        # Regression — enum.Enum members still produce their `.value`.
        class _S(enum.Enum):
            COMPLETED = "completed"

        class _Obj:
            status = _S.COMPLETED

        assert _extract_status(_Obj()) == "completed"


# =============================================================================
# Cluster 3: reporter.py — true undetected count in the summary
# =============================================================================


class TestReporterTrueUndetectedCount:
    """FINDING #7 (LOW C3): the summary reported `len(novel)` (capped at
    10), silently understating the undetected/novel bypass volume in a
    committed audit artifact.
    """

    def test_summary_reports_true_undetected_count_when_above_top_10(self, tmp_path: Path) -> None:
        # Build 15 undetected results — the report's top-10 display slice
        # should still be 10 rows, but the summary line MUST show 15.
        rep = RedTeamReporter(json_dir=tmp_path / "j", md_dir=tmp_path / "m")
        results = [
            RedTeamResult(
                payload=f"payload_{i}",
                technique=Technique.PARAPHRASE,
                intent="t",
                detected=False,
                flags=(),
                generated_by="x/y",
                generated_at=RedTeamResult.now_iso(),
                novelty_score=0.5 + i * 0.01,
            )
            for i in range(15)
        ]
        _, md_path = rep.write(results, provider="x", run_date="2026-05-25")
        text = md_path.read_text()
        # Must contain the TRUE count of 15
        assert "Undetected payloads: 15" in text
        # And it must still cap the top-N display at 10
        novel_lines = [
            line
            for line in text.splitlines()
            if line.startswith(tuple(f"{n}. " for n in range(1, 16)))
        ]
        assert len(novel_lines) == 10

    def test_summary_reports_zero_when_all_detected(self, tmp_path: Path) -> None:
        # Regression: when every payload is detected, undetected count is 0
        # and the "_None — every undetected payload had a near-corpus match._"
        # placeholder is still produced.
        rep = RedTeamReporter(json_dir=tmp_path / "j", md_dir=tmp_path / "m")
        results = [
            RedTeamResult(
                payload="caught",
                technique=Technique.PARAPHRASE,
                intent="t",
                detected=True,
                flags=("injection_attempt",),
                generated_by="x/y",
                generated_at=RedTeamResult.now_iso(),
            )
        ]
        _, md_path = rep.write(results, provider="x", run_date="2026-05-25")
        text = md_path.read_text()
        assert "Undetected payloads: 0" in text


# =============================================================================
# CYCLE-3 A2 follow-up — conditional top-N parenthetical (cosmetic, LOW)
# =============================================================================


class TestCycle3ReporterConditionalParenthetical:
    """CYCLE-3 A2 (LOW C2): the cycle-2 F7 fix unconditionally appended
    `(top-N by novelty score shown below)` to the undetected-count
    summary line. When `len(undetected) <= len(novel)` the parenthetical
    is redundant — the full undetected set IS the shown list. The
    cosmetic fix conditions the suffix on `len(undetected) > len(novel)`.
    """

    def test_no_parenthetical_when_undetected_below_top_n(self, tmp_path: Path) -> None:
        # 3 undetected, top-10 slice → all 3 shown → no parenthetical
        rep = RedTeamReporter(json_dir=tmp_path / "j", md_dir=tmp_path / "m")
        results = [
            RedTeamResult(
                payload=f"payload_{i}",
                technique=Technique.PARAPHRASE,
                intent="t",
                detected=False,
                flags=(),
                generated_by="x/y",
                generated_at=RedTeamResult.now_iso(),
                novelty_score=0.5 + i * 0.01,
            )
            for i in range(3)
        ]
        _, md_path = rep.write(results, provider="x", run_date="2026-05-26")
        text = md_path.read_text()
        assert "Undetected payloads: 3" in text
        # The redundant parenthetical must NOT appear when undetected ≤ top-N
        assert "top-3" not in text
        assert "top-0" not in text

    def test_parenthetical_present_when_undetected_above_top_n(self, tmp_path: Path) -> None:
        # 15 undetected → top-10 sliced → parenthetical needed
        rep = RedTeamReporter(json_dir=tmp_path / "j", md_dir=tmp_path / "m")
        results = [
            RedTeamResult(
                payload=f"payload_{i}",
                technique=Technique.PARAPHRASE,
                intent="t",
                detected=False,
                flags=(),
                generated_by="x/y",
                generated_at=RedTeamResult.now_iso(),
                novelty_score=0.5 + i * 0.01,
            )
            for i in range(15)
        ]
        _, md_path = rep.write(results, provider="x", run_date="2026-05-26")
        text = md_path.read_text()
        assert "Undetected payloads: 15" in text
        assert "(top-10 by novelty score shown below)" in text

    def test_no_parenthetical_when_all_detected(self, tmp_path: Path) -> None:
        # 0 undetected → no parenthetical (placeholder line appears below)
        rep = RedTeamReporter(json_dir=tmp_path / "j", md_dir=tmp_path / "m")
        results = [
            RedTeamResult(
                payload="caught",
                technique=Technique.PARAPHRASE,
                intent="t",
                detected=True,
                flags=("injection_attempt",),
                generated_by="x/y",
                generated_at=RedTeamResult.now_iso(),
            )
        ]
        _, md_path = rep.write(results, provider="x", run_date="2026-05-26")
        text = md_path.read_text()
        assert "Undetected payloads: 0" in text
        assert "top-0" not in text  # no nonsense parenthetical
        assert "_None — every undetected payload had a near-corpus match._" in text
