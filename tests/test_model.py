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
