"""Exact enumeration of all direct-confirm sets for Problem 2 verification.

Enumerates all 2^16 = 65536 subsets of targets, rebuilds UAV routes for
each, evaluates closed-loop performance, and compares the rebuild search
solution against the global optimum found by enumeration.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import inf

from c_uav_inspection.data import ProblemData
from c_uav_inspection.model import summarize_uav_solution
from c_uav_inspection.objective import (
    bounds_from_candidates,
    weighted_normalized_objective,
)
from c_uav_inspection.problem2 import (
    _rebuild_for_direct_set,
    solve_joint_problem_for_k,
)

# ---------------------------------------------------------------------------
# Weights — same as PROBLEM2_WEIGHTS (plan section 2)
# ---------------------------------------------------------------------------
ENUMERATION_WEIGHTS: dict[str, float] = {
    "closed_loop_time_s": 0.45,
    "ground_review_time_s": 0.20,
    "weighted_manual_cost": 0.15,
    "manual_count": 0.10,
    "total_energy_j": 0.05,
    "load_std_s": 0.05,
}


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DirectSetEvaluation:
    """Closed-loop evaluation for a specific direct-confirm set.

    Attributes:
        direct_nodes: Node IDs selected for direct confirmation.
        feasible: Whether a feasible UAV route plan exists.
        closed_loop_time_s: Total closed-loop time (uav + ground).
        uav_phase_time_s: UAV phase duration.
        ground_review_time_s: Ground personnel review time.
        manual_count: Number of distinct manual review points.
        weighted_manual_cost: Sum of priority_weight over manual targets.
        direct_confirm_count: Number of directly confirmed targets.
        total_energy_j: Total UAV energy consumption.
        load_std_s: Standard deviation of UAV work times.
        route_count: Total number of UAV sorties.
        normalized_objective: Normalized multi-objective score (0..1).
    """

    direct_nodes: tuple[int, ...]
    feasible: bool
    closed_loop_time_s: float
    uav_phase_time_s: float
    ground_review_time_s: float
    manual_count: int
    weighted_manual_cost: int
    direct_confirm_count: int
    total_energy_j: float
    load_std_s: float
    route_count: int
    normalized_objective: float


@dataclass(frozen=True)
class DirectSetEnumerationResult:
    """Result of full enumeration over all direct-confirm subsets.

    Attributes:
        total_subsets: Total number of subsets enumerated (2^n).
        feasible_subsets: Number of subsets with feasible route plans.
        best_by_closed_loop: Best evaluation by closed_loop_time_s.
        best_by_objective: Best evaluation by normalized_objective.
        rebuild_solution: Evaluation of the rebuild search solution.
        rebuild_time_rank: Rank of rebuild solution by closed_loop_time_s.
        rebuild_time_gap_s: Gap to best closed_loop_time_s.
        rebuild_time_gap_pct: Gap as percentage of best closed_loop_time_s.
        rebuild_objective_rank: Rank of rebuild solution by normalized_objective.
        rebuild_objective_gap: Gap to best normalized_objective.
        top_by_closed_loop: Top N evaluations sorted by closed_loop_time_s.
        top_by_objective: Top N evaluations sorted by normalized_objective.
    """

    total_subsets: int
    feasible_subsets: int
    best_by_closed_loop: DirectSetEvaluation
    best_by_objective: DirectSetEvaluation
    rebuild_solution: DirectSetEvaluation | None
    rebuild_time_rank: int
    rebuild_time_gap_s: float
    rebuild_time_gap_pct: float
    rebuild_objective_rank: int
    rebuild_objective_gap: float
    top_by_closed_loop: tuple[DirectSetEvaluation, ...]
    top_by_objective: tuple[DirectSetEvaluation, ...]


# ---------------------------------------------------------------------------
# Infeasible sentinel (immutable)
# ---------------------------------------------------------------------------

_INFEASIBLE = DirectSetEvaluation(
    direct_nodes=(),
    feasible=False,
    closed_loop_time_s=inf,
    uav_phase_time_s=inf,
    ground_review_time_s=inf,
    manual_count=0,
    weighted_manual_cost=0,
    direct_confirm_count=0,
    total_energy_j=inf,
    load_std_s=inf,
    route_count=0,
    normalized_objective=inf,
)


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def _evaluate_direct_set(
    data: ProblemData,
    k: int,
    direct_nodes: tuple[int, ...],
    direct_threshold_multiplier: float = 1.0,
    allow_split_hover: bool = True,
) -> DirectSetEvaluation:
    """Evaluate closed-loop performance for a specific direct-confirm set.

    Rebuilds all UAV routes via _rebuild_for_direct_set and computes
    the full closed-loop metrics.

    Args:
        data: Problem dataset.
        k: Number of UAVs.
        direct_nodes: Node IDs to directly confirm.
        direct_threshold_multiplier: Multiplier for direct-confirm threshold.
        allow_split_hover: Whether hover can span multiple sorties.

    Returns:
        DirectSetEvaluation with feasibility and metrics.
    """
    result = _rebuild_for_direct_set(
        data, k, direct_nodes, direct_threshold_multiplier,
        allow_split_hover=allow_split_hover,
    )
    if result is None:
        return replace(_INFEASIBLE, direct_nodes=direct_nodes)

    sw = data.params.battery_swap_time_s
    summary = summarize_uav_solution(result.routes, data, sw)
    cl = result.closed_loop

    return DirectSetEvaluation(
        direct_nodes=direct_nodes,
        feasible=True,
        closed_loop_time_s=cl.closed_loop_time_s,
        uav_phase_time_s=cl.uav_phase_time_s,
        ground_review_time_s=cl.ground_review_time_s,
        manual_count=cl.manual_count,
        weighted_manual_cost=cl.weighted_manual_cost,
        direct_confirm_count=len(cl.direct_confirmed_nodes),
        total_energy_j=summary.total_energy_j,
        load_std_s=summary.load_std_s,
        route_count=len(result.routes),
        normalized_objective=0.0,  # placeholder — populated by normalizer
    )


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def _with_normalized_objectives(
    evaluations: list[DirectSetEvaluation],
) -> list[DirectSetEvaluation]:
    """Compute and attach normalized multi-objective scores.

    Only feasible evaluations participate in normalization bounds.
    Infeasible evaluations retain normalized_objective=inf.

    Args:
        evaluations: List of DirectSetEvaluation objects.

    Returns:
        New list with normalized_objective populated for feasible entries.
    """
    term_names = list(ENUMERATION_WEIGHTS.keys())
    feasible = [ev for ev in evaluations if ev.feasible]
    if not feasible:
        return list(evaluations)

    # Build candidate dicts for bounds computation
    candidates: list[dict[str, float]] = [
        {name: getattr(ev, name) for name in term_names} for ev in feasible
    ]
    bounds = bounds_from_candidates(candidates, term_names)

    # Score each feasible evaluation
    scored: list[DirectSetEvaluation] = []
    for ev in feasible:
        values = {name: getattr(ev, name) for name in term_names}
        score = weighted_normalized_objective(values, bounds, ENUMERATION_WEIGHTS)
        scored.append(replace(ev, normalized_objective=round(float(score), 6)))

    # Preserve original order
    result: list[DirectSetEvaluation] = []
    si = 0
    for ev in evaluations:
        if ev.feasible:
            result.append(scored[si])
            si += 1
        else:
            result.append(ev)
    return result


# ---------------------------------------------------------------------------
# Full enumeration
# ---------------------------------------------------------------------------


def enumerate_direct_confirm_sets(
    data: ProblemData,
    k: int,
    direct_threshold_multiplier: float = 1.0,
    allow_split_hover: bool = True,
    top_n: int = 20,
) -> DirectSetEnumerationResult:
    """Enumerate all 2^n direct-confirm subsets and rank by closed-loop metrics.

    Evaluates every possible subset of targets for direct confirmation,
    rebuilds UAV routes for each, and compares the rebuild search solution
    (solve_joint_problem_for_k) against the global optimum.

    Args:
        data: Problem dataset.
        k: Number of UAVs.
        direct_threshold_multiplier: Multiplier for direct-confirm threshold.
        allow_split_hover: Whether hover can span multiple sorties.
        top_n: Number of top evaluations to retain in each ranking.

    Returns:
        DirectSetEnumerationResult with full enumeration statistics.
    """
    node_ids = [t.node_id for t in data.targets]
    n = len(node_ids)
    total_subsets = 1 << n

    # Enumerate all subsets
    evaluations: list[DirectSetEvaluation] = []
    for mask in range(total_subsets):
        direct_nodes = tuple(
            node_ids[i] for i in range(n) if (mask >> i) & 1
        )
        ev = _evaluate_direct_set(
            data, k, direct_nodes, direct_threshold_multiplier,
            allow_split_hover=allow_split_hover,
        )
        evaluations.append(ev)

    # Normalize objectives across feasible evaluations
    evaluations = _with_normalized_objectives(evaluations)

    feasible_subsets = sum(1 for ev in evaluations if ev.feasible)

    # Sort by closed_loop_time_s ascending
    by_time = sorted(
        [ev for ev in evaluations if ev.feasible],
        key=lambda ev: ev.closed_loop_time_s,
    )
    # Sort by normalized_objective ascending
    by_obj = sorted(
        [ev for ev in evaluations if ev.feasible],
        key=lambda ev: ev.normalized_objective,
    )

    best_by_closed_loop = by_time[0] if by_time else _INFEASIBLE
    best_by_objective = by_obj[0] if by_obj else _INFEASIBLE

    # Rebuild search solution for comparison
    try:
        rebuild = solve_joint_problem_for_k(
            data, k, direct_threshold_multiplier,
            allow_split_hover=allow_split_hover,
        )
        sw = data.params.battery_swap_time_s
        rebuild_summary = summarize_uav_solution(rebuild.routes, data, sw)
        rebuild_cl = rebuild.closed_loop

        rebuild_direct = tuple(rebuild_cl.direct_confirmed_nodes)
        rebuild_eval = DirectSetEvaluation(
            direct_nodes=rebuild_direct,
            feasible=True,
            closed_loop_time_s=rebuild_cl.closed_loop_time_s,
            uav_phase_time_s=rebuild_cl.uav_phase_time_s,
            ground_review_time_s=rebuild_cl.ground_review_time_s,
            manual_count=rebuild_cl.manual_count,
            weighted_manual_cost=rebuild_cl.weighted_manual_cost,
            direct_confirm_count=len(rebuild_cl.direct_confirmed_nodes),
            total_energy_j=rebuild_summary.total_energy_j,
            load_std_s=rebuild_summary.load_std_s,
            route_count=len(rebuild.routes),
            normalized_objective=0.0,
        )
        # Normalize rebuild_eval within the same bounds
        rebuild_eval_list = _with_normalized_objectives([rebuild_eval])
        rebuild_eval = rebuild_eval_list[0]
    except Exception:
        rebuild_eval = None

    # Compute ranks and gaps
    if rebuild_eval is not None and by_time:
        rebuild_time_rank = _find_rank_by_time(by_time, rebuild_eval)
        best_time = by_time[0].closed_loop_time_s
        rebuild_time_gap_s = max(
            0.0, rebuild_eval.closed_loop_time_s - best_time
        )
        rebuild_time_gap_pct = (
            (rebuild_time_gap_s / best_time * 100.0) if best_time > 0 else 0.0
        )
    else:
        rebuild_time_rank = total_subsets + 1
        rebuild_time_gap_s = inf
        rebuild_time_gap_pct = inf

    if rebuild_eval is not None and by_obj:
        rebuild_objective_rank = _find_rank_by_obj(by_obj, rebuild_eval)
        best_obj = by_obj[0].normalized_objective
        rebuild_objective_gap = max(
            0.0, rebuild_eval.normalized_objective - best_obj
        )
        rebuild_objective_rank = rebuild_objective_rank
    else:
        rebuild_objective_rank = total_subsets + 1
        rebuild_objective_gap = inf

    return DirectSetEnumerationResult(
        total_subsets=total_subsets,
        feasible_subsets=feasible_subsets,
        best_by_closed_loop=best_by_closed_loop,
        best_by_objective=best_by_objective,
        rebuild_solution=rebuild_eval,
        rebuild_time_rank=rebuild_time_rank,
        rebuild_time_gap_s=round(rebuild_time_gap_s, 2),
        rebuild_time_gap_pct=round(rebuild_time_gap_pct, 4),
        rebuild_objective_rank=rebuild_objective_rank,
        rebuild_objective_gap=round(rebuild_objective_gap, 6),
        top_by_closed_loop=tuple(by_time[:top_n]),
        top_by_objective=tuple(by_obj[:top_n]),
    )


def _find_rank_by_time(
    by_time: list[DirectSetEvaluation],
    target: DirectSetEvaluation,
) -> int:
    """Find 1-based rank of target in the time-sorted list.

    For ties in closed_loop_time_s, the first occurrence gets the lower rank.
    """
    for idx, ev in enumerate(by_time):
        if ev.closed_loop_time_s >= target.closed_loop_time_s - 1e-9:
            return idx + 1
    return len(by_time) + 1


def _find_rank_by_obj(
    by_obj: list[DirectSetEvaluation],
    target: DirectSetEvaluation,
) -> int:
    """Find 1-based rank of target in the objective-sorted list.

    For ties in normalized_objective, the first occurrence gets the lower rank.
    """
    for idx, ev in enumerate(by_obj):
        if ev.normalized_objective >= target.normalized_objective - 1e-9:
            return idx + 1
    return len(by_obj) + 1
