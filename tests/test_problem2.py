"""Tests for Problem 2: closed-loop inspection with rebuild search."""

from pathlib import Path

from c_uav_inspection.data import load_problem_data
from c_uav_inspection.problem1 import solve_problem1_for_k
from c_uav_inspection.problem2 import (
    effective_direct_threshold,
    evaluate_closed_loop,
    solve_ground_tsp,
)

DATA_PATH = Path("2026同济数学建模竞赛赛题/2026C数据.xlsx")


def test_ground_tsp_all_manual_starts_and_ends_at_p0():
    data = load_problem_data(DATA_PATH)
    manual_points = tuple(target.manual_point_id for target in data.targets)

    result = solve_ground_tsp(data, manual_points)

    assert result.path[0] == "P0"
    assert result.path[-1] == "P0"
    assert sorted(result.path[1:-1]) == sorted(manual_points)
    assert result.total_time_s > 2670


def test_closed_loop_marks_all_base_only_targets_manual():
    data = load_problem_data(DATA_PATH)
    p1 = solve_problem1_for_k(data, k=2, battery_swap_time_s=300)

    closed = evaluate_closed_loop(data, p1.routes, direct_threshold_multiplier=1.0)

    assert closed.uav_phase_time_s == p1.summary.uav_phase_time_s
    assert closed.manual_count >= 1
    assert closed.closed_loop_time_s == closed.uav_phase_time_s + closed.ground_review_time_s


def test_direct_threshold_multiplier_is_floored_by_base_hover_time():
    data = load_problem_data(DATA_PATH)

    for target in data.targets:
        threshold = effective_direct_threshold(target, direct_threshold_multiplier=0.70)
        assert threshold >= target.base_hover_time_s


from c_uav_inspection.problem2 import solve_joint_problem_for_k


def test_joint_solver_reduces_or_matches_manual_count_against_base_only():
    data = load_problem_data(DATA_PATH)
    base = evaluate_closed_loop(data, solve_problem1_for_k(data, k=3, battery_swap_time_s=300).routes, 1.0)
    joint = solve_joint_problem_for_k(data, k=3, direct_threshold_multiplier=1.0)

    assert joint.closed_loop.manual_count <= base.manual_count
    assert joint.closed_loop.closed_loop_time_s > 0
    assert all(route.node_sequence[0] == 0 and route.node_sequence[-1] == 0 for route in joint.routes)


def test_joint_solver_direct_confirmed_nodes_meet_effective_thresholds():
    data = load_problem_data(DATA_PATH)
    joint = solve_joint_problem_for_k(data, k=4, direct_threshold_multiplier=0.70)
    hover_by_node = {}
    for route in joint.routes:
        for node_id, seconds in route.hover_times_s.items():
            hover_by_node[node_id] = hover_by_node.get(node_id, 0.0) + seconds

    by_id = {target.node_id: target for target in data.targets}
    for node_id in joint.closed_loop.direct_confirmed_nodes:
        assert hover_by_node[node_id] >= effective_direct_threshold(by_id[node_id], 0.70)


import pytest


def test_effective_direct_threshold_raises_on_non_positive_multiplier():
    """effective_direct_threshold must reject multiplier <= 0 with ValueError."""
    from c_uav_inspection.data import Target

    target = Target(
        node_id=1,
        node_name="T1",
        building_id="B1",
        x_m=0.0,
        y_m=0.0,
        z_m=0.0,
        priority_level="High",
        priority_weight=3,
        issue_type="crack",
        base_hover_time_s=100.0,
        direct_confirm_time_s=200.0,
        manual_point_id="MP01",
        manual_x_m=0.0,
        manual_y_m=0.0,
        manual_service_time_s=30.0,
    )

    with pytest.raises(ValueError, match="multiplier must be positive"):
        effective_direct_threshold(target, direct_threshold_multiplier=0.0)

    with pytest.raises(ValueError, match="multiplier must be positive"):
        effective_direct_threshold(target, direct_threshold_multiplier=-0.5)


def test_solve_ground_tsp_empty_manual_points():
    """solve_ground_tsp with empty manual_point_ids must return path ("P0","P0")
    with zero travel, service, and total time."""
    data = load_problem_data(DATA_PATH)
    result = solve_ground_tsp(data, tuple())

    assert result.path == ("P0", "P0")
    assert result.travel_time_s == 0.0
    assert result.service_time_s == 0.0
    assert result.total_time_s == 0.0
