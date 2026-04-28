import copy
from pathlib import Path
import csv

from c_uav_inspection.experiments import (
    _add_normalized_objective,
    run_all_experiments,
)


DATA_PATH = Path("2026同济数学建模竞赛赛题/2026C数据.xlsx")


def test_run_all_experiments_writes_expected_files(tmp_path):
    run_all_experiments(DATA_PATH, tmp_path)

    assert (tmp_path / "problem1_k_comparison.csv").exists()
    assert (tmp_path / "problem1_swap_sensitivity.csv").exists()
    assert (tmp_path / "problem2_k_comparison.csv").exists()
    assert (tmp_path / "problem2_threshold_sensitivity.csv").exists()
    assert (tmp_path / "recommended_solution.json").exists()

    with (tmp_path / "problem2_k_comparison.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert "normalized_objective" in rows[0]
    assert all(0.0 <= float(row["normalized_objective"]) <= 1.0 for row in rows)


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
