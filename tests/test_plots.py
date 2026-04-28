from pathlib import Path

import pytest

from c_uav_inspection.experiments import run_all_experiments
from c_uav_inspection.plots import generate_all_figures


DATA_PATH = Path("2026同济数学建模竞赛赛题/2026C数据.xlsx")


def test_generate_all_figures_creates_png_files(tmp_path):
    run_all_experiments(DATA_PATH, tmp_path)
    generate_all_figures(DATA_PATH, tmp_path)

    assert (tmp_path / "problem1_k_comparison.png").exists()
    assert (tmp_path / "problem2_threshold_sensitivity.png").exists()
    assert (tmp_path / "recommended_routes.png").exists()


def test_generate_all_figures_raises_when_no_input_csv(tmp_path):
    """CR-003: verify error raised when required CSV/JSON is missing."""
    with pytest.raises(FileNotFoundError, match="problem1_k_comparison"):
        generate_all_figures(DATA_PATH, tmp_path)
