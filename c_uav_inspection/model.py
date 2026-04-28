"""Core model: UAVRoute, RouteMetrics, solution summary, and evaluation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

from c_uav_inspection.data import ProblemData


@dataclass(frozen=True)
class UAVRoute:
    """A single sortie flown by a UAV.

    Attributes:
        uav_id: Identifier for the UAV (1-indexed).
        sortie_id: Identifier for the sortie (1-indexed, per UAV).
        node_sequence: Ordered nodes visited, starting and ending at depot (0).
        hover_times_s: Hover time in seconds for each target node visited.
    """

    uav_id: int
    sortie_id: int
    node_sequence: tuple[int, ...]
    hover_times_s: Mapping[int, float]


@dataclass(frozen=True)
class RouteMetrics:
    """Computed metrics for a single UAVRoute.

    Attributes:
        duration_s: Total time for the route (flight + hover).
        energy_j: Total energy consumed (flight + hover).
        feasible_energy: Whether energy is within the battery limit.
    """

    duration_s: float
    energy_j: float
    feasible_energy: bool


@dataclass(frozen=True)
class UAVSolutionSummary:
    """Aggregated metrics for a complete multi-UAV solution.

    Attributes:
        uav_phase_time_s: Maximum work time across all UAVs (UAV phase duration).
        total_energy_j: Total energy consumed by all routes.
        uav_work_times_s: Mapping from uav_id to total work time (route time + swaps).
        load_std_s: Standard deviation of UAV work times (0 for 0 or 1 UAV).
        feasible_energy: True if every route is within energy limit.
    """

    uav_phase_time_s: float
    total_energy_j: float
    uav_work_times_s: dict[int, float]
    load_std_s: float
    feasible_energy: bool


def evaluate_uav_route(
    route: UAVRoute,
    data: ProblemData,
) -> RouteMetrics:
    """Evaluate a single UAVRoute, computing time, energy, and feasibility.

    Flight time and energy are accumulated along the full node sequence.
    Hover time is summed from route.hover_times_s. Hover energy = hover_time * hover_power.
    Feasibility checks total energy against effective_energy_limit_j.
    """
    seq = route.node_sequence
    flight_time = 0.0
    flight_energy = 0.0

    for i in range(len(seq) - 1):
        source = seq[i]
        target = seq[i + 1]
        flight_time += data.flight_time_s[(source, target)]
        flight_energy += data.flight_energy_j[(source, target)]

    hover_time = sum(route.hover_times_s.values())
    hover_energy = hover_time * data.params.hover_power_j_per_s

    duration_s = flight_time + hover_time
    energy_j = flight_energy + hover_energy
    feasible_energy = energy_j <= data.params.effective_energy_limit_j

    return RouteMetrics(
        duration_s=duration_s,
        energy_j=energy_j,
        feasible_energy=feasible_energy,
    )


def summarize_uav_solution(
    routes: tuple[UAVRoute, ...] | list[UAVRoute],
    data: ProblemData,
    battery_swap_time_s: float,
) -> UAVSolutionSummary:
    """Summarize a complete multi-UAV solution.

    For each UAV:
      - Work time = sum of route durations + (number_of_sorties - 1) * battery_swap_time_s.
    UAV phase time is the maximum work time across all UAVs.
    Load standard deviation uses population std on UAV work times.
    """
    # Group routes by uav_id
    uav_routes: dict[int, list[UAVRoute]] = {}
    for route in routes:
        uav_routes.setdefault(route.uav_id, []).append(route)

    uav_work_times_s: dict[int, float] = {}
    total_energy = 0.0
    all_feasible = True

    for uav_id, uav_route_list in uav_routes.items():
        route_durations = [
            evaluate_uav_route(r, data).duration_s for r in uav_route_list
        ]
        total_duration = sum(route_durations)
        sortie_count = len(uav_route_list)
        # Battery swap time applies between sorties: (n-1) swaps for n sorties
        swap_overhead = (sortie_count - 1) * battery_swap_time_s
        uav_work_times_s[uav_id] = total_duration + swap_overhead

        for r in uav_route_list:
            m = evaluate_uav_route(r, data)
            total_energy += m.energy_j
            if not m.feasible_energy:
                all_feasible = False

    # UAV phase time is the maximum work time
    uav_phase_time_s = max(uav_work_times_s.values()) if uav_work_times_s else 0.0

    # Load std: population standard deviation of work times
    work_times = list(uav_work_times_s.values())
    n = len(work_times)
    if n <= 1:
        load_std_s = 0.0
    else:
        mean = sum(work_times) / n
        variance = sum((t - mean) ** 2 for t in work_times) / n
        load_std_s = math.sqrt(variance)

    return UAVSolutionSummary(
        uav_phase_time_s=uav_phase_time_s,
        total_energy_j=total_energy,
        uav_work_times_s=uav_work_times_s,
        load_std_s=load_std_s,
        feasible_energy=all_feasible,
    )
