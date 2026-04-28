"""Tests for normalized multi-objective scoring."""

from __future__ import annotations

from c_uav_inspection.objective import (
    ObjectiveTermBounds,
    bounds_from_candidates,
    normalize_term,
    weighted_normalized_objective,
)


def test_normalize_term_maps_value_to_unit_interval():
    bounds = ObjectiveTermBounds(lower=100.0, upper=300.0)

    assert normalize_term(100.0, bounds) == 0.0
    assert normalize_term(200.0, bounds) == 0.5
    assert normalize_term(300.0, bounds) == 1.0


def test_normalize_term_handles_degenerate_bounds():
    bounds = ObjectiveTermBounds(lower=42.0, upper=42.0)

    assert normalize_term(42.0, bounds) == 0.0


def test_weighted_objective_does_not_let_large_units_dominate():
    rows = [
        {"time_s": 1000.0, "energy_j": 900000.0},
        {"time_s": 2000.0, "energy_j": 100000.0},
    ]
    bounds = bounds_from_candidates(rows, ("time_s", "energy_j"))

    score = weighted_normalized_objective(
        values={"time_s": 1000.0, "energy_j": 900000.0},
        bounds=bounds,
        weights={"time_s": 0.5, "energy_j": 0.5},
    )

    assert score == 0.5
