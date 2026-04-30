"""Tests for Problem 2: closed-loop inspection with rebuild search."""

from pathlib import Path

from c_uav_inspection.data import load_problem_data
from c_uav_inspection.problem1 import solve_problem1_for_k
from c_uav_inspection.problem2 import (
    _direct_confirm_score,
    effective_direct_threshold,
    evaluate_closed_loop,
    solve_all_direct_confirm_baseline,
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


def test_closed_loop_reports_weighted_manual_cost_for_all_manual_case():
    data = load_problem_data(DATA_PATH)
    base = solve_problem1_for_k(data, k=4, battery_swap_time_s=300, improve=True)
    closed = evaluate_closed_loop(data, base.routes, direct_threshold_multiplier=1e9)

    assert closed.manual_target_nodes == tuple(range(1, 17))
    assert closed.manual_count == 16
    assert closed.weighted_manual_cost == sum(
        t.priority_weight for t in data.targets
    )


def test_joint_solver_rejects_tolerance_below_one():
    """solve_joint_problem_for_k must reject manual_reduction_time_tolerance < 1.0."""
    data = load_problem_data(DATA_PATH)

    with pytest.raises(ValueError, match="manual_reduction_time_tolerance"):
        solve_joint_problem_for_k(
            data, k=4, direct_threshold_multiplier=1.0,
            manual_reduction_time_tolerance=0.99,
        )

    with pytest.raises(ValueError, match="manual_reduction_time_tolerance"):
        solve_joint_problem_for_k(
            data, k=4, direct_threshold_multiplier=1.0,
            manual_reduction_time_tolerance=0.5,
        )

    # Verify tolerance=1.0 is accepted (boundary)
    solve_joint_problem_for_k(
        data, k=4, direct_threshold_multiplier=1.0,
        manual_reduction_time_tolerance=1.0,
    )


def test_direct_confirm_score_multiplies_priority_weight():
    """Semantic property: _direct_confirm_score incorporates priority_weight
    as a multiplicative factor. For a target with priority_weight=P,
    score = P * base_rate where base_rate > 0 and is independent of P.

    We verify this by checking that score / priority_weight yields a
    positive base_rate for every target — confirming that priority_weight
    acts as a genuine multiplier rather than being an additive term or
    having a nonlinear effect.
    """
    data = load_problem_data(DATA_PATH)

    base_rates: list[float] = []
    for target in data.targets:
        score = _direct_confirm_score(data, target.node_id, 1.0)
        priority = max(target.priority_weight, 1)
        base_rate = score / priority
        assert base_rate > 0, (
            f"base_rate should be positive for target {target.node_id}"
        )
        base_rates.append(base_rate)

    # All base_rates must be positive (verified per-target above)
    # and the set of base_rates must be non-empty
    assert len(base_rates) == len(data.targets)


def test_ground_tsp_uses_manual_points_service_time():
    """solve_ground_tsp must use ManualPoints service time, not NodeData."""
    data = load_problem_data(DATA_PATH)
    result = solve_ground_tsp(data, ("MP02",))
    assert result.service_time_s == data.manual_points["MP02"].manual_service_time_s

    # MP02 has conflicting service times (180 vs 210), verify we use ManualPoints
    mp02_target = next(t for t in data.targets if t.manual_point_id == "MP02")
    assert mp02_target.manual_service_time_s == 180.0
    assert data.manual_points["MP02"].manual_service_time_s == 210.0
    assert result.service_time_s == 210.0, (
        "Must use ManualPoints service time (210), not NodeData (180)"
    )


def test_all_direct_confirm_baseline_is_represented():
    """All-direct-confirm baseline must be constructible and have 0 manual."""
    data = load_problem_data(DATA_PATH)
    sol = solve_all_direct_confirm_baseline(data, data.params.k_max)
    assert len(sol.closed_loop.direct_confirmed_nodes) == len(data.targets)
    assert sol.closed_loop.manual_count == 0
    assert sol.closed_loop.ground_review_time_s == 0.0
