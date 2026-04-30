"""Tests for Problem 1 time-priority DP solver."""

from pathlib import Path

import pytest

from c_uav_inspection.data import load_problem_data
from c_uav_inspection.model import evaluate_uav_route
from c_uav_inspection.problem1 import solve_problem1_for_k
from c_uav_inspection.problem1_time import (
    precompute_problem1_subset_routes,
    solve_problem1_time_priority_for_k,
)
from c_uav_inspection.search import InfeasibleError

DATA_PATH = Path("2026同济数学建模竞赛赛题/2026C数据.xlsx")


def test_subset_route_candidates_include_all_singletons():
    data = load_problem_data(DATA_PATH)
    candidates = precompute_problem1_subset_routes(data, improve=True)
    for idx, target in enumerate(data.targets):
        assert (1 << idx) in candidates


def test_time_priority_k4_covers_all_targets_energy_feasible():
    data = load_problem_data(DATA_PATH)
    sol = solve_problem1_time_priority_for_k(data, k=4, improve=True)
    expected = {target.node_id: target.base_hover_time_s for target in data.targets}
    assert sol.route_count <= 4
    assert sol.summary.feasible_energy
    assert sol.total_hover_by_node == pytest.approx(expected)
    assert all(route.sortie_id == 1 for route in sol.routes)
    assert all(
        evaluate_uav_route(route, data).feasible_energy for route in sol.routes
    )


def test_time_priority_k4_not_worse_than_current_packed_solution():
    data = load_problem_data(DATA_PATH)
    packed = solve_problem1_for_k(data, k=4, battery_swap_time_s=300, improve=True)
    time_priority = solve_problem1_time_priority_for_k(data, k=4, improve=True)
    assert (
        time_priority.summary.uav_phase_time_s
        <= packed.summary.uav_phase_time_s + 1e-9
    )


def test_solve_time_priority_k0_raises_value_error():
    """CR-009: k=0 should raise ValueError immediately."""
    data = load_problem_data(DATA_PATH)
    with pytest.raises(ValueError, match="k must be positive"):
        solve_problem1_time_priority_for_k(data, k=0)


def test_solve_time_priority_negative_k_raises_value_error():
    """CR-009: k=-1 should raise ValueError immediately."""
    data = load_problem_data(DATA_PATH)
    with pytest.raises(ValueError, match="k must be positive"):
        solve_problem1_time_priority_for_k(data, k=-1)


def test_solve_time_priority_k1_raises_infeasible_error():
    """CR-009: K=1 with 16 targets is infeasible due to energy limits."""
    data = load_problem_data(DATA_PATH)
    with pytest.raises(InfeasibleError):
        solve_problem1_time_priority_for_k(data, k=1)
