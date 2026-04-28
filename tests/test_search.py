"""Tests for nearest-neighbor ordering and divisible hover bin-packing."""

from dataclasses import replace
from pathlib import Path

import pytest

from c_uav_inspection.data import ProblemData, load_problem_data
from c_uav_inspection.model import evaluate_uav_route
from c_uav_inspection.search import (
    EPSILON,
    nearest_neighbor_order,
    split_order_into_energy_feasible_routes,
)

DATA_PATH = Path("2026同济数学建模竞赛赛题/2026C数据.xlsx")


def test_nearest_neighbor_order_visits_each_target_once() -> None:
    data = load_problem_data(DATA_PATH)
    order = nearest_neighbor_order(data, [target.node_id for target in data.targets])

    assert sorted(order) == list(range(1, 17))
    assert len(order) == 16


def test_nearest_neighbor_order_raises_on_duplicates() -> None:
    """CR-006: duplicate node_ids must raise ValueError."""
    data = load_problem_data(DATA_PATH)
    with pytest.raises(ValueError, match="duplicate"):
        nearest_neighbor_order(data, [1, 2, 3, 2])


def test_split_order_raises_on_zero_hover_power() -> None:
    """CR-007: zero hover_power_j_per_s must raise ValueError."""
    data = load_problem_data(DATA_PATH)
    data = replace(
        data,
        params=replace(data.params, hover_power_j_per_s=0.0),
    )
    hover = {1: 10.0}
    with pytest.raises(ValueError, match="hover_power"):
        split_order_into_energy_feasible_routes((1,), hover, data)


def test_partial_hover_ends_sortie_immediately() -> None:
    """SR-001: after partial hover service, the sortie ends.

    When a target in a multi-target order receives partial hover,
    the sortie must return to depot immediately. No further targets
    from the order should be visited in that sortie.
    """
    data = load_problem_data(DATA_PATH)
    # Pick two targets where t1 is close, t2 is far (smaller hover capacity)
    t1, t2 = 1, 16
    # Calculate max hover for t2 when visited alone
    max_hover_t2_alone = (
        data.params.effective_energy_limit_j
        - data.flight_energy_j[(0, t2)]
        - data.flight_energy_j[(t2, 0)]
    ) / data.params.hover_power_j_per_s
    # Give t1 minimal hover, t2 just enough to trigger partial service
    # after visiting t1. Use roundtrip from 0->t1->t2->0 energy for t1's
    # visit plus t2's own roundtrip overhead.
    hover = {t1: 0.0, t2: max_hover_t2_alone + 200.0}
    order = (t1, t2)

    routes = split_order_into_energy_feasible_routes(order, hover, data)

    # t2 must be served across multiple sorties (partial split)
    assert len(routes) >= 2
    # t2's total served hover must match demand
    served_t2 = sum(r.hover_times_s.get(t2, 0.0) for r in routes)
    assert served_t2 == pytest.approx(hover[t2])
    # The first sortie must serve t2 partially AND must not serve t2 fully
    t2_in_first = routes[0].hover_times_s.get(t2, 0.0)
    t2_in_second = routes[1].hover_times_s.get(t2, 0.0)
    # At least some hover served in both first and subsequent sorties
    assert t2_in_first > EPSILON, "t2 should be partially served in first sortie"
    assert t2_in_second > EPSILON, "t2 remainder should be in second sortie"
    # All routes must be energy feasible
    assert all(evaluate_uav_route(r, data).feasible_energy for r in routes)


def test_split_order_energy_accounting_matches_evaluate() -> None:
    """CR-008: energy_used_j in split logic must match evaluate_uav_route.

    Build a route via split_order_into_energy_feasible_routes, then
    verify that evaluate_uav_route reports energy <= effective_energy_limit_j
    (i.e., the internal energy accounting is consistent with reality).
    """
    data = load_problem_data(DATA_PATH)
    # Use two nearby targets to get a multi-target sortie
    order = (1, 2, 3)
    hover = {1: 50.0, 2: 30.0, 3: 40.0}

    routes = split_order_into_energy_feasible_routes(order, hover, data)

    # The internal energy accounting should NOT over-estimate, so
    # every route should be energy-feasible when actually evaluated.
    for route in routes:
        metrics = evaluate_uav_route(route, data)
        assert metrics.feasible_energy, (
            f"Route energy {metrics.energy_j:.2f} J exceeds "
            f"limit {data.params.effective_energy_limit_j:.2f} J. "
            f"Internal accounting mismatch."
        )


def test_split_order_into_energy_feasible_routes_satisfies_base_hover() -> None:
    data = load_problem_data(DATA_PATH)
    order = nearest_neighbor_order(data, [target.node_id for target in data.targets])
    hover: dict[int, float] = {
        target.node_id: target.base_hover_time_s for target in data.targets
    }

    routes = split_order_into_energy_feasible_routes(order, hover, data)
    served: dict[int, float] = {node_id: 0.0 for node_id in hover}
    for route in routes:
        for node_id, seconds in route.hover_times_s.items():
            served[node_id] += seconds

    assert len(routes) >= 2
    assert all(
        route.node_sequence[0] == 0 and route.node_sequence[-1] == 0
        for route in routes
    )
    assert all(evaluate_uav_route(route, data).feasible_energy for route in routes)
    assert served == pytest.approx(hover)


def test_split_order_allows_one_target_hover_to_span_multiple_sorties() -> None:
    data = load_problem_data(DATA_PATH)
    target_id = 16
    single_visit_hover_capacity = (
        data.params.effective_energy_limit_j
        - data.flight_energy_j[(0, target_id)]
        - data.flight_energy_j[(target_id, 0)]
    ) / data.params.hover_power_j_per_s
    hover = {target_id: single_visit_hover_capacity + 30.0}

    routes = split_order_into_energy_feasible_routes((target_id,), hover, data)
    served = sum(route.hover_times_s.get(target_id, 0.0) for route in routes)

    assert len(routes) >= 2
    assert served == pytest.approx(hover[target_id])
    assert all(evaluate_uav_route(route, data).feasible_energy for route in routes)
