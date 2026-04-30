"""Tests for normalized multi-objective scoring."""

from __future__ import annotations

from c_uav_inspection.objective import (
    ObjectiveTermBounds,
    bounds_from_candidates,
    is_dominated,
    normalize_term,
    pareto_front,
    score_with_fixed_bounds,
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


def test_pareto_front_removes_dominated_rows():
    rows = [
        {"name": "a", "time": 10.0, "energy": 10.0},
        {"name": "b", "time": 12.0, "energy": 10.0},
        {"name": "c", "time": 9.0, "energy": 12.0},
    ]
    front = pareto_front(rows, ("time", "energy"))
    names = {r["name"] for r in front}
    assert names == {"a", "c"}


def test_pareto_front_keeps_identical_rows():
    """Identical candidates should not dominate each other — both kept."""
    rows = [
        {"name": "a", "time": 10.0, "energy": 10.0},
        {"name": "b", "time": 10.0, "energy": 10.0},
    ]
    front = pareto_front(rows, ("time", "energy"))
    assert len(front) == 2


def test_pareto_front_tradeoff_keeps_both():
    """When each candidate wins on a different metric, both stay."""
    rows = [
        {"name": "a", "time": 10.0, "energy": 20.0},
        {"name": "b", "time": 20.0, "energy": 10.0},
    ]
    front = pareto_front(rows, ("time", "energy"))
    assert len(front) == 2


def test_is_dominated_no_worse_and_strictly_better():
    assert is_dominated(
        {"t": 10.0, "e": 10.0},
        {"t": 9.0, "e": 10.0},
        ("t", "e"),
    )
    assert not is_dominated(
        {"t": 10.0, "e": 10.0},
        {"t": 12.0, "e": 8.0},
        ("t", "e"),
    )


def test_fixed_bounds_scoring_uses_shared_candidate_pool():
    bounds = {
        "time": ObjectiveTermBounds(10.0, 20.0),
        "energy": ObjectiveTermBounds(100.0, 200.0),
    }
    score = score_with_fixed_bounds(
        {"time": 15.0, "energy": 150.0},
        bounds,
        {"time": 0.5, "energy": 0.5},
    )
    assert score == 0.5
