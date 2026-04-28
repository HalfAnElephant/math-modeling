"""Problem 2: Closed-loop inspection with ground personnel review.

Implements the complete closed-loop evaluation where targets that receive
insufficient UAV hover time are reviewed by ground personnel. Includes
ground TSP optimization and rebuild search for direct-confirm set selection.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import inf

from c_uav_inspection.data import ProblemData, Target
from c_uav_inspection.model import (
    UAVRoute,
    summarize_uav_solution,
)
from c_uav_inspection.problem1 import solve_uav_hover_plan
from c_uav_inspection.search import InfeasibleError


@dataclass(frozen=True)
class GroundReviewResult:
    """Result of ground personnel TSP routing.

    Attributes:
        path: Ordered sequence of points visited, starts and ends at "P0".
        travel_time_s: Total walking travel time along the path.
        service_time_s: Total service time at all review points.
        total_time_s: Total ground time (travel + service).
    """

    path: tuple[str, ...]
    travel_time_s: float
    service_time_s: float
    total_time_s: float


@dataclass(frozen=True)
class ClosedLoopResult:
    """Result of closed-loop evaluation for a UAV solution.

    Attributes:
        direct_confirmed_nodes: Target node_ids that meet the effective
            direct-confirm threshold and are confirmed by UAV alone.
        manual_nodes: Manual point IDs requiring ground personnel review.
        manual_count: Number of distinct manual review points.
        uav_phase_time_s: UAV phase duration (from summarize_uav_solution).
        ground_review_time_s: Total time for ground personnel (TSP + service).
        closed_loop_time_s: Total closed-loop time = uav_phase + ground_review.
        ground_path: Optimal ground personnel visitation path.
    """

    direct_confirmed_nodes: tuple[int, ...]
    manual_nodes: tuple[str, ...]
    manual_count: int
    uav_phase_time_s: float
    ground_review_time_s: float
    closed_loop_time_s: float
    ground_path: tuple[str, ...]


def effective_direct_threshold(
    target: Target,
    direct_threshold_multiplier: float,
) -> float:
    """Compute the effective direct-confirm threshold for a target.

    The threshold is the maximum of base hover time and the scaled
    direct-confirm time. This ensures that the threshold never falls
    below the minimum hover time required for basic inspection.

    Args:
        target: The inspection target.
        direct_threshold_multiplier: Must be > 0. Typically in (0.7, 1.0+).

    Returns:
        Effective hover threshold in seconds.

    Raises:
        ValueError: If direct_threshold_multiplier <= 0.
    """
    if direct_threshold_multiplier <= 0:
        raise ValueError(
            f"direct_threshold_multiplier must be positive, "
            f"got {direct_threshold_multiplier}"
        )
    return max(
        target.base_hover_time_s,
        target.direct_confirm_time_s * direct_threshold_multiplier,
    )


def _deduplicate_manual_points(
    manual_point_ids: tuple[str, ...],
) -> list[str]:
    """Remove duplicates from manual point IDs while preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for pid in manual_point_ids:
        if pid not in seen:
            seen.add(pid)
            result.append(pid)
    return result


def _held_karp_tsp(
    points: list[str],
    ground_time_s: dict[tuple[str, str], float],
) -> tuple[tuple[str, ...], float]:
    """Solve ground TSP via Held-Karp dynamic programming.

    Finds the shortest path starting and ending at "P0" that visits
    all given points.

    Args:
        points: List of manual point IDs to visit (distinct).
        ground_time_s: Ground travel time matrix.

    Returns:
        Tuple of (optimal_path, total_travel_time).
    """
    n = len(points)
    if n == 0:
        return ("P0", "P0"), 0.0

    # Map each point to an index 0..n-1
    idx_to_point: dict[int, str] = {i: p for i, p in enumerate(points)}

    full_mask = (1 << n) - 1

    # DP[mask][i] = min travel time to visit all points in mask, ending at i
    dp: list[list[float]] = [[inf] * n for _ in range(1 << n)]
    # parent[mask][i] = previous point index for path reconstruction
    parent: list[list[int]] = [[-1] * n for _ in range(1 << n)]

    # Base cases: single point masks
    for i in range(n):
        point = idx_to_point[i]
        dp[1 << i][i] = ground_time_s[("P0", point)]
        parent[1 << i][i] = -1

    # Fill DP table
    for mask in range(1 << n):
        if mask & (mask - 1) == 0:
            continue  # Skip single-bit masks (already filled)
        for i in range(n):
            if not (mask & (1 << i)):
                continue
            prev_mask = mask ^ (1 << i)
            best_time: float = inf
            best_prev: int = -1
            for j in range(n):
                if not (prev_mask & (1 << j)):
                    continue
                candidate = dp[prev_mask][j] + ground_time_s[
                    (idx_to_point[j], idx_to_point[i])
                ]
                if candidate < best_time:
                    best_time = candidate
                    best_prev = j
            dp[mask][i] = best_time
            parent[mask][i] = best_prev

    # Find best endpoint (minimum travel including return to P0)
    best_total: float = inf
    best_last: int = -1
    for i in range(n):
        total = dp[full_mask][i] + ground_time_s[(idx_to_point[i], "P0")]
        if total < best_total:
            best_total = total
            best_last = i

    # Reconstruct path
    if best_last == -1:
        return ("P0", "P0"), 0.0

    path_indices: list[int] = []
    mask = full_mask
    curr = best_last
    while curr != -1:
        path_indices.append(curr)
        next_curr = parent[mask][curr]
        mask ^= 1 << curr
        curr = next_curr
    path_indices.reverse()

    path: list[str] = ["P0"]
    path.extend(idx_to_point[i] for i in path_indices)
    path.append("P0")

    return tuple(path), best_total


def solve_ground_tsp(
    data: ProblemData,
    manual_point_ids: tuple[str, ...],
) -> GroundReviewResult:
    """Solve the ground personnel TSP for a set of manual review points.

    Computes the shortest path starting and ending at "P0" that visits
    all distinct manual point IDs. Service time is the sum of
    manual_service_time_s for the distinct points.

    Args:
        data: Problem dataset.
        manual_point_ids: IDs of manual review points to visit.
            May contain duplicates; empty tuple means no ground work.

    Returns:
        GroundReviewResult with optimal path and timing.
    """
    distinct_points = _deduplicate_manual_points(manual_point_ids)

    if not distinct_points:
        return GroundReviewResult(
            path=("P0", "P0"),
            travel_time_s=0.0,
            service_time_s=0.0,
            total_time_s=0.0,
        )

    # Build mapping from manual_point_id to service time
    service_by_point: dict[str, float] = {}
    for target in data.targets:
        mp = target.manual_point_id
        if mp not in service_by_point:
            service_by_point[mp] = target.manual_service_time_s

    travel_path, travel_time = _held_karp_tsp(
        distinct_points, data.ground_time_s
    )

    total_service = sum(
        service_by_point.get(pid, 0.0) for pid in distinct_points
    )

    return GroundReviewResult(
        path=travel_path,
        travel_time_s=travel_time,
        service_time_s=total_service,
        total_time_s=travel_time + total_service,
    )


def evaluate_closed_loop(
    data: ProblemData,
    routes: tuple[UAVRoute, ...] | list[UAVRoute],
    direct_threshold_multiplier: float,
) -> ClosedLoopResult:
    """Evaluate the closed-loop performance for a given UAV route plan.

    Computes which targets are directly confirmed by UAV hover
    inspection and which require ground personnel review. The ground
    review time is computed via optimal TSP routing.

    Args:
        data: Problem dataset.
        routes: UAV routes (from Problem 1 or rebuild search).
        direct_threshold_multiplier: Multiplier for direct-confirm time.

    Returns:
        ClosedLoopResult with full closed-loop metrics.
    """
    # Accumulate total hover time per node
    hover_by_node: dict[int, float] = {}
    for route in routes:
        for node_id, seconds in route.hover_times_s.items():
            hover_by_node[node_id] = (
                hover_by_node.get(node_id, 0.0) + seconds
            )

    # Classify targets: direct-confirmed vs manual review needed
    direct_confirmed: list[int] = []
    manual_point_ids: list[str] = []

    for target in data.targets:
        threshold = effective_direct_threshold(target, direct_threshold_multiplier)
        cumulative = hover_by_node.get(target.node_id, 0.0)

        if cumulative >= threshold - 1e-9:  # EPSILON tolerance
            direct_confirmed.append(target.node_id)
        else:
            manual_point_ids.append(target.manual_point_id)

    # Compute UAV phase time
    summary = summarize_uav_solution(
        routes, data, data.params.battery_swap_time_s
    )
    uav_phase_time_s = summary.uav_phase_time_s

    # Solve ground TSP for manual review points
    ground_result = solve_ground_tsp(data, tuple(manual_point_ids))

    closed_loop_time_s = uav_phase_time_s + ground_result.total_time_s

    return ClosedLoopResult(
        direct_confirmed_nodes=tuple(direct_confirmed),
        manual_nodes=tuple(sorted(set(manual_point_ids))),
        manual_count=len(set(manual_point_ids)),
        uav_phase_time_s=uav_phase_time_s,
        ground_review_time_s=ground_result.total_time_s,
        closed_loop_time_s=closed_loop_time_s,
        ground_path=ground_result.path,
    )


@dataclass(frozen=True)
class JointSolution:
    """Complete solution for Problem 2 (joint UAV + ground optimization).

    Attributes:
        routes: All UAV sorties for the optimized plan.
        closed_loop: Closed-loop evaluation results.
    """

    routes: tuple[UAVRoute, ...]
    closed_loop: ClosedLoopResult


def _find_target(data: ProblemData, node_id: int) -> Target:
    """Look up a target by its node_id."""
    for t in data.targets:
        if t.node_id == node_id:
            return t
    raise KeyError(f"Target with node_id {node_id} not found in data")


def _direct_confirm_score(
    data: ProblemData,
    target_id: int,
    direct_threshold_multiplier: float,
) -> float:
    """Compute the benefit/cost score for trying to direct-confirm a target.

    Higher score means more promising to attempt direct confirmation.
    Score = ground_savings_s / (1 + energy_penalty + extra_hover_cost), where:
      - ground_savings_s = RTT to manual point + service time (avoided ground work)
      - energy_penalty = roundtrip flight energy / sortie energy limit
        (measures how much of a sortie's energy budget is consumed just
        reaching this target)
      - extra_hover_cost = extra_hover_s / base_hover_time_s
        (additional hover seconds beyond base, normalized by base hover time;
        penalizes targets that require large increases in UAV hover duty)

    The three components follow the plan specification:
      1. extra hover = effective_threshold - base_hover_time_s (cost)
      2. ground savings = P0 roundtrip to manual point + service time (benefit)
      3. energy penalty = roundtrip flight energy / sortie energy limit (cost)

    Args:
        data: Problem dataset.
        target_id: Node ID of the candidate target.
        direct_threshold_multiplier: Multiplier for direct-confirm threshold.

    Returns:
        Benefit/cost score (higher is better for direct confirmation).
    """
    target = _find_target(data, target_id)
    base_hover = target.base_hover_time_s

    # 1. Extra hover cost: additional hover seconds needed to reach the
    #    effective direct-confirm threshold, normalized by base hover time.
    effective = effective_direct_threshold(target, direct_threshold_multiplier)
    extra_hover_s = max(0.0, effective - base_hover)
    extra_hover_cost = (
        extra_hover_s / max(base_hover, 1.0)
    )

    # 2. Ground time savings if we avoid manual review
    mp = target.manual_point_id
    ground_savings = (
        data.ground_time_s.get(("P0", mp), 0.0)
        + data.ground_time_s.get((mp, "P0"), 0.0)
        + target.manual_service_time_s
    )

    # 3. Energy penalty: how much of a single sortie is consumed by reaching
    #    and returning from this target
    roundtrip_energy = (
        data.flight_energy_j[(0, target_id)]
        + data.flight_energy_j[(target_id, 0)]
    )
    energy_penalty = (
        roundtrip_energy / data.params.effective_energy_limit_j
        if data.params.effective_energy_limit_j > 0
        else 1.0
    )

    return ground_savings / (1.0 + max(energy_penalty, 0.0) + extra_hover_cost)


def _hover_requirements_for_direct_set(
    data: ProblemData,
    direct_nodes: tuple[int, ...],
    direct_threshold_multiplier: float,
) -> dict[int, float]:
    """Compute hover requirements when a specific set of targets is to be
    directly confirmed.

    Targets in direct_nodes must receive at least their effective
    direct-confirm threshold; all others receive base hover time.

    Args:
        data: Problem dataset.
        direct_nodes: Node IDs to directly confirm.
        direct_threshold_multiplier: Multiplier for direct-confirm threshold.

    Returns:
        Dict mapping node_id -> required hover seconds.
    """
    direct_set = set(direct_nodes)
    requirements: dict[int, float] = {}
    for target in data.targets:
        if target.node_id in direct_set:
            requirements[target.node_id] = effective_direct_threshold(
                target, direct_threshold_multiplier
            )
        else:
            requirements[target.node_id] = target.base_hover_time_s
    return requirements


def _rebuild_for_direct_set(
    data: ProblemData,
    k: int,
    direct_nodes: tuple[int, ...],
    direct_threshold_multiplier: float,
) -> JointSolution | None:
    """Rebuild all UAV routes for a given direct-confirm set.

    Computes hover requirements, re-plans routes with improve=True,
    and evaluates closed-loop performance.

    Returns None if any route is energy-infeasible or the UAV phase
    exceeds the operating horizon.

    Args:
        data: Problem dataset.
        k: Number of UAVs.
        direct_nodes: Node IDs to directly confirm.
        direct_threshold_multiplier: Multiplier for direct-confirm threshold.

    Returns:
        JointSolution if feasible, None otherwise.
    """
    try:
        requirements = _hover_requirements_for_direct_set(
            data, direct_nodes, direct_threshold_multiplier
        )
        solution = solve_uav_hover_plan(
            data,
            k,
            data.params.battery_swap_time_s,
            requirements,
            improve=True,
        )
    except InfeasibleError:
        return None

    if not solution.summary.feasible_energy:
        return None
    if solution.summary.uav_phase_time_s > data.params.operating_horizon_s:
        return None

    closed = evaluate_closed_loop(data, solution.routes, direct_threshold_multiplier)
    return JointSolution(routes=solution.routes, closed_loop=closed)


def solve_joint_problem_for_k(
    data: ProblemData,
    k: int,
    direct_threshold_multiplier: float,
) -> JointSolution:
    """Solve Problem 2: joint UAV+ground optimization via rebuild search.

    Starting from a base solution with no direct confirmation, this
    iteratively tries to add promising targets to the direct-confirm set.
    Each candidate triggers a complete route rebuild. A candidate is
    accepted if:
      - closed_loop_time strictly decreases; or
      - manual_count decreases and closed_loop_time is within 1.03x of
        the current best.

    IMPORTANT: This uses rebuild search (ruin-and-recreate), not greedy
    single-point modification.

    Args:
        data: Problem dataset.
        k: Number of UAVs.
        direct_threshold_multiplier: Multiplier for direct-confirm threshold.

    Returns:
        JointSolution with optimized routes and closed-loop results.
    """
    # Start with empty direct confirm set (all targets base hover only)
    empty_direct: tuple[int, ...] = ()
    current = _rebuild_for_direct_set(
        data, k, empty_direct, direct_threshold_multiplier
    )
    if current is None:
        raise RuntimeError(
            "Base solution (all base hover) is infeasible — check data"
        )

    # Score all candidates
    candidates = [
        (target.node_id, _direct_confirm_score(
            data, target.node_id, direct_threshold_multiplier
        ))
        for target in data.targets
    ]
    candidates.sort(key=lambda x: x[1], reverse=True)

    # Track which targets we've tried (avoid redundant rebuilds)
    current_direct_set = set(current.closed_loop.direct_confirmed_nodes)

    for node_id, _score in candidates:
        if node_id in current_direct_set:
            continue

        # Try adding this candidate to the direct-confirm set
        new_direct_set = tuple(sorted(current_direct_set | {node_id}))
        candidate_solution = _rebuild_for_direct_set(
            data, k, new_direct_set, direct_threshold_multiplier
        )

        if candidate_solution is None:
            continue

        # Acceptance criteria
        new_closed_time = candidate_solution.closed_loop.closed_loop_time_s
        cur_closed_time = current.closed_loop.closed_loop_time_s
        new_manual = candidate_solution.closed_loop.manual_count
        cur_manual = current.closed_loop.manual_count

        accepted = False
        if new_closed_time < cur_closed_time - 1e-9:
            accepted = True
        elif new_manual < cur_manual and new_closed_time <= cur_closed_time * 1.03 + 1e-9:
            accepted = True

        if accepted:
            current = candidate_solution
            current_direct_set = set(current.closed_loop.direct_confirmed_nodes)

    return current
