"""RedTeamReporter — Markdown audit report + JSON corpus-extension writer.

Outputs two artifacts per run (per ADR-009 §Output contract):
- ``tests/fixtures/adversarial/generated/<provider>-<YYYY-MM-DD>.json`` —
  raw payloads with detection + novelty scores, human-reviewable
  before merge into the canonical corpus.
- ``docs/security/redteam-report-<YYYY-MM-DD>.md`` — committable
  Markdown summary: provider/model, technique breakdown, catch rate,
  novel-bypass list, recommended corpus additions, dual-use disclaimer.

Skips error-rows (where ``error`` is not None) per the empty-payload
contract documented in ``RedTeamResult.error``.
"""

from __future__ import annotations

import json
import logging
import os
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from aipea.redteam._types import RedTeamResult

logger = logging.getLogger(__name__)


_DUAL_USE_DISCLAIMER = (
    "**Dual-use disclaimer**: This tool generates jailbreak payloads "
    "for testing AI security systems. Use only against systems you "
    "own or have explicit authorization to test. Mirrors the "
    "convention established by Garak (NVIDIA) and Giskard."
)


def _atomic_write_text(path: Path, content: str) -> None:
    """Write to a sibling tmp file then os.replace into place.

    Prevents partial-write corruption on CI timeout / OOM-kill / SIGINT
    mid-write. Especially important here because the redteam reports
    are committed to git (`docs/security/redteam-report-<date>.md`)
    and a corrupt file could be inadvertently included in a commit.
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def _escape_markdown_preview(payload: str, *, limit: int = 120) -> str:
    """Sanitize an LLM-generated payload for inline-code rendering in
    the report. Two failure modes prevented:

    1. Markdown injection — a payload containing backticks closes the
       wrapper early; downstream content is then rendered as headings,
       links, or HTML. Crafted payloads with ``](javascript:...)``
       could create clickable links in GitHub's rendered preview.
    2. Layout breakage — control chars and zero-width characters are
       part of the Technique.UNICODE_EVASION corpus by design; they
       must not be rendered into the report's own structure.

    Strategy: collapse newlines, neutralize backticks with zero-width
    space wraps, and strip the C0 control-character range (except tab,
    which renders harmlessly).
    """
    preview = payload[:limit].replace("\n", " ").replace("\r", " ")
    # Neutralize backticks: U+200B before & after each backtick
    # prevents the Markdown parser from treating it as a code-span
    # delimiter while still showing the user-visible character.
    preview = preview.replace("`", "​`​")
    # Strip C0 control chars except tab
    return "".join(ch for ch in preview if ch == "\t" or ord(ch) >= 0x20)


class RedTeamReporter:
    """Writes JSON corpus-extension + Markdown audit report."""

    def __init__(
        self,
        *,
        json_dir: Path | None = None,
        md_dir: Path | None = None,
    ) -> None:
        # Default output locations relative to the project root. The
        # caller can override either path for tests or non-default
        # destinations.
        self.json_dir = json_dir or (
            Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "adversarial" / "generated"
        )
        self.md_dir = md_dir or (Path(__file__).resolve().parents[3] / "docs" / "security")

    def write(
        self,
        results: list[RedTeamResult],
        *,
        provider: str,
        run_date: str | None = None,
    ) -> tuple[Path, Path]:
        """Write both artifacts and return their paths."""
        date_stamp = run_date or datetime.now(UTC).strftime("%Y-%m-%d")
        json_path = self._write_json(results, provider=provider, date_stamp=date_stamp)
        md_path = self._write_markdown(results, provider=provider, date_stamp=date_stamp)
        return json_path, md_path

    def _write_json(self, results: list[RedTeamResult], *, provider: str, date_stamp: str) -> Path:
        self.json_dir.mkdir(parents=True, exist_ok=True)
        json_path = self.json_dir / f"{provider}-{date_stamp}.json"
        # Skip provider-error rows; they are generation noise, not corpus material.
        payload_rows = [
            {
                "payload": r.payload,
                "technique": r.technique.value,
                "intent": r.intent,
                "detected": r.detected,
                "flags": list(r.flags),
                "generated_by": r.generated_by,
                "generated_at": r.generated_at,
                "novelty_score": round(r.novelty_score, 4),
                "refinement_round": r.refinement_round,
                "cost_usd": round(r.cost_usd, 6),
                "latency_ms": r.latency_ms,
            }
            for r in results
            if r.error is None and r.payload
        ]
        _atomic_write_text(json_path, json.dumps(payload_rows, indent=2) + "\n")
        return json_path

    def _write_markdown(
        self, results: list[RedTeamResult], *, provider: str, date_stamp: str
    ) -> Path:
        self.md_dir.mkdir(parents=True, exist_ok=True)
        md_path = self.md_dir / f"redteam-report-{date_stamp}.md"
        _atomic_write_text(
            md_path,
            self._render_markdown(results, provider=provider, date_stamp=date_stamp),
        )
        return md_path

    def _render_markdown(
        self, results: list[RedTeamResult], *, provider: str, date_stamp: str
    ) -> str:
        valid = [r for r in results if r.error is None and r.payload]
        errored = [r for r in results if r.error is not None]
        total = len(valid)
        detected = sum(1 for r in valid if r.detected)
        catch_rate = (detected / total * 100.0) if total else 0.0
        per_tech = Counter(r.technique.value for r in valid)
        per_tech_caught = Counter(r.technique.value for r in valid if r.detected)
        cost_total = sum(r.cost_usd for r in results)
        # Track the full undetected set separately from the top-10 display
        # slice — the summary line below must report the TRUE undetected
        # count, not the capped `len(novel)` (which silently saturates at
        # 10 in a security audit artifact committed to git).
        undetected = [r for r in valid if not r.detected]
        novel = sorted(undetected, key=lambda r: r.novelty_score, reverse=True)[:10]

        lines: list[str] = [
            f"# Red-Team Report — {date_stamp} ({provider})",
            "",
            _DUAL_USE_DISCLAIMER,
            "",
            "## Summary",
            "",
            f"- Total valid payloads: {total}",
            f"- Detected by SecurityScanner: {detected} ({catch_rate:.1f}%)",
            # Cycle-3 A2: only show the "(top-N shown below)" parenthetical
            # when undetected count exceeds the displayed top-N — otherwise
            # the parenthetical is redundant (e.g. when undetected = 5 and
            # the full 5 are listed below, or when undetected = 0 and the
            # `_None — every undetected payload had a near-corpus match._`
            # placeholder appears).
            f"- Undetected payloads: {len(undetected)}"
            + (
                f" (top-{len(novel)} by novelty score shown below)"
                if len(undetected) > len(novel)
                else ""
            ),
            f"- Provider-error rows (skipped): {len(errored)}",
            f"- Total estimated cost: ${cost_total:.4f}",
            "",
            "## Technique Breakdown",
            "",
            "| Technique | Generated | Caught | Catch rate |",
            "| --- | ---: | ---: | ---: |",
        ]
        for tech, count in per_tech.most_common():
            caught = per_tech_caught.get(tech, 0)
            rate = (caught / count * 100.0) if count else 0.0
            lines.append(f"| `{tech}` | {count} | {caught} | {rate:.1f}% |")
        lines += [
            "",
            "## Top Novel Bypasses (highest novelty score, undetected)",
            "",
        ]
        if not novel:
            lines.append("_None — every undetected payload had a near-corpus match._")
        else:
            for i, r in enumerate(novel, 1):
                preview = _escape_markdown_preview(r.payload)
                lines.append(
                    f"{i}. `{r.technique.value}` (novelty {r.novelty_score:.3f}) — `{preview}`"
                )
        lines += [
            "",
            "## Recommended Corpus Additions",
            "",
            (
                "Top novel bypasses above are candidate additions to "
                "`tests/fixtures/adversarial/owasp_llm_top10.json`. "
                "**Human review required before merge** — never auto-merge "
                "LLM-generated content into the test suite."
            ),
            "",
            "---",
            "",
            f"*Generated by AIPEA `aipea redteam` on {date_stamp} via {provider}.*",
            "",
        ]
        return "\n".join(lines)
