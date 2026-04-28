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
        json_path.write_text(json.dumps(payload_rows, indent=2) + "\n", encoding="utf-8")
        return json_path

    def _write_markdown(
        self, results: list[RedTeamResult], *, provider: str, date_stamp: str
    ) -> Path:
        self.md_dir.mkdir(parents=True, exist_ok=True)
        md_path = self.md_dir / f"redteam-report-{date_stamp}.md"
        md_path.write_text(
            self._render_markdown(results, provider=provider, date_stamp=date_stamp),
            encoding="utf-8",
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
        novel = sorted(
            (r for r in valid if not r.detected),
            key=lambda r: r.novelty_score,
            reverse=True,
        )[:10]

        lines: list[str] = [
            f"# Red-Team Report — {date_stamp} ({provider})",
            "",
            _DUAL_USE_DISCLAIMER,
            "",
            "## Summary",
            "",
            f"- Total valid payloads: {total}",
            f"- Detected by SecurityScanner: {detected} ({catch_rate:.1f}%)",
            f"- Novel bypasses (top-10 by novelty score): {len(novel)}",
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
                preview = r.payload[:120].replace("\n", " ")
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
