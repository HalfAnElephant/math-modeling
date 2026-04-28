"""Nearest-neighbor ordering and divisible hover bin-packing.

Provides path construction tools that greedily order targets by flight
time, then split a greedy order into energy-feasible UAV sorties where
a single target's hover demand may span multiple sorties.
"""

from __future__ import annotations

from math import inf
from typing import Iterable, Mapping

from c_uav_inspection.data import ProblemData
from c_uav_inspection.model import UAVRoute, evaluate_uav_route

EPSILON: float = 1e-7


class InfeasibleError(ValueError):
    """Raised when a legitimate planning infeasibility is detected.

    This is distinct from ValueError, which signals programming errors
    (bad input, data corruption). InfeasibleError indicates that the
    planning problem itself has no feasible solution under the given
    constraints — e.g., a target is unreachable within a single sortie's
    energy budget.

    Callers that perform iterative search should catch InfeasibleError
    to skip infeasible candidates, but MUST NOT silently swallow plain
    ValueError, which indicates bugs.
    """



def _known_node_ids(data: ProblemData) -> frozenset[int]:
    """Return the set of all node IDs known to the flight matrix."""
    ids: set[int] = set()
    for a, b in data.flight_time_s:
        ids.add(a)
        ids.add(b)
    return frozenset(ids)


def nearest_neighbor_order(data: ProblemData, node_ids: list[int]) -> tuple[int, ...]:
    """Greedy nearest-neighbor ordering of targets starting from depot 0.

    From node 0, repeatedly pick the remaining target with the smallest
    flight time. On ties, the smaller node_id is chosen.

    Returns:
        Tuple of node IDs in visitation order (depot 0 NOT included).

    Raises:
        ValueError: If node_ids contains duplicate entries or IDs
                    not present in the flight matrix.
    """
    if 0 in node_ids:
        raise ValueError(
            "node_ids must not contain depot node 0 — the depot is the "
            "origin/destination, not a target to visit"
        )

    if len(set(node_ids)) != len(node_ids):
        raise ValueError(
            f"node_ids contains duplicate entries: {node_ids}"
        )

    known = _known_node_ids(data)
    unknown = [nid for nid in node_ids if nid not in known]
    if unknown:
        raise ValueError(
            f"node_ids contains IDs that do not exist in the flight "
            f"matrix: {unknown}"
        )

    remaining = set(node_ids)
    order: list[int] = []
    current = 0

    while remaining:
        best_node = -1
        best_time = inf
        for nid in remaining:
            t = data.flight_time_s[(current, nid)]
            if t < best_time - EPSILON:
                best_time = t
                best_node = nid
            elif abs(t - best_time) <= EPSILON and nid < best_node:
                best_node = nid
        order.append(best_node)
        remaining.discard(best_node)
        current = best_node

    return tuple(order)


def _extract_visited_nodes(
    node_sequence: Iterable[int],
) -> list[int]:
    """Extract non-depot nodes from a route sequence in order."""
    return [n for n in node_sequence if n != 0]


def split_order_into_energy_feasible_routes(
    order: tuple[int, ...],
    hover_times_s: Mapping[int, float],
    data: ProblemData,
) -> tuple[UAVRoute, ...]:
    """Split a node visitation order into energy-feasible UAV sorties.

    Each sortie starts and ends at depot 0. When a target's remaining
    hover demand cannot be fully served within the remaining energy of
    the current sortie, the hover is partially served up to the energy
    limit, the sortie returns to depot, and the remaining demand is
    carried over to the next sortie.

    Args:
        order: Ordered list of target node IDs to visit.
        hover_times_s: Total hover demand per node (may be partially served).
        data: Problem dataset.

    Returns:
        Tuple of UAVRoute instances (uav_id and sortie_id are placeholders 0, 1).

    Raises:
        ValueError: If a target's 0-roundtrip with 0 hover already exceeds
                    the single-sortie energy limit.
    """
    # Pre-validate: hover_times_s values must be non-negative.
    negative_nodes = [
        (nid, val) for nid, val in hover_times_s.items() if val < 0.0
    ]
    if negative_nodes:
        raise ValueError(
            f"hover_times_s values must be non-negative. "
            f"Negative values detected: {negative_nodes}"
        )

    remaining_hover: dict[int, float] = dict(hover_times_s)

    # Pre-validate: all node IDs in order and hover_times_s must exist in
    # the flight matrix (prevent raw KeyError for nonexistent nodes).
    known = _known_node_ids(data)
    unknown_order = sorted(nid for nid in order if nid not in known)
    unknown_hover = sorted(nid for nid in remaining_hover if nid not in known)
    if unknown_order:
        raise ValueError(
            f"order contains node IDs that do not exist in the flight "
            f"matrix: {unknown_order}"
        )
    if unknown_hover:
        raise ValueError(
            f"hover_times_s contains node IDs that do not exist in the "
            f"flight matrix: {unknown_hover}"
        )

    # Pre-validate: every hover_times_s key must appear in the order tuple.
    # Otherwise the while loop below would never visit the stranded node
    # and would loop forever (denial-of-service).
    order_set = set(order)
    for node_id in remaining_hover:
        if remaining_hover.get(node_id, 0.0) <= EPSILON:
            continue
        if node_id not in order_set:
            raise ValueError(
                f"Node {node_id} has positive hover demand but is "
                f"not present in the visitation order"
            )

    # Pre-validate: hover_power must be positive (avoid ZeroDivisionError).
    limit_j = data.params.effective_energy_limit_j
    hover_power = data.params.hover_power_j_per_s
    if hover_power <= 0.0:
        raise ValueError(
            f"hover_power_j_per_s must be positive, got {hover_power}"
        )

    # Pre-validate: every target must be reachable within a single sortie's energy
    # budget even with zero hover. If not, the target can never be served.
    # Use >= (not >) so that roundtrip == limit also raises — zero energy
    # remains for hover and the outer while loop would spin forever (CR-013).
    for node_id, demand_s in remaining_hover.items():
        if demand_s <= EPSILON:
            continue
        roundtrip_j = data.flight_energy_j[(0, node_id)] + data.flight_energy_j[(node_id, 0)]
        if roundtrip_j >= limit_j - EPSILON:
            raise InfeasibleError(
                f"Target {node_id} roundtrip energy ({roundtrip_j:.2f} J) "
                f"reaches or exceeds single-sortie energy limit "
                f"({limit_j:.2f} J) — zero energy remains for hover, "
                f"target is unreachable."
            )

    routes: list[UAVRoute] = []
    sortie_id = 0

    while any(v > EPSILON for v in remaining_hover.values()):
        sortie_id += 1
        node_sequence: list[int] = [0]
        route_hover: dict[int, float] = {}
        current_node = 0
        energy_used_j = 0.0

        for node_id in order:
            rm = remaining_hover.get(node_id, 0.0)
            if rm <= EPSILON:
                continue

            # One-way flight energy to reach this node
            arrival_energy = data.flight_energy_j[(current_node, node_id)]
            # Return energy from this node back to depot (worst-case)
            return_energy = data.flight_energy_j[(node_id, 0)]
            # Roundtrip energy if this is the last node visited
            roundtrip_energy = arrival_energy + return_energy

            residual_energy_j = data.params.effective_energy_limit_j - energy_used_j

            # If we can't even make the roundtrip+return, this sortie is done
            if roundtrip_energy > residual_energy_j + EPSILON:
                break

            # After roundtrip (arrival + worst-case return), remaining for hover
            energy_for_hover_j = residual_energy_j - roundtrip_energy
            if energy_for_hover_j < 0.0:
                energy_for_hover_j = 0.0

            max_hover_s = energy_for_hover_j / hover_power

            # Check: can we even serve 0 hover with this roundtrip?
            if max_hover_s <= EPSILON:
                # Not enough energy for even a token hover, end sortie
                break

            serve_hover_s = min(rm, max_hover_s)

            # Visit this node
            node_sequence.append(node_id)
            route_hover[node_id] = route_hover.get(node_id, 0.0) + serve_hover_s
            remaining_hover[node_id] = rm - serve_hover_s
            # Account for one-way arrival + hover only. Return leg is added
            # once when the sortie ends (see below). This avoids double-counting
            # return-to-depot energy for intermediate targets.
            energy_used_j += arrival_energy + serve_hover_s * hover_power
            current_node = node_id

            # If we only partially served this target's hover demand, end the
            # current sortie per the plan spec: "服务部分悬停后结束当前趟".
            # The remaining demand will be served in a subsequent sortie.
            if serve_hover_s < rm - EPSILON:
                break

        # Return to depot
        if node_sequence[-1] != 0:
            # Fly back from last visited node (the single return leg)
            last_node = node_sequence[-1]
            energy_used_j += data.flight_energy_j[(last_node, 0)]
        node_sequence.append(0)

        route = UAVRoute(
            uav_id=0,
            sortie_id=sortie_id,
            node_sequence=tuple(node_sequence),
            hover_times_s=dict(route_hover),
        )
        routes.append(route)

    # Validate: ensure no target has negative remaining hover
    for node_id, rem in remaining_hover.items():
        if rem < -EPSILON:
            raise ValueError(
                f"Target {node_id} has negative remaining hover: {rem}"
            )

    return tuple(routes)


def improve_route_by_two_opt(
    route: UAVRoute,
    data: ProblemData,
) -> UAVRoute:
    """Apply 2-opt local improvement to a single UAV route.

    Fixes the set of visited targets and their hover times. Only the
    visitation order (non-depot nodes) is reversed by 2-opt swaps.
    Accepts only candidates that are energy-feasible and strictly
    reduce route duration.

    Args:
        route: The UAVRoute to improve.
        data: Problem dataset.

    Returns:
        Improved UAVRoute, or the original if no improvement found.
    """
    # Extract non-depot nodes in order
    nodes = _extract_visited_nodes(route.node_sequence)
    n = len(nodes)
    if n <= 1:
        return route

    best_route = route
    best_metrics = evaluate_uav_route(route, data)
    best_duration = best_metrics.duration_s

    improved = True
    while improved:
        improved = False
        for i in range(len(nodes) - 1):
            for j in range(i + 2, len(nodes) + 1):
                # 2-opt: reverse segment [i:j]
                new_nodes = list(nodes)
                new_nodes[i:j] = reversed(new_nodes[i:j])

                new_seq = (0,) + tuple(new_nodes) + (0,)
                candidate = UAVRoute(
                    uav_id=route.uav_id,
                    sortie_id=route.sortie_id,
                    node_sequence=new_seq,
                    hover_times_s=dict(route.hover_times_s),
                )
                metrics = evaluate_uav_route(candidate, data)

                if (
                    metrics.feasible_energy
                    and metrics.duration_s < best_duration - EPSILON
                ):
                    best_route = candidate
                    best_duration = metrics.duration_s
                    improved = True
                    break
            if improved:
                nodes = _extract_visited_nodes(best_route.node_sequence)
                break

    return best_route
