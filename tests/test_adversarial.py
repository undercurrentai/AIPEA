"""AIPEA Adversarial Evaluation Suite (ADR-005).

Tests SecurityScanner against a vendored OWASP LLM Top-10 2026 corpus with
a two-tier failure model:

- **Bright-line** (must-pass): payloads AIPEA already claims to detect.
  A single failure blocks CI.
- **Extended** (baseline-budget): real adversarial techniques that regex-only
  defense may not yet handle.  Fails only on regression from a committed
  baseline snapshot.

Corpus: ``tests/fixtures/adversarial/owasp_llm_top10.json``
Baseline: ``tests/fixtures/adversarial/baseline.json``

Run: ``make adversarial`` or ``pytest tests/test_adversarial.py -v``
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

from aipea.security import SecurityContext, SecurityScanner

_FIXTURES = Path(__file__).parent / "fixtures" / "adversarial"
_CORPUS_PATH = _FIXTURES / "owasp_llm_top10.json"
_BASELINE_PATH = _FIXTURES / "baseline.json"


def _load_corpus(tier: str | None = None) -> list[dict[str, Any]]:
    data: list[dict[str, Any]] = json.loads(_CORPUS_PATH.read_text(encoding="utf-8"))
    if tier is not None:
        data = [e for e in data if e["tier"] == tier]
    return data


def _load_baseline() -> dict[str, Any]:
    return json.loads(_BASELINE_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _compute_results(
    scanner: SecurityScanner, corpus: list[dict[str, Any]]
) -> tuple[int, int, list[dict[str, Any]]]:
    ctx = SecurityContext()
    passed = 0
    failures: list[dict[str, Any]] = []
    for entry in corpus:
        result = scanner.scan(entry["payload"], ctx)
        expected = entry["expected_flag"]
        if expected is None:
            ok = not result.has_flags()
        else:
            ok = any(f.startswith(expected) for f in result.flags)
        if ok:
            passed += 1
        else:
            failures.append({"id": entry["id"], "expected": expected, "got": list(result.flags)})
    return passed, len(corpus), failures


def _generate_baseline() -> None:
    scanner = SecurityScanner()
    bl_corpus = _load_corpus(tier="bright_line")
    ext_corpus = _load_corpus(tier="extended")

    bl_passed, bl_total, _ = _compute_results(scanner, bl_corpus)
    ext_passed, ext_total, _ = _compute_results(scanner, ext_corpus)

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
    }
    _BASELINE_PATH.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")
    print(f"Baseline written to {_BASELINE_PATH}")  # noqa: T201
    print(  # noqa: T201
        f"  bright_line: {bl_passed}/{bl_total} ({baseline['bright_line']['pass_rate']:.1%})"
    )
    print(  # noqa: T201
        f"  extended:    {ext_passed}/{ext_total} ({baseline['extended']['pass_rate']:.1%})"
    )


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
    """Wider corpus — fails only on regression from baseline snapshot."""

    def test_pass_rate_no_regression(self) -> None:
        scanner = SecurityScanner()
        ext_corpus = _load_corpus(tier="extended")
        baseline = _load_baseline()

        passed, total, failures = _compute_results(scanner, ext_corpus)
        pass_rate = passed / total if total else 0.0
        ext = baseline["extended"]
        baseline_rate = ext["pass_rate"]

        assert pass_rate >= baseline_rate, (
            f"Extended corpus regression: {pass_rate:.3f} < baseline {baseline_rate:.3f} "
            f"({passed}/{total} vs {ext['passed']}/{ext['total']}). "
            f"First 5 new failures: {failures[:5]}"
        )


if __name__ == "__main__":
    if "--update-baseline" in sys.argv:
        _generate_baseline()
    else:
        print("Usage: python -m tests.test_adversarial --update-baseline")  # noqa: T201
        sys.exit(1)
