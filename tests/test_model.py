"""Tests for core model: UAVRoute, RouteMetrics, and solution summary."""

from __future__ import annotations

from pathlib import Path

from c_uav_inspection.data import load_problem_data
from c_uav_inspection.model import UAVRoute, evaluate_uav_route, summarize_uav_solution

DATA_PATH = Path("2026同济数学建模竞赛赛题/2026C数据.xlsx")


def test_evaluate_single_base_route_matches_manual_energy_formula():
    data = load_problem_data(DATA_PATH)
    route = UAVRoute(uav_id=1, sortie_id=1, node_sequence=(0, 1, 0), hover_times_s={1: 50})

    metrics = evaluate_uav_route(route, data)

    expected_energy = (
        data.flight_energy_j[(0, 1)]
        + data.flight_energy_j[(1, 0)]
        + 50 * data.params.hover_power_j_per_s
    )
    expected_time = (
        data.flight_time_s[(0, 1)] + data.flight_time_s[(1, 0)] + 50
    )
    assert metrics.energy_j == expected_energy
    assert metrics.duration_s == expected_time
    assert metrics.feasible_energy is True


def test_summarize_solution_includes_swap_time_between_sorties():
    data = load_problem_data(DATA_PATH)
    routes = (
        UAVRoute(uav_id=1, sortie_id=1, node_sequence=(0, 1, 0), hover_times_s={1: 50}),
        UAVRoute(uav_id=1, sortie_id=2, node_sequence=(0, 3, 0), hover_times_s={3: 35}),
        UAVRoute(uav_id=2, sortie_id=1, node_sequence=(0, 4, 0), hover_times_s={4: 55}),
    )

    summary = summarize_uav_solution(routes, data, battery_swap_time_s=300)

    uav1_route_time = sum(
        evaluate_uav_route(route, data).duration_s
        for route in routes
        if route.uav_id == 1
    )
    uav2_route_time = sum(
        evaluate_uav_route(route, data).duration_s
        for route in routes
        if route.uav_id == 2
    )
    assert summary.uav_work_times_s[1] == uav1_route_time + 300
    assert summary.uav_work_times_s[2] == uav2_route_time
    assert summary.uav_phase_time_s == max(summary.uav_work_times_s.values())


def test_summary_counts_idle_uavs_when_k_is_given():
    """When k is given, idle UAVs must be included with work time 0.0."""
    data = load_problem_data(DATA_PATH)
    route = UAVRoute(
        uav_id=1,
        sortie_id=1,
        node_sequence=(0, 1, 0),
        hover_times_s={1: data.targets[0].base_hover_time_s},
    )
    summary = summarize_uav_solution([route], data, 300.0, k=4)
    assert set(summary.uav_work_times_s) == {1, 2, 3, 4}
    assert summary.uav_work_times_s[2] == 0.0
    assert summary.load_std_s > 0.0


def test_completion_times_reach_base_hover():
    """Target completion times must include all targets with positive values."""
    from c_uav_inspection.model import compute_target_completion_times
    from c_uav_inspection.problem1 import solve_problem1_for_k

    data = load_problem_data(DATA_PATH)
    sol = solve_problem1_for_k(data, 4, data.params.battery_swap_time_s, improve=True)
    completion = compute_target_completion_times(
        sol.routes, data, data.params.battery_swap_time_s,
    )
    assert set(completion) == {t.node_id for t in data.targets}
    assert all(v > 0.0 for v in completion.values())
