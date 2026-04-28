"""Experiment runner: generates CSV/JSON result files for all scenarios.

Produces K-comparison tables, sensitivity analyses, data validation, and a
recommended solution summary for both Problem 1 and Problem 2.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from c_uav_inspection.data import ProblemData, load_problem_data, validate_problem_data
from c_uav_inspection.model import UAVRoute, summarize_uav_solution
from c_uav_inspection.objective import (
    bounds_from_candidates,
    weighted_normalized_objective,
)
from c_uav_inspection.problem1 import solve_problem1_for_k
from c_uav_inspection.problem2 import solve_joint_problem_for_k

# ---------------------------------------------------------------------------
# Problem 2 weights (plan section 2)
# ---------------------------------------------------------------------------
PROBLEM2_WEIGHTS: dict[str, float] = {
    "closed_loop_time_s": 0.50,
    "ground_review_time_s": 0.20,
    "manual_count": 0.10,
    "total_energy_j": 0.10,
    "load_std_s": 0.10,
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
    rows: list[dict[str, Any]] = []
    sw = data.params.battery_swap_time_s

    for k in range(1, 5):
        sol = solve_problem1_for_k(data, k, sw, improve=True)
        summary = summarize_uav_solution(sol.routes, data, sw)
        rows.append({
            "k": k,
            "uav_phase_time_s": summary.uav_phase_time_s,
            "total_energy_j": summary.total_energy_j,
            "load_std_s": summary.load_std_s,
            "route_count": len(sol.routes),
        })

    rows = _add_normalized_objective(rows, {
        "uav_phase_time_s": 1.0, "total_energy_j": 0.0, "load_std_s": 0.0,
    })
    _write_csv(output_dir / "problem1_k_comparison.csv", rows)


def _run_problem1_swap_sensitivity(data, output_dir: Path) -> None:
    rows: list[dict[str, Any]] = []
    k = data.params.k_max

    for swap_s in (0, 150, 300, 450, 600):
        sol = solve_problem1_for_k(data, k, float(swap_s), improve=True)
        summary = summarize_uav_solution(sol.routes, data, float(swap_s))
        rows.append({
            "battery_swap_time_s": swap_s,
            "uav_phase_time_s": summary.uav_phase_time_s,
            "total_energy_j": summary.total_energy_j,
            "load_std_s": summary.load_std_s,
            "route_count": len(sol.routes),
        })

    rows = _add_normalized_objective(rows, {
        "uav_phase_time_s": 1.0, "total_energy_j": 0.0, "load_std_s": 0.0,
    })
    _write_csv(output_dir / "problem1_swap_sensitivity.csv", rows)


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
            "ground_review_time_s": sol.closed_loop.ground_review_time_s,
            "manual_count": sol.closed_loop.manual_count,
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
            "ground_review_time_s": sol.closed_loop.ground_review_time_s,
            "manual_count": sol.closed_loop.manual_count,
            "total_energy_j": summary.total_energy_j,
            "load_std_s": summary.load_std_s,
        })

    rows = _add_normalized_objective(rows, PROBLEM2_WEIGHTS)
    _write_csv(output_dir / "problem2_threshold_sensitivity.csv", rows)


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


def _write_recommended_solution(data: ProblemData, output_dir: Path) -> None:
    """Solve Problem 2 at K_max, multiplier=1.0 and serialise the result."""
    sol = solve_joint_problem_for_k(data, data.params.k_max, 1.0)

    result: dict[str, Any] = {
        "closed_loop_time_s": sol.closed_loop.closed_loop_time_s,
        "manual_nodes": list(sol.closed_loop.manual_nodes),
        "direct_confirmed_nodes": list(sol.closed_loop.direct_confirmed_nodes),
        "ground_path": list(sol.closed_loop.ground_path),
        "routes": [_serialize_route(r) for r in sol.routes],
    }
    _write_json(output_dir / "recommended_solution.json", result)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_all_experiments(data_path: str | Path, output_dir: str | Path) -> None:
    """Run all experiments and write CSV/JSON results to *output_dir*.

    Produces:
      - data_validation.json
      - problem1_k_comparison.csv        (K = 1..4)
      - problem1_swap_sensitivity.csv    (swap = 0,150,300,450,600)
      - problem2_k_comparison.csv        (K = 1..4)
      - problem2_threshold_sensitivity.csv (mult = 0.70 .. 1.30)
      - recommended_solution.json
    """
    data_path = Path(data_path)
    output_dir = Path(output_dir)

    data = load_problem_data(data_path)

    # Data validation summary
    validation = validate_problem_data(data)
    _write_json(output_dir / "data_validation.json", validation)

    # Problem 1
    _run_problem1_k_comparison(data, output_dir)
    _run_problem1_swap_sensitivity(data, output_dir)

    # Problem 2
    _run_problem2_k_comparison(data, output_dir)
    _run_problem2_threshold_sensitivity(data, output_dir)

    # Recommended solution
    _write_recommended_solution(data, output_dir)
