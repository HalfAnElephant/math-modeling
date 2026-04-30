"""Tests for Problem 1 multi-UAV basic inspection solver."""

from pathlib import Path

from c_uav_inspection.data import load_problem_data
from c_uav_inspection.model import evaluate_uav_route
from c_uav_inspection.problem1 import solve_problem1_for_k

DATA_PATH = Path("2026同济数学建模竞赛赛题/2026C数据.xlsx")


def test_problem1_solution_satisfies_base_hover_and_energy_for_k2() -> None:
    data = load_problem_data(DATA_PATH)
    solution = solve_problem1_for_k(data, k=2, battery_swap_time_s=300)

    assert solution.summary.feasible_energy is True
    assert solution.summary.uav_phase_time_s <= data.params.operating_horizon_s
    for target in data.targets:
        assert (
            solution.total_hover_by_node[target.node_id]
            >= target.base_hover_time_s
        )


def test_problem1_solution_uses_only_requested_uav_count() -> None:
    data = load_problem_data(DATA_PATH)
    solution = solve_problem1_for_k(data, k=3, battery_swap_time_s=300)

    assert max(route.uav_id for route in solution.routes) <= 3
    assert min(route.uav_id for route in solution.routes) >= 1


def test_problem1_local_search_keeps_solution_feasible() -> None:
    data = load_problem_data(DATA_PATH)
    solution = solve_problem1_for_k(
        data, k=4, battery_swap_time_s=300, improve=True
    )

    assert solution.summary.feasible_energy is True
    assert solution.summary.uav_phase_time_s <= data.params.operating_horizon_s
    assert len(solution.routes) >= 1


def test_problem1_no_split_keeps_target_in_one_route() -> None:
    """With allow_split_hover=False, each target must be fully served in
    exactly one route. No target with positive hover demand may appear
    in more than one route's hover_times_s.
    """
    data = load_problem_data(DATA_PATH)
    EPSILON = 1e-7
    solution = solve_problem1_for_k(
        data, k=4, battery_swap_time_s=300, improve=True, allow_split_hover=False,
    )

    assert solution.summary.feasible_energy is True
    assert solution.summary.uav_phase_time_s <= data.params.operating_horizon_s

    for target in data.targets:
        assert (
            solution.total_hover_by_node[target.node_id]
            >= target.base_hover_time_s
        )

    # Count how many routes each target appears in
    appearances: dict[int, int] = {}
    for route in solution.routes:
        for node_id, h in route.hover_times_s.items():
            if h > EPSILON:
                appearances[node_id] = appearances.get(node_id, 0) + 1

    for node_id, count in appearances.items():
        assert count == 1, (
            f"Target {node_id} appears in {count} routes "
            f"with allow_split_hover=False"
        )

    # All routes must be energy-feasible
    assert all(
        evaluate_uav_route(r, data).feasible_energy
        for r in solution.routes
    )
