"""Black-box tests for Task 002: Core Model & Normalized Objective.

These tests verify the core model and objective modules through their
public external interfaces ONLY. No internal implementation details are
referenced — only the documented public API is used.

Coverage: all public types and functions across positive scenarios,
negative scenarios, edge cases, boundary conditions, and integration
between model and objective.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from c_uav_inspection.data import ProblemData, load_problem_data
from c_uav_inspection.model import (
    RouteMetrics,
    UAVRoute,
    UAVSolutionSummary,
    evaluate_uav_route,
    summarize_uav_solution,
)
from c_uav_inspection.objective import (
    ObjectiveTermBounds,
    bounds_from_candidates,
    normalize_term,
    weighted_normalized_objective,
)

DATA_PATH: Path = Path("2026同济数学建模竞赛赛题/2026C数据.xlsx")


# ══════════════════════════════════════════════════════════════════════════════
# Helpers — pure black-box: no knowledge of internal data structures
# ══════════════════════════════════════════════════════════════════════════════


def _basic_route(
    uav_id: int = 1,
    sortie_id: int = 1,
    nodes: tuple[int, ...] = (0, 1, 0),
    hover: dict[int, float] | None = None,
) -> UAVRoute:
    """Minimal helper to construct a UAVRoute via its public constructor only."""
    return UAVRoute(
        uav_id=uav_id,
        sortie_id=sortie_id,
        node_sequence=nodes,
        hover_times_s=hover or {},
    )


def _loaded_data() -> ProblemData:
    """Return freshly-loaded ProblemData. Call per test for isolation."""
    return load_problem_data(DATA_PATH)


# ══════════════════════════════════════════════════════════════════════════════
# model.py — evaluate_uav_route: Positive scenarios
# ══════════════════════════════════════════════════════════════════════════════


def test_evaluate_route_returns_route_metrics() -> None:
    """evaluate_uav_route returns a RouteMetrics instance with correct field types."""
    data = _loaded_data()
    route = _basic_route(hover={1: 50})

    metrics = evaluate_uav_route(route, data)

    assert isinstance(metrics, RouteMetrics)
    assert isinstance(metrics.duration_s, float)
    assert isinstance(metrics.energy_j, float)
    assert isinstance(metrics.feasible_energy, bool)


def test_evaluate_route_metrics_non_negative() -> None:
    """All computed metrics should be non-negative for any valid route."""
    data = _loaded_data()
    route = _basic_route(hover={1: 50})

    metrics = evaluate_uav_route(route, data)

    assert metrics.duration_s >= 0.0
    assert metrics.energy_j >= 0.0


def test_evaluate_route_duration_positive_for_nonzero_route() -> None:
    """A route with non-zero flight or hover must have positive duration."""
    data = _loaded_data()

    # Hover-only route (depot → depot, but with hover time)
    route_hover = _basic_route(nodes=(0, 0), hover={1: 50})
    assert evaluate_uav_route(route_hover, data).duration_s >= 50.0

    # Flight-only route has positive duration
    route_flight = _basic_route(hover={})
    assert evaluate_uav_route(route_flight, data).duration_s > 0.0


def test_evaluate_route_adding_hover_increases_metrics() -> None:
    """A route with hover must have strictly greater duration/energy than
    the same route without hover."""
    data = _loaded_data()

    no_hover = _basic_route(hover={})
    with_hover = _basic_route(hover={1: 50})

    m_no = evaluate_uav_route(no_hover, data)
    m_with = evaluate_uav_route(with_hover, data)

    assert m_with.duration_s > m_no.duration_s
    assert m_with.energy_j > m_no.energy_j


def test_evaluate_route_longer_path_has_longer_duration() -> None:
    """A longer flight path should take more time than a shorter one."""
    data = _loaded_data()

    short = _basic_route(nodes=(0, 1, 0), hover={})
    long = _basic_route(nodes=(0, 1, 2, 0), hover={})

    assert evaluate_uav_route(long, data).duration_s > evaluate_uav_route(short, data).duration_s


# ══════════════════════════════════════════════════════════════════════════════
# model.py — evaluate_uav_route: Edge cases & feasibility
# ══════════════════════════════════════════════════════════════════════════════


def test_evaluate_route_feasible_for_low_energy() -> None:
    """A short route with little hover should be feasible."""
    data = _loaded_data()
    route = _basic_route(hover={1: 1})

    metrics = evaluate_uav_route(route, data)
    assert metrics.feasible_energy is True


# ══════════════════════════════════════════════════════════════════════════════
# model.py — evaluate_uav_route: Negative scenarios
# ══════════════════════════════════════════════════════════════════════════════


def test_evaluate_route_invalid_node_raises() -> None:
    """A route referencing a node not in the flight matrix must raise an error."""
    data = _loaded_data()
    route = _basic_route(nodes=(0, 99999, 0), hover={99999: 10})

    with pytest.raises(Exception):
        evaluate_uav_route(route, data)


# ══════════════════════════════════════════════════════════════════════════════
# model.py — summarize_uav_solution: Positive scenarios
# ══════════════════════════════════════════════════════════════════════════════


def test_summarize_returns_uav_solution_summary() -> None:
    """summarize_uav_solution returns a UAVSolutionSummary with correct field types."""
    data = _loaded_data()
    r = _basic_route(hover={1: 50})

    s = summarize_uav_solution((r,), data, battery_swap_time_s=300)

    assert isinstance(s, UAVSolutionSummary)
    assert isinstance(s.uav_phase_time_s, float)
    assert isinstance(s.total_energy_j, float)
    assert isinstance(s.uav_work_times_s, dict)
    assert isinstance(s.load_std_s, float)
    assert isinstance(s.feasible_energy, bool)


def test_summarize_single_uav_single_sortie_no_swap() -> None:
    """Single UAV with one sortie has no battery swap overhead."""
    data = _loaded_data()
    r = _basic_route(hover={1: 30})

    s = summarize_uav_solution((r,), data, battery_swap_time_s=300)

    assert s.uav_work_times_s[1] == evaluate_uav_route(r, data).duration_s


def test_summarize_phase_time_is_max_work_time() -> None:
    """uav_phase_time_s must equal max(uav_work_times_s.values())."""
    data = _loaded_data()
    routes = (
        _basic_route(uav_id=1, nodes=(0, 1, 0), hover={1: 10}),
        _basic_route(uav_id=2, nodes=(0, 5, 0), hover={5: 200}),
    )

    s = summarize_uav_solution(routes, data, battery_swap_time_s=0)

    assert s.uav_phase_time_s == max(s.uav_work_times_s.values())


def test_summarize_total_energy_is_sum_of_routes() -> None:
    """total_energy_j must equal the sum of energy of all routes."""
    data = _loaded_data()
    routes = (
        _basic_route(uav_id=1, nodes=(0, 1, 0), hover={1: 30}),
        _basic_route(uav_id=2, nodes=(0, 3, 0), hover={3: 40}),
    )

    s = summarize_uav_solution(routes, data, battery_swap_time_s=0)

    expected = sum(evaluate_uav_route(r, data).energy_j for r in routes)
    assert s.total_energy_j == expected


def test_summarize_load_std_zero_for_equal_work_times() -> None:
    """Load std must be 0 when all UAVs have identical work time."""
    data = _loaded_data()
    routes = (
        _basic_route(uav_id=1, nodes=(0, 1, 0), hover={1: 50}),
        _basic_route(uav_id=2, nodes=(0, 1, 0), hover={1: 50}),
    )

    s = summarize_uav_solution(routes, data, battery_swap_time_s=0)

    assert s.uav_work_times_s[1] == s.uav_work_times_s[2]
    assert s.load_std_s == 0.0


def test_summarize_load_std_positive_for_unequal_work_times() -> None:
    """Load std must be > 0 when UAVs have different work times."""
    data = _loaded_data()
    routes = (
        _basic_route(uav_id=1, nodes=(0, 1, 0), hover={1: 5}),
        _basic_route(uav_id=2, nodes=(0, 5, 0), hover={5: 500}),
    )

    s = summarize_uav_solution(routes, data, battery_swap_time_s=0)

    assert s.uav_work_times_s[1] != s.uav_work_times_s[2]
    # Work times must differ by at least the hover delta
    assert abs(s.uav_work_times_s[1] - s.uav_work_times_s[2]) >= 495.0
    assert s.load_std_s > 0.0


def test_summarize_swap_overhead_is_n_minus_1_times_swap() -> None:
    """For a UAV with N sorties, swap overhead = (N - 1) * swap_time."""
    data = _loaded_data()
    swap = 300.0
    routes = (
        _basic_route(uav_id=1, sortie_id=1, nodes=(0, 1, 0), hover={1: 30}),
        _basic_route(uav_id=1, sortie_id=2, nodes=(0, 3, 0), hover={3: 30}),
        _basic_route(uav_id=1, sortie_id=3, nodes=(0, 5, 0), hover={5: 30}),
    )

    s = summarize_uav_solution(routes, data, battery_swap_time_s=swap)

    total_route = sum(evaluate_uav_route(r, data).duration_s for r in routes)
    expected = total_route + (3 - 1) * swap
    assert s.uav_work_times_s[1] == expected


def test_summarize_feasible_when_all_routes_feasible() -> None:
    """feasible_energy is True when every single route is feasible."""
    data = _loaded_data()
    r = _basic_route(nodes=(0, 0), hover={})

    s = summarize_uav_solution((r,), data, battery_swap_time_s=0)

    assert s.feasible_energy is True


def test_summarize_infeasible_when_any_route_infeasible() -> None:
    """feasible_energy is False when at least one route exceeds the energy limit."""
    data = _loaded_data()
    limit = data.params.effective_energy_limit_j
    # Use an absurdly large hover to exceed the energy limit
    huge_hover = limit / data.params.hover_power_j_per_s + 1000.0
    route_big = _basic_route(nodes=(0, 0), hover={1: huge_hover})
    route_ok = _basic_route(nodes=(0, 0), hover={})

    s = summarize_uav_solution((route_big, route_ok), data, battery_swap_time_s=0)

    assert s.feasible_energy is False


# ══════════════════════════════════════════════════════════════════════════════
# model.py — summarize_uav_solution: Edge cases
# ══════════════════════════════════════════════════════════════════════════════


def test_summarize_empty_solution() -> None:
    """An empty route list produces a valid, zero-valued summary."""
    data = _loaded_data()

    s = summarize_uav_solution((), data, battery_swap_time_s=300)

    assert s.uav_phase_time_s == 0.0
    assert s.total_energy_j == 0.0
    assert s.uav_work_times_s == {}
    assert s.load_std_s == 0.0
    assert s.feasible_energy is True


def test_summarize_single_uav_load_std_zero() -> None:
    """With only one UAV, load_std_s must be 0."""
    data = _loaded_data()
    r = _basic_route(nodes=(0, 1, 0), hover={1: 100})

    s = summarize_uav_solution((r,), data, battery_swap_time_s=0)

    assert s.load_std_s == 0.0


def test_summarize_zero_swap_time_no_overhead() -> None:
    """battery_swap_time_s=0 means no extra overhead for multi-sortie UAVs."""
    data = _loaded_data()
    routes = (
        _basic_route(uav_id=1, sortie_id=1, nodes=(0, 1, 0), hover={1: 30}),
        _basic_route(uav_id=1, sortie_id=2, nodes=(0, 2, 0), hover={2: 30}),
    )

    s = summarize_uav_solution(routes, data, battery_swap_time_s=0)

    total_route = sum(evaluate_uav_route(r, data).duration_s for r in routes)
    assert s.uav_work_times_s[1] == total_route


def test_summarize_large_swap_time() -> None:
    """A very large swap time dominates the UAV work time."""
    data = _loaded_data()
    large_swap = 10000.0
    routes = (
        _basic_route(uav_id=1, sortie_id=1, nodes=(0, 1, 0), hover={1: 1}),
        _basic_route(uav_id=1, sortie_id=2, nodes=(0, 1, 0), hover={1: 1}),
    )

    s = summarize_uav_solution(routes, data, battery_swap_time_s=large_swap)

    assert s.uav_work_times_s[1] >= large_swap


def test_summarize_three_uavs_load_std_with_skewed_load() -> None:
    """With 3 UAVs and very skewed work distribution, load_std_s reflects imbalance."""
    data = _loaded_data()
    routes = (
        _basic_route(uav_id=1, nodes=(0, 1, 0), hover={1: 10}),
        _basic_route(uav_id=2, nodes=(0, 2, 0), hover={2: 10}),
        _basic_route(uav_id=3, nodes=(0, 8, 0), hover={8: 800}),
    )

    s = summarize_uav_solution(routes, data, battery_swap_time_s=0)

    # The third UAV has far more work → std should be large
    assert s.load_std_s > 0.0
    # Std should be non-trivial (at least 10% of the max work time)
    assert s.load_std_s >= 0.1 * s.uav_phase_time_s


# ══════════════════════════════════════════════════════════════════════════════
# model.py — Immutability (all frozen dataclasses)
# ══════════════════════════════════════════════════════════════════════════════


def test_uav_route_is_immutable() -> None:
    """UAVRoute dataclass is frozen — attribute mutation must fail."""
    r = _basic_route()

    with pytest.raises(Exception):
        r.uav_id = 999  # type: ignore[misc]


def test_route_metrics_is_immutable() -> None:
    """RouteMetrics dataclass is frozen — attribute mutation must fail."""
    data = _loaded_data()
    m = evaluate_uav_route(_basic_route(), data)

    with pytest.raises(Exception):
        m.duration_s = 0.0  # type: ignore[misc]


def test_uav_solution_summary_is_immutable() -> None:
    """UAVSolutionSummary dataclass is frozen — attribute mutation must fail."""
    data = _loaded_data()
    s = summarize_uav_solution((_basic_route(),), data, battery_swap_time_s=0)

    with pytest.raises(Exception):
        s.uav_phase_time_s = 0.0  # type: ignore[misc]


# ══════════════════════════════════════════════════════════════════════════════
# objective.py — normalize_term: Positive scenarios
# ══════════════════════════════════════════════════════════════════════════════


def test_normalize_term_returns_float() -> None:
    """normalize_term always returns a Python float."""
    bounds = ObjectiveTermBounds(lower=0.0, upper=100.0)
    assert isinstance(normalize_term(50.0, bounds), float)


def test_normalize_term_output_always_in_unit_interval() -> None:
    """normalize_term never returns a value outside [0, 1]."""
    bounds = ObjectiveTermBounds(lower=10.0, upper=100.0)

    cases = (-100.0, 5.0, 10.0, 55.0, 100.0, 200.0, 1e9)
    for val in cases:
        result = normalize_term(val, bounds)
        assert 0.0 <= result <= 1.0, f"normalize_term({val}) = {result} not in [0, 1]"


def test_normalize_term_min_maps_to_zero_max_to_one() -> None:
    """The lower bound normalizes to 0.0; the upper bound normalizes to 1.0."""
    bounds = ObjectiveTermBounds(lower=100.0, upper=300.0)

    assert normalize_term(100.0, bounds) == 0.0
    assert normalize_term(300.0, bounds) == 1.0


def test_normalize_term_monotonic() -> None:
    """Larger raw values must produce larger or equal normalized values."""
    bounds = ObjectiveTermBounds(lower=0.0, upper=1000.0)
    pairs = [(0, 10), (50, 60), (0, 1000)]
    for lo, hi in pairs:
        assert normalize_term(lo, bounds) <= normalize_term(hi, bounds), (
            f"monotonicity violated: {lo} → {normalize_term(lo, bounds)}, "
            f"{hi} → {normalize_term(hi, bounds)}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# objective.py — normalize_term: Edge cases
# ══════════════════════════════════════════════════════════════════════════════


def test_normalize_term_degenerate_bounds_returns_zero() -> None:
    """When lower == upper, normalize_term should return 0.0 for ANY input."""
    bounds = ObjectiveTermBounds(lower=42.0, upper=42.0)

    for val in (0.0, 42.0, 100.0):
        assert normalize_term(val, bounds) == 0.0, (
            f"normalize_term({val}) with degenerate bounds should be 0.0"
        )


def test_normalize_term_negative_bounds() -> None:
    """Bounds can be negative; normalization should still work correctly."""
    bounds = ObjectiveTermBounds(lower=-100.0, upper=-10.0)

    assert normalize_term(-100.0, bounds) == 0.0
    assert normalize_term(-55.0, bounds) == 0.5
    assert normalize_term(-10.0, bounds) == 1.0


def test_normalize_term_clips_below_min() -> None:
    """Values below the lower bound should normalize to 0.0."""
    bounds = ObjectiveTermBounds(lower=50.0, upper=100.0)

    assert normalize_term(0.0, bounds) == 0.0
    assert normalize_term(49.0, bounds) == 0.0


def test_normalize_term_clips_above_max() -> None:
    """Values above the upper bound should normalize to 1.0."""
    bounds = ObjectiveTermBounds(lower=0.0, upper=100.0)

    assert normalize_term(101.0, bounds) == 1.0
    assert normalize_term(1e9, bounds) == 1.0


def test_normalize_term_zero_range_bounds() -> None:
    """Normalize around zero (crossing zero) should work."""
    bounds = ObjectiveTermBounds(lower=-100.0, upper=100.0)

    assert normalize_term(-100.0, bounds) == 0.0
    assert normalize_term(0.0, bounds) == 0.5
    assert normalize_term(100.0, bounds) == 1.0


# ══════════════════════════════════════════════════════════════════════════════
# objective.py — bounds_from_candidates
# ══════════════════════════════════════════════════════════════════════════════


def test_bounds_from_candidates_single_row() -> None:
    """With one candidate row, lower == upper == the value for each term."""
    rows = [{"x": 50.0, "y": 200.0}]
    bounds = bounds_from_candidates(rows, ("x", "y"))

    assert bounds["x"].lower == 50.0
    assert bounds["x"].upper == 50.0
    assert bounds["y"].lower == 200.0
    assert bounds["y"].upper == 200.0


def test_bounds_from_candidates_min_and_max() -> None:
    """bounds_from_candidates extracts true min and max across all rows."""
    rows = [
        {"cost": 10.0, "time": 300.0},
        {"cost": 50.0, "time": 100.0},
        {"cost": 30.0, "time": 500.0},
    ]
    bounds = bounds_from_candidates(rows, ("cost", "time"))

    assert bounds["cost"].lower == 10.0
    assert bounds["cost"].upper == 50.0
    assert bounds["time"].lower == 100.0
    assert bounds["time"].upper == 500.0


def test_bounds_from_candidates_all_identical() -> None:
    """When all candidates have identical values, lower == upper."""
    rows = [{"a": 7.0}, {"a": 7.0}, {"a": 7.0}]
    bounds = bounds_from_candidates(rows, ("a",))

    assert bounds["a"].lower == 7.0
    assert bounds["a"].upper == 7.0


def test_bounds_from_candidates_empty_rows() -> None:
    """Empty candidate list should produce zero-bounds without raising."""
    bounds = bounds_from_candidates([], ("x", "y"))

    assert bounds["x"].lower == 0.0
    assert bounds["x"].upper == 0.0
    assert bounds["y"].lower == 0.0
    assert bounds["y"].upper == 0.0


def test_bounds_from_candidates_negative_values() -> None:
    """bounds_from_candidates handles negative candidate values."""
    rows = [{"v": -10.0}, {"v": -5.0}, {"v": -1.0}]
    bounds = bounds_from_candidates(rows, ("v",))

    assert bounds["v"].lower == -10.0
    assert bounds["v"].upper == -1.0


# ══════════════════════════════════════════════════════════════════════════════
# objective.py — weighted_normalized_objective: Positive scenarios
# ══════════════════════════════════════════════════════════════════════════════


def test_weighted_objective_single_term() -> None:
    """With one term, the score equals the normalized value of that term."""
    bounds = {"x": ObjectiveTermBounds(lower=0.0, upper=100.0)}

    score = weighted_normalized_objective(
        values={"x": 75.0},
        bounds=bounds,
        weights={"x": 1.0},
    )

    assert score == 0.75


def test_weighted_objective_equal_weights_is_average() -> None:
    """With equal weights on all terms, score = average of normalized values."""
    bounds = {
        "a": ObjectiveTermBounds(lower=0.0, upper=100.0),
        "b": ObjectiveTermBounds(lower=0.0, upper=100.0),
    }

    # a=0 → 0.0, b=100 → 1.0, average = 0.5
    score = weighted_normalized_objective(
        values={"a": 0.0, "b": 100.0},
        bounds=bounds,
        weights={"a": 0.5, "b": 0.5},
    )

    assert score == 0.5


def test_weighted_objective_zero_weight_term_does_not_affect() -> None:
    """A term with weight 0 should not influence the score."""
    bounds = {
        "a": ObjectiveTermBounds(lower=0.0, upper=100.0),
        "b": ObjectiveTermBounds(lower=0.0, upper=100.0),
    }

    score = weighted_normalized_objective(
        values={"a": 100.0, "b": 0.0},
        bounds=bounds,
        weights={"a": 0.0, "b": 1.0},
    )

    # Only b matters (weight 1.0), b=0 → 0.0
    assert score == 0.0


def test_weighted_objective_unequal_weights() -> None:
    """A higher-weighted term should dominate the score."""
    bounds = {
        "a": ObjectiveTermBounds(lower=0.0, upper=100.0),
        "b": ObjectiveTermBounds(lower=0.0, upper=100.0),
    }

    # a=100 → 1.0, weight 0.75; b=0 → 0.0, weight 0.25
    # score = (0.75*1.0 + 0.25*0.0) / 1.0 = 0.75
    score = weighted_normalized_objective(
        values={"a": 100.0, "b": 0.0},
        bounds=bounds,
        weights={"a": 0.75, "b": 0.25},
    )

    assert score == 0.75


def test_weighted_objective_no_unit_dominance() -> None:
    """Terms with very different magnitudes (seconds vs joules) are normalized
    so that neither dominates purely because of unit scale."""
    # Simulate: time in seconds, energy in joules (much larger magnitude)
    rows = [
        {"time_s": 1000.0, "energy_j": 900000.0},
        {"time_s": 2000.0, "energy_j": 100000.0},
    ]
    bounds = bounds_from_candidates(rows, ("time_s", "energy_j"))

    # A solution that is best in time but worst in energy should score 0.5
    # (equal weight)
    score = weighted_normalized_objective(
        values={"time_s": 1000.0, "energy_j": 900000.0},
        bounds=bounds,
        weights={"time_s": 0.5, "energy_j": 0.5},
    )

    assert score == 0.5


def test_weighted_objective_output_in_unit_interval() -> None:
    """The weighted score must always be in [0, 1] for normalized terms."""
    bounds = {
        "a": ObjectiveTermBounds(lower=0.0, upper=100.0),
        "b": ObjectiveTermBounds(lower=0.0, upper=100.0),
    }

    score = weighted_normalized_objective(
        values={"a": 50.0, "b": 50.0},
        bounds=bounds,
        weights={"a": 0.3, "b": 0.7},
    )

    assert 0.0 <= score <= 1.0


# ══════════════════════════════════════════════════════════════════════════════
# objective.py — weighted_normalized_objective: Edge cases
# ══════════════════════════════════════════════════════════════════════════════


def test_weighted_objective_with_degenerate_bounds() -> None:
    """When a term has degenerate (zero-range) bounds, it normalizes to 0.0
    and the other term determines the score."""
    bounds = {
        "a": ObjectiveTermBounds(lower=42.0, upper=42.0),  # degenerate
        "b": ObjectiveTermBounds(lower=0.0, upper=100.0),
    }

    # a normalizes to 0 (degenerate), b=50 → 0.5
    # score = (0.5*0 + 0.5*0.5) / 1.0 = 0.25
    score = weighted_normalized_objective(
        values={"a": 42.0, "b": 50.0},
        bounds=bounds,
        weights={"a": 0.5, "b": 0.5},
    )

    assert score == 0.25


def test_weighted_objective_with_all_degenerate_bounds() -> None:
    """When all terms have zero-range bounds, the score should be 0.0."""
    bounds = {
        "a": ObjectiveTermBounds(lower=1.0, upper=1.0),
        "b": ObjectiveTermBounds(lower=2.0, upper=2.0),
    }

    score = weighted_normalized_objective(
        values={"a": 1.0, "b": 2.0},
        bounds=bounds,
        weights={"a": 0.5, "b": 0.5},
    )

    assert score == 0.0


def test_weighted_objective_with_values_outside_bounds() -> None:
    """Values outside their term bounds are clipped, keeping score in [0, 1]."""
    bounds = {
        "a": ObjectiveTermBounds(lower=0.0, upper=100.0),
        "b": ObjectiveTermBounds(lower=0.0, upper=100.0),
    }

    # a=-50 (below) → 0.0, b=150 (above) → 1.0, average = 0.5
    score = weighted_normalized_objective(
        values={"a": -50.0, "b": 150.0},
        bounds=bounds,
        weights={"a": 0.5, "b": 0.5},
    )

    assert score == 0.5


# ══════════════════════════════════════════════════════════════════════════════
# objective.py — Negative scenarios
# ══════════════════════════════════════════════════════════════════════════════


def test_weighted_objective_zero_total_weight_raises() -> None:
    """All weights zero must raise ValueError."""
    bounds = {"a": ObjectiveTermBounds(lower=0.0, upper=100.0)}

    with pytest.raises(ValueError):
        weighted_normalized_objective(
            values={"a": 50.0},
            bounds=bounds,
            weights={"a": 0.0},
        )


def test_weighted_objective_negative_total_weight_raises() -> None:
    """Negative total weight must raise ValueError."""
    bounds = {"a": ObjectiveTermBounds(lower=0.0, upper=100.0)}

    with pytest.raises(ValueError):
        weighted_normalized_objective(
            values={"a": 50.0},
            bounds=bounds,
            weights={"a": -1.0},
        )


# ══════════════════════════════════════════════════════════════════════════════
# objective.py — Immutability
# ══════════════════════════════════════════════════════════════════════════════


def test_objective_term_bounds_is_immutable() -> None:
    """ObjectiveTermBounds dataclass is frozen — attribute mutation must fail."""
    bounds = ObjectiveTermBounds(lower=0.0, upper=100.0)

    with pytest.raises(Exception):
        bounds.lower = 50.0  # type: ignore[misc]


# ══════════════════════════════════════════════════════════════════════════════
# Integration — model + objective used together
# ══════════════════════════════════════════════════════════════════════════════


def test_route_metrics_usable_in_objective_scoring() -> None:
    """RouteMetrics fields (duration_s, energy_j) can be fed directly into
    the objective scoring pipeline."""
    data = _loaded_data()
    route = _basic_route(nodes=(0, 1, 0), hover={1: 50})
    m = evaluate_uav_route(route, data)

    bounds = bounds_from_candidates(
        [{"duration_s": m.duration_s, "energy_j": m.energy_j}],
        ("duration_s", "energy_j"),
    )

    score = weighted_normalized_objective(
        values={"duration_s": m.duration_s, "energy_j": m.energy_j},
        bounds=bounds,
        weights={"duration_s": 0.5, "energy_j": 0.5},
    )

    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0


def test_solution_summary_usable_in_objective_scoring() -> None:
    """UAVSolutionSummary fields (uav_phase_time_s, total_energy_j, load_std_s)
    can be fed directly into the objective scoring pipeline."""
    data = _loaded_data()
    routes = (
        _basic_route(uav_id=1, nodes=(0, 1, 0), hover={1: 50}),
        _basic_route(uav_id=2, nodes=(0, 3, 0), hover={3: 40}),
    )
    s = summarize_uav_solution(routes, data, battery_swap_time_s=300)

    bounds = bounds_from_candidates(
        [
            {
                "phase": s.uav_phase_time_s,
                "energy": s.total_energy_j,
                "load_std": s.load_std_s,
            }
        ],
        ("phase", "energy", "load_std"),
    )

    score = weighted_normalized_objective(
        values={
            "phase": s.uav_phase_time_s,
            "energy": s.total_energy_j,
            "load_std": s.load_std_s,
        },
        bounds=bounds,
        weights={"phase": 0.4, "energy": 0.3, "load_std": 0.3},
    )

    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0


def test_multiple_candidate_solutions_can_be_scored() -> None:
    """Multiple solution summaries can be normalized and compared using
    the objective scoring pipeline."""
    data = _loaded_data()

    # Candidate A: two UAVs, balanced
    routes_a = (
        _basic_route(uav_id=1, nodes=(0, 1, 0), hover={1: 50}),
        _basic_route(uav_id=2, nodes=(0, 2, 0), hover={2: 50}),
    )
    s_a = summarize_uav_solution(routes_a, data, battery_swap_time_s=300)

    # Candidate B: two UAVs, imbalanced
    routes_b = (
        _basic_route(uav_id=1, nodes=(0, 1, 0), hover={1: 20}),
        _basic_route(uav_id=2, nodes=(0, 9, 0), hover={9: 200}),
    )
    s_b = summarize_uav_solution(routes_b, data, battery_swap_time_s=300)

    candidates = [
        {"phase": s_a.uav_phase_time_s, "energy": s_a.total_energy_j, "load": s_a.load_std_s},
        {"phase": s_b.uav_phase_time_s, "energy": s_b.total_energy_j, "load": s_b.load_std_s},
    ]

    bounds = bounds_from_candidates(candidates, ("phase", "energy", "load"))

    score_a = weighted_normalized_objective(
        values=candidates[0],
        bounds=bounds,
        weights={"phase": 0.4, "energy": 0.3, "load": 0.3},
    )
    score_b = weighted_normalized_objective(
        values=candidates[1],
        bounds=bounds,
        weights={"phase": 0.4, "energy": 0.3, "load": 0.3},
    )

    # Both scores must be in [0, 1]
    assert 0.0 <= score_a <= 1.0
    assert 0.0 <= score_b <= 1.0
    # Normalization is direction-agnostic: lower raw values → lower scores,
    # higher raw values → higher scores. When Candidate A is strictly better
    # (lower in all minimization objectives), it should score LOWER than B.
    assert score_a <= score_b, (
        f"Candidate A (balanced, lower values) scored {score_a}, "
        f"Candidate B (imbalanced, higher values) scored {score_b}"
    )
    # Scores should differ since candidates differ
    assert score_a != score_b
