"""Plot generation for problem results.

Produces PNG charts used by the paper.  The figures are generated from the
CSV/JSON outputs so that the paper visuals stay synchronized with experiments.
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


PAPER_DPI = 180
FIG_BG = "#ffffff"
GRID_COLOR = "#d9d9d9"


def _configure_matplotlib() -> None:
    """Set a paper-friendly plotting style with Chinese font fallback."""
    plt.rcParams.update({
        "font.sans-serif": [
            "Arial Unicode MS",
            "Hiragino Sans GB",
            "Songti SC",
            "Heiti TC",
            "DejaVu Sans",
        ],
        "axes.unicode_minus": False,
        "figure.facecolor": FIG_BG,
        "axes.facecolor": FIG_BG,
        "axes.edgecolor": "#333333",
        "axes.titleweight": "bold",
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 8,
    })


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(
            f"Required input file not found: {path}. "
            "Run run_all_experiments() first."
        )
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _as_float(value: str) -> float | None:
    return None if value == "" else float(value)


def _annotate_bars(ax: plt.Axes, bars, *, fmt: str = "{:.0f}") -> None:
    for bar in bars:
        height = bar.get_height()
        if height is None:
            continue
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height,
            fmt.format(height),
            ha="center",
            va="bottom",
            fontsize=8,
        )


_configure_matplotlib()


# ---------------------------------------------------------------------------
# Problem 1: K comparison bar chart
# ---------------------------------------------------------------------------


def _plot_problem1_k_comparison(result_dir: Path) -> None:
    packed_rows = _read_csv_rows(
        result_dir / "problem1_k_comparison_current_packed.csv"
    )
    time_rows = _read_csv_rows(
        result_dir / "problem1_time_priority_k_comparison.csv"
    )

    ks = [int(row["k"]) for row in packed_rows]
    packed_times = [float(row["uav_phase_time_s"]) for row in packed_rows]
    time_by_k = {
        int(row["k"]): _as_float(row["uav_phase_time_s"])
        for row in time_rows
    }
    time_energy_by_k = {
        int(row["k"]): _as_float(row["total_energy_j"])
        for row in time_rows
    }
    time_route_by_k = {
        int(row["k"]): _as_float(row["route_count"])
        for row in time_rows
    }

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.2, 4.2))

    width = 0.34
    packed_x = [k - width / 2 for k in ks]
    time_x = [k + width / 2 for k in ks if time_by_k[k] is not None]
    time_vals = [time_by_k[k] for k in ks if time_by_k[k] is not None]

    bars1 = ax1.bar(
        packed_x, packed_times, width=width, color="#4C78A8",
        edgecolor="#2f4f6f", label="packed基准",
    )
    bars2 = ax1.bar(
        time_x, time_vals, width=width, color="#F58518",
        edgecolor="#9f560d", label="time-priority",
    )
    ax1.text(
        1 + width / 2, max(packed_times) * 0.08, "不可行",
        ha="center", va="bottom", fontsize=8, color="#9f560d", rotation=90,
    )
    ax1.set_xlabel("无人机数量 K")
    ax1.set_ylabel("无人机阶段时间 / s")
    ax1.set_title("问题1：packed与time-priority阶段时间对比")
    ax1.set_xticks(ks)
    ax1.grid(axis="y", color=GRID_COLOR, alpha=0.7)
    ax1.legend()
    _annotate_bars(ax1, bars1)
    _annotate_bars(ax1, bars2)

    feasible_ks = [k for k in ks if time_by_k[k] is not None]
    route_counts = [time_route_by_k[k] for k in feasible_ks]
    energies = [time_energy_by_k[k] for k in feasible_ks]
    bars = ax2.bar(
        feasible_ks, route_counts, color="#54A24B", alpha=0.78,
        label="并行航次数",
    )
    ax2_twin = ax2.twinx()
    ax2_twin.plot(
        feasible_ks, energies, marker="o", linewidth=2.2,
        color="#E45756", label="总能耗",
    )
    ax2.set_xlabel("无人机数量 K")
    ax2.set_ylabel("time-priority航次数")
    ax2_twin.set_ylabel("总能耗 / J")
    ax2.set_title("问题1：并行路线增加带来的代价")
    ax2.set_xticks(ks)
    ax2.set_ylim(0, max(route_counts) + 1)
    ax2.grid(axis="y", color=GRID_COLOR, alpha=0.7)
    _annotate_bars(ax2, bars, fmt="{:.0f}")
    lines, labels = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2_twin.get_legend_handles_labels()
    ax2.legend(lines + lines2, labels + labels2, loc="upper left")

    fig.tight_layout()
    fig.savefig(result_dir / "problem1_k_comparison.png", dpi=PAPER_DPI)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Problem 2: threshold sensitivity line chart
# ---------------------------------------------------------------------------


def _plot_problem2_threshold_sensitivity(result_dir: Path) -> None:
    rows = _read_csv_rows(result_dir / "problem2_threshold_sensitivity.csv")

    mults = [float(row["direct_threshold_multiplier"]) for row in rows]
    objectives = [float(row["normalized_objective"]) for row in rows]
    closed_times = [float(row["closed_loop_time_s"]) for row in rows]
    ground_times = [float(row["ground_review_time_s"]) for row in rows]
    uav_times = [float(row["uav_phase_time_s"]) for row in rows]
    manual_counts = [int(row["manual_count"]) for row in rows]
    direct_counts = [int(row["direct_confirm_count"]) for row in rows]
    weighted_costs = [int(row["weighted_manual_cost"]) for row in rows]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.2, 4.2))

    ax1.plot(mults, closed_times, marker="o", label="闭环总时间", color="#4C78A8")
    ax1.plot(mults, ground_times, marker="s", label="地面复核时间", color="#F58518")
    ax1.plot(mults, uav_times, marker="^", label="无人机阶段时间", color="#54A24B")
    ax1.set_xlabel("直接确认阈值倍率 α")
    ax1.set_ylabel("时间 / s")
    ax1.set_title("问题2：阈值倍率对时间结构的影响")
    ax1.legend()
    ax1.grid(True, color=GRID_COLOR, alpha=0.7)

    ax2_twin = ax2.twinx()
    (line1,) = ax2.plot(
        mults, objectives, marker="o", color="#2E7D32", linewidth=2.2,
        label="归一化目标",
    )
    (line2,) = ax2_twin.plot(
        mults, manual_counts, marker="^", color="#D62728",
        linestyle="--", linewidth=2.0, label="人工点数",
    )
    (line3,) = ax2_twin.plot(
        mults, direct_counts, marker="v", color="#9467BD",
        linestyle=":", linewidth=2.0, label="直接确认数",
    )
    (line4,) = ax2_twin.plot(
        mults, weighted_costs, marker="s", color="#8C564B",
        linestyle="-.", linewidth=1.8, label="$C_M$",
    )
    ax2.set_xlabel("直接确认阈值倍率 α")
    ax2.set_ylabel("归一化目标", color="#2E7D32")
    ax2_twin.set_ylabel("数量 / 加权代价")
    ax2.set_title("问题2：人工负担与 $C_M$")
    ax2.set_ylim(0, 1.05)
    ax2.grid(True, color=GRID_COLOR, alpha=0.7)
    lines = [line1, line2, line3, line4]
    ax2.legend(lines, [l.get_label() for l in lines])

    fig.tight_layout()
    fig.savefig(result_dir / "problem2_threshold_sensitivity.png", dpi=PAPER_DPI)
    plt.close(fig)


def _plot_problem2_baseline_comparison(result_dir: Path) -> None:
    rows = _read_csv_rows(result_dir / "problem2_baseline_comparison.csv")
    labels = ["仅基础巡检", "联合优化"]
    uav_times = [float(row["uav_phase_time_s"]) for row in rows]
    ground_times = [float(row["ground_review_time_s"]) for row in rows]
    manual_counts = [int(row["manual_count"]) for row in rows]
    weighted_costs = [int(row["weighted_manual_cost"]) for row in rows]
    direct_counts = [int(row["direct_confirm_count"]) for row in rows]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.6, 4.2))
    xs = list(range(len(labels)))
    ax1.bar(xs, uav_times, color="#4C78A8", label="$T_u$")
    ax1.bar(xs, ground_times, bottom=uav_times, color="#F58518", label="$T_g$")
    totals = [u + g for u, g in zip(uav_times, ground_times)]
    for x, total in zip(xs, totals):
        ax1.text(x, total + 70, f"{total:.0f}s", ha="center", va="bottom", fontsize=8)
    ax1.set_xticks(xs, labels)
    ax1.set_ylabel("闭环时间构成 / s")
    ax1.set_title("仅基础巡检 vs 联合优化：时间分解")
    ax1.grid(axis="y", color=GRID_COLOR, alpha=0.7)
    ax1.legend()

    width = 0.24
    bars1 = ax2.bar([x - width for x in xs], manual_counts, width=width,
                    color="#D62728", label="人工点数")
    bars2 = ax2.bar(xs, weighted_costs, width=width,
                    color="#8C564B", label="$C_M$")
    bars3 = ax2.bar([x + width for x in xs], direct_counts, width=width,
                    color="#54A24B", label="直接确认数")
    ax2.set_xticks(xs, labels)
    ax2.set_ylabel("数量 / 加权代价")
    ax2.set_title("人工负担与直接确认能力")
    ax2.grid(axis="y", color=GRID_COLOR, alpha=0.7)
    ax2.legend()
    _annotate_bars(ax2, bars1)
    _annotate_bars(ax2, bars2)
    _annotate_bars(ax2, bars3)

    fig.tight_layout()
    fig.savefig(result_dir / "problem2_baseline_comparison.png", dpi=PAPER_DPI)
    plt.close(fig)


def _plot_problem2_k_comparison(result_dir: Path) -> None:
    rows = _read_csv_rows(result_dir / "problem2_k_comparison.csv")
    ks = [int(row["k"]) for row in rows]
    closed_times = [float(row["closed_loop_time_s"]) for row in rows]
    uav_times = [float(row["uav_phase_time_s"]) for row in rows]
    ground_times = [float(row["ground_review_time_s"]) for row in rows]
    manual_counts = [int(row["manual_count"]) for row in rows]
    direct_counts = [int(row["direct_confirm_count"]) for row in rows]
    weighted_costs = [int(row["weighted_manual_cost"]) for row in rows]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.2, 4.2))
    ax1.plot(ks, closed_times, marker="o", color="#4C78A8", linewidth=2.2,
             label="闭环总时间")
    ax1.plot(ks, uav_times, marker="^", color="#54A24B", linewidth=2,
             label="无人机阶段")
    ax1.plot(ks, ground_times, marker="s", color="#F58518", linewidth=2,
             label="地面复核")
    ax1.set_xlabel("无人机数量 K")
    ax1.set_ylabel("时间 / s")
    ax1.set_title("问题2：K对闭环时间的影响")
    ax1.set_xticks(ks)
    ax1.grid(True, color=GRID_COLOR, alpha=0.7)
    ax1.legend()

    ax2.plot(ks, manual_counts, marker="^", color="#D62728", linewidth=2,
             label="人工点数")
    ax2.plot(ks, direct_counts, marker="v", color="#54A24B", linewidth=2,
             label="直接确认数")
    ax2.plot(ks, weighted_costs, marker="s", color="#8C564B", linewidth=2,
             label="$C_M$")
    ax2.set_xlabel("无人机数量 K")
    ax2.set_ylabel("数量 / 加权代价")
    ax2.set_title("问题2：K对人工负担的影响")
    ax2.set_xticks(ks)
    ax2.grid(True, color=GRID_COLOR, alpha=0.7)
    ax2.legend()

    fig.tight_layout()
    fig.savefig(result_dir / "problem2_k_comparison.png", dpi=PAPER_DPI)
    plt.close(fig)


def _plot_problem2_acceptance_tolerance(result_dir: Path) -> None:
    rows = _read_csv_rows(
        result_dir / "problem2_acceptance_tolerance_sensitivity.csv"
    )
    tolerances = [float(row["manual_reduction_time_tolerance"]) for row in rows]
    closed_times = [float(row["closed_loop_time_s"]) for row in rows]
    uav_times = [float(row["uav_phase_time_s"]) for row in rows]
    ground_times = [float(row["ground_review_time_s"]) for row in rows]
    energies = [float(row["total_energy_j"]) for row in rows]
    manual_counts = [int(row["manual_count"]) for row in rows]
    direct_counts = [int(row["direct_confirm_count"]) for row in rows]
    weighted_costs = [int(row["weighted_manual_cost"]) for row in rows]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.2, 4.2))
    ax1.plot(tolerances, closed_times, marker="o", color="#4C78A8",
             linewidth=2.2, label="闭环总时间")
    ax1.plot(tolerances, uav_times, marker="^", color="#54A24B",
             linewidth=2, label="无人机阶段")
    ax1.plot(tolerances, ground_times, marker="s", color="#F58518",
             linewidth=2, label="地面复核")
    ax1.set_xlabel("接受准则容忍倍率")
    ax1.set_ylabel("时间 / s")
    ax1.set_title("接受准则：时间结构")
    ax1.grid(True, color=GRID_COLOR, alpha=0.7)
    ax1.legend()

    ax2_twin = ax2.twinx()
    ax2.plot(tolerances, manual_counts, marker="^", color="#D62728",
             linewidth=2, label="人工点数")
    ax2.plot(tolerances, direct_counts, marker="v", color="#54A24B",
             linewidth=2, label="直接确认数")
    ax2.plot(tolerances, weighted_costs, marker="s", color="#8C564B",
             linewidth=2, label="$C_M$")
    ax2_twin.plot(tolerances, energies, marker="o", color="#9467BD",
                  linestyle="--", linewidth=2, label="总能耗")
    ax2.set_xlabel("接受准则容忍倍率")
    ax2.set_ylabel("数量 / 加权代价")
    ax2_twin.set_ylabel("总能耗 / J")
    ax2.set_title("接受准则：人工负担与能耗")
    ax2.grid(True, color=GRID_COLOR, alpha=0.7)
    lines, labels = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2_twin.get_legend_handles_labels()
    ax2.legend(lines + lines2, labels + labels2, loc="upper left")

    fig.tight_layout()
    fig.savefig(
        result_dir / "problem2_acceptance_tolerance_sensitivity.png",
        dpi=PAPER_DPI,
    )
    plt.close(fig)


def _plot_problem2_energy_parameters(result_dir: Path) -> None:
    energy_rows = _read_csv_rows(result_dir / "problem2_energy_limit_sensitivity.csv")
    hover_rows = _read_csv_rows(result_dir / "problem2_hover_power_sensitivity.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.2, 4.2))

    e_labels = [f"{float(row['effective_energy_limit_j'])/1000:.1f}k" for row in energy_rows]
    e_times = [float(row["closed_loop_time_s"]) for row in energy_rows]
    e_direct = [int(row["direct_confirm_count"]) for row in energy_rows]
    xs = list(range(len(e_labels)))
    bars = ax1.bar(xs, e_times, color="#4C78A8", alpha=0.82,
                   label="闭环总时间")
    ax1_twin = ax1.twinx()
    ax1_twin.plot(xs, e_direct, marker="o", color="#D62728",
                  linewidth=2.2, label="直接确认数")
    ax1.set_xticks(xs, e_labels)
    ax1.set_xlabel("$E_{max}$ / J")
    ax1.set_ylabel("闭环总时间 / s")
    ax1_twin.set_ylabel("直接确认数")
    ax1.set_title("有效能量上限敏感性")
    ax1.grid(axis="y", color=GRID_COLOR, alpha=0.7)
    _annotate_bars(ax1, bars)
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax1_twin.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc="upper left")

    h_labels = [f"{float(row['hover_power_j_per_s']):.0f}" for row in hover_rows]
    h_times = [float(row["closed_loop_time_s"]) for row in hover_rows]
    h_direct = [int(row["direct_confirm_count"]) for row in hover_rows]
    xs2 = list(range(len(h_labels)))
    bars2 = ax2.bar(xs2, h_times, color="#F58518", alpha=0.82,
                    label="闭环总时间")
    ax2_twin = ax2.twinx()
    ax2_twin.plot(xs2, h_direct, marker="o", color="#D62728",
                  linewidth=2.2, label="直接确认数")
    ax2.set_xticks(xs2, h_labels)
    ax2.set_xlabel("$P_h$ / (J/s)")
    ax2.set_ylabel("闭环总时间 / s")
    ax2_twin.set_ylabel("直接确认数")
    ax2.set_title("悬停功率敏感性")
    ax2.grid(axis="y", color=GRID_COLOR, alpha=0.7)
    _annotate_bars(ax2, bars2)
    lines, labels = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2_twin.get_legend_handles_labels()
    ax2.legend(lines + lines2, labels + labels2, loc="upper left")

    fig.tight_layout()
    fig.savefig(result_dir / "problem2_energy_parameter_sensitivity.png",
                dpi=PAPER_DPI)
    plt.close(fig)


def _plot_problem2_split_hover_ablation(result_dir: Path) -> None:
    rows = _read_csv_rows(result_dir / "problem2_split_hover_ablation.csv")
    labels = [row["scheme"].replace("悬停", "") for row in rows]
    closed_times = [float(row["closed_loop_time_s"]) for row in rows]
    energies = [float(row["total_energy_j"]) for row in rows]
    weighted_costs = [int(row["weighted_manual_cost"]) for row in rows]
    objective = [float(row["normalized_objective"]) for row in rows]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.6, 4.2))
    xs = list(range(len(labels)))
    bars = ax1.bar(xs, closed_times, color=["#4C78A8", "#F58518"], alpha=0.84)
    ax1.set_xticks(xs, labels)
    ax1.set_ylabel("闭环总时间 / s")
    ax1.set_title("可拆分 vs 不可拆分：闭环时间")
    ax1.grid(axis="y", color=GRID_COLOR, alpha=0.7)
    _annotate_bars(ax1, bars)

    width = 0.28
    bars1 = ax2.bar([x - width for x in xs], [e / 1000 for e in energies],
                    width=width, color="#9467BD", label="总能耗(kJ)")
    bars2 = ax2.bar(xs, weighted_costs, width=width,
                    color="#8C564B", label="$C_M$")
    bars3 = ax2.bar([x + width for x in xs], objective, width=width,
                    color="#54A24B", label="归一化目标")
    ax2.set_xticks(xs, labels)
    ax2.set_ylabel("能耗(kJ) / 代价 / 目标值")
    ax2.set_title("可拆分策略的代价结构")
    ax2.grid(axis="y", color=GRID_COLOR, alpha=0.7)
    ax2.legend()
    _annotate_bars(ax2, bars1)
    _annotate_bars(ax2, bars2)
    _annotate_bars(ax2, bars3, fmt="{:.1f}")

    fig.tight_layout()
    fig.savefig(result_dir / "problem2_split_hover_ablation.png", dpi=PAPER_DPI)
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

    dc_raw = sol.get("direct_confirmed_nodes", "")
    if isinstance(dc_raw, list):
        direct_nodes = {int(n) for n in dc_raw}
    elif isinstance(dc_raw, str) and dc_raw.strip():
        direct_nodes = {int(n) for n in dc_raw.split()}
    else:
        direct_nodes: set[int] = set()

    mt_raw = sol.get("manual_target_nodes", "")
    if isinstance(mt_raw, list):
        manual_targets = {int(n) for n in mt_raw}
    elif isinstance(mt_raw, str) and mt_raw.strip():
        manual_targets = {int(n) for n in mt_raw.split()}
    else:
        manual_targets: set[int] = set()

    # Build node_id -> (x, y, z)
    node_coords: dict[int, tuple[float, float, float]] = {}
    manual_coords: dict[str, tuple[float, float]] = {}
    for t in data.targets:
        node_coords[t.node_id] = (t.x_m, t.y_m, t.z_m)
        manual_coords[t.manual_point_id] = (t.manual_x_m, t.manual_y_m)

    # Depot (node 0) — coordinates from flight matrix (may be origin at 0,0)
    # Use the first target closest to depot assumption, or use P0 position
    # The depot is node 0. We'll place it at origin or derive from targets.
    depot_x = 0.0
    depot_y = 0.0

    fig, ax = plt.subplots(figsize=(10.8, 8.2))

    # Plot UAV routes
    colors = ["#4C78A8", "#F58518", "#54A24B", "#9467BD"]
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

        ax.plot(
            path_x, path_y, marker=".", color=color, linewidth=1.8,
            label=f"无人机{uav_id}", alpha=0.72, zorder=2,
        )

    # Plot targets by final decision.
    direct_x = [node_coords[n][0] for n in sorted(direct_nodes)]
    direct_y = [node_coords[n][1] for n in sorted(direct_nodes)]
    manual_x = [node_coords[n][0] for n in sorted(manual_targets)]
    manual_y = [node_coords[n][1] for n in sorted(manual_targets)]
    if direct_x:
        ax.scatter(
            direct_x, direct_y, c="#2E7D32", marker="o", s=78,
            edgecolor="white", linewidth=0.8, zorder=5,
            label="无人机直接确认目标",
        )
    if manual_x:
        ax.scatter(
            manual_x, manual_y, c="#757575", marker="s", s=70,
            edgecolor="white", linewidth=0.8, zorder=5,
            label="需人工复核目标",
        )
    for nid, (x, y, _) in node_coords.items():
        ax.annotate(
            str(nid), (x, y), textcoords="offset points", xytext=(5, 5),
            fontsize=8, color="#111111", zorder=6,
        )

    # Plot depot after route lines so it stays visible.
    ax.scatter(
        [depot_x], [depot_y], c="#D62728", marker="*", s=260, zorder=7,
        label="服务中心P0",
    )
    ax.annotate(
        "P0", (depot_x, depot_y), textcoords="offset points", xytext=(6, 6),
        fontsize=10, color="#D62728", fontweight="bold", zorder=8,
    )

    # Plot ground path
    ground_path = sol.get("ground_path", [])
    if ground_path:
        gp_x: list[float] = []
        gp_y: list[float] = []
        for pid in ground_path:
            if pid == "P0":
                gp_x.append(depot_x)
                gp_y.append(depot_y)
            elif pid in manual_coords:
                mx, my = manual_coords[pid]
                gp_x.append(mx)
                gp_y.append(my)
            else:
                gp_x.append(depot_x)
                gp_y.append(depot_y)
        ax.plot(
            gp_x, gp_y, marker="^", color="#D62728", linewidth=2.2,
            linestyle="--", label="物业人员复核路径", alpha=0.72, zorder=3,
        )
        ax.scatter(
            gp_x[1:-1], gp_y[1:-1], marker="^", c="#D62728", s=72,
            edgecolor="white", linewidth=0.7, zorder=6,
            label="人工复核点",
        )

    ax.text(
        0.99, 0.02,
        (
            f"T={sol['closed_loop_time_s']:.0f}s, "
            f"T_u={sol['uav_phase_time_s']:.0f}s, "
            f"T_g={sol['ground_review_time_s']:.0f}s\n"
            f"直接确认{len(direct_nodes)}个, 人工复核{len(manual_targets)}个, "
            f"$C_M$={sol.get('weighted_manual_cost', '')}"
        ),
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=9,
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "alpha": 0.86,
              "edgecolor": "#cccccc"},
    )

    ax.set_xlabel("X / m")
    ax.set_ylabel("Y / m")
    ax.set_title("推荐闭环方案：无人机航线与物业复核路径")
    ax.legend(loc="upper left", fontsize=7, ncols=2)
    ax.set_aspect("equal", adjustable="datalim")
    ax.grid(True, color=GRID_COLOR, alpha=0.55)

    fig.tight_layout()
    fig.savefig(result_dir / "recommended_routes.png", dpi=PAPER_DPI)
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
      - problem2_baseline_comparison.png
      - problem2_k_comparison.png
      - problem2_threshold_sensitivity.png
      - problem2_acceptance_tolerance_sensitivity.png
      - problem2_energy_parameter_sensitivity.png
      - problem2_split_hover_ablation.png
      - recommended_routes.png
    """
    data_path = Path(data_path)
    result_dir = Path(result_dir)

    _plot_problem1_k_comparison(result_dir)
    _plot_problem2_baseline_comparison(result_dir)
    _plot_problem2_k_comparison(result_dir)
    _plot_problem2_threshold_sensitivity(result_dir)
    _plot_problem2_acceptance_tolerance(result_dir)
    _plot_problem2_energy_parameters(result_dir)
    _plot_problem2_split_hover_ablation(result_dir)
    _plot_recommended_routes(data_path, result_dir)
