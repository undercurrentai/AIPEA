"""Tests for the ALIG influence-certificate engine (``aipea.learning_integrity``).

Strategy:
- An INDEPENDENT brute-force verifier reconstructs the worst-case adversary edits
  via plain list operations + direct mean recomputation (not the module's
  closed-form sum-slice bounds), so disagreement catches arithmetic/off-by-one
  bugs in the module.
- Hypothesis property tests assert the certificate is **conservative** (never
  claims stability the brute force can break) and **tight** (one more edit does
  break it), and that the v1.8.0 hard gate never emits ``CERTIFIED``.
- Parametrized unit tests pin the concrete cases reasoned through in the
  Claude<->GPT-5.5-pro design dialogue.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from aipea.learning_integrity import (
    CERTIFIED_STATUS_ENABLED,
    CertificateStatus,
    PerturbationModel,
    _selection_holds,
    compute_influence_certificate,
)

LO = 0.0
HI = 4.0
MODELS = list(PerturbationModel)


# ---------------------------------------------------------------------------
# Independent brute-force verifier (mirrors the math via list ops, not formulas)
# ---------------------------------------------------------------------------


def _worst_selected(
    sel_sorted: Sequence[float], a: int, model: PerturbationModel, lo: float, min_samples: int
) -> float | None:
    n = len(sel_sorted)
    if model is PerturbationModel.INSERTION:
        v = [*sel_sorted, *([lo] * a)]
        return sum(v) / len(v)
    if model is PerturbationModel.REPLACEMENT:
        q = min(a, n)
        v = [*sel_sorted[: n - q], *([lo] * q)]
        return sum(v) / len(v)
    best: float | None = None
    for d in range(min(a, n - 1) + 1):
        if n - d < min_samples:
            return None
        v = sel_sorted[: n - d]
        m = sum(v) / len(v)
        best = m if best is None else min(best, m)
    return best


def _worst_rival(
    r_sorted: Sequence[float], b: int, model: PerturbationModel, hi: float, min_samples: int
) -> float | None:
    n = len(r_sorted)
    if model is PerturbationModel.INSERTION:
        eff = n + b
        if eff < min_samples:
            return None
        v = [*r_sorted, *([hi] * b)]
        return sum(v) / len(v)
    if model is PerturbationModel.REPLACEMENT:
        if n < min_samples:
            return None
        q = min(b, n)
        v = [*r_sorted[q:], *([hi] * q)]
        return sum(v) / len(v)
    best: float | None = None
    for d in range(min(b, n - 1) + 1):
        if n - d < min_samples:
            continue
        v = r_sorted[d:]
        m = sum(v) / len(v)
        best = m if best is None else max(best, m)
    return best


def _flip_possible(
    clipped: Mapping[str, Sequence[float]],
    selected: str,
    rivals: Sequence[str],
    k: int,
    model: PerturbationModel,
    min_samples: int,
) -> bool:
    if k == 0:
        return False  # zero edits cannot change the selection
    sel = sorted(clipped[selected])
    for a in range(k + 1):
        b = k - a
        ws = _worst_selected(sel, a, model, LO, min_samples)
        if ws is None:
            return True  # selected knocked out of eligibility
        for r in rivals:
            wr = _worst_rival(sorted(clipped.get(r, [])), b, model, HI, min_samples)
            if wr is not None and wr >= ws:
                return True
    return False


# ---------------------------------------------------------------------------
# Property-based tests
# ---------------------------------------------------------------------------


@st.composite
def _cells(draw: st.DrawFn) -> tuple[dict[str, list[float]], int, PerturbationModel]:
    names = draw(st.lists(st.sampled_from(["a", "b", "c"]), min_size=1, max_size=3, unique=True))
    data: dict[str, list[float]] = {}
    for name in names:
        vals = draw(st.lists(st.integers(min_value=0, max_value=4), min_size=0, max_size=6))
        data[name] = [float(v) for v in vals]
    min_samples = draw(st.integers(min_value=1, max_value=3))
    model = draw(st.sampled_from(MODELS))
    return data, min_samples, model


_SCAN_CAP = 40


@settings(max_examples=300, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(_cells())
def test_certificate_is_conservative_and_tight(
    case: tuple[dict[str, list[float]], int, PerturbationModel],
) -> None:
    data, min_samples, model = case
    cert = compute_influence_certificate(
        data,
        score_bounds=(LO, HI),
        min_samples=min_samples,
        perturbation_model=model,
        max_budget_scan=_SCAN_CAP,
    )
    if cert.status is not CertificateStatus.RAW_EVENT_EDIT_DIAGNOSTIC:
        return
    selected = cert.selected_strategy
    assert selected is not None
    rivals = [n for n in data if n != selected]
    k = cert.diagnostic_event_k
    # Conservative: no attack within the reported radius flips the selection.
    for budget in range(k + 1):
        assert not _flip_possible(data, selected, rivals, budget, model, min_samples), (
            f"over-promise at budget {budget} (radius={k}, model={model})"
        )
    # Tight: one more edit flips it (unless the scan ceiling was hit).
    if k < _SCAN_CAP:
        assert _flip_possible(data, selected, rivals, k + 1, model, min_samples), (
            f"under-report: radius {k} could be larger (model={model})"
        )


@settings(max_examples=200, deadline=None)
@given(_cells())
def test_estimates_in_bounds_and_hard_gate_holds(
    case: tuple[dict[str, list[float]], int, PerturbationModel],
) -> None:
    data, min_samples, model = case
    cert = compute_influence_certificate(
        data,
        score_bounds=(LO, HI),
        min_samples=min_samples,
        perturbation_model=model,
        max_budget_scan=_SCAN_CAP,
    )
    for value in cert.estimates.values():
        assert LO <= value <= HI
    # v1.8.0 hard gate: never certified, no certified_k, no matter the input.
    assert cert.certified_k is None
    assert cert.status is not CertificateStatus.CERTIFIED


def test_certified_status_is_disabled_in_v1_8() -> None:
    assert CERTIFIED_STATUS_ENABLED is False


def test_selection_holds_vacuously_true_at_zero_budget() -> None:
    """Binary-search base-case invariant: zero edits can never flip the argmax,
    even with a tie at the top. Guards the assumption ``_stable_radius`` relies on."""
    assert (
        _selection_holds(
            [0.5, 0.5, 0.5],
            {"r": [0.5, 0.5, 0.5]},
            0,
            PerturbationModel.INSERTION,
            0.0,
            1.0,
            1,
        )
        is True
    )


# ---------------------------------------------------------------------------
# Concrete cases from the design dialogue
# ---------------------------------------------------------------------------


def test_gpt_sanity_case_replacement() -> None:
    """A=ten 0.8, B=ten 0.7 -> robust to 1 replacement edit, flips at 2."""
    cert = compute_influence_certificate(
        {"A": [0.8] * 10, "B": [0.7] * 10},
        score_bounds=(0.0, 1.0),
        min_samples=3,
        perturbation_model=PerturbationModel.REPLACEMENT,
    )
    assert cert.status is CertificateStatus.RAW_EVENT_EDIT_DIAGNOSTIC
    assert cert.selected_strategy == "A"
    assert cert.diagnostic_event_k == 1
    assert cert.certified_k is None


def test_sanity_case_insertion() -> None:
    """Same A/B under the realistic insertion adversary -> radius 1."""
    cert = compute_influence_certificate(
        {"A": [0.8] * 10, "B": [0.7] * 10},
        score_bounds=(0.0, 1.0),
        min_samples=3,
        perturbation_model=PerturbationModel.INSERTION,
    )
    assert cert.diagnostic_event_k == 1


def test_deletion_eligibility_knockout() -> None:
    """Selected sitting exactly at min_samples is knocked ineligible by 1 deletion."""
    cert = compute_influence_certificate(
        {"A": [1.0] * 3, "B": [0.0] * 5},
        score_bounds=(0.0, 1.0),
        min_samples=3,
        perturbation_model=PerturbationModel.DELETION,
    )
    assert cert.selected_strategy == "A"
    assert cert.diagnostic_event_k == 0


def test_latent_rival_is_counted() -> None:
    """An approved-but-unseen rival (n=0) becomes a threat at min_samples insertions."""
    cert = compute_influence_certificate(
        {"a": [0.5] * 5},
        score_bounds=(0.0, 1.0),
        min_samples=3,
        approved_strategies=["a", "c"],  # c is latent (no data)
        perturbation_model=PerturbationModel.INSERTION,
    )
    assert cert.selected_strategy == "a"
    # c needs 3 insertions of 1.0 to become eligible and win -> robust to 2.
    assert cert.diagnostic_event_k == 2


def test_insufficient_data() -> None:
    cert = compute_influence_certificate({"a": [0.5, 0.5]}, score_bounds=(0.0, 1.0), min_samples=3)
    assert cert.status is CertificateStatus.INSUFFICIENT_DATA
    assert cert.selected_strategy is None
    assert cert.diagnostic_event_k == 0
    assert cert.certified_k is None


def test_assumptions_carry_the_caveat() -> None:
    cert = compute_influence_certificate({"a": [1.0] * 5, "b": [0.0] * 5}, min_samples=3)
    assert any("Diagnostic only" in a for a in cert.assumptions)


@pytest.mark.parametrize(
    "bounds,min_samples",
    [((1.0, 0.0), 3), ((0.5, 0.5), 3), ((0.0, 1.0), 0)],
    ids=["inverted-bounds", "equal-bounds", "min-samples-zero"],
)
def test_input_validation(bounds: tuple[float, float], min_samples: int) -> None:
    with pytest.raises(ValueError):
        compute_influence_certificate({"a": [0.5]}, score_bounds=bounds, min_samples=min_samples)
