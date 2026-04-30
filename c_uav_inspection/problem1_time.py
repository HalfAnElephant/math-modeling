"""Problem 1 time-priority solver: DP over target subsets.

Instead of packing targets into a single nearest-neighbor order and then
splitting it into energy-feasible sorties (the current "packed" approach),
this module precomputes a heuristic route candidate for every non-empty subset of
targets and then uses dynamic programming to partition the targets into
up to k routes such that the *maximum* route duration is minimized.

This "time-priority" formulation allows more UAVs to exploit additional
parallelism: when k > 2, the DP can split the workload across more
concurrent sorties rather than being locked into the 2-sortie structure
that the packed approach produces for this dataset.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import inf

from c_uav_inspection.data import ProblemData
from c_uav_inspection.model import (
    UAVRoute,
    UAVSolutionSummary,
    evaluate_uav_route,
    summarize_uav_solution,
)
from c_uav_inspection.search import (
    EPSILON,
    InfeasibleError,
    improve_route_by_two_opt,
    nearest_neighbor_order,
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SubsetRouteCandidate:
    """Precomputed best route for a specific subset of targets.

    Attributes:
        mask: Bitmask of the subset (bit i set = target i included).
        node_ids: Tuple of actual node IDs in this subset.
        route: The UAVRoute covering this subset.
        duration_s: Total duration of the route.
        energy_j: Total energy consumed.
        feasible_energy: Whether the route is within energy limits.
    """

    mask: int
    node_ids: tuple[int, ...]
    route: UAVRoute
    duration_s: float
    energy_j: float
    feasible_energy: bool


@dataclass(frozen=True)
class TimePriorityProblem1Solution:
    """Complete time-priority solution for Problem 1.

    Attributes:
        k: Number of UAVs the solution was computed for.
        routes: UAV sorties with assigned uav_id and sortie_id.
        total_hover_by_node: Accumulated hover time served per target.
        summary: Aggregated solution metrics.
        solver_name: Identifier for the solver variant.
        route_count: Actual number of routes used (<= k).
    """

    k: int
    routes: tuple[UAVRoute, ...]
    total_hover_by_node: dict[int, float]
    summary: UAVSolutionSummary
    solver_name: str
    route_count: int


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _target_maps(
    data: ProblemData,
) -> tuple[tuple[int, ...], dict[int, float], dict[int, int]]:
    """Extract ordered node IDs, base hover map, and node-to-bit mapping.

    Returns:
        (node_ids, base_hover, node_to_bit) where:
        - node_ids: ordered tuple of all target node IDs
        - base_hover: dict mapping node_id -> base_hover_time_s
        - node_to_bit: dict mapping node_id -> bit index (0-indexed)
    """
    node_ids: list[int] = []
    base_hover: dict[int, float] = {}
    node_to_bit: dict[int, int] = {}

    for idx, target in enumerate(data.targets):
        nid = target.node_id
        node_ids.append(nid)
        base_hover[nid] = target.base_hover_time_s
        node_to_bit[nid] = idx

    return tuple(node_ids), base_hover, node_to_bit


def _nodes_from_mask(mask: int, node_ids: tuple[int, ...]) -> tuple[int, ...]:
    """Return the tuple of node_ids whose bits are set in *mask*."""
    result: list[int] = []
    for idx, nid in enumerate(node_ids):
        if mask & (1 << idx):
            result.append(nid)
    return tuple(result)


# ---------------------------------------------------------------------------
# Subset route precomputation
# ---------------------------------------------------------------------------


def precompute_problem1_subset_routes(
    data: ProblemData,
    improve: bool = True,
) -> dict[int, SubsetRouteCandidate]:
    """Precompute heuristic route candidates for every non-empty target subset.

    Enumerates all 2^n - 1 non-empty subsets of the n targets. For each subset:
      1. Build a nearest-neighbor visitation order.
      2. (Optionally) improve it with 2-opt local search.
      3. Evaluate energy feasibility.
      4. Only keep candidates that are energy-feasible.

    Args:
        data: Problem dataset.
        improve: If True, apply 2-opt to each candidate route.

    Returns:
        Dict mapping bitmask -> SubsetRouteCandidate (only feasible masks).
    """
    node_ids, base_hover, _node_to_bit = _target_maps(data)
    n = len(node_ids)
    full_mask = (1 << n) - 1
    candidates: dict[int, SubsetRouteCandidate] = {}

    for mask in range(1, full_mask + 1):
        subset_nodes = _nodes_from_mask(mask, node_ids)
        if not subset_nodes:
            continue

        # Build nearest-neighbor order for this subset
        order = nearest_neighbor_order(data, list(subset_nodes))

        # Construct route: depot -> order -> depot, with base hover for each node
        node_sequence = (0,) + order + (0,)
        hover_times_s: dict[int, float] = {}
        for nid in subset_nodes:
            hover_times_s[nid] = base_hover[nid]

        route = UAVRoute(
            uav_id=0,
            sortie_id=1,
            node_sequence=node_sequence,
            hover_times_s=hover_times_s,
        )

        # Apply 2-opt improvement if requested
        if improve:
            route = improve_route_by_two_opt(route, data)

        # Evaluate
        metrics = evaluate_uav_route(route, data)

        # Only keep energy-feasible candidates
        if not metrics.feasible_energy:
            continue

        candidates[mask] = SubsetRouteCandidate(
            mask=mask,
            node_ids=subset_nodes,
            route=route,
            duration_s=metrics.duration_s,
            energy_j=metrics.energy_j,
            feasible_energy=metrics.feasible_energy,
        )

    return candidates


# ---------------------------------------------------------------------------
# Time-priority DP solver for a specific k
# ---------------------------------------------------------------------------


def solve_problem1_time_priority_for_k(
    data: ProblemData,
    k: int,
    improve: bool = True,
    candidates: dict[int, SubsetRouteCandidate] | None = None,
) -> TimePriorityProblem1Solution:
    """Solve Problem 1 for k UAVs using time-priority DP over subsets.

    Precomputes all feasible single-sortie subset routes, then uses dynamic
    programming to partition the full target set into at most k routes such
    that the *maximum* route duration is minimised.  This allows additional
    UAVs to reduce the UAV-phase time beyond the 2-sortie floor of the
    packed approach.

    Args:
        data: Problem dataset.
        k: Number of UAVs (upper bound on routes).
        improve: If True, apply 2-opt to each candidate route.
        candidates: Precomputed subset route candidates.  If None, computed
            internally via precompute_problem1_subset_routes.

    Returns:
        TimePriorityProblem1Solution with routes, summary, and verification.

    Raises:
        ValueError: If k <= 0.
        InfeasibleError: If no partition of targets into <= k
            energy-feasible routes exists.
    """
    if k <= 0:
        raise ValueError(f"k must be positive, got {k}")

    node_ids, base_hover, node_to_bit = _target_maps(data)
    n = len(node_ids)
    full_mask = (1 << n) - 1

    # Precompute all feasible subset routes (or use caller-supplied)
    if candidates is None:
        candidates = precompute_problem1_subset_routes(data, improve=improve)

    if not candidates:
        raise InfeasibleError(
            "No energy-feasible subset routes found — check data consistency."
        )

    # ------------------------------------------------------------------
    # DP: best[r][mask] = minimum possible max-route-duration when using
    # at most r routes to cover *mask*.
    #
    # base case: best[0][0] = 0.0, best[0][mask>0] = inf
    # recurrence:
    #   best[r][mask] = min(
    #       best[r-1][mask],          # use fewer than r routes
    #       min over non-empty sub ⊂ mask:
    #           max(best[r-1][mask\sub], candidates[sub].duration_s)
    #       )
    #
    # parent[r][mask] = (prev_mask, sub_mask) traces the optimal choice.
    # ------------------------------------------------------------------

    size = full_mask + 1
    best: list[list[float]] = [[inf] * size for _ in range(k + 1)]
    best[0][0] = 0.0

    parent: list[list[tuple[int, int] | None]] = [
        [None] * size for _ in range(k + 1)
    ]

    for r in range(1, k + 1):
        for mask in range(size):
            # Option 1: use fewer than r routes (carry over previous best)
            if best[r - 1][mask] < best[r][mask]:
                best[r][mask] = best[r - 1][mask]
                parent[r][mask] = (mask, 0)  # 0 sub_mask = inherit

            # Option 2: split mask into sub_mask + (mask \ sub_mask)
            sub = mask
            while sub:
                if sub in candidates:
                    prev_mask = mask ^ sub
                    if best[r - 1][prev_mask] < inf:
                        candidate_dur = candidates[sub].duration_s
                        max_dur = best[r - 1][prev_mask]
                        if candidate_dur > max_dur:
                            max_dur = candidate_dur
                        if max_dur < best[r][mask] - EPSILON:
                            best[r][mask] = max_dur
                            parent[r][mask] = (prev_mask, sub)
                sub = (sub - 1) & mask

    if best[k][full_mask] >= inf - EPSILON:
        raise InfeasibleError(
            f"Cannot partition all {n} targets into at most {k} "
            f"energy-feasible routes."
        )

    # ------------------------------------------------------------------
    # Route reconstruction
    # ------------------------------------------------------------------
    mask = full_mask
    r = k
    subset_masks: list[int] = []
    while mask != 0:
        p = parent[r][mask]
        if p is None:
            raise RuntimeError(
                "DP parent trace missing — this indicates a bug in the DP."
            )
        prev_mask, sub_mask = p
        if sub_mask == 0:
            # Inherited from r-1 → use fewer routes
            r = r - 1
        else:
            subset_masks.append(sub_mask)
            mask = prev_mask
            r = r - 1

    # Build routes from the selected subset masks
    raw_routes: list[UAVRoute] = []
    total_hover_by_node: dict[int, float] = {}
    for sm in subset_masks:
        cand = candidates[sm]
        raw_routes.append(cand.route)
        for nid, hover_s in cand.route.hover_times_s.items():
            total_hover_by_node[nid] = (
                total_hover_by_node.get(nid, 0.0) + hover_s
            )

    # Assign real uav_id and sortie_id: one UAV per route, each with sortie_id=1
    assigned_routes: list[UAVRoute] = []
    for idx, rt in enumerate(raw_routes):
        assigned = UAVRoute(
            uav_id=idx + 1,
            sortie_id=1,
            node_sequence=rt.node_sequence,
            hover_times_s=dict(rt.hover_times_s),
        )
        assigned_routes.append(assigned)

    assigned_routes.sort(key=lambda r: (r.uav_id, r.sortie_id))
    route_count = len(assigned_routes)

    # Summarise (battery swap time is 0 because each UAV has exactly 1 sortie)
    summary = summarize_uav_solution(
        tuple(assigned_routes), data, battery_swap_time_s=0.0
    )

    # Verify that every target received exactly its base hover
    for target in data.targets:
        nid = target.node_id
        actual = total_hover_by_node.get(nid, 0.0)
        expected = target.base_hover_time_s
        if abs(actual - expected) > EPSILON:
            raise RuntimeError(
                f"Target {nid}: accumulated hover {actual:.6f}s != "
                f"expected {expected:.6f}s"
            )

    return TimePriorityProblem1Solution(
        k=k,
        routes=tuple(assigned_routes),
        total_hover_by_node=total_hover_by_node,
        summary=summary,
        solver_name=f"time_priority_dp_k{k}",
        route_count=route_count,
    )
