"""Problem 1: Multi-UAV basic inspection solver.

Constructs a multi-UAV solution for Problem 1 where every target gets
at least its base_hover_time_s of hover inspection, using divisible
hover allocation across sorties.
"""

from __future__ import annotations

from dataclasses import dataclass

from c_uav_inspection.data import ProblemData
from c_uav_inspection.model import (
    UAVRoute,
    evaluate_uav_route,
    summarize_uav_solution,
)
from c_uav_inspection.model import (
    UAVSolutionSummary as _Summary,
)
from c_uav_inspection.search import (
    EPSILON,
    InfeasibleError,
    improve_route_by_two_opt,
    nearest_neighbor_order,
    split_order_into_energy_feasible_routes,
    split_order_into_energy_feasible_routes_no_split,
)


@dataclass(frozen=True)
class Problem1Solution:
    """Complete solution for Problem 1 (k-UAV basic inspection).

    Attributes:
        routes: All UAV sorties with assigned uav_id and sortie_id.
        total_hover_by_node: Accumulated hover time served per target.
        summary: Aggregated solution metrics.
    """

    routes: tuple[UAVRoute, ...]
    total_hover_by_node: dict[int, float]
    summary: _Summary


def _assign_routes_to_uavs(
    routes: tuple[UAVRoute, ...],
    k: int,
    data: ProblemData,
    battery_swap_time_s: float,
) -> tuple[UAVRoute, ...]:
    """Assign unassigned routes to k UAVs via longest-processing-time-first.

    Routes are sorted by total hover time (descending). Each route is
    assigned to the UAV with the smallest accumulated work time so far.
    Battery swap time is added between consecutive sorties of the same UAV.

    Returns routes with correct uav_id and sortie_id, sorted by (uav_id, sortie_id).
    """
    if k <= 0:
        raise ValueError(f"k must be positive, got {k}")

    # Sort routes by full route duration descending (LPT: longest processing time first)
    route_metrics = [
        (route, evaluate_uav_route(route, data).duration_s)
        for route in routes
    ]
    route_metrics.sort(key=lambda item: item[1], reverse=True)

    # uav_work_times tracks accumulated work time per UAV
    uav_work_times: dict[int, float] = {uid: 0.0 for uid in range(1, k + 1)}
    # uav_sortie_counts tracks how many sorties each UAV has
    uav_sortie_counts: dict[int, int] = {uid: 0 for uid in range(1, k + 1)}

    assigned: list[UAVRoute] = []

    for route, duration_s in route_metrics:
        # Find UAV with minimum work time (tie-break by smaller uav_id)
        best_uav = min(range(1, k + 1), key=lambda uid: uav_work_times[uid])

        uav_sortie_counts[best_uav] += 1
        sortie_id = uav_sortie_counts[best_uav]

        # Add battery swap time if not first sortie for this UAV
        additional = duration_s
        if sortie_id > 1:
            additional += battery_swap_time_s

        uav_work_times[best_uav] += additional

        new_route = UAVRoute(
            uav_id=best_uav,
            sortie_id=sortie_id,
            node_sequence=route.node_sequence,
            hover_times_s=dict(route.hover_times_s),
        )
        assigned.append(new_route)

    # Sort by (uav_id, sortie_id)
    assigned.sort(key=lambda r: (r.uav_id, r.sortie_id))
    return tuple(assigned)


def solve_uav_hover_plan(
    data: ProblemData,
    k: int,
    battery_swap_time_s: float,
    hover_requirements_s: dict[int, float],
    improve: bool = False,
    allow_split_hover: bool = True,
) -> Problem1Solution:
    """General-purpose multi-UAV hover plan solver.

    Args:
        data: Problem dataset.
        k: Number of UAVs.
        battery_swap_time_s: Battery swap time in seconds.
        hover_requirements_s: Dict mapping node_id -> required hover seconds.
        improve: If True, apply 2-opt local search to each route.
        allow_split_hover: If True (default), a target's hover demand may
            span multiple sorties. If False, each target must be fully
            served within exactly one sortie.

    Returns:
        Problem1Solution with assigned UAV routes and summary.
    """
    if battery_swap_time_s < 0:
        raise ValueError(
            f"battery_swap_time_s must be non-negative, got {battery_swap_time_s}"
        )

    # Generate visitation order via nearest-neighbor
    node_ids = list(hover_requirements_s.keys())
    order = nearest_neighbor_order(data, node_ids)

    # Split into energy-feasible routes
    if allow_split_hover:
        raw_routes = split_order_into_energy_feasible_routes(
            order, hover_requirements_s, data
        )
    else:
        raw_routes = split_order_into_energy_feasible_routes_no_split(
            order, hover_requirements_s, data
        )

    # Apply 2-opt improvement if requested
    if improve:
        improved_routes: list[UAVRoute] = []
        for route in raw_routes:
            improved = improve_route_by_two_opt(route, data)
            improved_routes.append(improved)
        raw_routes = tuple(improved_routes)

    # Assign routes to UAVs
    assigned_routes = _assign_routes_to_uavs(raw_routes, k, data, battery_swap_time_s)

    # Accumulate total hover per node
    total_hover_by_node: dict[int, float] = {}
    for route in assigned_routes:
        for node_id, seconds in route.hover_times_s.items():
            total_hover_by_node[node_id] = (
                total_hover_by_node.get(node_id, 0.0) + seconds
            )

    # Summarize
    summary = summarize_uav_solution(assigned_routes, data, battery_swap_time_s)

    # Enforce operating horizon
    if summary.uav_phase_time_s > data.params.operating_horizon_s + 1e-9:
        raise InfeasibleError(
            f"UAV phase time {summary.uav_phase_time_s:.2f}s exceeds "
            f"operating horizon {data.params.operating_horizon_s:.2f}s"
        )

    return Problem1Solution(
        routes=assigned_routes,
        total_hover_by_node=total_hover_by_node,
        summary=summary,
    )


def solve_problem1_for_k(
    data: ProblemData,
    k: int,
    battery_swap_time_s: float,
    improve: bool = False,
    allow_split_hover: bool = True,
) -> Problem1Solution:
    """Solve Problem 1 for k UAVs with base hover requirements.

    Each target must receive at least its base_hover_time_s of
    inspection hover time.

    Args:
        data: Problem dataset.
        k: Number of UAVs.
        battery_swap_time_s: Battery swap time in seconds.
        improve: If True, apply 2-opt local search to each route.
        allow_split_hover: If True (default), a target's hover demand may
            span multiple sorties. If False, each target must be fully
            served within exactly one sortie.

    Returns:
        Problem1Solution with the computed plan.
    """
    if battery_swap_time_s < 0:
        raise ValueError(
            f"battery_swap_time_s must be non-negative, got {battery_swap_time_s}"
        )

    hover_requirements_s = {
        target.node_id: target.base_hover_time_s for target in data.targets
    }
    return solve_uav_hover_plan(
        data,
        k,
        battery_swap_time_s,
        hover_requirements_s,
        improve=improve,
        allow_split_hover=allow_split_hover,
    )
