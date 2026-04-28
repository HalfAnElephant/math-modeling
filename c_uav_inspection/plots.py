"""Plot generation for problem results.

Produces PNG charts: K-comparison, threshold sensitivity, and route map.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")  # Non-interactive backend (test-safe)

import matplotlib.pyplot as plt  # noqa: E402  (must follow use('Agg'))

from c_uav_inspection.data import load_problem_data  # noqa: E402


# ---------------------------------------------------------------------------
# Problem 1: K comparison bar chart
# ---------------------------------------------------------------------------


def _plot_problem1_k_comparison(result_dir: Path) -> None:
    csv_path = result_dir / "problem1_k_comparison.csv"
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Required input file not found: {csv_path}. "
            "Run run_all_experiments() first."
        )

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    ks = [int(row["k"]) for row in rows]
    times = [float(row["uav_phase_time_s"]) for row in rows]
    objectives = [float(row["normalized_objective"]) for row in rows]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

    # UAV phase time
    bars = ax1.bar(ks, times, color="steelblue", edgecolor="black")
    ax1.set_xlabel("K")
    ax1.set_ylabel("UAV Phase Time (s)")
    ax1.set_title("Problem 1: UAV Phase Time vs K")
    ax1.set_xticks(ks)
    for bar, val in zip(bars, times):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 10,
                 f"{val:.0f}", ha="center", va="bottom", fontsize=8)

    # Normalized objective
    ax2.plot(ks, objectives, marker="o", color="darkorange", linewidth=2)
    ax2.set_xlabel("K")
    ax2.set_ylabel("Normalized Objective")
    ax2.set_title("Problem 1: Normalized Objective vs K")
    ax2.set_xticks(ks)
    ax2.set_ylim(0, 1.05)

    fig.tight_layout()
    fig.savefig(result_dir / "problem1_k_comparison.png", dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Problem 2: threshold sensitivity line chart
# ---------------------------------------------------------------------------


def _plot_problem2_threshold_sensitivity(result_dir: Path) -> None:
    csv_path = result_dir / "problem2_threshold_sensitivity.csv"
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Required input file not found: {csv_path}. "
            "Run run_all_experiments() first."
        )

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    mults = [float(row["direct_threshold_multiplier"]) for row in rows]
    objectives = [float(row["normalized_objective"]) for row in rows]
    closed_times = [float(row["closed_loop_time_s"]) for row in rows]
    ground_times = [float(row["ground_review_time_s"]) for row in rows]
    manual_counts = [int(row["manual_count"]) for row in rows]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

    # Closed-loop and ground times
    ax1.plot(mults, closed_times, marker="o", label="Closed-loop time", color="steelblue")
    ax1.plot(mults, ground_times, marker="s", label="Ground review time", color="darkorange")
    ax1.set_xlabel("Direct Threshold Multiplier")
    ax1.set_ylabel("Time (s)")
    ax1.set_title("Problem 2: Time vs Threshold Multiplier")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Normalized objective + manual count
    ax2_twin = ax2.twinx()
    (line1,) = ax2.plot(mults, objectives, marker="o", color="darkgreen", linewidth=2,
                        label="Normalized objective")
    (line2,) = ax2_twin.plot(mults, manual_counts, marker="^", color="crimson",
                             linestyle="--", label="Manual count")
    ax2.set_xlabel("Direct Threshold Multiplier")
    ax2.set_ylabel("Normalized Objective", color="darkgreen")
    ax2_twin.set_ylabel("Manual Count", color="crimson")
    ax2.set_title("Problem 2: Objective & Manual Count")
    ax2.set_ylim(0, 1.05)
    lines = [line1, line2]
    ax2.legend(lines, [l.get_label() for l in lines])

    fig.tight_layout()
    fig.savefig(result_dir / "problem2_threshold_sensitivity.png", dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Recommended routes map
# ---------------------------------------------------------------------------


def _plot_recommended_routes(data_path: Path, result_dir: Path) -> None:
    json_path = result_dir / "recommended_solution.json"
    if not json_path.exists():
        raise FileNotFoundError(
            f"Required input file not found: {json_path}. "
            "Run run_all_experiments() first."
        )

    data = load_problem_data(data_path)

    with json_path.open("r", encoding="utf-8") as handle:
        sol: dict[str, Any] = json.load(handle)

    # Build node_id -> (x, y, z)
    node_coords: dict[int, tuple[float, float, float]] = {}
    for t in data.targets:
        node_coords[t.node_id] = (t.x_m, t.y_m, t.z_m)

    # Depot (node 0) — coordinates from flight matrix (may be origin at 0,0)
    # Use the first target closest to depot assumption, or use P0 position
    # The depot is node 0. We'll place it at origin or derive from targets.
    depot_x = 0.0
    depot_y = 0.0

    fig, ax = plt.subplots(figsize=(10, 8))

    # Plot targets as scatter points
    xs = [c[0] for c in node_coords.values()]
    ys = [c[1] for c in node_coords.values()]
    ax.scatter(xs, ys, c="gray", marker="s", s=60, zorder=3, label="Targets")
    for nid, (x, y, _) in node_coords.items():
        ax.annotate(str(nid), (x, y), textcoords="offset points",
                    xytext=(5, 5), fontsize=8, color="black")

    # Plot depot
    ax.scatter([depot_x], [depot_y], c="red", marker="*", s=200, zorder=5, label="Depot (P0)")
    ax.annotate("P0", (depot_x, depot_y), textcoords="offset points",
                xytext=(5, 5), fontsize=9, color="red", fontweight="bold")

    # Plot UAV routes
    colors = ["steelblue", "darkorange", "green", "purple"]
    routes = sol.get("routes", [])
    for route in routes:
        uav_id = route["uav_id"]
        seq = route["node_sequence"]
        color = colors[(uav_id - 1) % len(colors)]

        # Build (x, y) path for this route
        path_x: list[float] = []
        path_y: list[float] = []
        for nid in seq:
            if nid == 0:
                path_x.append(depot_x)
                path_y.append(depot_y)
            else:
                cx, cy, _ = node_coords.get(nid, (depot_x, depot_y, 0))
                path_x.append(cx)
                path_y.append(cy)

        ax.plot(path_x, path_y, marker=".", color=color, linewidth=1.5,
                label=f"UAV {uav_id}", alpha=0.8)

    # Plot ground path
    ground_path = sol.get("ground_path", [])
    if ground_path:
        gp_x: list[float] = []
        gp_y: list[float] = []
        for pid in ground_path:
            if pid == "P0":
                gp_x.append(depot_x)
                gp_y.append(depot_y)
            else:
                # Find manual point coordinates from targets
                found = False
                for t in data.targets:
                    if t.manual_point_id == pid:
                        gp_x.append(t.manual_x_m)
                        gp_y.append(t.manual_y_m)
                        found = True
                        break
                if not found:
                    gp_x.append(depot_x)
                    gp_y.append(depot_y)
        ax.plot(gp_x, gp_y, marker="^", color="crimson", linewidth=2,
                linestyle="--", label="Ground path", alpha=0.7)

    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_title("Recommended Routes (UAV + Ground Personnel)")
    ax.legend(loc="upper left", fontsize=7)
    ax.set_aspect("equal", adjustable="datalim")
    ax.grid(True, alpha=0.2)

    fig.tight_layout()
    fig.savefig(result_dir / "recommended_routes.png", dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def generate_all_figures(data_path: str | Path, result_dir: str | Path) -> None:
    """Generate all PNG figures from experiment results in *result_dir*.

    Requires that run_all_experiments() has already been called to produce
    the CSV/JSON files.

    Produces:
      - problem1_k_comparison.png
      - problem2_threshold_sensitivity.png
      - recommended_routes.png
    """
    data_path = Path(data_path)
    result_dir = Path(result_dir)

    _plot_problem1_k_comparison(result_dir)
    _plot_problem2_threshold_sensitivity(result_dir)
    _plot_recommended_routes(data_path, result_dir)
