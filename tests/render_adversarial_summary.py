"""Render the latest adversarial baseline as a Markdown table for CI.

Reads ``tests/fixtures/adversarial/baseline.json`` and emits a per-source
table to stdout. Designed to be redirected into ``$GITHUB_STEP_SUMMARY``
by ``.github/workflows/adversarial.yml``.

Usage:
    python tests/render_adversarial_summary.py >> $GITHUB_STEP_SUMMARY
"""

from __future__ import annotations

import json
from pathlib import Path

_BASELINE_PATH = Path(__file__).parent / "fixtures" / "adversarial" / "baseline.json"


def _format_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def main() -> None:
    if not _BASELINE_PATH.exists():
        print(f"## Adversarial Baseline\n\n_baseline.json not found at {_BASELINE_PATH}_")
        return

    baseline = json.loads(_BASELINE_PATH.read_text(encoding="utf-8"))

    print("## AIPEA Adversarial Evaluation — Hit Rates")
    print()
    print(f"_Baseline snapshot: **{baseline.get('snapshot_date', 'unknown')}**_")
    print()

    bl = baseline.get("bright_line", {})
    ext = baseline.get("extended", {})

    print("### Tier totals")
    print()
    print("| Tier | Passed | Total | Rate |")
    print("|---|---:|---:|---:|")
    print(
        f"| **bright-line** (must-pass; gating in `ci.yml`) | "
        f"{bl.get('passed', 0)} | {bl.get('total', 0)} | "
        f"{_format_pct(bl.get('pass_rate', 0))} |"
    )
    print(
        f"| **extended** (baseline-snapshot; non-gating nightly) | "
        f"{ext.get('passed', 0)} | {ext.get('total', 0)} | "
        f"{_format_pct(ext.get('pass_rate', 0))} |"
    )
    print()

    by_source = baseline.get("by_source", {})
    if not by_source:
        print("_No per-source breakdown in baseline.json (legacy schema)._")
        return

    print("### Per-source breakdown")
    print()
    print("| Source | Passed | Total | Rate / FPR | Notes |")
    print("|---|---:|---:|---:|---|")

    notes_by_source = {
        "promptinject": "Canonical instruction-override family (MIT). Expected 60-80%.",
        "jbb_harmful": "JBB harmful goals (MIT). Most don't contain override syntax; low hit-rate is correct.",
        "jbb_benign_fpr": "JBB benign control (MIT). FPR; lower is better. Target <5%.",
        "garak_promptinject": "Garak probe extracts (Apache-2.0). Paraphrase-coverage breadth.",
    }

    for source in sorted(by_source.keys()):
        rec = by_source[source]
        passed = rec.get("passed", 0)
        total = rec.get("total", 0)
        if "fpr" in rec:
            rate_str = f"{_format_pct(rec['fpr'])} FPR"
        else:
            rate_str = _format_pct(rec.get("pass_rate", 0))
        note = notes_by_source.get(
            source, "OWASP LLM Top 10 2026 category." if source.startswith("OWASP") else ""
        )
        print(f"| `{source}` | {passed} | {total} | {rate_str} | {note} |")

    print()
    print(
        "_Honest losses included per [ADR-005 §C.1]"
        "(../../docs/adr/ADR-005-pr52-vc-adversarial-review-response.md). "
        "New regex patterns ship via separate PRs when this benchmark "
        "surfaces paraphrase or encoding gaps; ML-classifier replacement "
        "was declined per ADR-005 §C.1 with documented Revisit trigger._"
    )


if __name__ == "__main__":
    main()
