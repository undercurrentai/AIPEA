"""AIPEA Adversarial Evaluation Suite (ADR-008 + Phase 4.c expansion 2026-05-02).

Tests SecurityScanner against vendored adversarial corpora with a
two-tier failure model:

- **Bright-line** (must-pass): payloads AIPEA already claims to detect.
  A single failure blocks CI.
- **Extended** (baseline-budget): real adversarial techniques that regex-only
  defense may not yet handle.  Fails only on regression from a committed
  baseline snapshot.

Corpora (vendored — see ``tests/fixtures/adversarial/SOURCES.md``):

- ``owasp_llm_top10.json`` — OWASP LLM Top 10 2026 taxonomy (CC-BY-SA, ADR-008).
  Contains both ``bright_line`` and ``extended`` tiers.
- ``promptinject.json`` — agencyenterprise/PromptInject (MIT). Extended only.
- ``jbb_behaviors.json`` — JailbreakBench JBB-Behaviors (MIT). Extended only,
  split into ``jbb_harmful`` (low-hit-rate is correct) and ``jbb_benign_fpr``
  (FPR control: anything flagged is a false positive).
- ``garak_promptinject.json`` — NVIDIA/garak probe extracts (Apache-2.0).
  Extended only.

Baseline: ``tests/fixtures/adversarial/baseline.json``. Schema is additive:
the legacy ``bright_line`` + ``extended`` keys are preserved for back-compat;
new ``by_source`` map breaks down the extended-tier numbers per corpus so a
regression in (say) PromptInject can no longer be masked by a flat overall
rate.

Run: ``make adversarial`` or ``pytest tests/test_adversarial.py -v``
Re-baseline (after intentional corpus or scanner change):
``make adversarial-update-baseline``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

from aipea.security import SecurityContext, SecurityScanner

_FIXTURES = Path(__file__).parent / "fixtures" / "adversarial"
_BASELINE_PATH = _FIXTURES / "baseline.json"

# Corpus files in priority order. Order is stable for reproducibility of
# the legacy ``extended`` flat counts (which are computed across the union
# of all extended-tier entries).
_CORPUS_FILES: tuple[Path, ...] = (
    _FIXTURES / "owasp_llm_top10.json",
    _FIXTURES / "promptinject.json",
    _FIXTURES / "jbb_behaviors.json",
    _FIXTURES / "garak_promptinject.json",
)

# Source identifier for the FPR-inverted assertion path. Entries with this
# ``source`` value are scored as "PASS if NOT flagged"; any flag is a
# false positive. baseline.json reports an ``fpr`` field for this source
# instead of ``pass_rate``.
_FPR_SOURCE = "jbb_benign_fpr"


def _load_corpus(tier: str | None = None) -> list[dict[str, Any]]:
    """Load and concatenate all vendored corpora, optionally filtered by tier."""
    data: list[dict[str, Any]] = []
    for path in _CORPUS_FILES:
        if not path.exists():
            continue  # graceful degradation if a corpus file is removed
        data.extend(json.loads(path.read_text(encoding="utf-8")))
    if tier is not None:
        data = [e for e in data if e["tier"] == tier]
    return data


def _load_baseline() -> dict[str, Any]:
    return json.loads(_BASELINE_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _entry_passes(scanner: SecurityScanner, entry: dict[str, Any]) -> bool:
    """Return True if AIPEA's behavior on ``entry`` matches the entry's expectation.

    Three modes:
    - ``source == "jbb_benign_fpr"`` → PASS iff scanner does NOT flag (FPR control)
    - ``expected_flag is None`` → PASS iff scanner does NOT flag (false-positive guard)
    - otherwise → PASS iff at least one flag has the expected prefix
    """
    ctx = SecurityContext()
    result = scanner.scan(entry["payload"], ctx)
    expected = entry["expected_flag"]
    if entry.get("source") == _FPR_SOURCE or expected is None:
        return not result.has_flags()
    return any(f.startswith(expected) for f in result.flags)


def _compute_results(
    scanner: SecurityScanner, corpus: list[dict[str, Any]]
) -> tuple[int, int, list[dict[str, Any]]]:
    """Aggregate pass count + failure list across an arbitrary corpus subset."""
    passed = 0
    failures: list[dict[str, Any]] = []
    for entry in corpus:
        if _entry_passes(scanner, entry):
            passed += 1
        else:
            ctx = SecurityContext()
            result = scanner.scan(entry["payload"], ctx)
            failures.append(
                {
                    "id": entry["id"],
                    "source": entry.get("source", "unknown"),
                    "expected": entry["expected_flag"],
                    "got": list(result.flags),
                }
            )
    return passed, len(corpus), failures


def _compute_results_by_source(
    scanner: SecurityScanner, corpus: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """Group results by the ``source`` field on each corpus entry.

    For ``jbb_benign_fpr`` source, the result includes ``fpr`` (false-positive
    rate: fraction of benign prompts that were flagged) instead of
    ``pass_rate``. For all other sources, ``pass_rate`` is the fraction of
    payloads that produced the expected flag (or no flag, for entries with
    ``expected_flag=None``).
    """
    by_source: dict[str, list[dict[str, Any]]] = {}
    for entry in corpus:
        by_source.setdefault(entry.get("source", "unknown"), []).append(entry)

    out: dict[str, dict[str, Any]] = {}
    for source, entries in sorted(by_source.items()):
        passed, total, failures = _compute_results(scanner, entries)
        rec: dict[str, Any] = {
            "total": total,
            "passed": passed,
        }
        if source == _FPR_SOURCE:
            # Lower is better: count "passes" here means "not flagged".
            # FPR = 1 - pass_rate = (total - passed) / total.
            rec["fpr"] = round((total - passed) / total, 4) if total else 0.0
        else:
            rec["pass_rate"] = round(passed / total, 4) if total else 0.0
        rec["sample_failures"] = failures[:5]
        out[source] = rec
    return out


def _generate_baseline() -> None:
    scanner = SecurityScanner()
    bl_corpus = _load_corpus(tier="bright_line")
    ext_corpus = _load_corpus(tier="extended")

    bl_passed, bl_total, _ = _compute_results(scanner, bl_corpus)
    ext_passed, ext_total, _ = _compute_results(scanner, ext_corpus)
    by_source = _compute_results_by_source(scanner, ext_corpus)

    # Strip ``sample_failures`` from the by_source map for the committed
    # baseline (failures are noisy; we recompute them at test time anyway).
    by_source_clean = {
        source: {k: v for k, v in rec.items() if k != "sample_failures"}
        for source, rec in by_source.items()
    }

    baseline = {
        "snapshot_date": __import__("datetime").date.today().isoformat(),
        "bright_line": {
            "total": bl_total,
            "passed": bl_passed,
            "pass_rate": round(bl_passed / bl_total, 4) if bl_total else 0.0,
        },
        "extended": {
            "total": ext_total,
            "passed": ext_passed,
            "pass_rate": round(ext_passed / ext_total, 4) if ext_total else 0.0,
        },
        "by_source": by_source_clean,
    }
    _BASELINE_PATH.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")
    print(f"Baseline written to {_BASELINE_PATH}")
    print(f"  bright_line: {bl_passed}/{bl_total} ({baseline['bright_line']['pass_rate']:.1%})")
    print(f"  extended:    {ext_passed}/{ext_total} ({baseline['extended']['pass_rate']:.1%})")
    for source, rec in by_source_clean.items():
        if "fpr" in rec:
            print(
                f"    [{source}] FPR: {rec['passed']}/{rec['total']} not-flagged ({rec['fpr']:.2%} FPR)"
            )
        else:
            print(f"    [{source}] {rec['passed']}/{rec['total']} ({rec['pass_rate']:.1%})")


_BRIGHT_LINE_CORPUS = _load_corpus(tier="bright_line")
_BRIGHT_LINE_IDS = [e["id"] for e in _BRIGHT_LINE_CORPUS]


@pytest.mark.adversarial
class TestBrightLine:
    """Payloads AIPEA must detect (or must NOT flag for false-positive controls).

    A single failure blocks CI.
    """

    @pytest.fixture()
    def scanner(self) -> SecurityScanner:
        return SecurityScanner()

    @pytest.mark.parametrize(
        "entry",
        _BRIGHT_LINE_CORPUS,
        ids=_BRIGHT_LINE_IDS,
    )
    def test_payload(self, scanner: SecurityScanner, entry: dict[str, Any]) -> None:
        ctx = SecurityContext()
        result = scanner.scan(entry["payload"], ctx)
        expected = entry["expected_flag"]

        if expected is None:
            assert not result.has_flags(), (
                f"{entry['id']}: false positive on benign input — "
                f"flags={result.flags}, payload={entry['payload']!r}"
            )
        else:
            matching = [f for f in result.flags if f.startswith(expected)]
            assert matching, (
                f"{entry['id']}: expected flag prefix {expected!r}, "
                f"got {result.flags}, payload={entry['payload']!r}"
            )


@pytest.mark.adversarial
class TestExtendedBaseline:
    """Wider corpus (all sources, all extended-tier entries) — fails only on
    regression from baseline snapshot.

    This is the **flat** view across the union of all extended corpora.
    The per-source view is in :class:`TestExtendedBaselinePerSource` below
    and is what catches a regression in (e.g.) PromptInject that would
    otherwise be averaged away across the larger combined corpus.
    """

    def test_pass_rate_no_regression(self) -> None:
        scanner = SecurityScanner()
        ext_corpus = _load_corpus(tier="extended")
        baseline = _load_baseline()

        passed, total, failures = _compute_results(scanner, ext_corpus)
        ext = baseline["extended"]

        # Compare on raw counts when totals match — this isolates the
        # regression check from corpus-size churn. When the corpus has
        # grown (or shrunk), fall back to a precision-aligned rate
        # comparison so adding extended-tier payloads that the scanner
        # doesn't yet catch doesn't false-fail. The baseline.json
        # `pass_rate` is rounded to 4 decimals; mirror that on the
        # live side so the comparison is symmetric.
        if total == ext["total"]:
            assert passed >= ext["passed"], (
                f"Extended corpus regression: {passed}/{total} < baseline "
                f"{ext['passed']}/{ext['total']}. First 5 new failures: {failures[:5]}"
            )
        else:
            pass_rate_rounded = round(passed / total, 4) if total else 0.0
            baseline_rate = ext["pass_rate"]
            assert pass_rate_rounded >= baseline_rate, (
                f"Extended corpus rate regression: {pass_rate_rounded:.4f} < "
                f"baseline {baseline_rate:.4f} ({passed}/{total} vs "
                f"{ext['passed']}/{ext['total']}; corpus size changed — "
                f"re-baseline if growth was intentional). "
                f"First 5 new failures: {failures[:5]}"
            )


@pytest.mark.adversarial
class TestExtendedBaselinePerSource:
    """Per-source no-regression view (Phase 4.c expansion 2026-05-02).

    For each source listed in ``baseline.json["by_source"]``, assert that
    the live AIPEA scanner does not regress against the committed snapshot
    for that source specifically. This is what catches a per-corpus
    regression that the flat :class:`TestExtendedBaseline` cannot — e.g., a
    drop in PromptInject hit-rate from 70% to 50% would be invisible at the
    flat-extended-rate level (because PromptInject is one of several
    corpora) but is loud here.

    The ``jbb_benign_fpr`` source is special-cased: it asserts that the
    **false-positive rate** does not increase (lower is better; a benign
    prompt that newly trips a flag is a regression).
    """

    @staticmethod
    def _sources() -> list[str]:
        baseline = _load_baseline()
        by_source = baseline.get("by_source", {})
        return sorted(by_source.keys())

    @pytest.fixture()
    def scanner(self) -> SecurityScanner:
        return SecurityScanner()

    @pytest.fixture()
    def by_source_live(self, scanner: SecurityScanner) -> dict[str, dict[str, Any]]:
        ext_corpus = _load_corpus(tier="extended")
        return _compute_results_by_source(scanner, ext_corpus)

    @pytest.mark.parametrize("source", _load_baseline().get("by_source", {}).keys())
    def test_no_regression(
        self,
        source: str,
        by_source_live: dict[str, dict[str, Any]],
    ) -> None:
        baseline = _load_baseline()
        baseline_rec = baseline["by_source"][source]
        live = by_source_live.get(source)

        if live is None:
            # Corpus file missing or source name removed; treat as informational.
            pytest.skip(f"source '{source}' present in baseline but not in live corpus")

        if source == _FPR_SOURCE:
            # FPR: lower is better. live.fpr <= baseline.fpr (with rounding tolerance).
            live_fpr = live["fpr"]
            baseline_fpr = baseline_rec["fpr"]
            assert live_fpr <= baseline_fpr + 1e-4, (
                f"[{source}] FPR regression: {live_fpr:.4f} > baseline {baseline_fpr:.4f}. "
                f"First 5 new false-positives: {live.get('sample_failures', [])[:5]}"
            )
            return

        # Standard: pass_rate >= baseline.pass_rate.
        if live["total"] == baseline_rec["total"]:
            assert live["passed"] >= baseline_rec["passed"], (
                f"[{source}] regression: {live['passed']}/{live['total']} < "
                f"baseline {baseline_rec['passed']}/{baseline_rec['total']}. "
                f"First 5 new failures: {live.get('sample_failures', [])[:5]}"
            )
        else:
            live_rate = round(live["passed"] / live["total"], 4) if live["total"] else 0.0
            baseline_rate = baseline_rec["pass_rate"]
            assert live_rate >= baseline_rate, (
                f"[{source}] rate regression: {live_rate:.4f} < baseline {baseline_rate:.4f} "
                f"({live['passed']}/{live['total']} vs "
                f"{baseline_rec['passed']}/{baseline_rec['total']}; corpus size changed — "
                f"re-baseline if growth was intentional). "
                f"First 5 new failures: {live.get('sample_failures', [])[:5]}"
            )


if __name__ == "__main__":
    if "--update-baseline" in sys.argv:
        _generate_baseline()
    else:
        print("Usage: python -m tests.test_adversarial --update-baseline")
        sys.exit(1)
