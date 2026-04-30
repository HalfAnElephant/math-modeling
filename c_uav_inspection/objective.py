"""Normalized multi-objective scoring.

All terms are normalized to [0, 1] before weighted summation, so that
terms with different units (e.g. seconds vs joules) do not dominate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class ObjectiveTermBounds:
    """Min/max bounds for one objective term, used for min-max normalization.

    Attributes:
        lower: Minimum observed value across candidate solutions.
        upper: Maximum observed value across candidate solutions.
    """

    lower: float
    upper: float


def normalize_term(value: float, bounds: ObjectiveTermBounds) -> float:
    """Normalize a value to the [0, 1] interval using min-max normalization.

    If bounds are degenerate (upper <= lower), returns 0.0.
    Otherwise returns (value - lower) / (upper - lower) clipped to [0, 1].
    """
    if bounds.upper <= bounds.lower:
        return 0.0
    normalized = (value - bounds.lower) / (bounds.upper - bounds.lower)
    if normalized < 0.0:
        return 0.0
    if normalized > 1.0:
        return 1.0
    return normalized


def bounds_from_candidates(
    rows: Iterable[Mapping[str, float]],
    term_names: Sequence[str],
) -> dict[str, ObjectiveTermBounds]:
    """Extract per-term [min, max] bounds from a collection of candidate solutions.

    Args:
        rows: Iterable of candidate dicts, each mapping term_name -> value.
        term_names: Names of terms to compute bounds for.

    Returns:
        Dict mapping term_name -> ObjectiveTermBounds(lower=min, upper=max).
    """
    # Collect all values per term
    values_by_term: dict[str, list[float]] = {name: [] for name in term_names}
    for row in rows:
        for name in term_names:
            values_by_term[name].append(row[name])

    bounds: dict[str, ObjectiveTermBounds] = {}
    for name in term_names:
        vals = values_by_term[name]
        if not vals:
            bounds[name] = ObjectiveTermBounds(lower=0.0, upper=0.0)
        else:
            bounds[name] = ObjectiveTermBounds(lower=min(vals), upper=max(vals))
    return bounds


def weighted_normalized_objective(
    values: Mapping[str, float],
    bounds: dict[str, ObjectiveTermBounds],
    weights: Mapping[str, float],
) -> float:
    """Compute the weighted sum of normalized objective terms.

    Each term is normalized to [0, 1] using its bounds, then multiplied
    by its weight. The sum is divided by total weight (normalized weighted sum).

    Args:
        values: Raw term values for a single solution.
        bounds: Per-term normalization bounds.
        weights: Per-term weight in [0, 1]. Weights must sum to > 0.

    Returns:
        Score in [0, 1].

    Raises:
        ValueError: If total weight is not positive.
    """
    total_weight = sum(weights[name] for name in values)
    if total_weight <= 0:
        raise ValueError(
            f"Total weight must be positive, got {total_weight}"
        )

    weighted_sum = 0.0
    for name in values:
        term_bounds = bounds[name]
        normalized = normalize_term(values[name], term_bounds)
        weighted_sum += weights[name] * normalized

    return weighted_sum / total_weight


def is_dominated(
    candidate: Mapping[str, float],
    other: Mapping[str, float],
    minimize_terms: Sequence[str],
) -> bool:
    """Check whether *other* dominates *candidate* on the given minimize terms.

    Domination: other is no worse on all terms AND strictly better on at least one.
    """
    no_worse = all(other[t] <= candidate[t] for t in minimize_terms)
    strictly_better = any(other[t] < candidate[t] for t in minimize_terms)
    return no_worse and strictly_better


def pareto_front(
    rows: Sequence[Mapping[str, float]],
    minimize_terms: Sequence[str],
) -> list[Mapping[str, float]]:
    """Return the Pareto front (non-dominated rows) for the given minimize terms.

    A row is on the front if no other row dominates it.
    """
    result: list[Mapping[str, float]] = []
    for row in rows:
        if not any(is_dominated(row, other, minimize_terms) for other in rows):
            result.append(row)
    return result


def score_with_fixed_bounds(
    row: Mapping[str, float],
    bounds: Mapping[str, ObjectiveTermBounds],
    weights: Mapping[str, float],
) -> float:
    """Score a candidate row using pre-computed normalization bounds.

    Unlike in-table normalization, the bounds come from a shared candidate
    pool, making scores comparable across different experiments.
    """
    values = {name: float(row[name]) for name in weights}
    return weighted_normalized_objective(values, dict(bounds), weights)
