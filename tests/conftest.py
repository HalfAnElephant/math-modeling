"""Shared pytest fixtures for the c_uav_inspection test suite."""

from __future__ import annotations

import pytest

from c_uav_inspection.data import ProblemData, Target, UAVParams


@pytest.fixture
def make_small_data() -> ProblemData:
    """Build a minimal ProblemData with 4 targets → 16 subsets for fast enumeration."""
    params = UAVParams(
        k_max=4,
        battery_capacity_j=540000.0,
        safety_reserve_j=0.0,
        effective_energy_limit_j=540000.0,
        horizontal_speed_mps=10.0,
        vertical_speed_mps=2.0,
        horizontal_energy_j_per_m=50.0,
        up_energy_j_per_m=100.0,
        down_energy_j_per_m=20.0,
        hover_power_j_per_s=220.0,
        battery_swap_time_s=300.0,
        operating_horizon_s=2600.0,
        walking_speed_mps=1.2,
        walking_detour_factor=1.5,
    )

    targets = [
        Target(
            node_id=1, node_name="T1", building_id="B1",
            x_m=100.0, y_m=0.0, z_m=10.0,
            priority_level="High", priority_weight=3,
            issue_type="crack",
            base_hover_time_s=30.0, direct_confirm_time_s=80.0,
            manual_point_id="MP01", manual_x_m=150.0, manual_y_m=0.0,
            manual_service_time_s=60.0,
        ),
        Target(
            node_id=2, node_name="T2", building_id="B1",
            x_m=200.0, y_m=0.0, z_m=10.0,
            priority_level="Medium", priority_weight=2,
            issue_type="rust",
            base_hover_time_s=40.0, direct_confirm_time_s=100.0,
            manual_point_id="MP02", manual_x_m=250.0, manual_y_m=0.0,
            manual_service_time_s=60.0,
        ),
        Target(
            node_id=3, node_name="T3", building_id="B2",
            x_m=0.0, y_m=100.0, z_m=10.0,
            priority_level="Low", priority_weight=1,
            issue_type="loose",
            base_hover_time_s=20.0, direct_confirm_time_s=60.0,
            manual_point_id="MP03", manual_x_m=0.0, manual_y_m=150.0,
            manual_service_time_s=60.0,
        ),
        Target(
            node_id=4, node_name="T4", building_id="B2",
            x_m=0.0, y_m=200.0, z_m=10.0,
            priority_level="Medium", priority_weight=2,
            issue_type="water",
            base_hover_time_s=25.0, direct_confirm_time_s=70.0,
            manual_point_id="MP04", manual_x_m=0.0, manual_y_m=250.0,
            manual_service_time_s=60.0,
        ),
    ]

    node_coords = {
        0: (0.0, 0.0),
        1: (100.0, 0.0),
        2: (200.0, 0.0),
        3: (0.0, 100.0),
        4: (0.0, 200.0),
    }
    flight_time_s: dict[tuple[int, int], float] = {}
    flight_energy_j: dict[tuple[int, int], float] = {}
    for i in range(5):
        for j in range(5):
            if i == j:
                continue
            dx = node_coords[i][0] - node_coords[j][0]
            dy = node_coords[i][1] - node_coords[j][1]
            dist = (dx**2 + dy**2) ** 0.5
            flight_time_s[(i, j)] = dist / params.horizontal_speed_mps
            flight_energy_j[(i, j)] = dist * params.horizontal_energy_j_per_m

    mp_coords = {
        "P0": (0.0, 0.0),
        "MP01": (150.0, 0.0),
        "MP02": (250.0, 0.0),
        "MP03": (0.0, 150.0),
        "MP04": (0.0, 250.0),
    }
    ground_time_s: dict[tuple[str, str], float] = {}
    for a_name, a_pos in mp_coords.items():
        for b_name, b_pos in mp_coords.items():
            if a_name == b_name:
                continue
            dx = a_pos[0] - b_pos[0]
            dy = a_pos[1] - b_pos[1]
            dist = (dx**2 + dy**2) ** 0.5
            ground_time_s[(a_name, b_name)] = (
                dist / params.walking_speed_mps * params.walking_detour_factor
            )

    from c_uav_inspection.data import ManualPoint

    manual_points = {
        "MP01": ManualPoint("MP01", 150.0, 0.0, 60.0, (1,)),
        "MP02": ManualPoint("MP02", 250.0, 0.0, 60.0, (2,)),
        "MP03": ManualPoint("MP03", 0.0, 150.0, 60.0, (3,)),
        "MP04": ManualPoint("MP04", 0.0, 250.0, 60.0, (4,)),
    }

    return ProblemData(
        params=params,
        targets=targets,
        manual_points=manual_points,
        flight_time_s=flight_time_s,
        flight_energy_j=flight_energy_j,
        ground_time_s=ground_time_s,
    )
