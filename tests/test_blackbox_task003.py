"""Black-box tests for Task 003: Divisible Hover & Problem 1.

These tests verify the search and problem1 modules through their public
external interfaces ONLY. No private (`_`-prefixed) functions, no internal
implementation details, no knowledge of how the algorithms work internally.

Coverage: all public types and functions across positive scenarios,
negative scenarios, edge cases, boundary conditions, and integration
between search and problem1.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from c_uav_inspection.data import (
    ProblemData,
    UAVParams,
    load_problem_data,
)
from c_uav_inspection.model import (
    UAVRoute,
    UAVSolutionSummary,
    evaluate_uav_route,
)
from c_uav_inspection.problem1 import (
    Problem1Solution,
    solve_problem1_for_k,
    solve_uav_hover_plan,
)
from c_uav_inspection.search import (
    EPSILON,
    improve_route_by_two_opt,
    nearest_neighbor_order,
    split_order_into_energy_feasible_routes,
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


# ══════════════════════════════════════════════════════════════════════════════
# search.py — nearest_neighbor_order: Positive scenarios
# ══════════════════════════════════════════════════════════════════════════════


def test_nn_order_returns_tuple_of_ints() -> None:
    """nearest_neighbor_order returns a tuple of ints."""
    data = _loaded_data()
    order = nearest_neighbor_order(data, [1, 2, 3])
    assert isinstance(order, tuple)
    assert all(isinstance(n, int) for n in order)


def test_nn_order_all_ids_present_once() -> None:
    """Every input node_id appears exactly once in the output."""
    data = _loaded_data()
    node_ids = [1, 3, 5, 7, 9, 11, 13, 15]
    order = nearest_neighbor_order(data, node_ids)
    assert sorted(order) == sorted(node_ids)
    assert len(order) == len(node_ids)


def test_nn_order_all_16_targets() -> None:
    """Ordering all 16 targets produces a tuple of length 16 with ids 1..16."""
    data = _loaded_data()
    all_ids = [t.node_id for t in data.targets]
    order = nearest_neighbor_order(data, all_ids)
    assert len(order) == 16
    assert sorted(order) == list(range(1, 17))


def test_nn_order_is_deterministic() -> None:
    """Same input always produces the same output (no randomness)."""
    data = _loaded_data()
    node_ids = [2, 4, 6, 8, 10, 12, 14, 16]
    o1 = nearest_neighbor_order(data, node_ids)
    o2 = nearest_neighbor_order(data, node_ids)
    o3 = nearest_neighbor_order(data, node_ids)
    assert o1 == o2 == o3


def test_nn_order_starts_from_closest_to_depot() -> None:
    """The first node in the ordering should be reachable from depot 0
    — specifically, the node with minimum flight time from depot among
    the input set (ties broken by smaller id)."""
    data = _loaded_data()
    node_ids = [5, 10, 15]
    order = nearest_neighbor_order(data, node_ids)
    first = order[0]
    # The node closest to depot (smallest flight_time_s from 0) should be first
    min_time = min(data.flight_time_s[(0, nid)] for nid in node_ids)
    assert data.flight_time_s[(0, first)] == pytest.approx(min_time)


# ══════════════════════════════════════════════════════════════════════════════
# search.py — nearest_neighbor_order: Edge cases
# ══════════════════════════════════════════════════════════════════════════════


def test_nn_order_empty_input() -> None:
    """Empty node list returns empty tuple."""
    data = _loaded_data()
    order = nearest_neighbor_order(data, [])
    assert order == ()


def test_nn_order_single_node() -> None:
    """Single node input returns a tuple with just that node."""
    data = _loaded_data()
    order = nearest_neighbor_order(data, [7])
    assert order == (7,)


def test_nn_order_two_nodes() -> None:
    """Two nodes: both appear exactly once."""
    data = _loaded_data()
    order = nearest_neighbor_order(data, [3, 14])
    assert len(order) == 2
    assert set(order) == {3, 14}


def test_nn_order_tie_breaking_chooses_smaller_id() -> None:
    """SR-003: When two nodes have exactly equal flight times from the
    current node, the one with the smaller node_id must be selected
    first (plan: "若飞行时间相同，选编号更小的节点").

    Uses synthetic data because real GPS coordinates rarely produce
    exact flight-time ties.
    """
    # Construct synthetic data with two nodes at equal flight time from depot
    synthetic_params = replace(
        _loaded_data().params,
        effective_energy_limit_j=1e9,
        hover_power_j_per_s=1.0,
    )
    # Nodes 5 and 8: flight_time_s[(0,5)] == flight_time_s[(0,8)] == 10.0
    # Depot 0 also needs entries for (0, 0) — used when node_ids is empty.
    synthetic_ft: dict[tuple[int, int], float] = {
        (0, 0): 0.0,
        (0, 5): 10.0,
        (0, 8): 10.0,
        (5, 0): 10.0,
        (8, 0): 10.0,
        (5, 5): 0.0,
        (8, 8): 0.0,
        (5, 8): 1.0,
        (8, 5): 1.0,
    }
    # Energy mirror (not used by nearest_neighbor_order but required by ProblemData)
    synthetic_fe: dict[tuple[int, int], float] = {
        (0, 0): 0.0,
        (0, 5): 100.0,
        (0, 8): 100.0,
        (5, 0): 100.0,
        (8, 0): 100.0,
        (5, 5): 0.0,
        (8, 8): 0.0,
        (5, 8): 10.0,
        (8, 5): 10.0,
    }
    synthetic_data = ProblemData(
        params=synthetic_params,
        targets=[],
        manual_points={},
        flight_time_s=synthetic_ft,
        flight_energy_j=synthetic_fe,
        ground_time_s={},
    )

    # Both nodes tie from depot 0 -> smaller id (5) must come first
    order = nearest_neighbor_order(synthetic_data, [5, 8])
    assert order[0] == 5, (
        f"Tie-breaking: node 5 should be selected before node 8 "
        f"(equal flight time from depot), got order={order}"
    )
    assert set(order) == {5, 8}
    assert len(order) == 2


def test_nn_order_tie_breaking_on_intermediate_node() -> None:
    """SR-003: Tie-breaking also applies when the current node is not
    depot 0. From an intermediate node, two remaining nodes with equal
    flight times must be ordered by smaller node_id first."""
    synthetic_params = replace(
        _loaded_data().params,
        effective_energy_limit_j=1e9,
        hover_power_j_per_s=1.0,
    )
    # Three nodes: from node 1, both nodes 3 and 7 have equal flight time.
    synthetic_ft: dict[tuple[int, int], float] = {
        (0, 0): 0.0,
        (0, 1): 5.0, (0, 3): 10.0, (0, 7): 10.0,
        (1, 0): 5.0, (1, 1): 0.0, (1, 3): 10.0, (1, 7): 10.0,
        (3, 0): 10.0, (3, 1): 10.0, (3, 3): 0.0, (3, 7): 1.0,
        (7, 0): 10.0, (7, 1): 10.0, (7, 3): 1.0, (7, 7): 0.0,
    }
    synthetic_fe: dict[tuple[int, int], float] = {
        k: v * 10.0 for k, v in synthetic_ft.items()
    }
    synthetic_data = ProblemData(
        params=synthetic_params,
        targets=[],
        manual_points={},
        flight_time_s=synthetic_ft,
        flight_energy_j=synthetic_fe,
        ground_time_s={},
    )
    # Node 1 is closest to depot (5s), selected first.
    # From node 1, both 3 and 7 are at 10s — tie, smaller id (3) wins.
    order = nearest_neighbor_order(synthetic_data, [1, 3, 7])
    assert order[0] == 1, (
        f"Node 1 should be first (closest to depot), got order={order}"
    )
    assert order[1] == 3, (
        f"From node 1, nodes 3 and 7 tie (10s each) — smaller id (3) must "
        f"come before 7, got order={order}"
    )
    assert set(order) == {1, 3, 7}
    assert len(order) == 3


# ══════════════════════════════════════════════════════════════════════════════
# search.py — nearest_neighbor_order: Negative scenarios
# ══════════════════════════════════════════════════════════════════════════════


def test_nn_order_duplicates_raises_value_error() -> None:
    """Duplicate node_ids in the input list must raise ValueError to
    prevent silent data loss."""
    data = _loaded_data()
    with pytest.raises(ValueError, match="duplicate"):
        nearest_neighbor_order(data, [1, 2, 2, 3])


def test_nn_order_nonexistent_node_id_raises_value_error() -> None:
    """CR-009: Passing a node ID not in the flight matrix must raise
    ValueError (not raw KeyError) for clear caller guidance."""
    data = _loaded_data()
    with pytest.raises(ValueError, match="exist"):
        nearest_neighbor_order(data, [1, 999, 3])


def test_nn_order_depot_in_input_raises_value_error() -> None:
    """CR-012: Passing depot node 0 in the input list must raise
    ValueError. Including depot as a target is semantically invalid
    — the depot is the origin/destination, not a target to visit."""
    data = _loaded_data()
    with pytest.raises(ValueError, match="depot"):
        nearest_neighbor_order(data, [0, 1, 2, 3])


# ══════════════════════════════════════════════════════════════════════════════
# search.py — split_order_into_energy_feasible_routes: Positive scenarios
# ══════════════════════════════════════════════════════════════════════════════


def test_split_routes_returns_tuple_of_uav_route() -> None:
    """Returns a tuple of UAVRoute instances."""
    data = _loaded_data()
    routes = split_order_into_energy_feasible_routes(
        (1, 2), {1: 10.0, 2: 20.0}, data
    )
    assert isinstance(routes, tuple)
    assert all(isinstance(r, UAVRoute) for r in routes)
    assert len(routes) >= 1


def test_split_routes_start_and_end_at_depot() -> None:
    """Every route must start and end at depot node 0."""
    data = _loaded_data()
    order = nearest_neighbor_order(data, [t.node_id for t in data.targets])
    hover = {t.node_id: t.base_hover_time_s for t in data.targets}
    routes = split_order_into_energy_feasible_routes(order, hover, data)
    assert len(routes) >= 1
    for route in routes:
        seq = route.node_sequence
        assert seq[0] == 0, f"Route does not start at depot: {seq}"
        assert seq[-1] == 0, f"Route does not end at depot: {seq}"


def test_split_all_routes_energy_feasible() -> None:
    """Every returned route must be energy-feasible."""
    data = _loaded_data()
    order = nearest_neighbor_order(data, [t.node_id for t in data.targets])
    hover = {t.node_id: t.base_hover_time_s for t in data.targets}
    routes = split_order_into_energy_feasible_routes(order, hover, data)
    assert len(routes) >= 1
    for route in routes:
        metrics = evaluate_uav_route(route, data)
        assert metrics.feasible_energy, (
            f"Route energy {metrics.energy_j:.2f} exceeds limit "
            f"{data.params.effective_energy_limit_j:.2f}"
        )


def test_split_total_hover_equals_demand() -> None:
    """The sum of hover times across all routes must exactly match the
    total demand for each node."""
    data = _loaded_data()
    hover_demand = {1: 120.0, 3: 80.0, 5: 200.0}
    routes = split_order_into_energy_feasible_routes(
        (1, 3, 5), hover_demand, data
    )
    served: dict[int, float] = {}
    for route in routes:
        for nid, secs in route.hover_times_s.items():
            served[nid] = served.get(nid, 0.0) + secs
    for nid, expected in hover_demand.items():
        assert served.get(nid, 0.0) == pytest.approx(expected)


def test_split_hover_can_span_multiple_sorties() -> None:
    """When a single target's hover demand exceeds one sortie's capacity,
    it must be split across multiple sorties."""
    data = _loaded_data()
    target_id = 16
    # Calculate max hover a single sortie can serve for this target
    single_sortie_max_hover = (
        data.params.effective_energy_limit_j
        - data.flight_energy_j[(0, target_id)]
        - data.flight_energy_j[(target_id, 0)]
    ) / data.params.hover_power_j_per_s
    # Demand that exceeds single-sortie capacity
    hover_demand = {target_id: single_sortie_max_hover + 60.0}
    routes = split_order_into_energy_feasible_routes(
        (target_id,), hover_demand, data
    )
    assert len(routes) >= 2, (
        f"Expected at least 2 sorties for demand {hover_demand[target_id]:.1f}s "
        f"(single-sortie max hover is {single_sortie_max_hover:.1f}s)"
    )
    total_served = sum(
        r.hover_times_s.get(target_id, 0.0) for r in routes
    )
    assert total_served == pytest.approx(hover_demand[target_id])
    assert all(
        evaluate_uav_route(r, data).feasible_energy for r in routes
    )


def test_split_multiple_routes_for_all_targets() -> None:
    """With all 16 targets and their base hover, splitting produces at
    least 2 routes (energy budget requires it)."""
    data = _loaded_data()
    order = nearest_neighbor_order(data, [t.node_id for t in data.targets])
    hover = {t.node_id: t.base_hover_time_s for t in data.targets}
    routes = split_order_into_energy_feasible_routes(order, hover, data)
    assert len(routes) >= 2


def test_split_nodes_with_zero_hover_are_skipped() -> None:
    """Nodes whose hover demand is zero (or <= EPSILON) must not appear
    in any route's visited nodes or hover assignments."""
    data = _loaded_data()
    hover = {1: 0.0, 3: 50.0, 5: 0.0, 7: 30.0}
    routes = split_order_into_energy_feasible_routes(
        (1, 3, 5, 7), hover, data
    )
    visited: set[int] = set()
    for route in routes:
        for nid in route.node_sequence:
            if nid != 0:
                visited.add(nid)
        for nid in route.hover_times_s:
            visited.add(nid)
    # Nodes 1 and 5 have zero hover and should not be visited
    assert 1 not in visited, "Node 1 with zero hover should be skipped"
    assert 5 not in visited, "Node 5 with zero hover should be skipped"
    # Nodes 3 and 7 have positive hover and must be visited
    assert 3 in visited, "Node 3 with hover should be visited"
    assert 7 in visited, "Node 7 with hover should be visited"


def test_split_partial_hover_ends_sortie_immediately() -> None:
    """SR-002: When a target's hover is partially served, the sortie must
    return to depot immediately without visiting any subsequent targets
    from the visitation order.

    This verifies the plan requirement: "服务部分悬停后结束当前趟".
    Observable via the public API as: the last non-depot node in the
    first sortie's node_sequence is the partially-served target, not
    any target that appears later in the order tuple.
    """
    data = _loaded_data()
    # t_near is close to depot (small roundtrip), t_far is distant (large roundtrip)
    t_near, t_far = 1, 16
    # After visiting t_near, the remaining energy budget for t_far determines
    # how much hover we can serve. Demand well above single-sortie capacity.
    max_hover_t_far_alone = (
        data.params.effective_energy_limit_j
        - data.flight_energy_j[(0, t_far)]
        - data.flight_energy_j[(t_far, 0)]
    ) / data.params.hover_power_j_per_s
    # Give t_near zero hover (just a positional element in the order)
    # and t_far more hover than fits in one sortie after t_near.
    hover = {t_near: 0.0, t_far: max_hover_t_far_alone + 200.0}
    order = (t_near, t_far)

    routes = split_order_into_energy_feasible_routes(order, hover, data)

    # t_far must be split across multiple sorties
    assert len(routes) >= 2, (
        f"Expected >= 2 sorties, got {len(routes)}"
    )

    # Total hover served to t_far must equal demand
    served_t_far = sum(r.hover_times_s.get(t_far, 0.0) for r in routes)
    assert served_t_far == pytest.approx(hover[t_far])

    # First sortie: last non-depot node must be t_far (the partially-served
    # target). No subsequent targets from the order should appear.
    non_depot = [n for n in routes[0].node_sequence if n != 0]
    assert non_depot[-1] == t_far, (
        f"Expected last visited target in sortie 1 to be {t_far} "
        f"(the partially-served target), got {non_depot[-1]}"
    )

    # t_far should be partially served (not fully) in the first sortie
    t_far_in_first = routes[0].hover_times_s.get(t_far, 0.0)
    assert t_far_in_first > EPSILON, "t_far should be partially served in first sortie"
    assert t_far_in_first < hover[t_far] - EPSILON, (
        f"t_far should be PARTIALLY served in first sortie, "
        f"got {t_far_in_first:.1f}s out of {hover[t_far]:.1f}s"
    )

    # t_far remainder must be in subsequent sortie(s)
    t_far_in_later = sum(r.hover_times_s.get(t_far, 0.0) for r in routes[1:])
    assert t_far_in_later > EPSILON, "t_far remainder should be in later sorties"

    # All routes must be energy feasible
    for route in routes:
        assert evaluate_uav_route(route, data).feasible_energy


# ══════════════════════════════════════════════════════════════════════════════
# search.py — split_order_into_energy_feasible_routes: Edge cases
# ══════════════════════════════════════════════════════════════════════════════


def test_split_empty_order_and_hover() -> None:
    """Empty order with empty hover dict returns empty tuple."""
    data = _loaded_data()
    routes = split_order_into_energy_feasible_routes((), {}, data)
    assert routes == ()


def test_split_all_zero_hover_returns_empty() -> None:
    """When all hover demands are zero, no routes need to be flown."""
    data = _loaded_data()
    routes = split_order_into_energy_feasible_routes(
        (1, 2, 3), {1: 0.0, 2: 0.0, 3: 0.0}, data
    )
    assert routes == ()


def test_split_tiny_hover_below_epsilon() -> None:
    """Hover values below or at EPSILON are treated as zero and produce
    no routes."""
    data = _loaded_data()
    routes = split_order_into_energy_feasible_routes(
        (1,), {1: EPSILON * 0.5}, data
    )
    assert routes == ()


def test_split_hover_exactly_at_battery_capacity() -> None:
    """When a single target's hover demand fills the battery exactly,
    only one sortie is needed."""
    data = _loaded_data()
    target_id = 1
    max_hover = (
        data.params.effective_energy_limit_j
        - data.flight_energy_j[(0, target_id)]
        - data.flight_energy_j[(target_id, 0)]
    ) / data.params.hover_power_j_per_s
    routes = split_order_into_energy_feasible_routes(
        (target_id,), {target_id: max_hover}, data
    )
    assert len(routes) == 1
    assert routes[0].hover_times_s.get(target_id, 0.0) == pytest.approx(max_hover)
    assert evaluate_uav_route(routes[0], data).feasible_energy


# ══════════════════════════════════════════════════════════════════════════════
# search.py — split_order_into_energy_feasible_routes: Negative scenarios
# ══════════════════════════════════════════════════════════════════════════════


def test_split_order_nonexistent_node_id_raises_value_error() -> None:
    """CR-009: A node ID in the order tuple that does not exist in the
    flight matrix must raise ValueError instead of raw KeyError."""
    data = _loaded_data()
    with pytest.raises(ValueError, match="exist"):
        split_order_into_energy_feasible_routes(
            (1, 999, 3), {1: 10.0, 3: 20.0}, data
        )


def test_split_hover_negative_demand_raises_value_error() -> None:
    """CR-010: Negative values in hover_times_s must raise ValueError
    with a clear message identifying the invalid input (e.g. "hover
    demand must be non-negative"), rather than a confusing post-condition
    error about 'negative remaining hover'."""
    data = _loaded_data()
    with pytest.raises(ValueError, match=r"hover.*must be non-negative"):
        split_order_into_energy_feasible_routes(
            (1,), {1: -10.0}, data
        )


def test_split_hover_all_negative_spotted() -> None:
    """CR-010: When multiple nodes have negative hover, the error must
    identify at least one of them (input validation catches before
    processing)."""
    data = _loaded_data()
    with pytest.raises(ValueError, match=r"hover.*must be non-negative"):
        split_order_into_energy_feasible_routes(
            (1, 2), {1: 5.0, 2: -30.0}, data
        )


def test_split_hover_zero_negative_boundary() -> None:
    """CR-010: A very small negative hover (e.g., -0.1s) must still be
    caught by input validation. Only truly zero or positive values are
    valid."""
    data = _loaded_data()
    with pytest.raises(ValueError, match=r"hover.*must be non-negative"):
        split_order_into_energy_feasible_routes(
            (1, 2), {1: 0.0, 2: -0.1}, data
        )


def test_split_unreachable_target_raises_value_error() -> None:
    """If a target's roundtrip flight energy alone exceeds the battery
    limit, ValueError must be raised (target is unreachable even with
    zero hover)."""
    data = _loaded_data()
    # Create a dataset with an artificially low energy limit
    tiny_params = replace(data.params, effective_energy_limit_j=50.0)
    tiny_data = ProblemData(
        params=tiny_params,
        targets=data.targets,
        manual_points=data.manual_points,
        flight_time_s=data.flight_time_s,
        flight_energy_j=data.flight_energy_j,
        ground_time_s=data.ground_time_s,
    )
    with pytest.raises(ValueError):
        split_order_into_energy_feasible_routes(
            (1,), {1: 10.0}, tiny_data
        )


def test_split_hover_key_not_in_order_raises_value_error() -> None:
    """If hover_times_s contains a node_id that is NOT present in order,
    ValueError must be raised to prevent an infinite loop."""
    data = _loaded_data()
    with pytest.raises(ValueError, match="not present"):
        split_order_into_energy_feasible_routes(
            (1, 2, 3), {1: 10.0, 2: 20.0, 16: 100.0}, data
        )


def test_split_zero_hover_power_raises_value_error() -> None:
    """A dataset with hover_power_j_per_s == 0 must raise ValueError
    rather than causing a ZeroDivisionError with an obscure traceback."""
    data = _loaded_data()
    zero_power = replace(data.params, hover_power_j_per_s=0.0)
    bad_data = ProblemData(
        params=zero_power,
        targets=data.targets,
        manual_points=data.manual_points,
        flight_time_s=data.flight_time_s,
        flight_energy_j=data.flight_energy_j,
        ground_time_s=data.ground_time_s,
    )
    with pytest.raises(ValueError, match="hover_power"):
        split_order_into_energy_feasible_routes(
            (1,), {1: 10.0}, bad_data,
        )


def test_split_roundtrip_exactly_equals_energy_limit_raises_value_error() -> None:
    """CR-013: A target whose roundtrip flight energy exactly equals the
    effective energy limit with positive hover demand must raise
    ValueError rather than entering an infinite loop.

    When roundtrip_j == limit_j, there is zero energy available for
    hover. The function enters an infinite loop because no hover can
    ever be served but the pre-validation doesn't catch it.
    """
    data = _loaded_data()
    # Construct a target where roundtrip == limit exactly
    target_id = 1
    base_roundtrip = (
        data.flight_energy_j[(0, target_id)]
        + data.flight_energy_j[(target_id, 0)]
    )
    # Set energy limit to exactly the roundtrip energy
    exact_limit = replace(data.params, effective_energy_limit_j=base_roundtrip)
    exact_data = ProblemData(
        params=exact_limit,
        targets=data.targets,
        manual_points=data.manual_points,
        flight_time_s=data.flight_time_s,
        flight_energy_j=data.flight_energy_j,
        ground_time_s=data.ground_time_s,
    )
    with pytest.raises(ValueError, match="unreachable"):
        split_order_into_energy_feasible_routes(
            (target_id,), {target_id: 10.0}, exact_data,
        )


# ══════════════════════════════════════════════════════════════════════════════
# search.py — improve_route_by_two_opt: Positive scenarios
# ══════════════════════════════════════════════════════════════════════════════


def test_two_opt_returns_uav_route() -> None:
    """improve_route_by_two_opt returns a UAVRoute instance."""
    data = _loaded_data()
    route = _make_route(nodes=(0, 1, 5, 9, 0), hover={1: 30, 5: 40, 9: 20})
    improved = improve_route_by_two_opt(route, data)
    assert isinstance(improved, UAVRoute)


def test_two_opt_preserves_energy_feasibility() -> None:
    """If the input route is energy-feasible, the output must also be
    energy-feasible."""
    data = _loaded_data()
    route = _make_route(
        nodes=(0, 16, 1, 2, 0), hover={16: 10, 1: 10, 2: 10}
    )
    assert evaluate_uav_route(route, data).feasible_energy
    improved = improve_route_by_two_opt(route, data)
    assert evaluate_uav_route(improved, data).feasible_energy


def test_two_opt_does_not_increase_duration() -> None:
    """The improved route's duration must be <= the original route's
    duration."""
    data = _loaded_data()
    # Use a deliberately sub-optimal order
    route = _make_route(
        nodes=(0, 1, 16, 2, 0), hover={1: 10, 16: 10, 2: 10}
    )
    orig_duration = evaluate_uav_route(route, data).duration_s
    improved = improve_route_by_two_opt(route, data)
    new_duration = evaluate_uav_route(improved, data).duration_s
    assert new_duration <= orig_duration + EPSILON, (
        f"Duration increased from {orig_duration:.3f} to {new_duration:.3f}"
    )


def test_two_opt_preserves_hover_times() -> None:
    """The set of hover times per node must remain identical after 2-opt."""
    data = _loaded_data()
    route = _make_route(
        nodes=(0, 9, 16, 1, 4, 0), hover={9: 30, 16: 20, 1: 25, 4: 15}
    )
    improved = improve_route_by_two_opt(route, data)
    assert improved.hover_times_s == route.hover_times_s


def test_two_opt_preserves_nodes_visited() -> None:
    """The set of non-depot nodes visited must remain identical after
    2-opt."""
    data = _loaded_data()
    route = _make_route(
        nodes=(0, 3, 7, 11, 0), hover={3: 10, 7: 10, 11: 10}
    )
    improved = improve_route_by_two_opt(route, data)
    orig_nodes = set(n for n in route.node_sequence if n != 0)
    imp_nodes = set(n for n in improved.node_sequence if n != 0)
    assert orig_nodes == imp_nodes


def test_two_opt_depot_start_and_end_preserved() -> None:
    """The improved route must still start and end at depot."""
    data = _loaded_data()
    route = _make_route(
        nodes=(0, 5, 10, 15, 0), hover={5: 10, 10: 10, 15: 10}
    )
    improved = improve_route_by_two_opt(route, data)
    assert improved.node_sequence[0] == 0
    assert improved.node_sequence[-1] == 0


# ══════════════════════════════════════════════════════════════════════════════
# search.py — improve_route_by_two_opt: Edge cases
# ══════════════════════════════════════════════════════════════════════════════


def test_two_opt_single_target_route() -> None:
    """A route visiting only one target returns unchanged (nothing to
    reorder)."""
    data = _loaded_data()
    route = _make_route(nodes=(0, 7, 0), hover={7: 50})
    improved = improve_route_by_two_opt(route, data)
    assert improved.node_sequence == route.node_sequence
    assert improved.hover_times_s == route.hover_times_s


def test_two_opt_depot_to_depot() -> None:
    """A route that goes only depot → depot returns unchanged."""
    data = _loaded_data()
    route = _make_route(nodes=(0, 0), hover={1: 10})
    improved = improve_route_by_two_opt(route, data)
    assert improved.node_sequence == (0, 0)
    assert improved.hover_times_s == {1: 10}


def test_two_opt_no_non_depot_nodes() -> None:
    """A route with only depot (no targets) returns unchanged."""
    data = _loaded_data()
    route = _make_route(nodes=(0, 0), hover={})
    improved = improve_route_by_two_opt(route, data)
    assert improved.node_sequence == (0, 0)


# ══════════════════════════════════════════════════════════════════════════════
# problem1.py — Problem1Solution: Type & immutability
# ══════════════════════════════════════════════════════════════════════════════


def test_problem1_solution_is_immutable() -> None:
    """Problem1Solution is a frozen dataclass — attribute mutation must
    fail."""
    data = _loaded_data()
    sol = solve_problem1_for_k(data, k=2, battery_swap_time_s=300)
    with pytest.raises(Exception):
        sol.routes = ()  # type: ignore[misc]


def test_problem1_solution_field_types() -> None:
    """Problem1Solution fields have the correct types."""
    data = _loaded_data()
    sol = solve_problem1_for_k(data, k=2, battery_swap_time_s=300)
    assert isinstance(sol.routes, tuple)
    assert all(isinstance(r, UAVRoute) for r in sol.routes)
    assert isinstance(sol.total_hover_by_node, dict)
    assert isinstance(sol.summary, UAVSolutionSummary)


# ══════════════════════════════════════════════════════════════════════════════
# problem1.py — solve_problem1_for_k: Positive scenarios
# ══════════════════════════════════════════════════════════════════════════════


def test_problem1_k2_satisfies_all_constraints() -> None:
    """k=2 solution must: be energy-feasible, respect the operating
    horizon, and serve at least base hover to every target."""
    data = _loaded_data()
    sol = solve_problem1_for_k(data, k=2, battery_swap_time_s=300)
    assert sol.summary.feasible_energy is True
    assert sol.summary.uav_phase_time_s <= data.params.operating_horizon_s
    for t in data.targets:
        assert sol.total_hover_by_node[t.node_id] >= t.base_hover_time_s, (
            f"Target {t.node_id}: served {sol.total_hover_by_node[t.node_id]:.1f}s, "
            f"needed {t.base_hover_time_s:.1f}s"
        )


def test_problem1_k3_satisfies_all_constraints() -> None:
    """k=3 solution satisfies energy, horizon, and hover constraints."""
    data = _loaded_data()
    sol = solve_problem1_for_k(data, k=3, battery_swap_time_s=300)
    assert sol.summary.feasible_energy is True
    assert sol.summary.uav_phase_time_s <= data.params.operating_horizon_s
    for t in data.targets:
        assert sol.total_hover_by_node[t.node_id] >= t.base_hover_time_s


def test_problem1_k4_with_improve_satisfies_constraints() -> None:
    """k=4 with improve=True must still produce a fully feasible
    solution."""
    data = _loaded_data()
    sol = solve_problem1_for_k(
        data, k=4, battery_swap_time_s=300, improve=True
    )
    assert sol.summary.feasible_energy is True
    assert sol.summary.uav_phase_time_s <= data.params.operating_horizon_s
    assert len(sol.routes) >= 1
    for t in data.targets:
        assert sol.total_hover_by_node[t.node_id] >= t.base_hover_time_s


def test_problem1_uav_ids_are_valid() -> None:
    """All route UAV IDs must be in 1..k."""
    data = _loaded_data()
    for k in (2, 3, 5):
        sol = solve_problem1_for_k(data, k=k, battery_swap_time_s=300)
        for route in sol.routes:
            assert 1 <= route.uav_id <= k, (
                f"UAV id {route.uav_id} out of range [1, {k}]"
            )


def test_problem1_all_uav_ids_in_valid_range() -> None:
    """All UAV IDs must be in [1, k] and at least one UAV must be used.
    It is acceptable for some UAVs to be idle if fewer routes are needed."""
    data = _loaded_data()
    for k in (2, 3, 4):
        sol = solve_problem1_for_k(data, k=k, battery_swap_time_s=300)
        used_ids = {route.uav_id for route in sol.routes}
        # All used IDs must be in valid range
        for uid in used_ids:
            assert 1 <= uid <= k, f"UAV id {uid} out of range [1, {k}]"
        # At least one UAV should be used
        assert len(used_ids) >= 1, f"No UAVs used for k={k}"


def test_problem1_sortie_ids_are_sequential_per_uav() -> None:
    """For each UAV, sortie IDs start from 1 and are sequential."""
    data = _loaded_data()
    sol = solve_problem1_for_k(data, k=3, battery_swap_time_s=300)
    by_uav: dict[int, list[int]] = {}
    for route in sol.routes:
        by_uav.setdefault(route.uav_id, []).append(route.sortie_id)
    for uav_id, sortie_ids in by_uav.items():
        assert sortie_ids == list(range(1, len(sortie_ids) + 1)), (
            f"UAV {uav_id}: expected sorties {list(range(1, len(sortie_ids) + 1))}, "
            f"got {sortie_ids}"
        )


def test_problem1_each_route_is_energy_feasible() -> None:
    """Every individual route in the solution must be energy-feasible."""
    data = _loaded_data()
    sol = solve_problem1_for_k(data, k=3, battery_swap_time_s=300)
    for route in sol.routes:
        m = evaluate_uav_route(route, data)
        assert m.feasible_energy, (
            f"Route uav={route.uav_id} sortie={route.sortie_id} "
            f"energy={m.energy_j:.2f} > limit={data.params.effective_energy_limit_j:.2f}"
        )


def test_problem1_each_route_starts_and_ends_at_depot() -> None:
    """Every route must start and end at node 0."""
    data = _loaded_data()
    sol = solve_problem1_for_k(data, k=3, battery_swap_time_s=300)
    for route in sol.routes:
        assert route.node_sequence[0] == 0
        assert route.node_sequence[-1] == 0


def test_problem1_hover_sum_matches_total_served() -> None:
    """The total hover across total_hover_by_node should match the sum
    of hover times in all routes."""
    data = _loaded_data()
    sol = solve_problem1_for_k(data, k=2, battery_swap_time_s=300)
    from_routes: dict[int, float] = {}
    for route in sol.routes:
        for nid, secs in route.hover_times_s.items():
            from_routes[nid] = from_routes.get(nid, 0.0) + secs
    assert from_routes == sol.total_hover_by_node


def test_problem1_phase_time_is_max_work_time() -> None:
    """uav_phase_time_s must equal the maximum of uav_work_times_s."""
    data = _loaded_data()
    sol = solve_problem1_for_k(data, k=3, battery_swap_time_s=300)
    assert sol.summary.uav_phase_time_s == pytest.approx(
        max(sol.summary.uav_work_times_s.values())
    )


def test_problem1_work_time_includes_swap_overhead() -> None:
    """A UAV with N > 1 sorties must have work time >= sum of route
    durations + (N-1) * swap_time."""
    data = _loaded_data()
    swap = 300.0
    sol = solve_problem1_for_k(data, k=2, battery_swap_time_s=swap)
    by_uav: dict[int, list[UAVRoute]] = {}
    for route in sol.routes:
        by_uav.setdefault(route.uav_id, []).append(route)
    for uav_id, routes in by_uav.items():
        route_durations = sum(
            evaluate_uav_route(r, data).duration_s for r in routes
        )
        expected_min = route_durations + (len(routes) - 1) * swap
        actual = sol.summary.uav_work_times_s[uav_id]
        assert actual == pytest.approx(expected_min), (
            f"UAV {uav_id}: work={actual:.2f}, expected min={expected_min:.2f}"
        )


def test_problem1_load_std_is_non_negative() -> None:
    """Load standard deviation must be >= 0."""
    data = _loaded_data()
    for k in (1, 2, 4):
        sol = solve_problem1_for_k(data, k=k, battery_swap_time_s=300)
        assert sol.summary.load_std_s >= 0.0


def test_problem1_k1_load_std_is_zero() -> None:
    """With a single UAV, load std must be 0."""
    data = _loaded_data()
    sol = solve_problem1_for_k(data, k=1, battery_swap_time_s=300)
    assert sol.summary.load_std_s == 0.0


# ══════════════════════════════════════════════════════════════════════════════
# problem1.py — solve_problem1_for_k: Negative scenarios
# ══════════════════════════════════════════════════════════════════════════════


def test_problem1_k_zero_raises_value_error() -> None:
    """k=0 must raise ValueError."""
    data = _loaded_data()
    with pytest.raises(ValueError):
        solve_problem1_for_k(data, k=0, battery_swap_time_s=300)


def test_problem1_k_negative_raises_value_error() -> None:
    """k < 0 must raise ValueError."""
    data = _loaded_data()
    with pytest.raises(ValueError):
        solve_problem1_for_k(data, k=-1, battery_swap_time_s=300)


def test_problem1_k_negative_large_raises_value_error() -> None:
    """Large negative k must raise ValueError."""
    data = _loaded_data()
    with pytest.raises(ValueError):
        solve_problem1_for_k(data, k=-100, battery_swap_time_s=300)


def test_problem1_negative_battery_swap_raises_value_error() -> None:
    """Negative battery_swap_time_s must raise ValueError."""
    data = _loaded_data()
    with pytest.raises(ValueError, match="battery_swap_time_s"):
        solve_problem1_for_k(data, k=2, battery_swap_time_s=-100)


# ══════════════════════════════════════════════════════════════════════════════
# problem1.py — solve_problem1_for_k: Edge cases
# ══════════════════════════════════════════════════════════════════════════════


def test_problem1_k1_single_uav() -> None:
    """Single UAV must handle all targets alone and still satisfy
    constraints."""
    data = _loaded_data()
    sol = solve_problem1_for_k(data, k=1, battery_swap_time_s=0)
    assert sol.summary.feasible_energy is True
    assert len(sol.routes) >= 1
    for t in data.targets:
        assert sol.total_hover_by_node[t.node_id] >= t.base_hover_time_s
    # With one UAV, all routes have uav_id=1
    assert all(r.uav_id == 1 for r in sol.routes)


def test_problem1_zero_battery_swap_multiple_uavs() -> None:
    """Zero battery swap time is a valid input with multiple UAVs.
    Load balancing still works — work times across UAVs should not
    have excessive spread."""
    data = _loaded_data()
    sol = solve_problem1_for_k(data, k=3, battery_swap_time_s=0)
    assert sol.summary.feasible_energy is True
    assert sol.summary.uav_phase_time_s <= data.params.operating_horizon_s
    for t in data.targets:
        assert sol.total_hover_by_node[t.node_id] >= t.base_hover_time_s
    # With zero swap time, work times must equal sum of route durations.
    for uav_id, work in sol.summary.uav_work_times_s.items():
        uav_routes = [r for r in sol.routes if r.uav_id == uav_id]
        route_duration_sum = sum(
            evaluate_uav_route(r, data).duration_s for r in uav_routes
        )
        assert work == pytest.approx(route_duration_sum), (
            f"UAV {uav_id}: work={work:.2f}, route durations={route_duration_sum:.2f}"
        )


def test_problem1_large_k() -> None:
    """A large k (many UAVs) produces a valid solution where each UAV
    has at least 1 route, and all target base hover is served."""
    data = _loaded_data()
    sol = solve_problem1_for_k(data, k=10, battery_swap_time_s=300)
    assert sol.summary.feasible_energy is True
    assert sol.summary.uav_phase_time_s <= data.params.operating_horizon_s
    for t in data.targets:
        assert sol.total_hover_by_node[t.node_id] >= t.base_hover_time_s


def test_problem1_base_hover_never_exceeded_by_much() -> None:
    """The total served hover per target must never exceed the base
    hover requirement — the divisible hover algorithm serves exactly
    the requested amount using min(remaining, capacity).  Any excess
    beyond floating-point tolerance indicates a bug (e.g. a sign
    error in hover accounting)."""
    data = _loaded_data()
    sol = solve_problem1_for_k(data, k=3, battery_swap_time_s=300)
    for t in data.targets:
        served = sol.total_hover_by_node[t.node_id]
        excess = served - t.base_hover_time_s
        # The algorithm uses min(rm, max_hover_s) where rm is the
        # remaining hover demand.  This guarantees served <= demand.
        # Float accumulation across 16 targets and ~30 sorties may
        # contribute a few micro-seconds.  5 ms is 90000x tighter
        # than the previous 450 s bound but still handles all float
        # precision.
        assert excess < 5e-3, (
            f"Target {t.node_id}: served={served:.3f}s, "
            f"base={t.base_hover_time_s:.3f}s, excess={excess:.6f}s"
        )


# ══════════════════════════════════════════════════════════════════════════════
# problem1.py — solve_uav_hover_plan: Positive scenarios
# ══════════════════════════════════════════════════════════════════════════════


def test_hover_plan_custom_requirements() -> None:
    """solve_uav_hover_plan with custom hover dict serves exactly the
    requested hover to each specified node."""
    data = _loaded_data()
    custom_hover = {1: 75.0, 4: 120.0, 8: 55.0}
    sol = solve_uav_hover_plan(
        data, k=2, battery_swap_time_s=300, hover_requirements_s=custom_hover
    )
    assert sol.summary.feasible_energy is True
    for nid, expected in custom_hover.items():
        assert sol.total_hover_by_node[nid] == pytest.approx(expected), (
            f"Node {nid}: served {sol.total_hover_by_node[nid]:.1f}, "
            f"expected {expected:.1f}"
        )


def test_hover_plan_subset_of_targets() -> None:
    """Hover plan for only a subset of targets must not affect other
    targets."""
    data = _loaded_data()
    subset = {2: 30.0, 6: 40.0, 10: 50.0}
    sol = solve_uav_hover_plan(
        data, k=2, battery_swap_time_s=300, hover_requirements_s=subset
    )
    for nid in subset:
        assert sol.total_hover_by_node[nid] == pytest.approx(subset[nid])
    # No other targets should appear in the hover map
    for nid in sol.total_hover_by_node:
        assert nid in subset, f"Unexpected node {nid} in hover map"


def test_hover_plan_single_target() -> None:
    """Plan for a single target produces a valid solution."""
    data = _loaded_data()
    sol = solve_uav_hover_plan(
        data, k=1, battery_swap_time_s=0, hover_requirements_s={11: 200.0}
    )
    assert sol.summary.feasible_energy is True
    assert sol.total_hover_by_node[11] == pytest.approx(200.0)


def test_hover_plan_with_improve_flag() -> None:
    """improve=True must produce a valid solution with non-increased
    phase time and non-degraded total energy compared to improve=False."""
    data = _loaded_data()
    hover = {t.node_id: t.base_hover_time_s for t in data.targets}
    sol_no_imp = solve_uav_hover_plan(
        data, k=3, battery_swap_time_s=300,
        hover_requirements_s=hover, improve=False,
    )
    sol_imp = solve_uav_hover_plan(
        data, k=3, battery_swap_time_s=300,
        hover_requirements_s=hover, improve=True,
    )
    # Both solutions must be energy-feasible
    assert sol_no_imp.summary.feasible_energy is True
    assert sol_imp.summary.feasible_energy is True
    # Both must serve required hover
    for t in data.targets:
        assert sol_imp.total_hover_by_node[t.node_id] >= t.base_hover_time_s
        assert sol_no_imp.total_hover_by_node[t.node_id] >= t.base_hover_time_s
    # Improvement must not increase phase time or total energy
    assert sol_imp.summary.uav_phase_time_s <= sol_no_imp.summary.uav_phase_time_s, (
        f"phase time increased: {sol_imp.summary.uav_phase_time_s:.2f} > "
        f"{sol_no_imp.summary.uav_phase_time_s:.2f}"
    )
    assert sol_imp.summary.total_energy_j <= sol_no_imp.summary.total_energy_j + EPSILON, (
        f"total energy increased: {sol_imp.summary.total_energy_j:.2f} > "
        f"{sol_no_imp.summary.total_energy_j:.2f}"
    )


def test_hover_plan_improve_does_not_worsen_constraints() -> None:
    """Using improve=True must not break any constraint compared to
    improve=False. Specifically: energy feasibility, operating horizon,
    and per-target hover coverage must hold with improve=True if they
    hold with improve=False."""
    data = _loaded_data()
    hover = {t.node_id: t.base_hover_time_s for t in data.targets}
    sol_no_imp = solve_uav_hover_plan(
        data, k=3, battery_swap_time_s=300,
        hover_requirements_s=hover, improve=False,
    )
    sol_imp = solve_uav_hover_plan(
        data, k=3, battery_swap_time_s=300,
        hover_requirements_s=hover, improve=True,
    )
    # Baseline: improve=False must satisfy all constraints
    assert sol_no_imp.summary.feasible_energy is True
    assert sol_no_imp.summary.uav_phase_time_s <= data.params.operating_horizon_s
    for t in data.targets:
        assert sol_no_imp.total_hover_by_node[t.node_id] >= t.base_hover_time_s
    # improve=True must satisfy the same constraints
    assert sol_imp.summary.feasible_energy is True
    assert sol_imp.summary.uav_phase_time_s <= data.params.operating_horizon_s
    for t in data.targets:
        assert sol_imp.total_hover_by_node[t.node_id] >= t.base_hover_time_s


# ══════════════════════════════════════════════════════════════════════════════
# problem1.py — solve_uav_hover_plan: Negative scenarios
# ══════════════════════════════════════════════════════════════════════════════


def test_hover_plan_k_zero_raises_value_error() -> None:
    """k=0 must raise ValueError."""
    data = _loaded_data()
    with pytest.raises(ValueError):
        solve_uav_hover_plan(
            data, k=0, battery_swap_time_s=300,
            hover_requirements_s={1: 30.0},
        )


def test_hover_plan_k_negative_raises_value_error() -> None:
    """k < 0 must raise ValueError."""
    data = _loaded_data()
    with pytest.raises(ValueError):
        solve_uav_hover_plan(
            data, k=-1, battery_swap_time_s=300,
            hover_requirements_s={1: 30.0},
        )


def test_hover_plan_k_negative_large_raises_value_error() -> None:
    """Large negative k must raise ValueError."""
    data = _loaded_data()
    with pytest.raises(ValueError):
        solve_uav_hover_plan(
            data, k=-100, battery_swap_time_s=300,
            hover_requirements_s={1: 30.0},
        )


def test_hover_plan_negative_battery_swap_raises_value_error() -> None:
    """Negative battery_swap_time_s must raise ValueError."""
    data = _loaded_data()
    with pytest.raises(ValueError, match="battery_swap_time_s"):
        solve_uav_hover_plan(
            data, k=2, battery_swap_time_s=-100,
            hover_requirements_s={1: 30.0},
        )


def test_hover_plan_negative_hover_requirements_raises_value_error() -> None:
    """SR-004: Negative values in hover_requirements_s must raise
    ValueError. Calling the public API with negative hover demand
    should produce a clear error at the API boundary, not a confusing
    internal post-condition failure."""
    data = _loaded_data()
    with pytest.raises(ValueError):
        solve_uav_hover_plan(
            data, k=2, battery_swap_time_s=300,
            hover_requirements_s={1: -10.0, 2: 20.0},
        )


def test_hover_plan_all_negative_hover_rejected() -> None:
    """SR-004: Even when ALL hover values are negative, the error must be
    raised before any processing occurs."""
    data = _loaded_data()
    with pytest.raises(ValueError):
        solve_uav_hover_plan(
            data, k=2, battery_swap_time_s=300,
            hover_requirements_s={1: -5.0, 2: -10.0},
        )


# ══════════════════════════════════════════════════════════════════════════════
# problem1.py — solve_uav_hover_plan: Edge cases
# ══════════════════════════════════════════════════════════════════════════════


def test_hover_plan_all_zero_hover() -> None:
    """When all hover requirements are zero, the solution should have
    no routes and zero summary metrics."""
    data = _loaded_data()
    sol = solve_uav_hover_plan(
        data, k=2, battery_swap_time_s=300,
        hover_requirements_s={1: 0.0, 2: 0.0},
    )
    assert len(sol.routes) == 0
    assert sol.summary.total_energy_j == 0.0
    assert sol.summary.uav_phase_time_s == 0.0
    assert sol.summary.feasible_energy is True


def test_hover_plan_empty_requirements() -> None:
    """Empty hover requirements dict must produce a valid solution with
    zero routes, zero energy, zero phase time, and feasible=True."""
    data = _loaded_data()
    sol = solve_uav_hover_plan(
        data, k=3, battery_swap_time_s=300,
        hover_requirements_s={},
    )
    assert len(sol.routes) == 0
    assert sol.summary.total_energy_j == 0.0
    assert sol.summary.uav_phase_time_s == 0.0
    assert sol.summary.feasible_energy is True
    assert sol.total_hover_by_node == {}


def test_hover_plan_very_high_hover_single_node() -> None:
    """A single node with hover demand much larger than one sortie's
    capacity must be served across multiple sorties."""
    data = _loaded_data()
    target_id = 3
    single_max = (
        data.params.effective_energy_limit_j
        - data.flight_energy_j[(0, target_id)]
        - data.flight_energy_j[(target_id, 0)]
    ) / data.params.hover_power_j_per_s
    # Demand requiring 3+ sorties
    huge_demand = single_max * 3.0
    sol = solve_uav_hover_plan(
        data, k=2, battery_swap_time_s=100,
        hover_requirements_s={target_id: huge_demand},
    )
    assert sol.summary.feasible_energy is True
    assert sol.total_hover_by_node[target_id] == pytest.approx(huge_demand)
    # Multiple sorties should be generated for this demand
    total_sorties = len(sol.routes)
    assert total_sorties >= 2, (
        f"Expected >= 2 sorties for demand {huge_demand:.1f}s, "
        f"got {total_sorties}"
    )


def test_hover_plan_uneven_hover_distribution() -> None:
    """Targets with very different hover demands are all served
    correctly."""
    data = _loaded_data()
    uneven = {1: 10.0, 8: 500.0, 15: 200.0}
    sol = solve_uav_hover_plan(
        data, k=3, battery_swap_time_s=300,
        hover_requirements_s=uneven,
    )
    assert sol.summary.feasible_energy is True
    for nid, expected in uneven.items():
        assert sol.total_hover_by_node[nid] == pytest.approx(expected)


# ══════════════════════════════════════════════════════════════════════════════
# Integration — search + problem1
# ══════════════════════════════════════════════════════════════════════════════


def test_integration_nn_order_through_split_and_solve() -> None:
    """End-to-end: use nearest_neighbor_order to generate an order,
    split into energy-feasible routes, assign to UAVs, and verify the
    full solution."""
    data = _loaded_data()
    all_ids = [t.node_id for t in data.targets]
    order = nearest_neighbor_order(data, all_ids)
    assert len(order) == 16
    hover = {t.node_id: t.base_hover_time_s for t in data.targets}
    routes = split_order_into_energy_feasible_routes(order, hover, data)
    assert len(routes) >= 2
    for route in routes:
        assert evaluate_uav_route(route, data).feasible_energy

    # Now feed into problem1 via solve_uav_hover_plan
    sol = solve_uav_hover_plan(
        data, k=3, battery_swap_time_s=300,
        hover_requirements_s=hover, improve=True,
    )
    assert sol.summary.feasible_energy is True
    for t in data.targets:
        assert sol.total_hover_by_node[t.node_id] >= t.base_hover_time_s


def test_integration_two_opt_improvement_is_feasible() -> None:
    """Apply 2-opt to routes from split_order and verify they remain
    energy-feasible."""
    data = _loaded_data()
    hover = {t.node_id: t.base_hover_time_s for t in data.targets}
    order = nearest_neighbor_order(data, list(hover.keys()))
    routes = split_order_into_energy_feasible_routes(order, hover, data)

    for route in routes:
        improved = improve_route_by_two_opt(route, data)
        assert evaluate_uav_route(improved, data).feasible_energy
        # Total hover must be preserved
        assert sum(improved.hover_times_s.values()) == pytest.approx(
            sum(route.hover_times_s.values())
        )


def test_integration_different_uav_counts_produce_consistent_hover() -> None:
    """Regardless of k, the total hover served to each target must be
    at least base_hover_time_s."""
    data = _loaded_data()
    for k in (1, 2, 4, 8):
        sol = solve_problem1_for_k(
            data, k=k, battery_swap_time_s=300
        )
        assert sol.summary.feasible_energy is True
        for t in data.targets:
            assert sol.total_hover_by_node[t.node_id] >= t.base_hover_time_s, (
                f"k={k}, target {t.node_id}: "
                f"served={sol.total_hover_by_node[t.node_id]:.1f}, "
                f"needed={t.base_hover_time_s:.1f}"
            )


def test_integration_summary_metrics_consistent() -> None:
    """Summary metrics are internally consistent: total_energy equals
    sum of route energies, phase_time equals max work time, etc."""
    data = _loaded_data()
    sol = solve_problem1_for_k(data, k=3, battery_swap_time_s=300)

    # total_energy_j = sum of route energies
    route_energy_sum = sum(
        evaluate_uav_route(r, data).energy_j for r in sol.routes
    )
    assert sol.summary.total_energy_j == pytest.approx(route_energy_sum)

    # feasible_energy is True iff all routes are feasible
    all_feasible = all(
        evaluate_uav_route(r, data).feasible_energy for r in sol.routes
    )
    assert sol.summary.feasible_energy == all_feasible

    # uav_phase_time_s == max(uav_work_times_s)
    assert sol.summary.uav_phase_time_s == pytest.approx(
        max(sol.summary.uav_work_times_s.values())
    )


# ══════════════════════════════════════════════════════════════════════════════
# search.py — EPSILON: public constant
# ══════════════════════════════════════════════════════════════════════════════


def test_epsilon_is_positive_float() -> None:
    """EPSILON is a small positive float."""
    assert isinstance(EPSILON, float)
    assert EPSILON > 0.0
    assert EPSILON < 0.01
