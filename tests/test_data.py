from pathlib import Path

import pytest

from c_uav_inspection.data import _read_uav_params, load_problem_data, validate_problem_data


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


def test_read_uav_params_raises_on_unexpected_parameter():
    """CR-004 regression: _read_uav_params must reject extra parameters."""
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active

    # 14 params (rows 4-17), with one expected key replaced by an unexpected one
    params = [
        ("K_max", 4),
        ("battery_capacity_J", 500000),
        ("safety_reserve_J", 80000),
        ("effective_energy_limit_J", 135000),
        ("horizontal_speed_mps", 20),
        ("vertical_speed_mps", 4),
        ("horizontal_energy_J_per_m", 12),
        ("up_energy_J_per_m", 15),
        ("down_energy_J_per_m", 8),
        ("hover_power_J_per_s", 220),
        ("battery_swap_time_s", 300),
        ("operating_horizon_s", 2600),
        ("walking_speed_mps", 1.2),
        ("UNEXPECTED_EXTRA_PARAM", 42),  # replaces walking_detour_factor
    ]

    for i, (name, val) in enumerate(params, start=4):
        ws.cell(row=i, column=1, value=name)
        ws.cell(row=i, column=2, value=val)

    with pytest.raises(ValueError, match=r"(?i)(unexpected|unknown|extra)"):
        _read_uav_params(ws)


def test_read_uav_params_raises_on_missing_parameter():
    """CR-004 regression: _read_uav_params must reject missing parameters."""
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active

    params = [
        ("K_max", 4),
        ("battery_capacity_J", 500000),
        ("safety_reserve_J", 80000),
        ("effective_energy_limit_J", 135000),
        ("horizontal_speed_mps", 20),
        ("vertical_speed_mps", 4),
        ("horizontal_energy_J_per_m", 12),
        ("up_energy_J_per_m", 15),
        ("down_energy_J_per_m", 8),
        ("hover_power_J_per_s", 220),
        ("battery_swap_time_s", 300),
        ("operating_horizon_s", 2600),
        # walking_speed_mps and walking_detour_factor intentionally missing
    ]

    for i, (name, val) in enumerate(params, start=4):
        ws.cell(row=i, column=1, value=name)
        ws.cell(row=i, column=2, value=val)

    with pytest.raises(ValueError, match=r"(?i)(missing)"):
        _read_uav_params(ws)


def test_validate_problem_data_returns_expected_summary():
    data = load_problem_data(DATA_PATH)
    summary = validate_problem_data(data)

    assert summary["target_count"] == 16
    assert summary["base_hover_sum_s"] == 790
    assert summary["direct_hover_sum_s"] == 5210
    assert summary["confirm_thresholds_valid"] is True
    assert summary["max_single_direct_confirm_energy_j"] <= data.params.effective_energy_limit_j
