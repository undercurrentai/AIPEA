#!/usr/bin/env python3
"""AIPEA Wave C1 — GPT second-reviewer gate (Responses API, background mode).

Invokes gpt-5.4-pro via the OpenAI Responses API against a PR diff and writes
a structured Markdown review to an output file. Designed for use as a
GitHub Actions job step, but runnable standalone for local dry-runs.

Rationale for the background + polling pattern (not plain synchronous call):

    gpt-5.4-pro is available on the Responses API only and, per the model
    card at platform.openai.com/docs/models/gpt-5.4-pro, "may take several
    minutes to finish. To avoid timeouts, try using background mode."

    A synchronous `client.responses.create(...)` call without
    `background=True` will time out on real security diffs. Background mode
    enqueues the response server-side and lets us poll `responses.retrieve`
    until the status is terminal, with a hard cap so the workflow timeout
    always wins.

Contract:

    - Reads a unified diff from the path passed via --diff.
    - Writes a Markdown review to the path passed via --output.
    - Exits 0 on success, non-zero on any failure (workflow timeout, API
      error, empty response). The caller's job-level failure handler
      still writes a fallback PR comment so the gate always posts
      *something*, but the job itself stays red if the review failed.

Environment:

    OPENAI_API_KEY                         OpenAI API key with gpt-5.4-pro access
    PR_NUMBER, PR_TITLE, PR_BASE,          PR metadata — injected into the
    PR_HEAD_SHA, PR_REPO                   system prompt so the model knows
                                           what it's reviewing.
    AIPEA_REVIEW_MODEL                     Default: gpt-5.4-pro
    AIPEA_REVIEW_EFFORT                    Default: high (one of medium/high/xhigh)
    AIPEA_REVIEW_POLL_TIMEOUT_SECONDS      Default: 1500 (25 minutes)
    AIPEA_REVIEW_POLL_INTERVAL_SECONDS     Default: 5
"""

from __future__ import annotations

import argparse
import contextlib
import os
import sys
from pathlib import Path

try:
    from openai import APIError, OpenAI
except ImportError as exc:  # pragma: no cover - CI installs openai before running
    sys.stderr.write(
        f"openai SDK not installed: {exc}\n"
        "Install with: pip install 'openai>=2.11'\n"
    )
    sys.exit(2)

# Shared polling helper, exported by the aipea package since v1.7.0
# (PR #64 + #65, ADR-009 / Wave-22). The library + this CI script now
# share one canonical poll-until-terminal implementation.
from aipea.redteam._polling import PollTimeoutError, poll_until_terminal

SYSTEM_PROMPT = """\
You are the gpt-5.4-pro half of AIPEA's automated dual-AI second-reviewer
gate. You are reviewing a pull request that touches at least one of AIPEA's
security-critical paths:

    - src/aipea/security.py        (PII/PHI/injection scanning; compliance modes)
    - src/aipea/__init__.py        (public API surface / __all__)
    - src/aipea/errors.py          (custom exception hierarchy introduced in v1.4)
    - pyproject.toml               (dependencies, project metadata)
    - .github/workflows/**         (CI, release, and this very gate)
    - .github/CODEOWNERS           (accountable-reviewer mapping)

Your counterpart on the same PR is Codex CLI running the same diff in a
separate job. The two reviews are posted as independent PR comments and BOTH
must pass branch protection before the PR can merge. Your accountable human
reviewer is @joshuakirby, who reads your review alongside their own. You
augment human judgment — you do not replace it.

YOUR JOB
========

Catch bugs, security regressions, compliance-behavior changes, and
public-API mistakes that a busy solo maintainer might miss. Be direct,
specific, and concrete. Cite file:line evidence from the diff. Propose fixes
rather than raising vague concerns. If the diff is trivial (typo, comment
fix, dependency bump with no behavioral impact), say so explicitly in the
Verdict section rather than padding observations.

Watch specifically for:

    * broad `except Exception:` reintroduced after Wave C3 narrowed them
    * hard-coded SecurityContext or compliance_mode that bypasses the
      caller's setting (cf. Wave 19 bug #96 — HIPAA/TACTICAL leak)
    * regex patterns that reintroduce ReDoS classes (cf. bug #107); in
      particular, quantified groups with duplicated alternatives
    * homoglyph coverage gaps in security.py's CONFUSABLE_MAP
    * public API exports that are breaking (removal, rename) without a
      deprecation cycle — additive changes are fine
    * FedRAMP enforcement re-introduced without an updated ADR-002
      (the mode is deprecated; a PR resurrecting it needs explicit
      governance sign-off)
    * CI workflow edits that remove SHA pinning on GitHub Actions uses
    * CI workflow edits that introduce secrets to non-OIDC jobs
    * pyproject.toml additions of GPL/LGPL/AGPL dependencies (incompatible
      with AIPEA's MIT license)
    * pyproject.toml additions of any new runtime dep beyond stdlib + httpx
      (AIPEA's zero-external-deps-in-core invariant)
    * test files wrapped in `pytest.warns` for a DeprecationWarning that
      no longer fires
    * scope creep: changes outside the gated paths bundled in the same PR
      that obscure the security-relevant change

Watch for things that are NOT bugs but look like them:

    * ComplianceMode.FEDRAMP is DEPRECATED in v1.3.4, not deleted. Seeing
      references to it is expected. Flag only if a PR re-expands its
      behavior or removes the DeprecationWarning.
    * pytest-asyncio uses `asyncio_mode = auto` — async tests without
      `@pytest.mark.asyncio` are intentional.
    * test_live.py::test_all_has_42_symbols asserts the public API surface
      — if the diff changes __all__, this test MUST be updated in the
      same PR. Flag if the test and __all__ are out of sync.

FORMAT
======

Respond in Markdown with these sections in order:

## Verdict

One of: `APPROVE`, `REQUEST_CHANGES`, `COMMENT`. Use `APPROVE` only if you
have high confidence the change is correct. Use `REQUEST_CHANGES` if you
found a blocking concern. Use `COMMENT` if the diff is trivial or if you
want to flag observations without blocking.

## Blocking concerns

Bulleted list. Empty or "_None._" if Verdict is APPROVE or COMMENT.
Each bullet must include: what is wrong, file:line evidence from the diff,
and a proposed fix.

## Non-blocking observations

Bulleted list. Style/craftsmanship/suggested-improvement items that don't
gate the merge.

## Specific line callouts

Short table or bulleted list referencing specific added/removed lines by
file:line. Use ` ` code spans for identifiers.

## What I did NOT review

Explicit list of things outside your scope: runtime behavior you could not
verify from the diff alone, tests you didn't run, benchmarks you didn't
measure. Keeping this section honest helps @joshuakirby know where to
focus their own review.

Be terse. No preamble, no chain-of-thought, no summary at the end. The PR
comment is rendered as-is.
"""


def _read_diff(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"gpt_review: diff file not found: {path}")
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        raise SystemExit(f"gpt_review: diff file is empty: {path}")
    return text


def _build_user_message(diff_text: str) -> str:
    pr_number = os.environ.get("PR_NUMBER", "?")
    pr_title = os.environ.get("PR_TITLE", "(no title)")
    pr_base = os.environ.get("PR_BASE", "main")
    pr_head = os.environ.get("PR_HEAD_SHA", "(unknown)")
    pr_repo = os.environ.get("PR_REPO", "(unknown)")
    return (
        f"Repository: {pr_repo}\n"
        f"PR: #{pr_number} — {pr_title}\n"
        f"Base ref: {pr_base}\n"
        f"Head SHA: {pr_head}\n"
        "\n"
        "Unified diff against base ref:\n\n"
        "```diff\n"
        f"{diff_text}\n"
        "```\n"
    )


def _extract_text(response: object) -> str:
    """Pull the final text content out of a Responses API result.

    The SDK exposes `output_text` as a convenience accessor when the
    response is a single text message. For mixed-output responses (tool
    calls, reasoning items, multi-message final answers) we fall back to
    walking `response.output` and concatenating any text items.
    """
    output_text = getattr(response, "output_text", None)
    if output_text:
        return output_text  # type: ignore[no-any-return]

    parts: list[str] = []
    output = getattr(response, "output", None) or []
    for item in output:
        item_type = getattr(item, "type", None)
        if item_type in (None, "message"):
            content = getattr(item, "content", None) or []
            for c in content:
                text = getattr(c, "text", None)
                if text:
                    parts.append(text)
        elif item_type == "output_text":
            text = getattr(item, "text", None)
            if text:
                parts.append(text)
    return "\n".join(p for p in parts if p).strip()


def _fallback_markdown(reason: str) -> str:
    return (
        "## Verdict\n\n"
        "`COMMENT` — review could not be completed.\n\n"
        "## Blocking concerns\n\n"
        "_Review execution failed before a verdict could be produced._\n\n"
        "## Non-blocking observations\n\n"
        f"- Reason: {reason}\n"
        "- The `gpt-review` job status is red; branch protection will hold the PR.\n"
        "- @joshuakirby: inspect the workflow logs to decide whether to retry or "
        "admin-override.\n\n"
        "## Specific line callouts\n\n"
        "_None._\n\n"
        "## What I did NOT review\n\n"
        "- The diff itself (the review process failed before the model was consulted).\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="AIPEA gpt-5.4-pro second-reviewer gate")
    parser.add_argument("--diff", type=Path, required=True, help="Path to unified diff file")
    parser.add_argument("--output", type=Path, required=True, help="Path to write Markdown review")
    args = parser.parse_args()

    model = os.environ.get("AIPEA_REVIEW_MODEL", "gpt-5.4-pro")
    effort = os.environ.get("AIPEA_REVIEW_EFFORT", "high")
    poll_timeout = int(os.environ.get("AIPEA_REVIEW_POLL_TIMEOUT_SECONDS", "1500"))
    poll_interval = int(os.environ.get("AIPEA_REVIEW_POLL_INTERVAL_SECONDS", "5"))

    if not os.environ.get("OPENAI_API_KEY"):
        args.output.write_text(
            _fallback_markdown("OPENAI_API_KEY is not set in the workflow environment"),
            encoding="utf-8",
        )
        sys.stderr.write("gpt_review: OPENAI_API_KEY not set\n")
        return 2

    try:
        diff_text = _read_diff(args.diff)
    except SystemExit as exc:
        args.output.write_text(
            _fallback_markdown(f"failed to read diff: {exc}"), encoding="utf-8"
        )
        raise

    client = OpenAI()
    user_message = _build_user_message(diff_text)

    sys.stderr.write(
        f"gpt_review: model={model} effort={effort} poll_timeout={poll_timeout}s\n"
    )

    try:
        initial = client.responses.create(
            model=model,
            reasoning={"effort": effort},
            background=True,
            store=True,
            instructions=SYSTEM_PROMPT,
            input=[
                {
                    "role": "user",
                    "content": user_message,
                }
            ],
        )
    except APIError as exc:
        args.output.write_text(
            _fallback_markdown(f"responses.create failed: {exc}"), encoding="utf-8"
        )
        sys.stderr.write(f"gpt_review: create failed: {exc}\n")
        return 3

    response_id = getattr(initial, "id", None)
    if not response_id:
        args.output.write_text(
            _fallback_markdown("responses.create returned no id"), encoding="utf-8"
        )
        return 4

    sys.stderr.write(f"gpt_review: response id={response_id}\n")

    def _safe_cancel(rid: str) -> None:
        # Best-effort cancel to free the server-side slot. APIError is
        # the only swallowed exception (matches pre-Wave-23 behavior).
        with contextlib.suppress(APIError):
            client.responses.cancel(rid)

    try:
        final = poll_until_terminal(
            response_id,
            retrieve=client.responses.retrieve,
            cancel=_safe_cancel,
            poll_timeout_seconds=poll_timeout,
            poll_interval_seconds=poll_interval,
        )
    except PollTimeoutError as exc:
        args.output.write_text(
            _fallback_markdown(f"polling failed: {exc}"), encoding="utf-8"
        )
        raise SystemExit(f"gpt_review: {exc}") from exc

    status = getattr(final, "status", None)
    if status != "completed":
        args.output.write_text(
            _fallback_markdown(f"response status was {status!r}, not completed"),
            encoding="utf-8",
        )
        sys.stderr.write(f"gpt_review: non-completed status: {status}\n")
        return 5

    markdown = _extract_text(final).strip()
    if not markdown:
        args.output.write_text(
            _fallback_markdown("response produced no text output"), encoding="utf-8"
        )
        sys.stderr.write("gpt_review: empty output\n")
        return 6

    args.output.write_text(markdown + "\n", encoding="utf-8")
    sys.stderr.write(
        f"gpt_review: wrote {len(markdown)} chars to {args.output}\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
