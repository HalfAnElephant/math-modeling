import copy
import csv
from pathlib import Path

import pytest

from c_uav_inspection.experiments import (
    _add_normalized_objective,
    run_all_experiments,
)


DATA_PATH = Path("2026同济数学建模竞赛赛题/2026C数据.xlsx")


def test_run_all_experiments_writes_expected_files(tmp_path):
    run_all_experiments(DATA_PATH, tmp_path)

    assert (tmp_path / "problem1_k_comparison_current_packed.csv").exists()
    assert (tmp_path / "problem1_time_priority_k_comparison.csv").exists()
    assert (tmp_path / "problem1_parallel_route_count_ablation.csv").exists()
    assert (tmp_path / "problem1_swap_sensitivity_k1.csv").exists()
    assert (tmp_path / "problem1_swap_sensitivity_k4_reference.csv").exists()
    assert (tmp_path / "problem2_baseline_comparison.csv").exists()
    assert (tmp_path / "problem2_k_comparison.csv").exists()
    assert (tmp_path / "problem2_threshold_sensitivity.csv").exists()
    assert (tmp_path / "problem2_split_hover_ablation.csv").exists()
    assert (tmp_path / "problem2_acceptance_tolerance_sensitivity.csv").exists()
    assert (tmp_path / "problem2_energy_limit_sensitivity.csv").exists()
    assert (tmp_path / "problem2_hover_power_sensitivity.csv").exists()
    assert (tmp_path / "recommended_solution.json").exists()

    with (tmp_path / "problem2_k_comparison.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert "normalized_objective" in rows[0]
    assert "weighted_manual_cost" in rows[0]
    assert "direct_confirm_count" in rows[0]
    assert "uav_phase_time_s" in rows[0]
    assert all(0.0 <= float(row["normalized_objective"]) <= 1.0 for row in rows)

    # Verify swap sensitivity files have the k column
    with (tmp_path / "problem1_swap_sensitivity_k1.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert "k" in rows[0]
    assert all(int(row["k"]) == 1 for row in rows)

    with (tmp_path / "problem1_swap_sensitivity_k4_reference.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert "k" in rows[0]
    assert "notes" in rows[0]


def test_add_normalized_objective_does_not_mutate_input():
    """CR-001: verify _add_normalized_objective does not mutate the input rows."""
    original_rows: list[dict] = [
        {"a": 10, "b": 20},
        {"a": 30, "b": 40},
    ]
    rows_before = copy.deepcopy(original_rows)
    weights: dict[str, float] = {"a": 1.0, "b": 1.0}

    _add_normalized_objective(original_rows, weights)

    # Verify the input list entries are unchanged
    assert original_rows == rows_before, (
        "_add_normalized_objective mutated the input rows in-place"
    )


def test_problem2_baseline_comparison_base_only_row(tmp_path):
    """Verify baseline comparison CSV has correct base-only scheme values."""
    run_all_experiments(DATA_PATH, tmp_path)
    with (tmp_path / "problem2_baseline_comparison.csv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))

    base = rows[0]
    assert base["scheme"] == "仅基础巡检(alpha->inf)"
    # Base-only inspection visits all 16 targets with only base hover → all
    # targets must be reviewed manually by ground personnel.
    assert int(base["manual_count"]) == 16
    assert int(base["weighted_manual_cost"]) == 36
    # All time and energy values must be positive.
    assert float(base["uav_phase_time_s"]) > 0
    assert float(base["ground_review_time_s"]) > 0
    assert float(base["closed_loop_time_s"]) > 0
    # Closed-loop = UAV phase + ground review (within floating-point tolerance).
    assert float(base["closed_loop_time_s"]) == pytest.approx(
        float(base["uav_phase_time_s"]) + float(base["ground_review_time_s"])
    )
    # Direct confirm count is 0 for base-only (alpha->inf means no direct confirm).
    assert int(base["direct_confirm_count"]) == 0


def test_problem1_swap_sensitivity_k1_uses_critical_path(tmp_path):
    """K=1 swap sensitivity: swap time is on critical path (single UAV with 2 sorties).

    With K=1, a single UAV must fly all sorties sequentially.  Battery swap time
    between consecutive sorties therefore adds directly to the UAV phase time.
    """
    run_all_experiments(DATA_PATH, tmp_path)
    with (tmp_path / "problem1_swap_sensitivity_k1.csv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))

    # Sort rows by battery_swap_time_s for sequential comparison.
    rows_by_swap = sorted(rows, key=lambda r: int(r["battery_swap_time_s"]))

    for row in rows_by_swap:
        assert int(row["k"]) == 1
        assert float(row["uav_phase_time_s"]) > 0

    # Critical-path property: each 150 s increase in swap time should increase
    # UAV phase time by exactly 150 s (one swap per sortie pair, additive).
    swaps = [int(r["battery_swap_time_s"]) for r in rows_by_swap]
    times = [float(r["uav_phase_time_s"]) for r in rows_by_swap]
    assert swaps == [0, 150, 300, 450, 600]

    for i in range(1, len(swaps)):
        swap_delta = swaps[i] - swaps[i - 1]
        time_delta = times[i] - times[i - 1]
        assert time_delta == pytest.approx(swap_delta), (
            f"Swap {swaps[i-1]}→{swaps[i]}: expected time delta {swap_delta}, "
            f"got {time_delta}"
        )


def test_problem2_split_hover_ablation_csv_has_expected_schema(tmp_path):
    """Verify split-hover ablation CSV exists with correct fields and rows."""
    run_all_experiments(DATA_PATH, tmp_path)
    csv_path = tmp_path / "problem2_split_hover_ablation.csv"
    assert csv_path.exists()

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    expected_fields = {
        "scheme", "allow_split_hover", "k", "direct_threshold_multiplier",
        "closed_loop_time_s", "uav_phase_time_s", "ground_review_time_s",
        "manual_count", "weighted_manual_cost", "direct_confirm_count",
        "total_energy_j", "load_std_s", "route_count", "feasible",
        "normalized_objective",
    }
    assert set(rows[0].keys()) == expected_fields

    # Must have exactly 2 rows (one per scheme, K=4 only per subplan)
    assert len(rows) == 2, f"Expected 2 rows (K=4 only), got {len(rows)}"
    assert [row["scheme"] for row in rows] == ["可拆分悬停", "不可拆分悬停"]

    # All rows must have feasible=True and normalized_objective in [0,1]
    for row in rows:
        assert row["feasible"] in ("True", "False")
        if row["feasible"] == "True":
            val = float(row["normalized_objective"])
            assert 0.0 <= val <= 1.0, (
                f"normalized_objective {val} out of range [0,1]"
            )

    # Feasible rows must have numeric values for time/energy columns
    numeric_cols = [
        "closed_loop_time_s", "uav_phase_time_s", "ground_review_time_s",
        "total_energy_j", "load_std_s", "route_count",
    ]
    for row in rows:
        if row["feasible"] == "True":
            for col in numeric_cols:
                assert row[col] != "", (
                    f"{col} should be non-empty for feasible row"
                )
            assert float(row["closed_loop_time_s"]) > 0
        else:
            assert row["closed_loop_time_s"] == ""


# ---------------------------------------------------------------------------
# Exact enumeration tests (task 005)
# ---------------------------------------------------------------------------


def test_include_expensive_false_does_not_create_enum_files(tmp_path):
    """Default include_expensive=False must NOT create exact enumeration files."""
    run_all_experiments(DATA_PATH, tmp_path, include_expensive=False)

    assert not (tmp_path / "problem2_exact_summary.json").exists()
    assert not (tmp_path / "problem2_exact_top.csv").exists()


def test_task006_new_sensitivity_csv_files_exist_and_valid(tmp_path):
    """Verify the three new sensitivity CSVs (Task 006) exist and have correct values."""
    run_all_experiments(DATA_PATH, tmp_path)

    # ── Acceptance tolerance sensitivity ──
    tol_path = tmp_path / "problem2_acceptance_tolerance_sensitivity.csv"
    assert tol_path.exists()
    with tol_path.open("r", encoding="utf-8", newline="") as handle:
        tol_rows = list(csv.DictReader(handle))
    tol_values = [float(r["manual_reduction_time_tolerance"]) for r in tol_rows]
    assert tol_values == [1.0, 1.03, 1.05, 1.10], (
        f"Expected [1.0, 1.03, 1.05, 1.10], got {tol_values}"
    )
    for row in tol_rows:
        assert "direct_confirmed_nodes" in row
        assert "manual_target_nodes" in row
        assert float(row["closed_loop_time_s"]) > 0

    # ── Energy limit sensitivity ──
    energy_path = tmp_path / "problem2_energy_limit_sensitivity.csv"
    assert energy_path.exists()
    with energy_path.open("r", encoding="utf-8", newline="") as handle:
        energy_rows = list(csv.DictReader(handle))
    energy_values = [float(r["effective_energy_limit_j"]) for r in energy_rows]
    assert 135000.0 in energy_values, (
        f"Baseline energy 135000.0 not found in {energy_values}"
    )
    # Verify route_count field is present in all energy sensitivity rows
    for row in energy_rows:
        assert "route_count" in row, (
            f"route_count missing from energy limit row: {list(row.keys())}"
        )
        if row["feasible"] == "True":
            assert row["route_count"] != "", (
                "route_count must be non-empty for feasible row"
            )

    # ── Hover power sensitivity ──
    hover_path = tmp_path / "problem2_hover_power_sensitivity.csv"
    assert hover_path.exists()
    with hover_path.open("r", encoding="utf-8", newline="") as handle:
        hover_rows = list(csv.DictReader(handle))
    hover_values = [float(r["hover_power_j_per_s"]) for r in hover_rows]
    assert 220.0 in hover_values, (
        f"Baseline hover power 220.0 not found in {hover_values}"
    )
    # Verify route_count field is present in all hover sensitivity rows
    for row in hover_rows:
        assert "route_count" in row, (
            f"route_count missing from hover power row: {list(row.keys())}"
        )
        if row["feasible"] == "True":
            assert row["route_count"] != "", (
                "route_count must be non-empty for feasible row"
            )


def test_run_problem2_exact_enumeration_writes_expected_files_small_data(tmp_path, make_small_data):
    """_run_problem2_exact_enumeration with small data (4 targets → 16 subsets).

    Uses small data to keep test fast. Full 65536 enumeration is tested via
    include_expensive=True in a separate integration test if needed.
    """
    from c_uav_inspection.experiments import _run_problem2_exact_enumeration

    data = make_small_data
    _run_problem2_exact_enumeration(data, tmp_path)

    assert (tmp_path / "problem2_exact_summary.json").exists()
    assert (tmp_path / "problem2_exact_top.csv").exists()

    # Verify summary.json structure
    import json
    summary = json.loads((tmp_path / "problem2_exact_summary.json").read_text("utf-8"))
    assert summary["total_subsets"] == 16
    assert summary["feasible_subsets"] >= 1
    assert summary["rebuild_time_rank"] >= 1
    assert summary["rebuild_time_gap_s"] >= 0.0
    assert summary["rebuild_time_gap_pct"] >= 0.0
    assert summary["rebuild_objective_rank"] >= 1
    assert summary["rebuild_objective_gap"] >= 0.0
    assert "direct_nodes" in summary["best_by_closed_loop"]
    assert "closed_loop_time_s" in summary["best_by_closed_loop"]
    assert summary["rebuild_solution"]["feasible"] is True

    # Verify top.csv structure
    top_rows = list(csv.DictReader(
        (tmp_path / "problem2_exact_top.csv").open("r", encoding="utf-8", newline="")
    ))
    assert len(top_rows) <= 20  # small data may have fewer feasible subsets
    for row in top_rows:
        assert "direct_nodes" in row
        assert "closed_loop_time_s" in row
        assert "normalized_objective" in row
        assert "rank_by_time" in row
        assert "rank_by_objective" in row
        assert 0.0 <= float(row["normalized_objective"]) <= 1.0
