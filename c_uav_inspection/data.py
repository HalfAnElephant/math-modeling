"""Data loading and validation for Problem C UAV inspection."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import openpyxl


@dataclass(frozen=True)
class UAVParams:
    """UAV and operational parameters read from UAV_Params sheet."""

    k_max: int
    battery_capacity_j: float
    safety_reserve_j: float
    effective_energy_limit_j: float
    horizontal_speed_mps: float
    vertical_speed_mps: float
    horizontal_energy_j_per_m: float
    up_energy_j_per_m: float
    down_energy_j_per_m: float
    hover_power_j_per_s: float
    battery_swap_time_s: float
    operating_horizon_s: float
    walking_speed_mps: float
    walking_detour_factor: float


@dataclass(frozen=True)
class Target:
    """A single inspection target point (node_id 1..16)."""

    node_id: int
    node_name: str
    building_id: str
    x_m: float
    y_m: float
    z_m: float
    priority_level: str
    priority_weight: int
    issue_type: str
    base_hover_time_s: float
    direct_confirm_time_s: float
    manual_point_id: str
    manual_x_m: float
    manual_y_m: float
    manual_service_time_s: float


@dataclass(frozen=True)
class ProblemData:
    """Complete problem data loaded from the Excel workbook."""

    params: UAVParams
    targets: list[Target]
    flight_time_s: dict[tuple[int, int], float]
    flight_energy_j: dict[tuple[int, int], float]
    ground_time_s: dict[tuple[str, str], float]


def _read_uav_params(ws: Any) -> UAVParams:
    """Read UAVParams from UAV_Params worksheet rows 4-17."""
    raw: dict[str, float] = {}
    for row in ws.iter_rows(min_row=4, max_row=17, values_only=True):
        param_name = str(row[0]).strip()
        raw[param_name] = float(row[1])
    return UAVParams(
        k_max=int(raw["K_max"]),
        battery_capacity_j=raw["battery_capacity_J"],
        safety_reserve_j=raw["safety_reserve_J"],
        effective_energy_limit_j=raw["effective_energy_limit_J"],
        horizontal_speed_mps=raw["horizontal_speed_mps"],
        vertical_speed_mps=raw["vertical_speed_mps"],
        horizontal_energy_j_per_m=raw["horizontal_energy_J_per_m"],
        up_energy_j_per_m=raw["up_energy_J_per_m"],
        down_energy_j_per_m=raw["down_energy_J_per_m"],
        hover_power_j_per_s=raw["hover_power_J_per_s"],
        battery_swap_time_s=raw["battery_swap_time_s"],
        operating_horizon_s=raw["operating_horizon_s"],
        walking_speed_mps=raw["walking_speed_mps"],
        walking_detour_factor=raw["walking_detour_factor"],
    )


def _read_targets(ws: Any) -> list[Target]:
    """Read Target list from NodeData worksheet rows 5-20 (node_id 1..16)."""
    targets: list[Target] = []
    for row in ws.iter_rows(min_row=5, max_row=20, values_only=True):
        targets.append(Target(
            node_id=int(row[0]),
            node_name=str(row[1]),
            building_id=str(row[2]),
            x_m=float(row[3]),
            y_m=float(row[4]),
            z_m=float(row[5]),
            priority_level=str(row[6]),
            priority_weight=int(row[7]),
            issue_type=str(row[8]),
            base_hover_time_s=float(row[9]),
            direct_confirm_time_s=float(row[10]),
            manual_point_id=str(row[12]),
            manual_x_m=float(row[13]),
            manual_y_m=float(row[14]),
            manual_service_time_s=float(row[15]),
        ))
    return targets


def _read_matrix_sheet(
    ws: Any,
    key_type: str,
) -> dict[tuple[int, int] | tuple[str, str], float]:
    """Read a flight/ground time/energy matrix from a worksheet.

    Args:
        ws: The openpyxl worksheet.
        key_type: "int" for flight matrices (0..16), "str" for ground matrix.

    Returns:
        Dict mapping (from_id, to_id) -> value.
    """
    # Read header row (row 3) to get column identifiers
    header_row = next(ws.iter_rows(min_row=3, max_row=3, values_only=True))
    col_ids: list[int | str] = []
    for col_val in header_row[2:]:
        if col_val is None:
            break
        if key_type == "int":
            col_ids.append(int(col_val))
        else:
            col_ids.append(str(col_val))

    matrix: dict[tuple[int | str, int | str], float] = {}
    for row in ws.iter_rows(min_row=4, max_row=20, values_only=True):
        if key_type == "int":
            from_id: int | str = int(row[0])
        else:
            from_id = str(row[0])
        for idx, to_id in enumerate(col_ids):
            value = float(row[2 + idx])
            matrix[(from_id, to_id)] = value
    return matrix


def load_problem_data(path: str | Path) -> ProblemData:
    """Load complete problem data from the Excel workbook.

    Reads UAV_Params, NodeData, FlightTime, FlightEnergy, and GroundTime sheets.
    Preserves flight matrix keys (i, j) for nodes 0..16 and string keys
    like ("P0", "MP01") for the ground matrix.
    """
    wb = openpyxl.load_workbook(str(path), data_only=True)
    try:
        params = _read_uav_params(wb["UAV_Params"])
        targets = _read_targets(wb["NodeData"])

        flight_time_s = _read_matrix_sheet(wb["FlightTime"], key_type="int")
        flight_energy_j = _read_matrix_sheet(wb["FlightEnergy"], key_type="int")
        ground_time_s = _read_matrix_sheet(wb["GroundTime"], key_type="str")
    finally:
        wb.close()
    return ProblemData(
        params=params,
        targets=targets,
        flight_time_s=flight_time_s,
        flight_energy_j=flight_energy_j,
        ground_time_s=ground_time_s,
    )


def validate_problem_data(data: ProblemData) -> dict[str, Any]:
    """Validate loaded problem data and return a summary dictionary.

    The returned dictionary includes at minimum:
        target_count, base_hover_sum_s, direct_hover_sum_s,
        confirm_thresholds_valid, max_single_direct_confirm_energy_j.
    """
    targets = data.targets
    params = data.params
    flight_energy = data.flight_energy_j

    target_count = len(targets)
    base_hover_sum_s = sum(t.base_hover_time_s for t in targets)
    direct_hover_sum_s = sum(t.direct_confirm_time_s for t in targets)
    confirm_thresholds_valid = all(
        t.direct_confirm_time_s >= t.base_hover_time_s for t in targets
    )

    # max single-target direct-confirm roundtrip energy:
    # roundtrip flight energy (0 -> target -> 0) + hover energy for direct confirm
    max_energy: float = 0.0
    for t in targets:
        nid = t.node_id
        roundtrip_flight = flight_energy.get((0, nid), 0.0) + flight_energy.get((nid, 0), 0.0)
        confirm_energy = roundtrip_flight + t.direct_confirm_time_s * params.hover_power_j_per_s
        if confirm_energy > max_energy:
            max_energy = confirm_energy

    return {
        "target_count": target_count,
        "base_hover_sum_s": base_hover_sum_s,
        "direct_hover_sum_s": direct_hover_sum_s,
        "confirm_thresholds_valid": confirm_thresholds_valid,
        "max_single_direct_confirm_energy_j": max_energy,
    }
