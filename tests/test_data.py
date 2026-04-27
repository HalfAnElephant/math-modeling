from pathlib import Path

from c_uav_inspection.data import load_problem_data, validate_problem_data


DATA_PATH = Path("2026同济数学建模竞赛赛题/2026C数据.xlsx")


def test_load_problem_data_counts_targets_and_params():
    data = load_problem_data(DATA_PATH)

    assert len(data.targets) == 16
    assert data.params.k_max == 4
    assert data.params.effective_energy_limit_j == 135000
    assert data.params.hover_power_j_per_s == 220
    assert data.params.battery_swap_time_s == 300
    assert data.params.operating_horizon_s == 2600


def test_loaded_targets_preserve_key_values():
    data = load_problem_data(DATA_PATH)
    by_id = {target.node_id: target for target in data.targets}

    assert by_id[1].node_name == "B1-东立面裂缝"
    assert by_id[1].base_hover_time_s == 50
    assert by_id[1].direct_confirm_time_s == 200
    assert by_id[16].priority_weight == 3
    assert by_id[16].direct_confirm_time_s == 560


def test_matrices_include_depot_and_target_pairs():
    data = load_problem_data(DATA_PATH)

    assert data.flight_time_s[(0, 1)] > 0
    assert data.flight_energy_j[(0, 16)] > 0
    assert data.ground_time_s[("P0", "MP01")] > 0
    assert data.flight_time_s[(3, 3)] == 0


def test_validate_problem_data_returns_expected_summary():
    data = load_problem_data(DATA_PATH)
    summary = validate_problem_data(data)

    assert summary["target_count"] == 16
    assert summary["base_hover_sum_s"] == 790
    assert summary["direct_hover_sum_s"] == 5210
    assert summary["confirm_thresholds_valid"] is True
    assert summary["max_single_direct_confirm_energy_j"] <= data.params.effective_energy_limit_j
