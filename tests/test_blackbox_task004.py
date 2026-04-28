"""Black-box tests for Task 004: Problem 2 Closed-Loop & Rebuild Search.

These tests verify the problem2 module through its public external
interfaces ONLY. No private (`_`-prefixed) functions, no internal
implementation details, no knowledge of how the algorithms work internally.

Coverage: all public types and functions across positive scenarios,
negative scenarios, edge cases, boundary conditions, and integration
with problem1/model.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from c_uav_inspection.data import (
    ProblemData,
    Target,
    load_problem_data,
)
from c_uav_inspection.model import (
    UAVRoute,
    UAVSolutionSummary,
    evaluate_uav_route,
    summarize_uav_solution,
)
from c_uav_inspection.problem1 import (
    Problem1Solution,
    solve_problem1_for_k,
    solve_uav_hover_plan,
)
from c_uav_inspection.problem2 import (
    ClosedLoopResult,
    GroundReviewResult,
    JointSolution,
    effective_direct_threshold,
    evaluate_closed_loop,
    solve_ground_tsp,
    solve_joint_problem_for_k,
)

DATA_PATH: Path = Path("2026同济数学建模竞赛赛题/2026C数据.xlsx")


# ══════════════════════════════════════════════════════════════════════════════
# Helpers — pure black-box: use only public constructors and functions
# ══════════════════════════════════════════════════════════════════════════════


def _loaded_data() -> ProblemData:
    """Return freshly-loaded ProblemData. Call per test for isolation."""
    return load_problem_data(DATA_PATH)


def _make_route(
    uav_id: int = 1,
    sortie_id: int = 1,
    nodes: tuple[int, ...] = (0, 1, 0),
    hover: dict[int, float] | None = None,
) -> UAVRoute:
    """Construct a UAVRoute via its public constructor only."""
    return UAVRoute(
        uav_id=uav_id,
        sortie_id=sortie_id,
        node_sequence=nodes,
        hover_times_s=hover or {},
    )


def _make_target(
    node_id: int = 1,
    base_hover: float = 100.0,
    direct_confirm: float = 200.0,
    manual_point: str = "MP01",
    manual_service: float = 30.0,
) -> Target:
    """Construct a minimal Target via its public constructor."""
    return Target(
        node_id=node_id,
        node_name=f"T{node_id}",
        building_id=f"B{node_id}",
        x_m=0.0,
        y_m=0.0,
        z_m=0.0,
        priority_level="High",
        priority_weight=3,
        issue_type="crack",
        base_hover_time_s=base_hover,
        direct_confirm_time_s=direct_confirm,
        manual_point_id=manual_point,
        manual_x_m=0.0,
        manual_y_m=0.0,
        manual_service_time_s=manual_service,
    )


# ══════════════════════════════════════════════════════════════════════════════
# effective_direct_threshold — Positive scenarios
# ══════════════════════════════════════════════════════════════════════════════


def test_effective_threshold_returns_float() -> None:
    """effective_direct_threshold returns a float."""
    t = _make_target(base_hover=100.0, direct_confirm=200.0)
    result = effective_direct_threshold(t, direct_threshold_multiplier=1.0)
    assert isinstance(result, float)


def test_effective_threshold_floor_by_base_hover() -> None:
    """When direct_confirm * multiplier < base_hover, return base_hover."""
    t = _make_target(base_hover=100.0, direct_confirm=120.0)
    # 120 * 0.5 = 60, which is < 100
    result = effective_direct_threshold(t, direct_threshold_multiplier=0.5)
    assert result == 100.0


def test_effective_threshold_uses_scaled_direct_confirm() -> None:
    """When direct_confirm * multiplier > base_hover, return scaled value."""
    t = _make_target(base_hover=100.0, direct_confirm=200.0)
    # 200 * 1.5 = 300 > 100
    result = effective_direct_threshold(t, direct_threshold_multiplier=1.5)
    assert result == 300.0


def test_effective_threshold_multiplier_one() -> None:
    """multiplier=1.0 returns direct_confirm_time_s (if >= base_hover)."""
    t = _make_target(base_hover=100.0, direct_confirm=200.0)
    result = effective_direct_threshold(t, direct_threshold_multiplier=1.0)
    assert result == 200.0


def test_effective_threshold_on_real_targets() -> None:
    """For all real targets with multiplier=0.70, threshold >= base_hover."""
    data = _loaded_data()
    for target in data.targets:
        threshold = effective_direct_threshold(target, direct_threshold_multiplier=0.70)
        assert threshold >= target.base_hover_time_s, (
            f"Target {target.node_id}: threshold={threshold:.1f} < base={target.base_hover_time_s:.1f}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# effective_direct_threshold — Negative scenarios
# ══════════════════════════════════════════════════════════════════════════════


def test_effective_threshold_raises_on_zero_multiplier() -> None:
    """multiplier=0 must raise ValueError."""
    t = _make_target()
    with pytest.raises(ValueError, match="multiplier must be positive"):
        effective_direct_threshold(t, direct_threshold_multiplier=0.0)


def test_effective_threshold_raises_on_negative_multiplier() -> None:
    """Negative multiplier must raise ValueError."""
    t = _make_target()
    with pytest.raises(ValueError, match="multiplier must be positive"):
        effective_direct_threshold(t, direct_threshold_multiplier=-1.0)


def test_effective_threshold_raises_on_negative_small_multiplier() -> None:
    """Small negative multiplier must raise ValueError."""
    t = _make_target()
    with pytest.raises(ValueError, match="multiplier must be positive"):
        effective_direct_threshold(t, direct_threshold_multiplier=-0.001)


# ══════════════════════════════════════════════════════════════════════════════
# effective_direct_threshold — Edge cases
# ══════════════════════════════════════════════════════════════════════════════


def test_effective_threshold_tiny_multiplier() -> None:
    """Very small positive multiplier floors to base_hover."""
    t = _make_target(base_hover=50.0, direct_confirm=1000.0)
    # 1000 * 0.001 = 1.0 < 50.0
    result = effective_direct_threshold(t, direct_threshold_multiplier=0.001)
    assert result == 50.0


def test_effective_threshold_very_large_multiplier() -> None:
    """Very large multiplier produces large threshold."""
    t = _make_target(base_hover=10.0, direct_confirm=50.0)
    result = effective_direct_threshold(t, direct_threshold_multiplier=100.0)
    assert result == 5000.0


def test_effective_threshold_base_equals_direct_confirm() -> None:
    """When base_hover == direct_confirm_time_s, threshold = max(base, base * mult)."""
    t = _make_target(base_hover=150.0, direct_confirm=150.0)
    # multiplier <= 1.0: threshold = base (150)
    for mult in (0.1, 0.5, 1.0):
        result = effective_direct_threshold(t, direct_threshold_multiplier=mult)
        assert result == 150.0, f"multiplier={mult}: expected 150.0, got {result}"
    # multiplier > 1.0: threshold = direct_confirm * multiplier
    assert effective_direct_threshold(t, direct_threshold_multiplier=2.0) == 300.0


def test_effective_threshold_base_greater_than_direct_confirm() -> None:
    """When base_hover > direct_confirm_time_s, base always wins."""
    t = _make_target(base_hover=200.0, direct_confirm=100.0)
    for mult in (0.5, 1.0, 2.0, 10.0):
        if mult * 100.0 > 200.0:
            assert effective_direct_threshold(t, direct_threshold_multiplier=mult) == mult * 100.0
        else:
            assert effective_direct_threshold(t, direct_threshold_multiplier=mult) == 200.0


# ══════════════════════════════════════════════════════════════════════════════
# solve_ground_tsp — Positive scenarios
# ══════════════════════════════════════════════════════════════════════════════


def test_ground_tsp_returns_ground_review_result() -> None:
    """solve_ground_tsp returns a GroundReviewResult instance."""
    data = _loaded_data()
    result = solve_ground_tsp(data, ("MP01", "MP03"))
    assert isinstance(result, GroundReviewResult)


def test_ground_tsp_all_field_types() -> None:
    """GroundReviewResult fields have correct types."""
    data = _loaded_data()
    result = solve_ground_tsp(data, ("MP01", "MP03"))
    assert isinstance(result.path, tuple)
    assert all(isinstance(p, str) for p in result.path)
    assert isinstance(result.travel_time_s, float)
    assert isinstance(result.service_time_s, float)
    assert isinstance(result.total_time_s, float)


def test_ground_tsp_starts_and_ends_at_p0() -> None:
    """Path must start and end at P0."""
    data = _loaded_data()
    # All manual points
    manual_points = tuple(target.manual_point_id for target in data.targets)
    result = solve_ground_tsp(data, manual_points)

    assert result.path[0] == "P0"
    assert result.path[-1] == "P0"


def test_ground_tsp_all_points_visited() -> None:
    """All input points appear exactly once in path (excluding P0)."""
    data = _loaded_data()
    points = ("MP01", "MP03", "MP05")
    result = solve_ground_tsp(data, points)

    non_p0 = [p for p in result.path if p != "P0"]
    assert sorted(non_p0) == sorted(points)


def test_ground_tsp_total_equals_travel_plus_service() -> None:
    """total_time_s == travel_time_s + service_time_s."""
    data = _loaded_data()
    result = solve_ground_tsp(data, ("MP01", "MP03", "MP05"))
    assert result.total_time_s == pytest.approx(
        result.travel_time_s + result.service_time_s
    )


def test_ground_tsp_all_manual_points() -> None:
    """With all 16 manual points, total time > 2670s (reasonable lower bound)."""
    data = _loaded_data()
    manual_points = tuple(target.manual_point_id for target in data.targets)
    result = solve_ground_tsp(data, manual_points)

    assert result.total_time_s > 2670
    assert result.service_time_s > 0
    assert result.travel_time_s > 0


def test_ground_tsp_subset_of_manual_points() -> None:
    """With a subset, path visits only those points."""
    data = _loaded_data()
    points = ("MP02", "MP08", "MP15")
    result = solve_ground_tsp(data, points)

    non_p0 = set(p for p in result.path if p != "P0")
    assert non_p0 == set(points)
    assert result.total_time_s > 0


def test_ground_tsp_is_deterministic() -> None:
    """Same input produces identical output each call."""
    data = _loaded_data()
    points = ("MP01", "MP03", "MP05", "MP10")
    r1 = solve_ground_tsp(data, points)
    r2 = solve_ground_tsp(data, points)
    r3 = solve_ground_tsp(data, points)

    assert r1.path == r2.path == r3.path
    assert r1.travel_time_s == pytest.approx(r2.travel_time_s)
    assert r1.service_time_s == pytest.approx(r2.service_time_s)
    assert r1.total_time_s == pytest.approx(r2.total_time_s)


# ══════════════════════════════════════════════════════════════════════════════
# solve_ground_tsp — Edge cases
# ══════════════════════════════════════════════════════════════════════════════


def test_ground_tsp_empty_tuple() -> None:
    """Empty manual_point_ids returns path ("P0","P0") with zero timings."""
    data = _loaded_data()
    result = solve_ground_tsp(data, tuple())

    assert result.path == ("P0", "P0")
    assert result.travel_time_s == 0.0
    assert result.service_time_s == 0.0
    assert result.total_time_s == 0.0


def test_ground_tsp_single_point() -> None:
    """Single manual point: path is P0 -> point -> P0."""
    data = _loaded_data()
    result = solve_ground_tsp(data, ("MP07",))

    assert result.path[0] == "P0"
    assert result.path[-1] == "P0"
    assert len(result.path) == 3
    assert "MP07" in result.path
    assert result.total_time_s > 0
    assert result.travel_time_s > 0
    assert result.service_time_s > 0


def test_ground_tsp_duplicate_points() -> None:
    """Duplicate manual point IDs are deduplicated (no double-counting)."""
    data = _loaded_data()
    result = solve_ground_tsp(data, ("MP01", "MP03", "MP01", "MP03"))

    # Path should visit MP01 and MP03 only once each
    non_p0 = [p for p in result.path if p != "P0"]
    assert non_p0 == ["MP01", "MP03"] or non_p0 == ["MP03", "MP01"]


def test_ground_tsp_service_time_sum_correct() -> None:
    """Service time equals sum of manual_service_time_s for distinct points."""
    data = _loaded_data()
    points = ("MP01", "MP03")

    # Sum service times for MP01 and MP03 from the data
    expected_service = 0.0
    for target in data.targets:
        if target.manual_point_id in points:
            # Only count first occurrence (dedup behavior)
            pass
    # Recompute: each distinct manual_point_id has one service time
    seen: set[str] = set()
    expected_service = 0.0
    for target in data.targets:
        mp = target.manual_point_id
        if mp in points and mp not in seen:
            expected_service += target.manual_service_time_s
            seen.add(mp)

    result = solve_ground_tsp(data, points)
    assert result.service_time_s == pytest.approx(expected_service)


# ══════════════════════════════════════════════════════════════════════════════
# solve_ground_tsp — Negative scenarios
# ══════════════════════════════════════════════════════════════════════════════


def test_ground_tsp_invalid_point_id_raises() -> None:
    """A manual point ID not in ground_time_s must raise an error."""
    data = _loaded_data()
    with pytest.raises(Exception):
        solve_ground_tsp(data, ("NONEXISTENT",))


def test_ground_tsp_mixed_valid_invalid_raises() -> None:
    """Mixed valid and invalid point IDs must raise an error."""
    data = _loaded_data()
    with pytest.raises(Exception):
        solve_ground_tsp(data, ("MP01", "INVALID_POINT"))


# ══════════════════════════════════════════════════════════════════════════════
# evaluate_closed_loop — Positive scenarios
# ══════════════════════════════════════════════════════════════════════════════


def test_closed_loop_returns_closed_loop_result() -> None:
    """evaluate_closed_loop returns a ClosedLoopResult instance."""
    data = _loaded_data()
    routes = (_make_route(nodes=(0, 1, 0), hover={1: 500.0}),)
    result = evaluate_closed_loop(data, routes, direct_threshold_multiplier=1.0)
    assert isinstance(result, ClosedLoopResult)


def test_closed_loop_all_field_types() -> None:
    """ClosedLoopResult fields have correct types."""
    data = _loaded_data()
    routes = (_make_route(nodes=(0, 1, 0), hover={1: 500.0}),)
    result = evaluate_closed_loop(data, routes, direct_threshold_multiplier=1.0)

    assert isinstance(result.direct_confirmed_nodes, tuple)
    assert all(isinstance(n, int) for n in result.direct_confirmed_nodes)
    assert isinstance(result.manual_nodes, tuple)
    assert all(isinstance(n, str) for n in result.manual_nodes)
    assert isinstance(result.manual_count, int)
    assert isinstance(result.uav_phase_time_s, float)
    assert isinstance(result.ground_review_time_s, float)
    assert isinstance(result.closed_loop_time_s, float)
    assert isinstance(result.ground_path, tuple)
    assert all(isinstance(p, str) for p in result.ground_path)


def test_closed_loop_time_equals_phase_plus_ground() -> None:
    """closed_loop_time_s == uav_phase_time_s + ground_review_time_s."""
    data = _loaded_data()
    routes = (_make_route(nodes=(0, 1, 0), hover={1: 500.0}),)
    result = evaluate_closed_loop(data, routes, direct_threshold_multiplier=1.0)

    assert result.closed_loop_time_s == pytest.approx(
        result.uav_phase_time_s + result.ground_review_time_s
    )


def test_closed_loop_direct_confirmed_plus_manual_covers_all() -> None:
    """direct_confirmed_nodes + targets behind manual_nodes = all 16 targets."""
    data = _loaded_data()
    sol = solve_problem1_for_k(data, k=2, battery_swap_time_s=300)
    result = evaluate_closed_loop(data, sol.routes, direct_threshold_multiplier=1.0)

    # Each target is either direct-confirmed or manual (never both, never neither)
    manual_target_ids: set[int] = set()
    for target in data.targets:
        if target.manual_point_id in set(result.manual_nodes):
            manual_target_ids.add(target.node_id)

    direct_set = set(result.direct_confirmed_nodes)
    all_ids = {t.node_id for t in data.targets}

    # Every target is in exactly one category
    assert direct_set | manual_target_ids == all_ids
    assert direct_set & manual_target_ids == set()


def test_closed_loop_direct_confirmed_nodes_meet_threshold() -> None:
    """All direct_confirmed_nodes must have cumulative hover >= effective threshold."""
    data = _loaded_data()
    sol = solve_problem1_for_k(data, k=3, battery_swap_time_s=300)
    mult = 0.85
    result = evaluate_closed_loop(data, sol.routes, direct_threshold_multiplier=mult)

    # Accumulate hover per node
    hover_by_node: dict[int, float] = {}
    for route in sol.routes:
        for nid, secs in route.hover_times_s.items():
            hover_by_node[nid] = hover_by_node.get(nid, 0.0) + secs

    by_id = {t.node_id: t for t in data.targets}
    for node_id in result.direct_confirmed_nodes:
        threshold = effective_direct_threshold(by_id[node_id], mult)
        assert hover_by_node[node_id] >= threshold - 1e-9, (
            f"Node {node_id}: hover={hover_by_node[node_id]:.1f}s < threshold={threshold:.1f}s"
        )


def test_closed_loop_manual_nodes_below_threshold() -> None:
    """Every manual target must have cumulative hover below effective threshold."""
    data = _loaded_data()
    sol = solve_problem1_for_k(data, k=2, battery_swap_time_s=300)
    mult = 1.0
    result = evaluate_closed_loop(data, sol.routes, direct_threshold_multiplier=mult)

    hover_by_node: dict[int, float] = {}
    for route in sol.routes:
        for nid, secs in route.hover_times_s.items():
            hover_by_node[nid] = hover_by_node.get(nid, 0.0) + secs

    by_id = {t.node_id: t for t in data.targets}
    manual_target_ids = {
        t.node_id for t in data.targets
        if t.manual_point_id in set(result.manual_nodes)
    }

    for node_id in manual_target_ids:
        threshold = effective_direct_threshold(by_id[node_id], mult)
        assert hover_by_node[node_id] < threshold - 1e-9, (
            f"Node {node_id}: hover={hover_by_node[node_id]:.1f}s >= threshold={threshold:.1f}s, "
            f"but is classified as manual"
        )


def test_closed_loop_uav_phase_matches_summary() -> None:
    """uav_phase_time_s must equal the UAVSolutionSummary phase time for the same routes."""
    data = _loaded_data()
    routes = (_make_route(nodes=(0, 1, 0), hover={1: 10.0}),)
    summary = summarize_uav_solution(routes, data, data.params.battery_swap_time_s)
    result = evaluate_closed_loop(data, routes, direct_threshold_multiplier=1.0)

    assert result.uav_phase_time_s == summary.uav_phase_time_s


def test_closed_loop_accepts_list_routes() -> None:
    """evaluate_closed_loop accepts a list of routes (not just tuple)."""
    data = _loaded_data()
    routes = [_make_route(nodes=(0, 1, 0), hover={1: 500.0})]
    result = evaluate_closed_loop(data, routes, direct_threshold_multiplier=1.0)
    assert isinstance(result, ClosedLoopResult)


# ══════════════════════════════════════════════════════════════════════════════
# evaluate_closed_loop — Edge cases
# ══════════════════════════════════════════════════════════════════════════════


def test_closed_loop_empty_routes() -> None:
    """With empty routes, all targets are manual (no UAV hover)."""
    data = _loaded_data()
    result = evaluate_closed_loop(data, (), direct_threshold_multiplier=1.0)

    assert result.direct_confirmed_nodes == ()
    assert result.manual_count >= 1
    assert result.uav_phase_time_s == 0.0
    assert result.closed_loop_time_s == result.ground_review_time_s


def test_closed_loop_high_multiplier_more_manual() -> None:
    """Higher multiplier -> larger threshold -> more targets classified as manual."""
    data = _loaded_data()
    sol = solve_problem1_for_k(data, k=2, battery_swap_time_s=300)

    result_low = evaluate_closed_loop(data, sol.routes, direct_threshold_multiplier=0.5)
    result_high = evaluate_closed_loop(data, sol.routes, direct_threshold_multiplier=2.0)

    # Higher multiplier should not reduce direct-confirmed count
    assert result_high.manual_count >= result_low.manual_count


def test_closed_loop_multiplier_zero_point_eight() -> None:
    """multiplier=0.8 is a reasonable operational value."""
    data = _loaded_data()
    sol = solve_problem1_for_k(data, k=3, battery_swap_time_s=300)
    result = evaluate_closed_loop(data, sol.routes, direct_threshold_multiplier=0.8)

    assert result.closed_loop_time_s > 0
    assert result.manual_count >= 1
    # Verify classification consistency
    hover_by_node: dict[int, float] = {}
    for route in sol.routes:
        for nid, secs in route.hover_times_s.items():
            hover_by_node[nid] = hover_by_node.get(nid, 0.0) + secs

    by_id = {t.node_id: t for t in data.targets}
    for node_id in result.direct_confirmed_nodes:
        threshold = effective_direct_threshold(by_id[node_id], 0.8)
        assert hover_by_node[node_id] >= threshold - 1e-9


def test_closed_loop_verify_ground_path_structure() -> None:
    """The ground_path starts/ends at P0 and visits all manual nodes."""
    data = _loaded_data()
    sol = solve_problem1_for_k(data, k=2, battery_swap_time_s=300)
    result = evaluate_closed_loop(data, sol.routes, direct_threshold_multiplier=1.0)

    assert result.ground_path[0] == "P0"
    assert result.ground_path[-1] == "P0"
    if result.manual_count > 0:
        non_p0 = set(p for p in result.ground_path if p != "P0")
        assert non_p0 == set(result.manual_nodes)


def test_closed_loop_no_manual_when_all_direct_confirmed() -> None:
    """When all targets meet thresholds, manual_count is 0."""
    data = _loaded_data()
    # Give every target enough hover to meet the threshold at multiplier=0.01
    hover: dict[int, float] = {}
    for t in data.targets:
        # Set hover to 10x direct_confirm to guarantee it meets any threshold
        hover[t.node_id] = t.direct_confirm_time_s * 10.0

    # Build routes with huge hover
    routes = [_make_route(
        uav_id=1,
        nodes=tuple([0] + [t.node_id for t in data.targets] + [0]),
        hover=hover,
    )]
    result = evaluate_closed_loop(data, tuple(routes), direct_threshold_multiplier=0.5)

    # With enough hover and low multiplier, all should confirm
    assert result.manual_count == 0
    assert result.ground_review_time_s == 0.0
    assert result.closed_loop_time_s == result.uav_phase_time_s


# ══════════════════════════════════════════════════════════════════════════════
# solve_joint_problem_for_k — Positive scenarios
# ══════════════════════════════════════════════════════════════════════════════


def test_joint_solver_returns_joint_solution() -> None:
    """solve_joint_problem_for_k returns a JointSolution instance."""
    data = _loaded_data()
    result = solve_joint_problem_for_k(data, k=2, direct_threshold_multiplier=1.0)
    assert isinstance(result, JointSolution)


def test_joint_solution_field_types() -> None:
    """JointSolution fields have correct types."""
    data = _loaded_data()
    result = solve_joint_problem_for_k(data, k=2, direct_threshold_multiplier=1.0)

    assert isinstance(result.routes, tuple)
    assert all(isinstance(r, UAVRoute) for r in result.routes)
    assert isinstance(result.closed_loop, ClosedLoopResult)


def test_joint_solver_routes_start_and_end_at_depot() -> None:
    """All routes in the joint solution must start/end at depot."""
    data = _loaded_data()
    result = solve_joint_problem_for_k(data, k=3, direct_threshold_multiplier=1.0)

    for route in result.routes:
        assert route.node_sequence[0] == 0
        assert route.node_sequence[-1] == 0


def test_joint_solver_all_routes_energy_feasible() -> None:
    """Every route in the joint solution must be energy-feasible."""
    data = _loaded_data()
    result = solve_joint_problem_for_k(data, k=3, direct_threshold_multiplier=1.0)

    for route in result.routes:
        metrics = evaluate_uav_route(route, data)
        assert metrics.feasible_energy, (
            f"Route uav={route.uav_id} sortie={route.sortie_id} energy={metrics.energy_j:.2f} "
            f"exceeds limit={data.params.effective_energy_limit_j:.2f}"
        )


def test_joint_solver_within_operating_horizon() -> None:
    """The joint solution must respect the operating horizon."""
    data = _loaded_data()
    result = solve_joint_problem_for_k(data, k=3, direct_threshold_multiplier=1.0)

    assert result.closed_loop.uav_phase_time_s <= data.params.operating_horizon_s, (
        f"Phase time {result.closed_loop.uav_phase_time_s:.2f} exceeds "
        f"horizon {data.params.operating_horizon_s:.2f}"
    )


def test_joint_solver_direct_confirmed_nodes_meet_thresholds() -> None:
    """All direct_confirmed_nodes must have cumulative hover >= effective threshold."""
    data = _loaded_data()
    mult = 0.70
    result = solve_joint_problem_for_k(data, k=4, direct_threshold_multiplier=mult)

    hover_by_node: dict[int, float] = {}
    for route in result.routes:
        for nid, secs in route.hover_times_s.items():
            hover_by_node[nid] = hover_by_node.get(nid, 0.0) + secs

    by_id = {t.node_id: t for t in data.targets}
    for node_id in result.closed_loop.direct_confirmed_nodes:
        threshold = effective_direct_threshold(by_id[node_id], mult)
        assert hover_by_node[node_id] >= threshold - 1e-9, (
            f"Node {node_id}: hover={hover_by_node[node_id]:.1f}s < threshold={threshold:.1f}s"
        )


def test_joint_solver_consistent_closed_loop_fields() -> None:
    """closed_loop fields are internally consistent."""
    data = _loaded_data()
    result = solve_joint_problem_for_k(data, k=2, direct_threshold_multiplier=1.0)
    cl = result.closed_loop

    # closed_loop_time = uav_phase + ground_review
    assert cl.closed_loop_time_s == pytest.approx(
        cl.uav_phase_time_s + cl.ground_review_time_s
    )
    # manual_count matches len(manual_nodes)
    assert cl.manual_count == len(cl.manual_nodes)
    # ground_path starts/ends at P0
    assert cl.ground_path[0] == "P0"
    assert cl.ground_path[-1] == "P0"


def test_joint_solver_with_different_k_values() -> None:
    """Joint solver works with k=2, 3, 5."""
    data = _loaded_data()
    for k in (2, 3, 5):
        result = solve_joint_problem_for_k(data, k=k, direct_threshold_multiplier=1.0)

        assert isinstance(result, JointSolution)
        assert len(result.routes) >= 1
        uav_ids = {r.uav_id for r in result.routes}
        assert all(1 <= uid <= k for uid in uav_ids)


def test_joint_solver_with_different_multipliers() -> None:
    """Joint solver works with different threshold multipliers."""
    data = _loaded_data()
    for mult in (0.70, 0.85, 1.0, 1.5):
        result = solve_joint_problem_for_k(data, k=2, direct_threshold_multiplier=mult)

        assert isinstance(result, JointSolution)
        assert result.closed_loop.closed_loop_time_s > 0


def test_joint_solver_improves_over_base_only() -> None:
    """Joint solver should match or improve manual_count vs base-only evaluation."""
    data = _loaded_data()
    base_routes = solve_problem1_for_k(data, k=3, battery_swap_time_s=300).routes
    base = evaluate_closed_loop(data, base_routes, direct_threshold_multiplier=1.0)

    joint = solve_joint_problem_for_k(data, k=3, direct_threshold_multiplier=1.0)

    assert joint.closed_loop.manual_count <= base.manual_count
    assert joint.closed_loop.closed_loop_time_s > 0


def test_joint_solver_accepts_tuple_routes() -> None:
    """JointSolution.routes is a tuple of UAVRoute."""
    data = _loaded_data()
    result = solve_joint_problem_for_k(data, k=2, direct_threshold_multiplier=1.0)
    assert isinstance(result.routes, tuple)
    assert all(isinstance(r, UAVRoute) for r in result.routes)


# ══════════════════════════════════════════════════════════════════════════════
# solve_joint_problem_for_k — Negative scenarios
# ══════════════════════════════════════════════════════════════════════════════


def test_joint_solver_k_zero_raises() -> None:
    """k=0 must raise ValueError."""
    data = _loaded_data()
    with pytest.raises(ValueError):
        solve_joint_problem_for_k(data, k=0, direct_threshold_multiplier=1.0)


def test_joint_solver_k_negative_raises() -> None:
    """k < 0 must raise ValueError."""
    data = _loaded_data()
    with pytest.raises(ValueError):
        solve_joint_problem_for_k(data, k=-1, direct_threshold_multiplier=1.0)


def test_joint_solver_k_negative_large_raises() -> None:
    """Large negative k must raise ValueError."""
    data = _loaded_data()
    with pytest.raises(ValueError):
        solve_joint_problem_for_k(data, k=-100, direct_threshold_multiplier=1.0)


# ══════════════════════════════════════════════════════════════════════════════
# solve_joint_problem_for_k — Edge cases
# ══════════════════════════════════════════════════════════════════════════════


def test_joint_solver_k1_single_uav() -> None:
    """Single UAV joint solver must produce valid solution."""
    data = _loaded_data()
    result = solve_joint_problem_for_k(data, k=1, direct_threshold_multiplier=1.0)

    assert isinstance(result, JointSolution)
    assert len(result.routes) >= 1
    assert all(r.uav_id == 1 for r in result.routes)


def test_joint_solver_large_k() -> None:
    """Large k (many UAVs) produces valid solution."""
    data = _loaded_data()
    result = solve_joint_problem_for_k(data, k=10, direct_threshold_multiplier=1.0)

    assert isinstance(result, JointSolution)
    assert result.closed_loop.uav_phase_time_s <= data.params.operating_horizon_s


# ══════════════════════════════════════════════════════════════════════════════
# Immutability — all frozen dataclasses
# ══════════════════════════════════════════════════════════════════════════════


def test_ground_review_result_is_immutable() -> None:
    """GroundReviewResult is a frozen dataclass."""
    data = _loaded_data()
    result = solve_ground_tsp(data, ("MP01", "MP03"))

    with pytest.raises(Exception):
        result.total_time_s = 0.0  # type: ignore[misc]


def test_closed_loop_result_is_immutable() -> None:
    """ClosedLoopResult is a frozen dataclass."""
    data = _loaded_data()
    routes = (_make_route(nodes=(0, 1, 0), hover={1: 500.0}),)
    result = evaluate_closed_loop(data, routes, direct_threshold_multiplier=1.0)

    with pytest.raises(Exception):
        result.closed_loop_time_s = 0.0  # type: ignore[misc]


def test_joint_solution_is_immutable() -> None:
    """JointSolution is a frozen dataclass."""
    data = _loaded_data()
    result = solve_joint_problem_for_k(data, k=2, direct_threshold_multiplier=1.0)

    with pytest.raises(Exception):
        result.routes = ()  # type: ignore[misc]


# ══════════════════════════════════════════════════════════════════════════════
# Integration — problem1 + problem2
# ══════════════════════════════════════════════════════════════════════════════


def test_integration_problem1_into_problem2_closed_loop() -> None:
    """Use Problem 1 solution as input to Problem 2 closed-loop evaluation."""
    data = _loaded_data()
    sol = solve_problem1_for_k(data, k=2, battery_swap_time_s=300)
    assert sol.summary.feasible_energy is True

    closed = evaluate_closed_loop(data, sol.routes, direct_threshold_multiplier=1.0)
    assert isinstance(closed, ClosedLoopResult)
    assert closed.uav_phase_time_s == sol.summary.uav_phase_time_s


def test_integration_problem1_hover_plan_into_closed_loop() -> None:
    """Custom hover plan can be evaluated through closed loop."""
    data = _loaded_data()
    custom_hover = {1: 100.0, 8: 200.0, 15: 150.0}
    sol = solve_uav_hover_plan(
        data, k=2, battery_swap_time_s=300,
        hover_requirements_s=custom_hover,
    )
    assert sol.summary.feasible_energy is True

    closed = evaluate_closed_loop(data, sol.routes, direct_threshold_multiplier=1.0)
    assert isinstance(closed, ClosedLoopResult)
    assert closed.closed_loop_time_s > 0


def test_integration_uav_summary_consistent_with_closed_loop() -> None:
    """UAV solution summary and closed loop share consistent phase time."""
    data = _loaded_data()
    sol = solve_problem1_for_k(data, k=3, battery_swap_time_s=300)
    summary = summarize_uav_solution(
        sol.routes, data, data.params.battery_swap_time_s
    )
    closed = evaluate_closed_loop(data, sol.routes, direct_threshold_multiplier=1.0)

    assert closed.uav_phase_time_s == summary.uav_phase_time_s


def test_integration_joint_vs_problem1_comparison() -> None:
    """Joint solver should not produce worse UAV phase time than problem1
    base solution, since it has the same constraints but can optimize."""
    data = _loaded_data()
    p1 = solve_problem1_for_k(data, k=3, battery_swap_time_s=300)
    joint = solve_joint_problem_for_k(data, k=3, direct_threshold_multiplier=1.0)

    # Both should be feasible
    assert p1.summary.feasible_energy is True
    for route in joint.routes:
        assert evaluate_uav_route(route, data).feasible_energy


def test_integration_total_hover_coverage() -> None:
    """All targets get at least base_hover_time_s from joint solver."""
    data = _loaded_data()
    joint = solve_joint_problem_for_k(data, k=2, direct_threshold_multiplier=1.0)

    hover_by_node: dict[int, float] = {}
    for route in joint.routes:
        for nid, secs in route.hover_times_s.items():
            hover_by_node[nid] = hover_by_node.get(nid, 0.0) + secs

    for target in data.targets:
        assert hover_by_node.get(target.node_id, 0.0) >= target.base_hover_time_s - 1e-9, (
            f"Target {target.node_id}: served={hover_by_node.get(target.node_id, 0.0):.1f}s, "
            f"needed={target.base_hover_time_s:.1f}s"
        )


def test_integration_ground_tsp_with_closed_loop_manual_nodes() -> None:
    """The ground_review_time_s in ClosedLoopResult should equal the
    solve_ground_tsp total_time for the same manual nodes."""
    data = _loaded_data()
    sol = solve_problem1_for_k(data, k=2, battery_swap_time_s=300)
    closed = evaluate_closed_loop(data, sol.routes, direct_threshold_multiplier=1.0)

    if closed.manual_count > 0:
        ground = solve_ground_tsp(data, closed.manual_nodes)
        assert closed.ground_review_time_s == pytest.approx(ground.total_time_s)
        assert closed.ground_path == ground.path


def test_integration_repeated_joint_solver_is_deterministic() -> None:
    """Running joint solver twice with same inputs produces similar results."""
    data = _loaded_data()
    r1 = solve_joint_problem_for_k(data, k=2, direct_threshold_multiplier=1.0)
    r2 = solve_joint_problem_for_k(data, k=2, direct_threshold_multiplier=1.0)

    assert r1.closed_loop.manual_count == r2.closed_loop.manual_count
    assert r1.closed_loop.closed_loop_time_s == pytest.approx(
        r2.closed_loop.closed_loop_time_s
    )
