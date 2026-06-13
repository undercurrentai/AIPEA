"""Adaptive Learning Integrity Guardrails (ALIG) — finite-sample influence certificate.

A pure-stdlib engine that bounds how far a budget-limited adversary can shift the
*discrete argmax* strategy selection of the adaptive-learning engine, and exposes
that bound as an auditable certificate.

Status semantics (v1.8.0, "diagnostic-only" — see
``docs/adr/ADR-011-learning-integrity-guardrails.md``):

    ``CERTIFIED`` is mechanically disabled (``CERTIFIED_STATUS_ENABLED is False``);
    no public config, env var, or test hook may flip it. The strongest status this
    module emits is ``RAW_EVENT_EDIT_DIAGNOSTIC`` — an honest *event-level* edit
    bound that is NOT a user/source/Sybil guarantee and MUST NOT authorize adaptive
    strategy switching. The certified tier (request-bound, per-source-capped
    aggregation *units*) unlocks in v1.9.0.

Design lineage: certified-poisoning robustness (Deep Partition Aggregation;
Steinhardt-Koh-Liang) is established for neural-network training; the
budget-bounded-adversary + bounded-reward framing is standard in bandit/RLHF
poisoning defense (Rangi et al. limited-verification; "Learning When to Trust").
ALIG's contribution is the *transplant* of an exact finite-sample influence
certificate onto a low-dimensional discrete strategy selector in middleware.

This module has ZERO ``aipea`` imports (stdlib only), mirroring the
zero-dependency-core principle of ``security.py`` / ``knowledge.py``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Final

# ---------------------------------------------------------------------------
# Hard gate + caveat (v1.8.0 diagnostic-only)
# ---------------------------------------------------------------------------

# The certified tier is disabled by construction in v1.8.0. There is deliberately
# NO code path in this module that constructs ``CertificateStatus.CERTIFIED`` while
# this is False; it exists so the v1.9.0 certified tier can be added behind it.
CERTIFIED_STATUS_ENABLED: Final[bool] = False

DIAGNOSTIC_CAVEAT: Final[str] = (
    "Diagnostic only: bounds edits to recorded, clipped feedback events under "
    "fixed server-resolved labels; not a user/source/Sybil guarantee; must not "
    "authorize adaptive strategy switching."
)

_DEFAULT_MIN_SAMPLES: Final[int] = 20
# Ceiling on the budget search; a reported radius equal to this means "no rival
# can overtake the selection within a practical budget" (e.g. no contender).
_MAX_BUDGET_SCAN: Final[int] = 1000


class CertificateStatus(Enum):
    """Outcome of an influence-certificate computation."""

    NOT_CERTIFIABLE = "not_certifiable"
    INSUFFICIENT_DATA = "insufficient_data"
    RAW_EVENT_EDIT_DIAGNOSTIC = "raw_event_edit_diagnostic"
    # v1.9.0+; unreachable while CERTIFIED_STATUS_ENABLED is False.
    CERTIFIED = "certified"


class PerturbationModel(Enum):
    """Adversary edit model the certificate is computed against.

    INSERTION is the realistic feedback-poisoning adversary (submits <=k extra
    feedback events). REPLACEMENT and DELETION model the stronger store-tamper
    adversary (can modify/remove existing stored events).
    """

    INSERTION = "event_insertion"
    REPLACEMENT = "event_replacement"
    DELETION = "event_deletion"


@dataclass(frozen=True)
class InfluenceCertificate:
    """An auditable bound on adversarial influence over strategy selection.

    Attributes:
        status: See :class:`CertificateStatus`.
        perturbation_model: The edit model the radius is computed against.
        selected_strategy: The current argmax strategy among eligible cells.
        diagnostic_event_k: Largest budget of cell-local *event* edits under which
            the selection provably does not change. An event-level bound only.
        certified_k: ``None`` unless ``status is CERTIFIED`` (v1.9.0+). Always
            ``None`` in the v1.8.0 diagnostic-only build.
        margin: Observed gap between the top-1 and top-2 eligible estimates.
        estimates: Per-strategy mean feedback score (strategies with data).
        n_units: Per-strategy observation count.
        min_samples: Eligibility threshold a strategy must meet to be selectable.
        score_bounds: The ``(low, high)`` clip range applied to scores.
        assumptions: Human-readable caveats; always includes ``DIAGNOSTIC_CAVEAT``.
    """

    status: CertificateStatus
    perturbation_model: PerturbationModel
    selected_strategy: str | None
    diagnostic_event_k: int
    certified_k: int | None
    margin: float
    estimates: Mapping[str, float]
    n_units: Mapping[str, int]
    min_samples: int
    score_bounds: tuple[float, float]
    assumptions: tuple[str, ...]


# ---------------------------------------------------------------------------
# Exact finite-sample bounds for a bounded (clipped) mean
# ---------------------------------------------------------------------------


def _mean(scores: Sequence[float]) -> float:
    return sum(scores) / len(scores)


def _selected_lower(
    sorted_asc: Sequence[float],
    a: int,
    model: PerturbationModel,
    lo: float,
    min_samples: int,
) -> float | None:
    """Minimum achievable mean of the selected strategy after ``a`` edits.

    Returns ``None`` if the adversary can render the strategy ineligible
    (count drops below ``min_samples`` under DELETION), which is a selection
    loss = certificate failure.
    """
    n = len(sorted_asc)
    s = sum(sorted_asc)
    if model is PerturbationModel.INSERTION:
        return (s + a * lo) / (n + a)
    if model is PerturbationModel.REPLACEMENT:
        q = min(a, n)
        top_q = sum(sorted_asc[n - q :]) if q else 0.0
        return (s - top_q + q * lo) / n
    # DELETION: minimise the mean by deleting the highest-valued events.
    d_max = min(a, n - 1)
    if n - d_max < min_samples:
        return None
    best: float | None = None
    for d in range(d_max + 1):
        top_d = sum(sorted_asc[n - d :]) if d else 0.0
        m = (s - top_d) / (n - d)
        best = m if best is None else min(best, m)
    return best


def _rival_upper(
    sorted_asc: Sequence[float],
    b: int,
    model: PerturbationModel,
    hi: float,
    min_samples: int,
) -> float | None:
    """Maximum achievable mean of a rival after ``b`` edits.

    Returns ``None`` if the rival cannot be made *eligible* (>= ``min_samples``)
    with this budget under this model, i.e. it is not a threat at budget ``b``.
    """
    n = len(sorted_asc)
    s = sum(sorted_asc)
    if model is PerturbationModel.INSERTION:
        eff_n = n + b
        if eff_n < min_samples:
            return None
        return (s + b * hi) / eff_n
    if model is PerturbationModel.REPLACEMENT:
        if n < min_samples:  # replacement cannot change the count
            return None
        q = min(b, n)
        bot_q = sum(sorted_asc[:q])
        return (s - bot_q + q * hi) / n
    # DELETION: maximise the mean by deleting the lowest-valued events.
    best: float | None = None
    for d in range(min(b, n - 1) + 1):
        if n - d < min_samples:
            continue
        bot_d = sum(sorted_asc[:d]) if d else 0.0
        m = (s - bot_d) / (n - d)
        best = m if best is None else max(best, m)
    return best


def _selection_holds(
    selected_sorted: Sequence[float],
    rivals_sorted: Mapping[str, Sequence[float]],
    budget: int,
    model: PerturbationModel,
    lo: float,
    hi: float,
    min_samples: int,
) -> bool:
    """True iff no shared budget of ``budget`` edits flips the argmax.

    The adversary splits the budget into ``a`` edits depressing the selected
    strategy and ``b = budget - a`` edits boosting a single chosen rival.
    """
    if budget == 0:
        # Zero edits cannot change the selection (the current argmax stands).
        return True
    for a in range(budget + 1):
        b = budget - a
        lower = _selected_lower(selected_sorted, a, model, lo, min_samples)
        if lower is None:
            return False  # selected can be knocked out of eligibility
        for rival_scores in rivals_sorted.values():
            upper = _rival_upper(rival_scores, b, model, hi, min_samples)
            if upper is not None and lower <= upper:
                return False
    return True


def _stable_radius(
    selected_sorted: Sequence[float],
    rivals_sorted: Mapping[str, Sequence[float]],
    model: PerturbationModel,
    lo: float,
    hi: float,
    min_samples: int,
    max_scan: int,
) -> int:
    """Largest budget K (0..max_scan) under which the selection provably holds.

    ``_selection_holds`` is monotone in the budget (more budget never helps the
    defender) and ``holds(0)`` is always True, so the largest holding budget is
    found by binary search in O(log max_scan) checks.
    """

    def holds(k: int) -> bool:
        return _selection_holds(selected_sorted, rivals_sorted, k, model, lo, hi, min_samples)

    if holds(max_scan):
        return max_scan  # robust beyond the practical budget (e.g. no contender)
    # Invariant: holds(low) is True, holds(high) is False.
    low, high = 0, max_scan
    while high - low > 1:
        mid = (low + high) // 2
        if holds(mid):
            low = mid
        else:
            high = mid
    return low


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def compute_influence_certificate(
    scores_by_strategy: Mapping[str, Sequence[float]],
    *,
    score_bounds: tuple[float, float] = (0.0, 1.0),
    min_samples: int = _DEFAULT_MIN_SAMPLES,
    approved_strategies: Iterable[str] | None = None,
    perturbation_model: PerturbationModel = PerturbationModel.INSERTION,
    max_budget_scan: int = _MAX_BUDGET_SCAN,
) -> InfluenceCertificate:
    """Compute the influence certificate for a strategy-selection cell.

    Args:
        scores_by_strategy: Mapping of strategy name -> observed feedback scores.
        score_bounds: ``(low, high)`` range; scores are clipped into it.
        min_samples: Minimum observations for a strategy to be selectable.
        approved_strategies: Full approved strategy set. Names not present in
            ``scores_by_strategy`` are treated as *latent rivals* (n=0) that an
            INSERTION adversary could make eligible. Defaults to the observed set.
        perturbation_model: Adversary edit model (default INSERTION).
        max_budget_scan: Ceiling on the budget search.

    Returns:
        An :class:`InfluenceCertificate`. In the v1.8.0 build the status never
        reaches ``CERTIFIED``; ``certified_k`` is always ``None``.
    """
    lo, hi = score_bounds
    if lo >= hi:
        msg = f"score_bounds low must be < high (got {score_bounds})"
        raise ValueError(msg)
    if min_samples < 1:
        msg = f"min_samples must be >= 1 (got {min_samples})"
        raise ValueError(msg)

    clipped: dict[str, list[float]] = {
        name: sorted(min(hi, max(lo, float(x))) for x in vals)
        for name, vals in scores_by_strategy.items()
    }
    n_units: dict[str, int] = {name: len(v) for name, v in clipped.items()}
    estimates: dict[str, float] = {name: _mean(v) for name, v in clipped.items() if v}
    assumptions = (
        DIAGNOSTIC_CAVEAT,
        f"perturbation_model={perturbation_model.value}",
        "labels assumed server-resolved and immutable",
    )

    eligible = {name: v for name, v in clipped.items() if len(v) >= min_samples}
    if not eligible:
        return InfluenceCertificate(
            status=CertificateStatus.INSUFFICIENT_DATA,
            perturbation_model=perturbation_model,
            selected_strategy=None,
            diagnostic_event_k=0,
            certified_k=None,
            margin=0.0,
            estimates=estimates,
            n_units=n_units,
            min_samples=min_samples,
            score_bounds=(lo, hi),
            assumptions=assumptions,
        )

    selected = max(eligible, key=lambda name: _mean(eligible[name]))
    eligible_means = sorted((_mean(v) for v in eligible.values()), reverse=True)
    if len(eligible_means) > 1:
        margin = eligible_means[0] - eligible_means[1]
    else:
        margin = eligible_means[0] - lo

    approved = set(approved_strategies) if approved_strategies is not None else set(clipped)
    approved.discard(selected)
    rivals_sorted: dict[str, list[float]] = {name: clipped.get(name, []) for name in approved}

    radius = _stable_radius(
        eligible[selected], rivals_sorted, perturbation_model, lo, hi, min_samples, max_budget_scan
    )

    # v1.8.0 default-deny: the diagnostic radius is reported but the certified
    # tier is disabled, so the status never authorizes adaptive switching.
    return InfluenceCertificate(
        status=CertificateStatus.RAW_EVENT_EDIT_DIAGNOSTIC,
        perturbation_model=perturbation_model,
        selected_strategy=selected,
        diagnostic_event_k=radius,
        certified_k=None,
        margin=margin,
        estimates=estimates,
        n_units=n_units,
        min_samples=min_samples,
        score_bounds=(lo, hi),
        assumptions=assumptions,
    )
