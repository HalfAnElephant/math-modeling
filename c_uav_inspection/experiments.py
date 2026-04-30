"""Experiment runner: generates CSV/JSON result files for all scenarios.

Produces K-comparison tables, sensitivity analyses, data validation, and a
recommended solution summary for both Problem 1 and Problem 2.
"""

from __future__ import annotations

import csv
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from c_uav_inspection.data import ProblemData, load_problem_data, validate_problem_data
from c_uav_inspection.model import UAVRoute, evaluate_uav_route, summarize_uav_solution
from c_uav_inspection.objective import (
    bounds_from_candidates,
    pareto_front,
    score_with_fixed_bounds,
    weighted_normalized_objective,
)
from c_uav_inspection.problem1 import solve_problem1_for_k
from c_uav_inspection.problem1_time import (
    precompute_problem1_subset_routes,
    solve_problem1_time_priority_for_k,
)
from c_uav_inspection.problem2 import (
    solve_all_direct_confirm_baseline,
    solve_ground_tsp,
    solve_joint_problem_for_k,
)
from c_uav_inspection.exact import (
    DirectSetEvaluation,
    enumerate_direct_confirm_sets,
)
from c_uav_inspection.search import InfeasibleError

# ---------------------------------------------------------------------------
# Problem 2 weights (plan section 2)
# ---------------------------------------------------------------------------
PROBLEM2_WEIGHTS: dict[str, float] = {
    "closed_loop_time_s": 0.45,
    "ground_review_time_s": 0.20,
    "weighted_manual_cost": 0.15,
    "manual_count": 0.10,
    "total_energy_j": 0.05,
    "load_std_s": 0.05,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write rows to a CSV file using UTF-8 with headers."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, data: Any) -> None:
    """Write a JSON-serialisable object to path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False, default=str)


def _serialize_direct_set_eval(ev: DirectSetEvaluation) -> dict[str, Any]:
    """Convert a DirectSetEvaluation to a CSV-serialisable dict."""
    return {
        "direct_nodes": ",".join(str(n) for n in ev.direct_nodes),
        "feasible": ev.feasible,
        "closed_loop_time_s": ev.closed_loop_time_s,
        "uav_phase_time_s": ev.uav_phase_time_s,
        "ground_review_time_s": ev.ground_review_time_s,
        "manual_count": ev.manual_count,
        "weighted_manual_cost": ev.weighted_manual_cost,
        "direct_confirm_count": ev.direct_confirm_count,
        "total_energy_j": ev.total_energy_j,
        "load_std_s": ev.load_std_s,
        "route_count": ev.route_count,
        "normalized_objective": ev.normalized_objective,
    }


def _add_normalized_objective(
    rows: list[dict[str, Any]],
    weights: dict[str, float],
) -> list[dict[str, Any]]:
    """Return new rows with 'normalized_objective' column added.

    The input *rows* are never mutated — each returned dict is a shallow copy
    augmented with the computed score column.
    """
    term_names = list(weights.keys())
    bounds = bounds_from_candidates(rows, term_names)
    result: list[dict[str, Any]] = []
    for row in rows:
        values = {name: row[name] for name in term_names}
        score = weighted_normalized_objective(values, bounds, weights)
        new_row = {**row, "normalized_objective": round(score, 6)}
        result.append(new_row)
    return result


# ---------------------------------------------------------------------------
# Problem 1 experiments
# ---------------------------------------------------------------------------


def _run_problem1_k_comparison(data, output_dir: Path) -> None:
    """Problem 1 K-comparison using the current packed split-hover solver.

    Output: problem1_k_comparison_current_packed.csv
    """
    rows: list[dict[str, Any]] = []
    sw = data.params.battery_swap_time_s

    for k in range(1, 5):
        sol = solve_problem1_for_k(data, k, sw, improve=True)
        summary = summarize_uav_solution(sol.routes, data, sw)
        rows.append({
            "k": k,
            "solver_name": "current_packed_split_hover",
            "uav_phase_time_s": summary.uav_phase_time_s,
            "total_energy_j": summary.total_energy_j,
            "load_std_s": summary.load_std_s,
            "route_count": len(sol.routes),
        })

    rows = _add_normalized_objective(rows, {
        "uav_phase_time_s": 1.0, "total_energy_j": 0.0, "load_std_s": 0.0,
    })
    _write_csv(output_dir / "problem1_k_comparison_current_packed.csv", rows)


def _run_problem1_swap_sensitivity(data, output_dir: Path) -> None:
    """Swap sensitivity for K=1 where battery swap is on the critical path.

    With a single UAV executing multiple sorties, battery swap time
    between consecutive sorties directly adds to the phase time.

    Output: problem1_swap_sensitivity_k1.csv
    """
    rows: list[dict[str, Any]] = []
    k = 1

    for swap_s in (0, 150, 300, 450, 600):
        sol = solve_problem1_for_k(data, k, float(swap_s), improve=True)
        summary = summarize_uav_solution(sol.routes, data, float(swap_s))
        rows.append({
            "k": k,
            "battery_swap_time_s": swap_s,
            "uav_phase_time_s": summary.uav_phase_time_s,
            "total_energy_j": summary.total_energy_j,
            "load_std_s": summary.load_std_s,
            "route_count": len(sol.routes),
        })

    rows = _add_normalized_objective(rows, {
        "uav_phase_time_s": 1.0, "total_energy_j": 0.0, "load_std_s": 0.0,
    })
    _write_csv(output_dir / "problem1_swap_sensitivity_k1.csv", rows)


def _run_problem1_swap_sensitivity_k4_reference(
    data: ProblemData, output_dir: Path,
) -> None:
    """Swap sensitivity for K=4 as a reference comparison.

    With K=4 and only 2 sorties generated, at most 2 UAVs are used.
    No single UAV executes consecutive sorties, so battery swap time
    never enters the critical path.

    Output: problem1_swap_sensitivity_k4_reference.csv
    """
    rows: list[dict[str, Any]] = []
    k = data.params.k_max

    for swap_s in (0, 150, 300, 450, 600):
        sol = solve_problem1_for_k(data, k, float(swap_s), improve=True)
        summary = summarize_uav_solution(sol.routes, data, float(swap_s))
        rows.append({
            "k": k,
            "battery_swap_time_s": swap_s,
            "uav_phase_time_s": summary.uav_phase_time_s,
            "total_energy_j": summary.total_energy_j,
            "load_std_s": summary.load_std_s,
            "route_count": len(sol.routes),
            "notes": "K=4, 仅2趟航次分配给至多2架无人机, 每架最多1趟, 换电不进入关键路径",
        })

    rows = _add_normalized_objective(rows, {
        "uav_phase_time_s": 1.0, "total_energy_j": 0.0, "load_std_s": 0.0,
    })
    _write_csv(output_dir / "problem1_swap_sensitivity_k4_reference.csv", rows)


def _run_problem1_time_priority_k_comparison(
    data: ProblemData, output_dir: Path,
) -> None:
    """Problem 1 K-comparison using the time-priority DP solver.

    Output: problem1_time_priority_k_comparison.csv
    """
    rows: list[dict[str, Any]] = []

    # Precompute subset routes once for all k values (CR-007)
    candidates = precompute_problem1_subset_routes(data, improve=True)

    for k in range(1, 5):
        try:
            sol = solve_problem1_time_priority_for_k(
                data, k, improve=True, candidates=candidates,
            )
            rows.append({
                "k": k,
                "solver_name": sol.solver_name,
                "feasible": True,
                "uav_phase_time_s": sol.summary.uav_phase_time_s,
                "total_energy_j": sol.summary.total_energy_j,
                "load_std_s": sol.summary.load_std_s,
                "route_count": sol.route_count,
            })
        except InfeasibleError:
            rows.append({
                "k": k,
                "solver_name": f"time_priority_dp_k{k}",
                "feasible": False,
                "uav_phase_time_s": "",
                "total_energy_j": "",
                "load_std_s": "",
                "route_count": "",
            })

    # Normalize only the feasible rows
    feasible = [r for r in rows if r["feasible"] is True]
    if feasible:
        feasible = _add_normalized_objective(feasible, {
            "uav_phase_time_s": 1.0, "total_energy_j": 0.0, "load_std_s": 0.0,
        })
        # Rebuild rows preserving order: insert normalized values where feasible
        result: list[dict[str, Any]] = []
        fi = 0
        for r in rows:
            if r["feasible"] is True:
                result.append(feasible[fi])
                fi += 1
            else:
                result.append({**r, "normalized_objective": ""})
        rows = result

    _write_csv(output_dir / "problem1_time_priority_k_comparison.csv", rows)


def _run_problem1_parallel_route_count_ablation(
    data: ProblemData, output_dir: Path,
) -> None:
    """Ablation: what happens when we vary the route budget from 1 to 4?

    Output: problem1_parallel_route_count_ablation.csv
    """
    rows: list[dict[str, Any]] = []

    # Precompute subset routes once for all route_budget values (CR-007)
    candidates = precompute_problem1_subset_routes(data, improve=True)

    for route_budget in (1, 2, 3, 4):
        try:
            sol = solve_problem1_time_priority_for_k(
                data, route_budget, improve=True, candidates=candidates,
            )
            actual_max_e = max(
                evaluate_uav_route(r, data).energy_j for r in sol.routes
            )
            rows.append({
                "route_budget": route_budget,
                "feasible": True,
                "uav_phase_time_s": sol.summary.uav_phase_time_s,
                "total_energy_j": sol.summary.total_energy_j,
                "route_count": sol.route_count,
                "max_route_energy_j": round(actual_max_e, 2),
                "notes": "",
            })
        except InfeasibleError:
            rows.append({
                "route_budget": route_budget,
                "feasible": False,
                "uav_phase_time_s": "",
                "total_energy_j": "",
                "route_count": "",
                "max_route_energy_j": "",
                "notes": (
                    f"no feasible partition with ≤{route_budget} routes"
                ),
            })

    _write_csv(output_dir / "problem1_parallel_route_count_ablation.csv", rows)


def _solve_base_only_closed_loop(data: ProblemData, k: int) -> dict[str, Any]:
    """Compute closed-loop metrics for base-only inspection (alpha->inf).

    All targets receive only base hover time, so zero targets are directly
    confirmed.  All manual points must be visited by ground personnel.
    """
    sw = data.params.battery_swap_time_s
    sol = solve_problem1_for_k(data, k, sw, improve=True)
    summary = summarize_uav_solution(sol.routes, data, sw)
    manual_points = tuple(target.manual_point_id for target in data.targets)
    ground = solve_ground_tsp(data, manual_points)
    weighted_manual_cost = sum(target.priority_weight for target in data.targets)

    return {
        "scheme": "仅基础巡检(alpha->inf)",
        "k": k,
        "direct_threshold_multiplier": "inf",
        "uav_phase_time_s": summary.uav_phase_time_s,
        "ground_review_time_s": ground.total_time_s,
        "closed_loop_time_s": summary.uav_phase_time_s + ground.total_time_s,
        "manual_count": len(set(manual_points)),
        "weighted_manual_cost": weighted_manual_cost,
        "direct_confirm_count": 0,
        "total_energy_j": summary.total_energy_j,
        "load_std_s": summary.load_std_s,
    }


def _run_problem2_baseline_comparison(
    data: ProblemData, output_dir: Path,
) -> None:
    """Compare base-only closed-loop (alpha->inf) with recommended joint solution.

    Output: problem2_baseline_comparison.csv
    """
    k = data.params.k_max
    sw = data.params.battery_swap_time_s
    base_row = _solve_base_only_closed_loop(data, k)

    joint = solve_joint_problem_for_k(data, k, 1.0)
    summary = summarize_uav_solution(joint.routes, data, sw)
    joint_row = {
        "scheme": "推荐方案(K=4, alpha=1.0)",
        "k": k,
        "direct_threshold_multiplier": 1.0,
        "uav_phase_time_s": joint.closed_loop.uav_phase_time_s,
        "ground_review_time_s": joint.closed_loop.ground_review_time_s,
        "closed_loop_time_s": joint.closed_loop.closed_loop_time_s,
        "manual_count": joint.closed_loop.manual_count,
        "weighted_manual_cost": joint.closed_loop.weighted_manual_cost,
        "direct_confirm_count": len(joint.closed_loop.direct_confirmed_nodes),
        "total_energy_j": summary.total_energy_j,
        "load_std_s": summary.load_std_s,
    }

    _write_csv(output_dir / "problem2_baseline_comparison.csv", [base_row, joint_row])


# ---------------------------------------------------------------------------
# Problem 2 experiments
# ---------------------------------------------------------------------------


def _run_problem2_k_comparison(data, output_dir: Path) -> None:
    rows: list[dict[str, Any]] = []
    multiplier = 1.0
    sw = data.params.battery_swap_time_s

    for k in range(1, 5):
        sol = solve_joint_problem_for_k(data, k, multiplier)
        summary = summarize_uav_solution(sol.routes, data, sw)
        rows.append({
            "k": k,
            "closed_loop_time_s": sol.closed_loop.closed_loop_time_s,
            "uav_phase_time_s": sol.closed_loop.uav_phase_time_s,
            "ground_review_time_s": sol.closed_loop.ground_review_time_s,
            "manual_count": sol.closed_loop.manual_count,
            "weighted_manual_cost": sol.closed_loop.weighted_manual_cost,
            "direct_confirm_count": len(sol.closed_loop.direct_confirmed_nodes),
            "total_energy_j": summary.total_energy_j,
            "load_std_s": summary.load_std_s,
        })

    rows = _add_normalized_objective(rows, PROBLEM2_WEIGHTS)
    _write_csv(output_dir / "problem2_k_comparison.csv", rows)


def _run_problem2_threshold_sensitivity(data, output_dir: Path) -> None:
    rows: list[dict[str, Any]] = []
    k = data.params.k_max
    sw = data.params.battery_swap_time_s

    for mult in (0.70, 0.85, 1.00, 1.15, 1.30):
        sol = solve_joint_problem_for_k(data, k, mult)
        summary = summarize_uav_solution(sol.routes, data, sw)
        rows.append({
            "direct_threshold_multiplier": mult,
            "closed_loop_time_s": sol.closed_loop.closed_loop_time_s,
            "uav_phase_time_s": sol.closed_loop.uav_phase_time_s,
            "ground_review_time_s": sol.closed_loop.ground_review_time_s,
            "manual_count": sol.closed_loop.manual_count,
            "weighted_manual_cost": sol.closed_loop.weighted_manual_cost,
            "direct_confirm_count": len(sol.closed_loop.direct_confirmed_nodes),
            "total_energy_j": summary.total_energy_j,
            "load_std_s": summary.load_std_s,
        })

    rows = _add_normalized_objective(rows, PROBLEM2_WEIGHTS)
    _write_csv(output_dir / "problem2_threshold_sensitivity.csv", rows)


def _node_tuple_to_string(nodes: tuple[int, ...]) -> str:
    """Format a tuple of node IDs as a space-separated string."""
    return " ".join(str(n) for n in nodes)


def _run_problem2_acceptance_tolerance_sensitivity(
    data: ProblemData, output_dir: Path,
) -> None:
    """Sensitivity of closed-loop results to the rebuild-search acceptance tolerance.

    Tests how varying manual_reduction_time_tolerance affects the search's
    willingness to accept a candidate that increases closed_loop_time_s in
    exchange for reducing manual_count or weighted_manual_cost.

    Output: problem2_acceptance_tolerance_sensitivity.csv
    """
    rows: list[dict[str, Any]] = []
    k = data.params.k_max
    multiplier = 1.0
    sw = data.params.battery_swap_time_s

    for tol in (1.00, 1.03, 1.05, 1.10):
        sol = solve_joint_problem_for_k(
            data, k, multiplier,
            manual_reduction_time_tolerance=tol,
        )
        summary = summarize_uav_solution(sol.routes, data, sw)
        rows.append({
            "manual_reduction_time_tolerance": tol,
            "closed_loop_time_s": sol.closed_loop.closed_loop_time_s,
            "uav_phase_time_s": sol.closed_loop.uav_phase_time_s,
            "ground_review_time_s": sol.closed_loop.ground_review_time_s,
            "manual_count": sol.closed_loop.manual_count,
            "weighted_manual_cost": sol.closed_loop.weighted_manual_cost,
            "direct_confirm_count": len(sol.closed_loop.direct_confirmed_nodes),
            "total_energy_j": summary.total_energy_j,
            "load_std_s": summary.load_std_s,
            "direct_confirmed_nodes": _node_tuple_to_string(
                sol.closed_loop.direct_confirmed_nodes
            ),
            "manual_target_nodes": _node_tuple_to_string(
                sol.closed_loop.manual_target_nodes
            ),
        })

    _write_csv(output_dir / "problem2_acceptance_tolerance_sensitivity.csv", rows)


def _run_problem2_energy_limit_sensitivity(
    data: ProblemData, output_dir: Path,
) -> None:
    """Sensitivity of closed-loop results to the effective energy limit.

    Varies effective_energy_limit_j using dataclasses.replace and handles
    infeasible cases where the modified energy budget cannot satisfy the
    base hover requirements.

    Output: problem2_energy_limit_sensitivity.csv
    """
    rows: list[dict[str, Any]] = []
    k = data.params.k_max
    multiplier = 1.0
    sw = data.params.battery_swap_time_s
    base_energy = data.params.effective_energy_limit_j

    for factor, energy_j in ((0.90, base_energy * 0.90), (1.00, base_energy), (1.10, base_energy * 1.10)):
        new_params = replace(data.params, effective_energy_limit_j=energy_j)
        new_data = replace(data, params=new_params)

        try:
            sol = solve_joint_problem_for_k(new_data, k, multiplier)
            summary = summarize_uav_solution(sol.routes, new_data, sw)
            rows.append({
                "effective_energy_limit_j": energy_j,
                "feasible": True,
                "route_count": len(sol.routes),
                "closed_loop_time_s": sol.closed_loop.closed_loop_time_s,
                "uav_phase_time_s": sol.closed_loop.uav_phase_time_s,
                "ground_review_time_s": sol.closed_loop.ground_review_time_s,
                "manual_count": sol.closed_loop.manual_count,
                "weighted_manual_cost": sol.closed_loop.weighted_manual_cost,
                "direct_confirm_count": len(sol.closed_loop.direct_confirmed_nodes),
                "direct_confirmed_nodes": _node_tuple_to_string(sol.closed_loop.direct_confirmed_nodes),
                "manual_target_nodes": _node_tuple_to_string(sol.closed_loop.manual_target_nodes),
                "manual_nodes": _node_tuple_to_string(sol.closed_loop.manual_nodes),
                "total_energy_j": summary.total_energy_j,
                "load_std_s": summary.load_std_s,
            })
        except (InfeasibleError, RuntimeError):
            rows.append({
                "effective_energy_limit_j": energy_j,
                "feasible": False,
                "route_count": "",
                "closed_loop_time_s": "",
                "uav_phase_time_s": "",
                "ground_review_time_s": "",
                "manual_count": "",
                "weighted_manual_cost": "",
                "direct_confirm_count": "",
                "total_energy_j": "",
                "load_std_s": "",
            })

    _write_csv(output_dir / "problem2_energy_limit_sensitivity.csv", rows)


def _run_problem2_hover_power_sensitivity(
    data: ProblemData, output_dir: Path,
) -> None:
    """Sensitivity of closed-loop results to the UAV hover power.

    Varies hover_power_j_per_s using dataclasses.replace and handles
    infeasible cases where the modified hover power makes base hover
    requirements exceed the energy budget.

    Output: problem2_hover_power_sensitivity.csv
    """
    rows: list[dict[str, Any]] = []
    k = data.params.k_max
    multiplier = 1.0
    sw = data.params.battery_swap_time_s
    base_hover = data.params.hover_power_j_per_s

    for factor, hover_j in ((0.90, base_hover * 0.90), (1.00, base_hover), (1.10, base_hover * 1.10)):
        new_params = replace(data.params, hover_power_j_per_s=hover_j)
        new_data = replace(data, params=new_params)

        try:
            sol = solve_joint_problem_for_k(new_data, k, multiplier)
            summary = summarize_uav_solution(sol.routes, new_data, sw)
            rows.append({
                "hover_power_j_per_s": hover_j,
                "feasible": True,
                "route_count": len(sol.routes),
                "closed_loop_time_s": sol.closed_loop.closed_loop_time_s,
                "uav_phase_time_s": sol.closed_loop.uav_phase_time_s,
                "ground_review_time_s": sol.closed_loop.ground_review_time_s,
                "manual_count": sol.closed_loop.manual_count,
                "weighted_manual_cost": sol.closed_loop.weighted_manual_cost,
                "direct_confirm_count": len(sol.closed_loop.direct_confirmed_nodes),
                "direct_confirmed_nodes": _node_tuple_to_string(sol.closed_loop.direct_confirmed_nodes),
                "manual_target_nodes": _node_tuple_to_string(sol.closed_loop.manual_target_nodes),
                "manual_nodes": _node_tuple_to_string(sol.closed_loop.manual_nodes),
                "total_energy_j": summary.total_energy_j,
                "load_std_s": summary.load_std_s,
            })
        except (InfeasibleError, RuntimeError):
            rows.append({
                "hover_power_j_per_s": hover_j,
                "feasible": False,
                "route_count": "",
                "closed_loop_time_s": "",
                "uav_phase_time_s": "",
                "ground_review_time_s": "",
                "manual_count": "",
                "weighted_manual_cost": "",
                "direct_confirm_count": "",
                "total_energy_j": "",
                "load_std_s": "",
            })

    _write_csv(output_dir / "problem2_hover_power_sensitivity.csv", rows)


# ---------------------------------------------------------------------------
# Recommended solution
# ---------------------------------------------------------------------------


def _serialize_route(route: UAVRoute) -> dict[str, Any]:
    """Convert a UAVRoute to a JSON-serialisable dict."""
    return {
        "uav_id": route.uav_id,
        "sortie_id": route.sortie_id,
        "node_sequence": list(route.node_sequence),
        "hover_times_s": {
            str(k): v for k, v in route.hover_times_s.items()
        },
    }


def _run_problem2_split_hover_ablation(
    data: ProblemData, output_dir: Path,
) -> None:
    """Ablation: compare split-hover vs no-split-hover in Problem 2.

    Runs solve_joint_problem_for_k with allow_split_hover=True and
    allow_split_hover=False for K=4, multiplier=1.0. Outputs a CSV
    comparing closed-loop metrics between the two strategies, including
    the normalized multi-objective score C_M.

    Output: problem2_split_hover_ablation.csv
    """
    rows: list[dict[str, Any]] = []
    k = data.params.k_max
    multiplier = 1.0
    sw = data.params.battery_swap_time_s

    for allow_split in (True, False):
        label = "可拆分悬停" if allow_split else "不可拆分悬停"
        try:
            joint = solve_joint_problem_for_k(
                data, k, multiplier, allow_split_hover=allow_split,
            )
            summary = summarize_uav_solution(joint.routes, data, sw)
            rows.append({
                "scheme": label,
                "allow_split_hover": allow_split,
                "k": k,
                "direct_threshold_multiplier": multiplier,
                "closed_loop_time_s": joint.closed_loop.closed_loop_time_s,
                "uav_phase_time_s": joint.closed_loop.uav_phase_time_s,
                "ground_review_time_s": joint.closed_loop.ground_review_time_s,
                "manual_count": joint.closed_loop.manual_count,
                "weighted_manual_cost": joint.closed_loop.weighted_manual_cost,
                "direct_confirm_count": len(
                    joint.closed_loop.direct_confirmed_nodes
                ),
                "total_energy_j": summary.total_energy_j,
                "load_std_s": summary.load_std_s,
                "route_count": len(joint.routes),
                "feasible": True,
            })
        except InfeasibleError:
            rows.append({
                "scheme": label,
                "allow_split_hover": allow_split,
                "k": k,
                "direct_threshold_multiplier": multiplier,
                "closed_loop_time_s": "",
                "uav_phase_time_s": "",
                "ground_review_time_s": "",
                "manual_count": "",
                "weighted_manual_cost": "",
                "direct_confirm_count": "",
                "total_energy_j": "",
                "load_std_s": "",
                "route_count": "",
                "feasible": False,
            })

    # Add normalized multi-objective score (C_M) per subplan 04 architecture.
    # Only feasible rows participate in normalization; infeasible rows get "".
    feasible = [r for r in rows if r["feasible"] is True]
    if feasible:
        feasible = _add_normalized_objective(feasible, PROBLEM2_WEIGHTS)
        fi = 0
        result: list[dict[str, Any]] = []
        for r in rows:
            if r["feasible"] is True:
                result.append(feasible[fi])
                fi += 1
            else:
                result.append({**r, "normalized_objective": ""})
        rows = result
    _write_csv(output_dir / "problem2_split_hover_ablation.csv", rows)


def _run_problem2_exact_enumeration(
    data: ProblemData, output_dir: Path,
) -> None:
    """Enumerate all direct-confirm subsets for Problem 2 verification.

    Outputs:
      - problem2_exact_summary.json – top-level enumeration statistics
      - problem2_exact_top.csv – top evaluations by closed_loop_time_s and
        normalized_objective
    """
    k = data.params.k_max
    result = enumerate_direct_confirm_sets(
        data, k, direct_threshold_multiplier=1.0, top_n=20,
    )

    # Summary JSON
    summary: dict[str, Any] = {
        "total_subsets": result.total_subsets,
        "feasible_subsets": result.feasible_subsets,
        "best_by_closed_loop": _serialize_direct_set_eval(
            result.best_by_closed_loop,
        ),
        "best_by_objective": _serialize_direct_set_eval(
            result.best_by_objective,
        ),
        "rebuild_solution": (
            _serialize_direct_set_eval(result.rebuild_solution)
            if result.rebuild_solution is not None
            else None
        ),
        "rebuild_time_rank": result.rebuild_time_rank,
        "rebuild_time_gap_s": result.rebuild_time_gap_s,
        "rebuild_time_gap_pct": result.rebuild_time_gap_pct,
        "rebuild_objective_rank": result.rebuild_objective_rank,
        "rebuild_objective_gap": result.rebuild_objective_gap,
    }
    _write_json(output_dir / "problem2_exact_summary.json", summary)

    # Top-N CSV
    top_rows: list[dict[str, Any]] = []
    for rank, ev in enumerate(result.top_by_closed_loop, start=1):
        row = _serialize_direct_set_eval(ev)
        row["rank_by_time"] = rank
        # Also find its objective rank
        obj_rank = 1
        for oev in result.top_by_objective:
            if oev.direct_nodes == ev.direct_nodes:
                row["rank_by_objective"] = obj_rank
                break
            obj_rank += 1
        else:
            row["rank_by_objective"] = ""
        top_rows.append(row)
    # Each DirectSetEvaluation already carries a normalized_objective computed
    # by _with_normalized_objectives against ALL feasible evaluations (not just
    # top-N).  Re-normalising here would shrink the bounds and produce different
    # scores than problem2_exact_summary.json — so we preserve the originals.
    _write_csv(output_dir / "problem2_exact_top.csv", top_rows)


def _run_problem2_candidate_pool(data: ProblemData, output_dir: Path) -> list[dict[str, Any]]:
    """Generate unified candidate pool for Problem 2.

    Includes: base_only, all_direct_confirm, rebuild variants, split/no-split,
    and acceptance tolerance candidates.

    Returns the list of candidate dicts for downstream Pareto/recommendation.
    """
    k = data.params.k_max
    sw = data.params.battery_swap_time_s
    multiplier = 1.0
    candidates: list[dict[str, Any]] = []

    # 1. base_only: all targets base hover, all manual review
    try:
        p1 = solve_problem1_for_k(data, k, sw, improve=True)
        from c_uav_inspection.problem2 import evaluate_closed_loop as ecl
        closed = ecl(data, p1.routes, multiplier)
        summary = summarize_uav_solution(p1.routes, data, sw)
        candidates.append({
            "candidate_id": "base_only",
            "source": "base_only",
            "k": k,
            "direct_threshold_multiplier": multiplier,
            "allow_split_hover": True,
            "manual_reduction_time_tolerance": "",
            "feasible": True,
            "infeasible_reason": "",
            "direct_confirmed_nodes": "",
            "manual_target_nodes": _node_tuple_to_string(closed.manual_target_nodes),
            "direct_confirm_count": len(closed.direct_confirmed_nodes),
            "manual_count": closed.manual_count,
            "weighted_manual_cost": closed.weighted_manual_cost,
            "uav_phase_time_s": closed.uav_phase_time_s,
            "ground_review_time_s": closed.ground_review_time_s,
            "closed_loop_time_s": closed.closed_loop_time_s,
            "total_energy_j": summary.total_energy_j,
            "load_std_s": summary.load_std_s,
            "route_count": len(p1.routes),
            "max_route_energy_j": max(evaluate_uav_route(r, data).energy_j for r in p1.routes),
            "operating_horizon_s": data.params.operating_horizon_s,
            "within_operating_horizon": closed.uav_phase_time_s <= data.params.operating_horizon_s + 1e-9,
            "notes": "所有目标仅基础巡检，全部人工复核",
        })
    except InfeasibleError:
        candidates.append({"candidate_id": "base_only", "source": "base_only",
                           "feasible": False, "infeasible_reason": "base_only infeasible"})

    # 2. all_direct_confirm: all 16 targets direct confirmed
    try:
        adc = solve_all_direct_confirm_baseline(data, k, multiplier)
        adc_summary = summarize_uav_solution(adc.routes, data, sw)
        candidates.append({
            "candidate_id": "all_direct_confirm",
            "source": "all_direct_confirm",
            "k": k,
            "direct_threshold_multiplier": multiplier,
            "allow_split_hover": True,
            "manual_reduction_time_tolerance": "",
            "feasible": True,
            "infeasible_reason": "",
            "direct_confirmed_nodes": _node_tuple_to_string(adc.closed_loop.direct_confirmed_nodes),
            "manual_target_nodes": "",
            "direct_confirm_count": len(adc.closed_loop.direct_confirmed_nodes),
            "manual_count": adc.closed_loop.manual_count,
            "weighted_manual_cost": adc.closed_loop.weighted_manual_cost,
            "uav_phase_time_s": adc.closed_loop.uav_phase_time_s,
            "ground_review_time_s": adc.closed_loop.ground_review_time_s,
            "closed_loop_time_s": adc.closed_loop.closed_loop_time_s,
            "total_energy_j": adc_summary.total_energy_j,
            "load_std_s": adc_summary.load_std_s,
            "route_count": len(adc.routes),
            "max_route_energy_j": max(evaluate_uav_route(r, data).energy_j for r in adc.routes),
            "operating_horizon_s": data.params.operating_horizon_s,
            "within_operating_horizon": adc.closed_loop.uav_phase_time_s <= data.params.operating_horizon_s + 1e-9,
            "notes": "全部目标无人机直接确认，零人工复核",
        })
    except InfeasibleError:
        candidates.append({"candidate_id": "all_direct_confirm", "source": "all_direct_confirm",
                           "feasible": False, "infeasible_reason": "all_direct_confirm infeasible"})

    # 3. rebuild candidates with different tolerances
    for tol, label in ((1.00, "rebuild_tolerance_1.00"), (1.03, "rebuild_default"),
                        (1.05, "rebuild_tolerance_1.05"), (1.10, "rebuild_tolerance_1.10")):
        try:
            joint = solve_joint_problem_for_k(
                data, k, multiplier,
                manual_reduction_time_tolerance=tol,
            )
            jsum = summarize_uav_solution(joint.routes, data, sw)
            candidates.append({
                "candidate_id": label,
                "source": label,
                "k": k,
                "direct_threshold_multiplier": multiplier,
                "allow_split_hover": True,
                "manual_reduction_time_tolerance": tol,
                "feasible": True,
                "infeasible_reason": "",
                "direct_confirmed_nodes": _node_tuple_to_string(joint.closed_loop.direct_confirmed_nodes),
                "manual_target_nodes": _node_tuple_to_string(joint.closed_loop.manual_target_nodes),
                "direct_confirm_count": len(joint.closed_loop.direct_confirmed_nodes),
                "manual_count": joint.closed_loop.manual_count,
                "weighted_manual_cost": joint.closed_loop.weighted_manual_cost,
                "uav_phase_time_s": joint.closed_loop.uav_phase_time_s,
                "ground_review_time_s": joint.closed_loop.ground_review_time_s,
                "closed_loop_time_s": joint.closed_loop.closed_loop_time_s,
                "total_energy_j": jsum.total_energy_j,
                "load_std_s": jsum.load_std_s,
                "route_count": len(joint.routes),
                "max_route_energy_j": max(evaluate_uav_route(r, data).energy_j for r in joint.routes),
                "operating_horizon_s": data.params.operating_horizon_s,
                "within_operating_horizon": joint.closed_loop.uav_phase_time_s <= data.params.operating_horizon_s + 1e-9,
                "notes": "",
            })
        except (InfeasibleError, RuntimeError):
            candidates.append({"candidate_id": label, "source": label,
                               "feasible": False, "infeasible_reason": f"{label} infeasible"})

    # 4. split_hover variants
    for allow_split, label in ((True, "split_hover_true"), (False, "split_hover_false")):
        try:
            joint = solve_joint_problem_for_k(
                data, k, multiplier, allow_split_hover=allow_split,
            )
            jsum = summarize_uav_solution(joint.routes, data, sw)
            candidates.append({
                "candidate_id": label,
                "source": label,
                "k": k,
                "direct_threshold_multiplier": multiplier,
                "allow_split_hover": allow_split,
                "manual_reduction_time_tolerance": 1.03,
                "feasible": True,
                "infeasible_reason": "",
                "direct_confirmed_nodes": _node_tuple_to_string(joint.closed_loop.direct_confirmed_nodes),
                "manual_target_nodes": _node_tuple_to_string(joint.closed_loop.manual_target_nodes),
                "direct_confirm_count": len(joint.closed_loop.direct_confirmed_nodes),
                "manual_count": joint.closed_loop.manual_count,
                "weighted_manual_cost": joint.closed_loop.weighted_manual_cost,
                "uav_phase_time_s": joint.closed_loop.uav_phase_time_s,
                "ground_review_time_s": joint.closed_loop.ground_review_time_s,
                "closed_loop_time_s": joint.closed_loop.closed_loop_time_s,
                "total_energy_j": jsum.total_energy_j,
                "load_std_s": jsum.load_std_s,
                "route_count": len(joint.routes),
                "max_route_energy_j": max(evaluate_uav_route(r, data).energy_j for r in joint.routes),
                "operating_horizon_s": data.params.operating_horizon_s,
                "within_operating_horizon": joint.closed_loop.uav_phase_time_s <= data.params.operating_horizon_s + 1e-9,
                "notes": "",
            })
        except (InfeasibleError, RuntimeError):
            candidates.append({"candidate_id": label, "source": label,
                               "feasible": False, "infeasible_reason": f"{label} infeasible"})

    _write_csv(output_dir / "problem2_candidate_pool.csv", candidates)
    return candidates


_PARETO_MINIMIZE_TERMS = (
    "closed_loop_time_s", "manual_count", "weighted_manual_cost",
    "total_energy_j", "route_count", "load_std_s",
)

_RECOMMENDATION_WEIGHTS: dict[str, float] = {
    "closed_loop_time_s": 0.40,
    "weighted_manual_cost": 0.20,
    "manual_count": 0.15,
    "total_energy_j": 0.10,
    "route_count": 0.10,
    "load_std_s": 0.05,
}


def choose_recommended_problem2_candidate(
    pareto_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Select the recommended Problem 2 candidate from the Pareto front.

    Rules (in priority order):
    1. Must be on Pareto front (caller ensures this)
    2. Prefer candidates with closed_loop_time_s <= 2600 and manual_count <= 2
    3. Otherwise score all by fixed weights and pick the best
    """
    # Prefer low closed-loop time with few manual points
    preferred = [
        r for r in pareto_rows
        if r.get("closed_loop_time_s", float("inf")) <= 2600
        and r.get("manual_count", float("inf")) <= 2
    ]
    if preferred:
        preferred.sort(key=lambda r: (
            r.get("weighted_manual_cost", 0),
            r.get("total_energy_j", 0),
            r.get("route_count", 0),
        ))
        result = dict(preferred[0])
        result["selection_rule"] = "closed_loop_under_2600_manual_under_2"
        result["recommendation_reason"] = (
            "闭环时间≤2600s且人工点数≤2，按加权人工代价、总能耗、航次数排序"
        )
        return result

    # Fallback: fixed-weight scoring
    bounds = bounds_from_candidates(pareto_rows, list(_RECOMMENDATION_WEIGHTS.keys()))
    for row in pareto_rows:
        row["recommendation_score"] = score_with_fixed_bounds(
            row, bounds, _RECOMMENDATION_WEIGHTS,
        )
    pareto_rows.sort(key=lambda r: r["recommendation_score"])
    result = dict(pareto_rows[0])
    result["selection_rule"] = "pareto_weighted_score"
    result["recommendation_reason"] = (
        "位于帕累托前沿，并在固定权重评分下排名第一"
    )
    return result


def _run_problem2_pareto_front(
    data: ProblemData, output_dir: Path, candidates: list[dict[str, Any]],
) -> None:
    """Generate Pareto front from candidate pool and write recommendation."""
    feasible = [
        r for r in candidates
        if r.get("feasible") is True
        and r.get("within_operating_horizon") is True
    ]
    if not feasible:
        _write_json(output_dir / "recommended_solution.json", {
            "error": "No feasible candidates in pool",
            "selection_rule": "none",
            "recommendation_reason": "无可行候选",
        })
        return

    front = pareto_front(feasible, _PARETO_MINIMIZE_TERMS)

    # Add pareto metadata
    for row in front:
        row["pareto_rank"] = 1
    _write_csv(output_dir / "problem2_pareto_front.csv", front)

    # Choose recommended
    recommended = choose_recommended_problem2_candidate(front)
    _write_json(output_dir / "recommended_solution.json", recommended)


def _write_output_manifest(output_dir: Path, include_expensive: bool) -> None:
    """Write MANIFEST.md listing all generated output files."""
    from datetime import datetime

    manifest_files = [
        ("data_validation.json", "run_all_experiments", "yes", "数据校验"),
        ("problem1_packed_k_comparison.csv", "run_all_experiments", "yes", "问题1装箱K对比"),
        ("problem1_time_priority_k_comparison.csv", "run_all_experiments", "yes", "问题1时间优先K对比"),
        ("problem1_parallel_route_count_ablation.csv", "run_all_experiments", "yes", "问题1航次预算消融"),
        ("problem1_swap_sensitivity_k1.csv", "run_all_experiments", "yes", "问题1换电敏感 K=1"),
        ("problem1_swap_sensitivity_k4_reference.csv", "run_all_experiments", "yes", "问题1换电敏感 K=4"),
        ("problem2_baseline_comparison.csv", "run_all_experiments", "yes", "问题2基准对比"),
        ("problem2_candidate_pool.csv", "run_all_experiments", "yes", "问题2候选池"),
        ("problem2_pareto_front.csv", "run_all_experiments", "yes", "问题2帕累托前沿"),
        ("problem2_k_comparison.csv", "run_all_experiments", "yes", "问题2 K对比"),
        ("problem2_threshold_sensitivity.csv", "run_all_experiments", "yes", "问题2阈值敏感性"),
        ("problem2_split_hover_ablation.csv", "run_all_experiments", "yes", "问题2可拆分消融"),
        ("problem2_acceptance_tolerance_sensitivity.csv", "run_all_experiments", "yes", "问题2接受准则敏感性（搜索行为，非推荐依据）"),
        ("problem2_energy_limit_sensitivity.csv", "run_all_experiments", "yes", "问题2能量限制敏感性"),
        ("problem2_hover_power_sensitivity.csv", "run_all_experiments", "yes", "问题2悬停功率敏感性"),
        ("recommended_solution.json", "run_all_experiments", "yes", "推荐方案"),
    ]

    if include_expensive:
        manifest_files.extend([
            ("problem2_exact_summary.json", "run_all_experiments", "yes", "全枚举摘要"),
            ("problem2_exact_top.csv", "run_all_experiments", "yes", "全枚举Top结果"),
        ])

    lines = [
        "# outputs/c_uav_inspection Manifest",
        "",
        f"Generated at: {datetime.now().isoformat()}",
        "Data source: 2026同济数学建模竞赛赛题/2026C数据.xlsx",
        f"include_expensive: {include_expensive}",
        "",
        "| File | Generated by | Used in paper | Notes |",
        "|---|---:|---|---|",
    ]
    for fname, gen_by, used, notes in manifest_files:
        exists = "yes" if (output_dir / fname).exists() else "no"
        lines.append(f"| {fname} | {gen_by} | {used} | {notes} (present: {exists}) |")

    (output_dir / "MANIFEST.md").write_text("\n".join(lines), encoding="utf-8")


def _write_recommended_solution(data: ProblemData, output_dir: Path) -> None:
    """Solve Problem 2 at K_max, multiplier=1.0 and serialise the result."""
    sol = solve_joint_problem_for_k(data, data.params.k_max, 1.0)

    result: dict[str, Any] = {
        "closed_loop_time_s": sol.closed_loop.closed_loop_time_s,
        "uav_phase_time_s": sol.closed_loop.uav_phase_time_s,
        "ground_review_time_s": sol.closed_loop.ground_review_time_s,
        "manual_nodes": list(sol.closed_loop.manual_nodes),
        "manual_target_nodes": list(sol.closed_loop.manual_target_nodes),
        "weighted_manual_cost": sol.closed_loop.weighted_manual_cost,
        "direct_confirmed_nodes": list(sol.closed_loop.direct_confirmed_nodes),
        "ground_path": list(sol.closed_loop.ground_path),
        "routes": [_serialize_route(r) for r in sol.routes],
    }
    _write_json(output_dir / "recommended_solution.json", result)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_all_experiments(
    data_path: str | Path,
    output_dir: str | Path,
    include_expensive: bool = False,
) -> None:
    """Run all experiments and write CSV/JSON results to *output_dir*.

    Produces:
      - data_validation.json
      - problem1_k_comparison_current_packed.csv              (K = 1..4, current solver)
      - problem1_time_priority_k_comparison.csv               (K = 1..4, time-priority DP)
      - problem1_parallel_route_count_ablation.csv            (route budget = 1..4)
      - problem1_swap_sensitivity_k1.csv                      (swap = 0..600, K=1)
      - problem1_swap_sensitivity_k4_reference.csv            (swap = 0..600, K=4)
      - problem2_baseline_comparison.csv                      (base-only vs joint)
      - problem2_k_comparison.csv                             (K = 1..4)
      - problem2_threshold_sensitivity.csv                    (mult = 0.70 .. 1.30)
      - problem2_split_hover_ablation.csv                     (split vs no-split hover)
      - problem2_acceptance_tolerance_sensitivity.csv         (tol = 1.00 .. 1.10)
      - problem2_energy_limit_sensitivity.csv                 (energy = 0.90x .. 1.10x)
      - problem2_hover_power_sensitivity.csv                  (hover = 0.90x .. 1.10x)
      - recommended_solution.json

    When include_expensive=True, also produces:
      - problem2_exact_summary.json                           (full enumeration verification)
      - problem2_exact_top.csv                                (top enumeration results)
    """
    data_path = Path(data_path)
    output_dir = Path(output_dir)

    data = load_problem_data(data_path)

    # Data validation summary
    validation = validate_problem_data(data)
    _write_json(output_dir / "data_validation.json", validation)

    # Problem 1
    _run_problem1_k_comparison(data, output_dir)
    _run_problem1_time_priority_k_comparison(data, output_dir)
    _run_problem1_parallel_route_count_ablation(data, output_dir)
    _run_problem1_swap_sensitivity(data, output_dir)
    _run_problem1_swap_sensitivity_k4_reference(data, output_dir)

    # Problem 2
    _run_problem2_baseline_comparison(data, output_dir)
    candidates = _run_problem2_candidate_pool(data, output_dir)
    _run_problem2_pareto_front(data, output_dir, candidates)
    _run_problem2_k_comparison(data, output_dir)
    _run_problem2_threshold_sensitivity(data, output_dir)
    _run_problem2_split_hover_ablation(data, output_dir)
    _run_problem2_acceptance_tolerance_sensitivity(data, output_dir)
    _run_problem2_energy_limit_sensitivity(data, output_dir)
    _run_problem2_hover_power_sensitivity(data, output_dir)

    # Exact enumeration (expensive — only when explicitly requested)
    if include_expensive:
        _run_problem2_exact_enumeration(data, output_dir)

    # Output manifest
    _write_output_manifest(output_dir, include_expensive)
