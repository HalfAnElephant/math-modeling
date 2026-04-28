"""Black-box tests for Task 001: Environment & Data Loading.

These tests verify the package through its public external interfaces ONLY.
No internal implementation details are referenced — no `_`-prefixed imports,
no knowledge of internal data structures, no mocking of internal state.

Coverage: all external interfaces (package, data loading, validation, data
classes) across positive scenarios, negative scenarios, and edge cases.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import c_uav_inspection
from c_uav_inspection.data import (
    ProblemData,
    Target,
    UAVParams,
    load_problem_data,
    validate_problem_data,
)

# ---------------------------------------------------------------------------
# Shared constants / fixtures
# ---------------------------------------------------------------------------

DATA_PATH: Path = Path("2026同济数学建模竞赛赛题/2026C数据.xlsx")

EXPECTED_TARGET_COUNT: int = 16
EXPECTED_UAV_PARAM_NAMES: frozenset[str] = frozenset({
    "k_max",
    "battery_capacity_j",
    "safety_reserve_j",
    "effective_energy_limit_j",
    "horizontal_speed_mps",
    "vertical_speed_mps",
    "horizontal_energy_j_per_m",
    "up_energy_j_per_m",
    "down_energy_j_per_m",
    "hover_power_j_per_s",
    "battery_swap_time_s",
    "operating_horizon_s",
    "walking_speed_mps",
    "walking_detour_factor",
})

EXPECTED_TARGET_FIELD_NAMES: frozenset[str] = frozenset({
    "node_id",
    "node_name",
    "building_id",
    "x_m",
    "y_m",
    "z_m",
    "priority_level",
    "priority_weight",
    "issue_type",
    "base_hover_time_s",
    "direct_confirm_time_s",
    "manual_point_id",
    "manual_x_m",
    "manual_y_m",
    "manual_service_time_s",
})

EXPECTED_VALIDATION_KEYS: frozenset[str] = frozenset({
    "target_count",
    "base_hover_sum_s",
    "direct_hover_sum_s",
    "confirm_thresholds_valid",
    "max_single_direct_confirm_energy_j",
})


# ---------------------------------------------------------------------------
# Positive scenarios — external interfaces
# ---------------------------------------------------------------------------


def test_package_exposes_version() -> None:
    """Package __init__ exposes __version__ == "0.1.0"."""
    assert c_uav_inspection.__version__ == "0.1.0"


def test_load_problem_data_returns_problem_data_instance() -> None:
    """load_problem_data returns a ProblemData instance."""
    data: ProblemData = load_problem_data(DATA_PATH)
    assert isinstance(data, ProblemData)


def test_problem_data_has_all_expected_fields() -> None:
    """ProblemData contains params, targets, flight_time_s, flight_energy_j,
    ground_time_s with correct types."""
    data: ProblemData = load_problem_data(DATA_PATH)

    assert isinstance(data.params, UAVParams)
    assert isinstance(data.targets, list)
    assert len(data.targets) > 0
    assert all(isinstance(t, Target) for t in data.targets)
    assert isinstance(data.flight_time_s, dict)
    assert isinstance(data.flight_energy_j, dict)
    assert isinstance(data.ground_time_s, dict)


def test_uav_params_has_all_expected_fields() -> None:
    """UAVParams instance exposes all 14 parameter fields with correct types."""
    data: ProblemData = load_problem_data(DATA_PATH)
    params: UAVParams = data.params

    # Verify every expected field exists and has a non-None value
    for name in EXPECTED_UAV_PARAM_NAMES:
        assert hasattr(params, name), f"UAVParams missing field: {name}"
        assert getattr(params, name) is not None, f"UAVParams field {name} is None"

    assert isinstance(params.k_max, int)
    assert all(
        isinstance(getattr(params, name), (int, float))
        for name in EXPECTED_UAV_PARAM_NAMES - {"k_max"}
    )


def test_target_has_all_expected_fields() -> None:
    """Every Target instance exposes all 15 fields with non-None values."""
    data: ProblemData = load_problem_data(DATA_PATH)

    for target in data.targets:
        for name in EXPECTED_TARGET_FIELD_NAMES:
            assert hasattr(target, name), f"Target missing field: {name}"
            assert getattr(target, name) is not None, (
                f"Target {target.node_id} field {name} is None"
            )

    # Spot-check types on first target
    t0: Target = data.targets[0]
    assert isinstance(t0.node_id, int)
    assert isinstance(t0.node_name, str)
    assert isinstance(t0.x_m, float)
    assert isinstance(t0.priority_weight, int)
    assert isinstance(t0.base_hover_time_s, float)


def test_targets_have_sequential_ids_1_to_16() -> None:
    """Target node_ids are exactly 1..16."""
    data: ProblemData = load_problem_data(DATA_PATH)
    ids: list[int] = sorted(t.node_id for t in data.targets)
    assert ids == list(range(1, 17))


def test_flight_matrices_use_int_tuple_keys() -> None:
    """Flight time and energy matrices use (int, int) keys covering
    depot (0) and all targets (1..16)."""
    data: ProblemData = load_problem_data(DATA_PATH)

    expected_ids: set[int] = set(range(0, 17))

    for matrix_name, matrix in [
        ("flight_time_s", data.flight_time_s),
        ("flight_energy_j", data.flight_energy_j),
    ]:
        assert len(matrix) > 0, f"{matrix_name} is empty"
        from_ids: set[int] = set()
        to_ids: set[int] = set()
        for key in matrix:
            assert isinstance(key, tuple), f"{matrix_name} key {key!r} is not tuple"
            assert len(key) == 2, f"{matrix_name} key {key!r} length != 2"
            frm, to = key
            assert isinstance(frm, int), f"{matrix_name} from-key {frm!r} is not int"
            assert isinstance(to, int), f"{matrix_name} to-key {to!r} is not int"
            from_ids.add(frm)
            to_ids.add(to)
        assert 0 in from_ids, f"{matrix_name} missing depot from-keys"
        assert from_ids == expected_ids, (
            f"{matrix_name} from-keys {sorted(from_ids)} != 0..16"
        )
        assert to_ids == expected_ids, (
            f"{matrix_name} to-keys {sorted(to_ids)} != 0..16"
        )


def test_ground_matrix_uses_str_tuple_keys() -> None:
    """Ground time matrix uses (str, str) keys."""
    data: ProblemData = load_problem_data(DATA_PATH)
    matrix: dict[tuple[str, str], float] = data.ground_time_s

    assert len(matrix) > 0, "ground_time_s is empty"
    for key in matrix:
        assert isinstance(key, tuple), f"ground key {key!r} is not tuple"
        assert len(key) == 2, f"ground key {key!r} length != 2"
        frm, to = key
        assert isinstance(frm, str), f"ground from-key {frm!r} is not str"
        assert isinstance(to, str), f"ground to-key {to!r} is not str"


def test_self_flight_time_and_energy_are_zero() -> None:
    """Flight time and energy from a node to itself should be 0."""
    data: ProblemData = load_problem_data(DATA_PATH)

    for nid in range(0, 17):
        assert data.flight_time_s[(nid, nid)] == 0.0, (
            f"flight_time_s[({nid}, {nid})] should be 0"
        )
        assert data.flight_energy_j[(nid, nid)] == 0.0, (
            f"flight_energy_j[({nid}, {nid})] should be 0"
        )


def test_target_consistency_with_matrices() -> None:
    """Every target (1..16) must appear in flight matrices as to/from keys."""
    data: ProblemData = load_problem_data(DATA_PATH)
    target_ids: set[int] = {t.node_id for t in data.targets}

    # Verify all targets referenced in flight_time_s from depot
    for nid in target_ids:
        assert (0, nid) in data.flight_time_s, (
            f"flight_time_s missing depot->target key (0, {nid})"
        )
        assert (nid, 0) in data.flight_time_s, (
            f"flight_time_s missing target->depot key ({nid}, 0)"
        )


def test_validate_problem_data_returns_expected_keys() -> None:
    """validate_problem_data returns dict with all 5 expected keys."""
    data: ProblemData = load_problem_data(DATA_PATH)
    summary: dict[str, Any] = validate_problem_data(data)

    for key in EXPECTED_VALIDATION_KEYS:
        assert key in summary, f"Validation summary missing key: {key}"
        assert summary[key] is not None, f"Validation summary key {key} is None"


def test_validate_target_count_matches() -> None:
    """Validation target_count matches actual target list length."""
    data: ProblemData = load_problem_data(DATA_PATH)
    summary: dict[str, Any] = validate_problem_data(data)

    assert summary["target_count"] == EXPECTED_TARGET_COUNT
    assert summary["target_count"] == len(data.targets)


def test_validate_hover_sums_are_positive() -> None:
    """Validation hover sums are positive numbers."""
    data: ProblemData = load_problem_data(DATA_PATH)
    summary: dict[str, Any] = validate_problem_data(data)

    assert summary["base_hover_sum_s"] > 0
    assert summary["direct_hover_sum_s"] > 0
    assert summary["base_hover_sum_s"] <= summary["direct_hover_sum_s"], (
        "base hover sum should not exceed direct confirm hover sum"
    )


def test_validate_confirm_thresholds_valid_is_true() -> None:
    """With real data, all direct_confirm_time_s >= base_hover_time_s."""
    data: ProblemData = load_problem_data(DATA_PATH)
    summary: dict[str, Any] = validate_problem_data(data)

    assert summary["confirm_thresholds_valid"] is True


def test_validate_energy_within_limit() -> None:
    """Max single direct-confirm energy does not exceed effective limit."""
    data: ProblemData = load_problem_data(DATA_PATH)
    summary: dict[str, Any] = validate_problem_data(data)

    assert summary["max_single_direct_confirm_energy_j"] > 0
    assert summary["max_single_direct_confirm_energy_j"] <= data.params.effective_energy_limit_j


def test_validate_energy_formula_consistency() -> None:
    """max_single_direct_confirm_energy_j must be at least the hover energy
    for the target with the largest roundtrip+hover cost."""
    data: ProblemData = load_problem_data(DATA_PATH)
    summary: dict[str, Any] = validate_problem_data(data)

    # Reconstruct expected minimum: for any target, the energy is at least
    # max(roundtrip_flight_j + direct_confirm_time_s * hover_power)
    min_possible: float = 0.0
    for t in data.targets:
        rt: float = data.flight_energy_j[(0, t.node_id)] + data.flight_energy_j[(t.node_id, 0)]
        energy: float = rt + t.direct_confirm_time_s * data.params.hover_power_j_per_s
        if energy > min_possible:
            min_possible = energy

    assert summary["max_single_direct_confirm_energy_j"] >= min_possible


# ---------------------------------------------------------------------------
# Negative scenarios — error handling
# ---------------------------------------------------------------------------


def test_load_nonexistent_file_raises() -> None:
    """load_problem_data with a non-existent file must raise an error."""
    nonexistent: Path = Path("nonexistent_file_xyz_12345.xlsx")
    with pytest.raises(Exception):
        load_problem_data(nonexistent)


def test_load_directory_path_raises() -> None:
    """load_problem_data with a directory path must raise an error."""
    with pytest.raises(Exception):
        load_problem_data(Path("."))


def test_load_non_excel_file_raises() -> None:
    """load_problem_data with a non-Excel file must raise an error."""
    with pytest.raises(Exception):
        load_problem_data(Path(__file__))  # this .py file is not an xlsx


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_repeated_loads_produce_consistent_data() -> None:
    """Loading the same file twice produces equivalent results."""
    data1: ProblemData = load_problem_data(DATA_PATH)
    data2: ProblemData = load_problem_data(DATA_PATH)

    assert data1.params == data2.params
    assert data1.targets == data2.targets
    assert data1.flight_time_s == data2.flight_time_s
    assert data1.flight_energy_j == data2.flight_energy_j
    assert data1.ground_time_s == data2.ground_time_s


def test_validate_is_pure_no_side_effects() -> None:
    """validate_problem_data does not mutate the ProblemData instance."""
    data: ProblemData = load_problem_data(DATA_PATH)

    targets_before: list[Target] = list(data.targets)
    params_before: UAVParams = data.params
    ft_before: dict[tuple[int, int], float] = dict(data.flight_time_s)

    validate_problem_data(data)

    assert list(data.targets) == targets_before, "targets mutated by validate"
    assert data.params == params_before, "params mutated by validate"
    assert dict(data.flight_time_s) == ft_before, "flight_time_s mutated by validate"


def test_target_is_immutable() -> None:
    """Target dataclass is frozen (immutable)."""
    data: ProblemData = load_problem_data(DATA_PATH)
    t: Target = data.targets[0]

    with pytest.raises(Exception):
        t.node_id = 999  # type: ignore[misc]


def test_uav_params_is_immutable() -> None:
    """UAVParams dataclass is frozen (immutable)."""
    data: ProblemData = load_problem_data(DATA_PATH)
    p: UAVParams = data.params

    with pytest.raises(Exception):
        p.k_max = 999  # type: ignore[misc]


def test_problem_data_is_immutable() -> None:
    """ProblemData dataclass is frozen (immutable)."""
    data: ProblemData = load_problem_data(DATA_PATH)

    with pytest.raises(Exception):
        data.params = data.params  # type: ignore[misc]


def test_all_matrices_have_non_negative_values() -> None:
    """All matrix values (flight time, flight energy, ground time) are >= 0."""
    data: ProblemData = load_problem_data(DATA_PATH)

    for matrix_name, matrix in [
        ("flight_time_s", data.flight_time_s),
        ("flight_energy_j", data.flight_energy_j),
        ("ground_time_s", data.ground_time_s),
    ]:
        for key, value in matrix.items():
            assert value >= 0, f"{matrix_name}[{key!r}] = {value} is negative"


def test_flight_matrices_symmetric_keys() -> None:
    """Flight matrices contain both (i, j) and (j, i) for all node pairs."""
    data: ProblemData = load_problem_data(DATA_PATH)

    for nid_i in range(0, 17):
        for nid_j in range(0, 17):
            assert (nid_i, nid_j) in data.flight_time_s, (
                f"flight_time_s missing key ({nid_i}, {nid_j})"
            )
            assert (nid_i, nid_j) in data.flight_energy_j, (
                f"flight_energy_j missing key ({nid_i}, {nid_j})"
            )
