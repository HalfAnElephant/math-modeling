# C UAV-Property Joint Inspection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible research workflow for Problem C, producing feasible multi-UAV patrol schedules, UAV-property joint inspection decisions, sensitivity experiments, figures, and paper-ready result tables without introducing ML/DL.

**Architecture:** Use a Python package centered on deterministic data loading, route evaluation, constrained constructive heuristics, local search, ground TSP optimization, experiment runners, and report exports. The mathematical model remains the primary contribution; algorithms only search for high-quality feasible solutions under the stated constraints.

**Tech Stack:** Python 3, `openpyxl`, `numpy`, standard-library `dataclasses`, `itertools`, `json`, `csv`, `unittest` or `pytest`; optional `matplotlib` for figures. Input data stays in `2026同济数学建模竞赛赛题/2026C数据.xlsx`.

---

## File Structure

- Create `c_uav_inspection/__init__.py`: package marker and version string.
- Create `c_uav_inspection/data.py`: workbook parser, typed records, matrix extraction, deterministic validation checks.
- Create `c_uav_inspection/model.py`: route/task/solution dataclasses and exact objective metric calculations.
- Create `c_uav_inspection/problem1.py`: baseline multi-UAV basic patrol solver and `K`/battery-swap comparison helpers.
- Create `c_uav_inspection/problem2.py`: direct-confirm decision logic, property-review TSP, and closed-loop solver.
- Create `c_uav_inspection/search.py`: route construction and local-search operators shared by both problems.
- Create `c_uav_inspection/experiments.py`: command-line experiment runner that writes CSV/JSON summaries.
- Create `c_uav_inspection/plots.py`: figure generator for route maps, Gantt charts, and sensitivity curves.
- Create `tests/test_data.py`: workbook parsing and consistency tests.
- Create `tests/test_model.py`: route energy/time/objective unit tests.
- Create `tests/test_problem1.py`: feasibility and comparison tests for the basic UAV patrol model.
- Create `tests/test_problem2.py`: closed-loop feasibility and direct-confirm tradeoff tests.
- Create `outputs/c_uav_inspection/`: generated results, CSV files, JSON schedules, and figures.
- Create `report/c_uav_inspection_results.md`: paper-ready result narrative, model equations, and table references.

## Research Defaults Locked In

- Do not introduce ML or DL in the main model, algorithm, or result discussion.
- Treat all UAVs as homogeneous and available from time 0.
- Ignore takeoff queues, landing queues, airspace collision avoidance, and weather disturbances, matching the problem statement.
- Allow a target point to be visited multiple times; its hover time is cumulative.
- Require every target point to satisfy `total_hover_s >= base_hover_time_s`.
- In Problem 2, set `direct_confirmed=True` only when `total_hover_s >= direct_confirm_time_s`.
- Property staff start after the UAV phase finishes; property time contributes to closed-loop time but is not constrained by `operating_horizon_s`.
- Use objective weights:
  - Problem 1: `time=0.55`, `priority_completion=0.20`, `energy=0.15`, `balance=0.10`.
  - Problem 2: `closed_loop_time=0.50`, `weighted_manual=0.20`, `manual_count=0.10`, `energy=0.10`, `balance=0.10`.
- Use sensitivity values:
  - UAV count `K = 1,2,3,4`.
  - Battery swap time `tau_b = 0,150,300,450,600`.
  - Direct-confirm threshold multiplier `m = 0.70,0.85,1.00,1.15,1.30`.

---

### Task 1: Create Package Skeleton and Test Harness

**Files:**
- Create: `c_uav_inspection/__init__.py`
- Create: `tests/test_package.py`

- [ ] **Step 1: Write the failing package import test**

Create `tests/test_package.py`:

```python
from c_uav_inspection import __version__


def test_package_exposes_version():
    assert __version__ == "0.1.0"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
python3 -m pytest tests/test_package.py -q
```

Expected: `ModuleNotFoundError: No module named 'c_uav_inspection'`.

- [ ] **Step 3: Create the package marker**

Create `c_uav_inspection/__init__.py`:

```python
"""Reproducible models and experiments for Problem C."""

__version__ = "0.1.0"
```

- [ ] **Step 4: Run the package test**

Run:

```bash
python3 -m pytest tests/test_package.py -q
```

Expected: `1 passed`.

- [ ] **Step 5: Commit**

```bash
git add c_uav_inspection/__init__.py tests/test_package.py
git commit -m "chore: initialize c problem package"
```

---

### Task 2: Implement Workbook Data Loading

**Files:**
- Create: `c_uav_inspection/data.py`
- Test: `tests/test_data.py`

- [ ] **Step 1: Write workbook loading tests**

Create `tests/test_data.py`:

```python
from pathlib import Path

from c_uav_inspection.data import load_problem_data


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m pytest tests/test_data.py -q
```

Expected: import failure for `c_uav_inspection.data`.

- [ ] **Step 3: Implement typed data loading**

Create `c_uav_inspection/data.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

from openpyxl import load_workbook


@dataclass(frozen=True)
class UAVParams:
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
    params: UAVParams
    targets: tuple[Target, ...]
    flight_time_s: Dict[Tuple[int, int], float]
    flight_energy_j: Dict[Tuple[int, int], float]
    ground_time_s: Dict[Tuple[str, str], float]


def _read_params(workbook) -> UAVParams:
    sheet = workbook["UAV_Params"]
    values = {}
    for parameter, value, _unit, _meaning in sheet.iter_rows(min_row=4, values_only=True):
        if parameter:
            values[str(parameter)] = value
    return UAVParams(
        k_max=int(values["K_max"]),
        battery_capacity_j=float(values["battery_capacity_J"]),
        safety_reserve_j=float(values["safety_reserve_J"]),
        effective_energy_limit_j=float(values["effective_energy_limit_J"]),
        horizontal_speed_mps=float(values["horizontal_speed_mps"]),
        vertical_speed_mps=float(values["vertical_speed_mps"]),
        horizontal_energy_j_per_m=float(values["horizontal_energy_J_per_m"]),
        up_energy_j_per_m=float(values["up_energy_J_per_m"]),
        down_energy_j_per_m=float(values["down_energy_J_per_m"]),
        hover_power_j_per_s=float(values["hover_power_J_per_s"]),
        battery_swap_time_s=float(values["battery_swap_time_s"]),
        operating_horizon_s=float(values["operating_horizon_s"]),
        walking_speed_mps=float(values["walking_speed_mps"]),
        walking_detour_factor=float(values["walking_detour_factor"]),
    )


def _read_targets(workbook) -> tuple[Target, ...]:
    sheet = workbook["NodeData"]
    headers = [cell.value for cell in sheet[3]]
    targets: list[Target] = []
    for row in sheet.iter_rows(min_row=5, values_only=True):
        record = dict(zip(headers, row))
        if not record.get("node_id") or int(record["node_id"]) == 0:
            continue
        targets.append(
            Target(
                node_id=int(record["node_id"]),
                node_name=str(record["node_name"]),
                building_id=str(record["building_id"]),
                x_m=float(record["x_m"]),
                y_m=float(record["y_m"]),
                z_m=float(record["z_m"]),
                priority_level=str(record["priority_level"]),
                priority_weight=int(record["priority_weight"]),
                issue_type=str(record["issue_type"]),
                base_hover_time_s=float(record["base_hover_time_s"]),
                direct_confirm_time_s=float(record["direct_confirm_time_s"]),
                manual_point_id=str(record["manual_point_id"]),
                manual_x_m=float(record["manual_x_m"]),
                manual_y_m=float(record["manual_y_m"]),
                manual_service_time_s=float(record["manual_service_time_s"]),
            )
        )
    return tuple(targets)


def _read_numeric_matrix(workbook, sheet_name: str) -> Dict[Tuple[int, int], float]:
    sheet = workbook[sheet_name]
    columns = [int(value) for value in next(sheet.iter_rows(min_row=3, max_row=3, min_col=3, values_only=True))]
    matrix: Dict[Tuple[int, int], float] = {}
    for row in sheet.iter_rows(min_row=4, values_only=True):
        if row[0] is None:
            continue
        source = int(row[0])
        for target, value in zip(columns, row[2:]):
            matrix[(source, target)] = float(value or 0)
    return matrix


def _read_ground_matrix(workbook) -> Dict[Tuple[str, str], float]:
    sheet = workbook["GroundTime"]
    columns = [str(value) for value in next(sheet.iter_rows(min_row=3, max_row=3, min_col=3, values_only=True))]
    matrix: Dict[Tuple[str, str], float] = {}
    for row in sheet.iter_rows(min_row=4, values_only=True):
        if row[0] is None:
            continue
        source = str(row[0])
        for target, value in zip(columns, row[2:]):
            matrix[(source, target)] = float(value or 0)
    return matrix


def load_problem_data(path: Path | str) -> ProblemData:
    workbook = load_workbook(Path(path), data_only=True)
    return ProblemData(
        params=_read_params(workbook),
        targets=_read_targets(workbook),
        flight_time_s=_read_numeric_matrix(workbook, "FlightTime"),
        flight_energy_j=_read_numeric_matrix(workbook, "FlightEnergy"),
        ground_time_s=_read_ground_matrix(workbook),
    )
```

- [ ] **Step 4: Run data tests**

Run:

```bash
python3 -m pytest tests/test_data.py -q
```

Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add c_uav_inspection/data.py tests/test_data.py
git commit -m "feat: load c problem workbook data"
```

---

### Task 3: Add Deterministic Data Consistency Checks

**Files:**
- Modify: `c_uav_inspection/data.py`
- Modify: `tests/test_data.py`

- [ ] **Step 1: Add validation tests**

Append to `tests/test_data.py`:

```python
from c_uav_inspection.data import validate_problem_data


def test_validate_problem_data_returns_expected_summary():
    data = load_problem_data(DATA_PATH)
    summary = validate_problem_data(data)

    assert summary["target_count"] == 16
    assert summary["base_hover_sum_s"] == 790
    assert summary["direct_hover_sum_s"] == 5210
    assert summary["confirm_thresholds_valid"] is True
    assert summary["max_single_direct_confirm_energy_j"] <= data.params.effective_energy_limit_j
```

- [ ] **Step 2: Run validation test to verify it fails**

Run:

```bash
python3 -m pytest tests/test_data.py::test_validate_problem_data_returns_expected_summary -q
```

Expected: import failure for `validate_problem_data`.

- [ ] **Step 3: Implement validation summary**

Append to `c_uav_inspection/data.py`:

```python
def validate_problem_data(data: ProblemData) -> dict[str, float | int | bool]:
    base_sum = sum(target.base_hover_time_s for target in data.targets)
    direct_sum = sum(target.direct_confirm_time_s for target in data.targets)
    thresholds_valid = all(
        target.direct_confirm_time_s >= target.base_hover_time_s
        for target in data.targets
    )
    max_single_direct_energy = max(
        data.flight_energy_j[(0, target.node_id)]
        + data.flight_energy_j[(target.node_id, 0)]
        + target.direct_confirm_time_s * data.params.hover_power_j_per_s
        for target in data.targets
    )
    return {
        "target_count": len(data.targets),
        "base_hover_sum_s": int(base_sum),
        "direct_hover_sum_s": int(direct_sum),
        "confirm_thresholds_valid": thresholds_valid,
        "max_single_direct_confirm_energy_j": max_single_direct_energy,
    }
```

- [ ] **Step 4: Run validation tests**

Run:

```bash
python3 -m pytest tests/test_data.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add c_uav_inspection/data.py tests/test_data.py
git commit -m "feat: validate c problem data"
```

---

### Task 4: Implement Core Route and Solution Metrics

**Files:**
- Create: `c_uav_inspection/model.py`
- Test: `tests/test_model.py`

- [ ] **Step 1: Write metric tests**

Create `tests/test_model.py`:

```python
from pathlib import Path

from c_uav_inspection.data import load_problem_data
from c_uav_inspection.model import UAVRoute, evaluate_uav_route, summarize_uav_solution


DATA_PATH = Path("2026同济数学建模竞赛赛题/2026C数据.xlsx")


def test_evaluate_single_base_route_matches_manual_energy_formula():
    data = load_problem_data(DATA_PATH)
    route = UAVRoute(uav_id=1, sortie_id=1, node_sequence=(0, 1, 0), hover_times_s={1: 50})

    metrics = evaluate_uav_route(route, data)

    expected_energy = data.flight_energy_j[(0, 1)] + data.flight_energy_j[(1, 0)] + 50 * data.params.hover_power_j_per_s
    expected_time = data.flight_time_s[(0, 1)] + data.flight_time_s[(1, 0)] + 50
    assert metrics.energy_j == expected_energy
    assert metrics.duration_s == expected_time
    assert metrics.feasible_energy is True


def test_summarize_solution_includes_swap_time_between_sorties():
    data = load_problem_data(DATA_PATH)
    routes = (
        UAVRoute(uav_id=1, sortie_id=1, node_sequence=(0, 1, 0), hover_times_s={1: 50}),
        UAVRoute(uav_id=1, sortie_id=2, node_sequence=(0, 3, 0), hover_times_s={3: 35}),
        UAVRoute(uav_id=2, sortie_id=1, node_sequence=(0, 4, 0), hover_times_s={4: 55}),
    )

    summary = summarize_uav_solution(routes, data, battery_swap_time_s=300)

    uav1_route_time = sum(evaluate_uav_route(route, data).duration_s for route in routes if route.uav_id == 1)
    uav2_route_time = sum(evaluate_uav_route(route, data).duration_s for route in routes if route.uav_id == 2)
    assert summary.uav_work_times_s[1] == uav1_route_time + 300
    assert summary.uav_work_times_s[2] == uav2_route_time
    assert summary.uav_phase_time_s == max(summary.uav_work_times_s.values())
```

- [ ] **Step 2: Run metric tests to verify they fail**

Run:

```bash
python3 -m pytest tests/test_model.py -q
```

Expected: import failure for `c_uav_inspection.model`.

- [ ] **Step 3: Implement route metrics**

Create `c_uav_inspection/model.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from statistics import pstdev
from typing import Mapping

from c_uav_inspection.data import ProblemData


@dataclass(frozen=True)
class UAVRoute:
    uav_id: int
    sortie_id: int
    node_sequence: tuple[int, ...]
    hover_times_s: Mapping[int, float]


@dataclass(frozen=True)
class RouteMetrics:
    duration_s: float
    energy_j: float
    feasible_energy: bool


@dataclass(frozen=True)
class UAVSolutionSummary:
    uav_phase_time_s: float
    total_energy_j: float
    uav_work_times_s: dict[int, float]
    load_std_s: float
    feasible_energy: bool


def evaluate_uav_route(route: UAVRoute, data: ProblemData) -> RouteMetrics:
    flight_time = 0.0
    flight_energy = 0.0
    for source, target in zip(route.node_sequence, route.node_sequence[1:]):
        flight_time += data.flight_time_s[(source, target)]
        flight_energy += data.flight_energy_j[(source, target)]
    hover_time = sum(route.hover_times_s.values())
    hover_energy = hover_time * data.params.hover_power_j_per_s
    total_energy = flight_energy + hover_energy
    return RouteMetrics(
        duration_s=flight_time + hover_time,
        energy_j=total_energy,
        feasible_energy=total_energy <= data.params.effective_energy_limit_j,
    )


def summarize_uav_solution(
    routes: tuple[UAVRoute, ...],
    data: ProblemData,
    battery_swap_time_s: float,
) -> UAVSolutionSummary:
    by_uav: dict[int, list[UAVRoute]] = {}
    total_energy = 0.0
    feasible_energy = True
    for route in routes:
        by_uav.setdefault(route.uav_id, []).append(route)
        metrics = evaluate_uav_route(route, data)
        total_energy += metrics.energy_j
        feasible_energy = feasible_energy and metrics.feasible_energy

    work_times: dict[int, float] = {}
    for uav_id, assigned_routes in by_uav.items():
        assigned_routes = sorted(assigned_routes, key=lambda item: item.sortie_id)
        route_time = sum(evaluate_uav_route(route, data).duration_s for route in assigned_routes)
        swap_time = max(0, len(assigned_routes) - 1) * battery_swap_time_s
        work_times[uav_id] = route_time + swap_time

    phase_time = max(work_times.values()) if work_times else 0.0
    load_std = pstdev(work_times.values()) if len(work_times) > 1 else 0.0
    return UAVSolutionSummary(
        uav_phase_time_s=phase_time,
        total_energy_j=total_energy,
        uav_work_times_s=work_times,
        load_std_s=load_std,
        feasible_energy=feasible_energy,
    )
```

- [ ] **Step 4: Run metric tests**

Run:

```bash
python3 -m pytest tests/test_model.py -q
```

Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add c_uav_inspection/model.py tests/test_model.py
git commit -m "feat: calculate uav route metrics"
```

---

### Task 5: Build Shared Route Construction Utilities

**Files:**
- Create: `c_uav_inspection/search.py`
- Test: `tests/test_search.py`

- [ ] **Step 1: Write search utility tests**

Create `tests/test_search.py`:

```python
from pathlib import Path

from c_uav_inspection.data import load_problem_data
from c_uav_inspection.search import nearest_neighbor_order, split_order_into_energy_feasible_routes


DATA_PATH = Path("2026同济数学建模竞赛赛题/2026C数据.xlsx")


def test_nearest_neighbor_order_visits_each_target_once():
    data = load_problem_data(DATA_PATH)
    order = nearest_neighbor_order(data, [target.node_id for target in data.targets])

    assert sorted(order) == list(range(1, 17))
    assert len(order) == 16


def test_split_order_into_energy_feasible_routes_satisfies_base_hover():
    data = load_problem_data(DATA_PATH)
    order = nearest_neighbor_order(data, [target.node_id for target in data.targets])
    hover = {target.node_id: target.base_hover_time_s for target in data.targets}

    routes = split_order_into_energy_feasible_routes(order, hover, data)

    assert len(routes) >= 2
    assert all(route.node_sequence[0] == 0 and route.node_sequence[-1] == 0 for route in routes)
    assert all(sum(route.hover_times_s.values()) > 0 for route in routes)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m pytest tests/test_search.py -q
```

Expected: import failure for `c_uav_inspection.search`.

- [ ] **Step 3: Implement deterministic construction helpers**

Create `c_uav_inspection/search.py`:

```python
from __future__ import annotations

from c_uav_inspection.data import ProblemData
from c_uav_inspection.model import UAVRoute, evaluate_uav_route


def nearest_neighbor_order(data: ProblemData, node_ids: list[int]) -> tuple[int, ...]:
    remaining = set(node_ids)
    current = 0
    order: list[int] = []
    while remaining:
        next_node = min(remaining, key=lambda node_id: (data.flight_time_s[(current, node_id)], node_id))
        order.append(next_node)
        remaining.remove(next_node)
        current = next_node
    return tuple(order)


def _candidate_route(sortie_id: int, nodes: list[int], hover_times_s: dict[int, float]) -> UAVRoute:
    return UAVRoute(
        uav_id=1,
        sortie_id=sortie_id,
        node_sequence=tuple([0, *nodes, 0]),
        hover_times_s={node_id: hover_times_s[node_id] for node_id in nodes},
    )


def split_order_into_energy_feasible_routes(
    order: tuple[int, ...],
    hover_times_s: dict[int, float],
    data: ProblemData,
) -> tuple[UAVRoute, ...]:
    routes: list[UAVRoute] = []
    current_nodes: list[int] = []
    sortie_id = 1
    for node_id in order:
        candidate_nodes = [*current_nodes, node_id]
        candidate = _candidate_route(sortie_id, candidate_nodes, hover_times_s)
        if current_nodes and not evaluate_uav_route(candidate, data).feasible_energy:
            routes.append(_candidate_route(sortie_id, current_nodes, hover_times_s))
            sortie_id += 1
            current_nodes = [node_id]
        else:
            current_nodes = candidate_nodes
    if current_nodes:
        routes.append(_candidate_route(sortie_id, current_nodes, hover_times_s))
    return tuple(routes)
```

- [ ] **Step 4: Run search tests**

Run:

```bash
python3 -m pytest tests/test_search.py -q
```

Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add c_uav_inspection/search.py tests/test_search.py
git commit -m "feat: construct energy-feasible uav sorties"
```

---

### Task 6: Implement Problem 1 Baseline Solver

**Files:**
- Create: `c_uav_inspection/problem1.py`
- Test: `tests/test_problem1.py`

- [ ] **Step 1: Write Problem 1 feasibility tests**

Create `tests/test_problem1.py`:

```python
from pathlib import Path

from c_uav_inspection.data import load_problem_data
from c_uav_inspection.problem1 import solve_problem1_for_k


DATA_PATH = Path("2026同济数学建模竞赛赛题/2026C数据.xlsx")


def test_problem1_solution_satisfies_base_hover_and_energy_for_k2():
    data = load_problem_data(DATA_PATH)
    solution = solve_problem1_for_k(data, k=2, battery_swap_time_s=300)

    assert solution.summary.feasible_energy is True
    assert solution.summary.uav_phase_time_s <= data.params.operating_horizon_s
    for target in data.targets:
        assert solution.total_hover_by_node[target.node_id] >= target.base_hover_time_s


def test_problem1_solution_uses_only_requested_uav_count():
    data = load_problem_data(DATA_PATH)
    solution = solve_problem1_for_k(data, k=3, battery_swap_time_s=300)

    assert max(route.uav_id for route in solution.routes) <= 3
    assert min(route.uav_id for route in solution.routes) >= 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m pytest tests/test_problem1.py -q
```

Expected: import failure for `c_uav_inspection.problem1`.

- [ ] **Step 3: Implement Problem 1 constructive solver**

Create `c_uav_inspection/problem1.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from c_uav_inspection.data import ProblemData
from c_uav_inspection.model import UAVRoute, UAVSolutionSummary, summarize_uav_solution
from c_uav_inspection.search import nearest_neighbor_order, split_order_into_energy_feasible_routes


@dataclass(frozen=True)
class Problem1Solution:
    routes: tuple[UAVRoute, ...]
    total_hover_by_node: dict[int, float]
    summary: UAVSolutionSummary


def _assign_routes_to_uavs(routes: tuple[UAVRoute, ...], k: int, data: ProblemData, battery_swap_time_s: float) -> tuple[UAVRoute, ...]:
    work_times = {uav_id: 0.0 for uav_id in range(1, k + 1)}
    sortie_counts = {uav_id: 0 for uav_id in range(1, k + 1)}
    assigned: list[UAVRoute] = []
    for route in sorted(routes, key=lambda item: sum(item.hover_times_s.values()), reverse=True):
        uav_id = min(work_times, key=lambda key: (work_times[key], key))
        sortie_counts[uav_id] += 1
        updated = UAVRoute(
            uav_id=uav_id,
            sortie_id=sortie_counts[uav_id],
            node_sequence=route.node_sequence,
            hover_times_s=route.hover_times_s,
        )
        assigned.append(updated)
        route_time = summarize_uav_solution((updated,), data, battery_swap_time_s=0).uav_phase_time_s
        if sortie_counts[uav_id] > 1:
            route_time += battery_swap_time_s
        work_times[uav_id] += route_time
    return tuple(sorted(assigned, key=lambda item: (item.uav_id, item.sortie_id)))


def solve_problem1_for_k(data: ProblemData, k: int, battery_swap_time_s: float) -> Problem1Solution:
    if k < 1 or k > data.params.k_max:
        raise ValueError(f"k must be between 1 and {data.params.k_max}, got {k}")
    hover = {target.node_id: target.base_hover_time_s for target in data.targets}
    order = nearest_neighbor_order(data, list(hover))
    raw_routes = split_order_into_energy_feasible_routes(order, hover, data)
    routes = _assign_routes_to_uavs(raw_routes, k, data, battery_swap_time_s)
    total_hover = {node_id: 0.0 for node_id in hover}
    for route in routes:
        for node_id, seconds in route.hover_times_s.items():
            total_hover[node_id] += seconds
    return Problem1Solution(
        routes=routes,
        total_hover_by_node=total_hover,
        summary=summarize_uav_solution(routes, data, battery_swap_time_s),
    )
```

- [ ] **Step 4: Run Problem 1 tests**

Run:

```bash
python3 -m pytest tests/test_problem1.py -q
```

Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add c_uav_inspection/problem1.py tests/test_problem1.py
git commit -m "feat: solve basic multi-uav patrol problem"
```

---

### Task 7: Add Local Search Improvements for Problem 1

**Files:**
- Modify: `c_uav_inspection/search.py`
- Modify: `c_uav_inspection/problem1.py`
- Modify: `tests/test_problem1.py`

- [ ] **Step 1: Add non-regression test for local search**

Append to `tests/test_problem1.py`:

```python
from c_uav_inspection.problem1 import solve_problem1_for_k


def test_problem1_local_search_keeps_solution_feasible():
    data = load_problem_data(DATA_PATH)
    solution = solve_problem1_for_k(data, k=4, battery_swap_time_s=300, improve=True)

    assert solution.summary.feasible_energy is True
    assert solution.summary.uav_phase_time_s <= data.params.operating_horizon_s
    assert len(solution.routes) >= 1
```

- [ ] **Step 2: Run the new test to verify it fails**

Run:

```bash
python3 -m pytest tests/test_problem1.py::test_problem1_local_search_keeps_solution_feasible -q
```

Expected: `TypeError` because `solve_problem1_for_k` has no `improve` argument.

- [ ] **Step 3: Add a deterministic 2-opt operator**

Append to `c_uav_inspection/search.py`:

```python
from c_uav_inspection.model import evaluate_uav_route


def improve_route_by_two_opt(route: UAVRoute, data: ProblemData) -> UAVRoute:
    nodes = list(route.node_sequence[1:-1])
    if len(nodes) < 4:
        return route
    best = route
    best_metrics = evaluate_uav_route(route, data)
    improved = True
    while improved:
        improved = False
        for left in range(len(nodes) - 1):
            for right in range(left + 2, len(nodes) + 1):
                candidate_nodes = nodes[:left] + list(reversed(nodes[left:right])) + nodes[right:]
                candidate = UAVRoute(
                    uav_id=route.uav_id,
                    sortie_id=route.sortie_id,
                    node_sequence=tuple([0, *candidate_nodes, 0]),
                    hover_times_s=route.hover_times_s,
                )
                metrics = evaluate_uav_route(candidate, data)
                if metrics.feasible_energy and metrics.duration_s < best_metrics.duration_s:
                    nodes = candidate_nodes
                    best = candidate
                    best_metrics = metrics
                    improved = True
                    break
            if improved:
                break
    return best
```

- [ ] **Step 4: Wire local search into Problem 1**

Modify the imports and function in `c_uav_inspection/problem1.py`:

```python
from c_uav_inspection.search import improve_route_by_two_opt, nearest_neighbor_order, split_order_into_energy_feasible_routes
```

Replace the function signature and route construction block:

```python
def solve_problem1_for_k(
    data: ProblemData,
    k: int,
    battery_swap_time_s: float,
    improve: bool = False,
) -> Problem1Solution:
    if k < 1 or k > data.params.k_max:
        raise ValueError(f"k must be between 1 and {data.params.k_max}, got {k}")
    hover = {target.node_id: target.base_hover_time_s for target in data.targets}
    order = nearest_neighbor_order(data, list(hover))
    raw_routes = split_order_into_energy_feasible_routes(order, hover, data)
    if improve:
        raw_routes = tuple(improve_route_by_two_opt(route, data) for route in raw_routes)
    routes = _assign_routes_to_uavs(raw_routes, k, data, battery_swap_time_s)
    total_hover = {node_id: 0.0 for node_id in hover}
    for route in routes:
        for node_id, seconds in route.hover_times_s.items():
            total_hover[node_id] += seconds
    return Problem1Solution(
        routes=routes,
        total_hover_by_node=total_hover,
        summary=summarize_uav_solution(routes, data, battery_swap_time_s),
    )
```

- [ ] **Step 5: Run Problem 1 tests**

Run:

```bash
python3 -m pytest tests/test_problem1.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add c_uav_inspection/search.py c_uav_inspection/problem1.py tests/test_problem1.py
git commit -m "feat: improve uav routes with local search"
```

---

### Task 8: Implement Ground TSP and Problem 2 Closed-Loop Metrics

**Files:**
- Create: `c_uav_inspection/problem2.py`
- Test: `tests/test_problem2.py`

- [ ] **Step 1: Write ground TSP and closed-loop tests**

Create `tests/test_problem2.py`:

```python
from pathlib import Path

from c_uav_inspection.data import load_problem_data
from c_uav_inspection.problem1 import solve_problem1_for_k
from c_uav_inspection.problem2 import solve_ground_tsp, evaluate_closed_loop


DATA_PATH = Path("2026同济数学建模竞赛赛题/2026C数据.xlsx")


def test_ground_tsp_all_manual_starts_and_ends_at_p0():
    data = load_problem_data(DATA_PATH)
    manual_points = tuple(target.manual_point_id for target in data.targets)

    result = solve_ground_tsp(data, manual_points)

    assert result.path[0] == "P0"
    assert result.path[-1] == "P0"
    assert sorted(result.path[1:-1]) == sorted(manual_points)
    assert result.total_time_s > 2670


def test_closed_loop_marks_all_base_only_targets_manual():
    data = load_problem_data(DATA_PATH)
    p1 = solve_problem1_for_k(data, k=2, battery_swap_time_s=300)

    closed = evaluate_closed_loop(data, p1.routes, direct_threshold_multiplier=1.0)

    assert closed.uav_phase_time_s == p1.summary.uav_phase_time_s
    assert closed.manual_count >= 1
    assert closed.closed_loop_time_s == closed.uav_phase_time_s + closed.ground_review_time_s
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m pytest tests/test_problem2.py -q
```

Expected: import failure for `c_uav_inspection.problem2`.

- [ ] **Step 3: Implement ground TSP and closed-loop evaluation**

Create `c_uav_inspection/problem2.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from c_uav_inspection.data import ProblemData
from c_uav_inspection.model import UAVRoute, summarize_uav_solution


@dataclass(frozen=True)
class GroundReviewResult:
    path: tuple[str, ...]
    travel_time_s: float
    service_time_s: float
    total_time_s: float


@dataclass(frozen=True)
class ClosedLoopResult:
    direct_confirmed_nodes: tuple[int, ...]
    manual_nodes: tuple[int, ...]
    manual_count: int
    uav_phase_time_s: float
    ground_review_time_s: float
    closed_loop_time_s: float
    ground_path: tuple[str, ...]


def solve_ground_tsp(data: ProblemData, manual_point_ids: tuple[str, ...]) -> GroundReviewResult:
    points = tuple(sorted(set(manual_point_ids)))
    if not points:
        return GroundReviewResult(path=("P0", "P0"), travel_time_s=0.0, service_time_s=0.0, total_time_s=0.0)

    service_by_point = {target.manual_point_id: target.manual_service_time_s for target in data.targets}

    @lru_cache(maxsize=None)
    def best_path(current: str, remaining: tuple[str, ...]) -> tuple[float, tuple[str, ...]]:
        if not remaining:
            return data.ground_time_s[(current, "P0")], ("P0",)
        best_time = float("inf")
        best_suffix: tuple[str, ...] = ()
        for point in remaining:
            next_remaining = tuple(item for item in remaining if item != point)
            suffix_time, suffix_path = best_path(point, next_remaining)
            candidate_time = data.ground_time_s[(current, point)] + suffix_time
            if candidate_time < best_time:
                best_time = candidate_time
                best_suffix = (point, *suffix_path)
        return best_time, best_suffix

    travel_time, suffix = best_path("P0", points)
    service_time = sum(service_by_point[point] for point in points)
    return GroundReviewResult(
        path=("P0", *suffix),
        travel_time_s=travel_time,
        service_time_s=service_time,
        total_time_s=travel_time + service_time,
    )


def _hover_by_node(routes: tuple[UAVRoute, ...]) -> dict[int, float]:
    hover: dict[int, float] = {}
    for route in routes:
        for node_id, seconds in route.hover_times_s.items():
            hover[node_id] = hover.get(node_id, 0.0) + seconds
    return hover


def evaluate_closed_loop(
    data: ProblemData,
    routes: tuple[UAVRoute, ...],
    direct_threshold_multiplier: float,
) -> ClosedLoopResult:
    hover = _hover_by_node(routes)
    direct_nodes: list[int] = []
    manual_nodes: list[int] = []
    manual_points: list[str] = []
    for target in data.targets:
        threshold = target.direct_confirm_time_s * direct_threshold_multiplier
        if hover.get(target.node_id, 0.0) >= threshold:
            direct_nodes.append(target.node_id)
        else:
            manual_nodes.append(target.node_id)
            manual_points.append(target.manual_point_id)
    ground = solve_ground_tsp(data, tuple(manual_points))
    summary = summarize_uav_solution(routes, data, data.params.battery_swap_time_s)
    return ClosedLoopResult(
        direct_confirmed_nodes=tuple(sorted(direct_nodes)),
        manual_nodes=tuple(sorted(manual_nodes)),
        manual_count=len(manual_nodes),
        uav_phase_time_s=summary.uav_phase_time_s,
        ground_review_time_s=ground.total_time_s,
        closed_loop_time_s=summary.uav_phase_time_s + ground.total_time_s,
        ground_path=ground.path,
    )
```

- [ ] **Step 4: Run Problem 2 tests**

Run:

```bash
python3 -m pytest tests/test_problem2.py -q
```

Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add c_uav_inspection/problem2.py tests/test_problem2.py
git commit -m "feat: evaluate closed-loop property review"
```

---

### Task 9: Add Direct-Confirm Tradeoff Solver

**Files:**
- Modify: `c_uav_inspection/problem2.py`
- Modify: `tests/test_problem2.py`

- [ ] **Step 1: Write direct-confirm solver tests**

Append to `tests/test_problem2.py`:

```python
from c_uav_inspection.problem2 import solve_joint_problem_for_k


def test_joint_solver_reduces_or_matches_manual_count_against_base_only():
    data = load_problem_data(DATA_PATH)
    base = evaluate_closed_loop(data, solve_problem1_for_k(data, k=3, battery_swap_time_s=300).routes, 1.0)
    joint = solve_joint_problem_for_k(data, k=3, direct_threshold_multiplier=1.0)

    assert joint.closed_loop.manual_count <= base.manual_count
    assert joint.closed_loop.closed_loop_time_s > 0
    assert all(route.node_sequence[0] == 0 and route.node_sequence[-1] == 0 for route in joint.routes)
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
python3 -m pytest tests/test_problem2.py::test_joint_solver_reduces_or_matches_manual_count_against_base_only -q
```

Expected: import failure for `solve_joint_problem_for_k`.

- [ ] **Step 3: Implement marginal-benefit direct-confirm selection**

Append to `c_uav_inspection/problem2.py`:

```python
from c_uav_inspection.model import evaluate_uav_route
from c_uav_inspection.problem1 import solve_problem1_for_k


@dataclass(frozen=True)
class JointSolution:
    routes: tuple[UAVRoute, ...]
    closed_loop: ClosedLoopResult


def _direct_confirm_score(data: ProblemData, target_id: int) -> float:
    target = next(item for item in data.targets if item.node_id == target_id)
    extra_hover = max(0.0, target.direct_confirm_time_s - target.base_hover_time_s)
    manual_proxy = (
        data.ground_time_s[("P0", target.manual_point_id)]
        + data.ground_time_s[(target.manual_point_id, "P0")]
        + target.manual_service_time_s
    )
    energy_ratio = (
        data.flight_energy_j[(0, target.node_id)]
        + data.flight_energy_j[(target.node_id, 0)]
        + target.direct_confirm_time_s * data.params.hover_power_j_per_s
    ) / data.params.effective_energy_limit_j
    return target.priority_weight * manual_proxy / (extra_hover + 1.0) - energy_ratio


def _upgrade_singleton_route_to_direct_confirm(data: ProblemData, target_id: int, uav_id: int, sortie_id: int) -> UAVRoute:
    target = next(item for item in data.targets if item.node_id == target_id)
    return UAVRoute(
        uav_id=uav_id,
        sortie_id=sortie_id,
        node_sequence=(0, target_id, 0),
        hover_times_s={target_id: target.direct_confirm_time_s},
    )


def solve_joint_problem_for_k(
    data: ProblemData,
    k: int,
    direct_threshold_multiplier: float,
) -> JointSolution:
    base = solve_problem1_for_k(data, k=k, battery_swap_time_s=data.params.battery_swap_time_s, improve=True)
    routes = list(base.routes)
    next_sortie_by_uav = {uav_id: 0 for uav_id in range(1, k + 1)}
    for route in routes:
        next_sortie_by_uav[route.uav_id] = max(next_sortie_by_uav[route.uav_id], route.sortie_id)

    ranked_targets = sorted(
        (target.node_id for target in data.targets),
        key=lambda node_id: (_direct_confirm_score(data, node_id), -node_id),
        reverse=True,
    )
    best_closed = evaluate_closed_loop(data, tuple(routes), direct_threshold_multiplier)
    for target_id in ranked_targets:
        uav_id = min(next_sortie_by_uav, key=lambda key: (next_sortie_by_uav[key], key))
        next_sortie_by_uav[uav_id] += 1
        candidate_route = _upgrade_singleton_route_to_direct_confirm(data, target_id, uav_id, next_sortie_by_uav[uav_id])
        if not evaluate_uav_route(candidate_route, data).feasible_energy:
            continue
        candidate_routes = tuple([*routes, candidate_route])
        candidate_closed = evaluate_closed_loop(data, candidate_routes, direct_threshold_multiplier)
        if (
            candidate_closed.uav_phase_time_s <= data.params.operating_horizon_s
            and candidate_closed.closed_loop_time_s <= best_closed.closed_loop_time_s
        ):
            routes.append(candidate_route)
            best_closed = candidate_closed
    return JointSolution(routes=tuple(routes), closed_loop=best_closed)
```

- [ ] **Step 4: Run Problem 2 tests**

Run:

```bash
python3 -m pytest tests/test_problem2.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add c_uav_inspection/problem2.py tests/test_problem2.py
git commit -m "feat: solve joint uav property inspection tradeoff"
```

---

### Task 10: Implement Experiment Runner

**Files:**
- Create: `c_uav_inspection/experiments.py`
- Test: `tests/test_experiments.py`

- [ ] **Step 1: Write experiment output tests**

Create `tests/test_experiments.py`:

```python
from pathlib import Path

from c_uav_inspection.experiments import run_all_experiments


DATA_PATH = Path("2026同济数学建模竞赛赛题/2026C数据.xlsx")


def test_run_all_experiments_writes_expected_files(tmp_path):
    run_all_experiments(DATA_PATH, tmp_path)

    assert (tmp_path / "problem1_k_comparison.csv").exists()
    assert (tmp_path / "problem1_swap_sensitivity.csv").exists()
    assert (tmp_path / "problem2_k_comparison.csv").exists()
    assert (tmp_path / "problem2_threshold_sensitivity.csv").exists()
    assert (tmp_path / "recommended_solution.json").exists()
```

- [ ] **Step 2: Run experiment test to verify it fails**

Run:

```bash
python3 -m pytest tests/test_experiments.py -q
```

Expected: import failure for `c_uav_inspection.experiments`.

- [ ] **Step 3: Implement CSV/JSON experiment writer**

Create `c_uav_inspection/experiments.py`:

```python
from __future__ import annotations

import csv
import json
from pathlib import Path

from c_uav_inspection.data import load_problem_data, validate_problem_data
from c_uav_inspection.problem1 import solve_problem1_for_k
from c_uav_inspection.problem2 import solve_joint_problem_for_k


def _write_csv(path: Path, rows: list[dict[str, float | int | str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else ["empty"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_all_experiments(data_path: Path | str, output_dir: Path | str) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    data = load_problem_data(data_path)

    validation = validate_problem_data(data)
    (output / "data_validation.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    k_rows = []
    for k in range(1, data.params.k_max + 1):
        solution = solve_problem1_for_k(data, k=k, battery_swap_time_s=data.params.battery_swap_time_s, improve=True)
        k_rows.append({
            "k": k,
            "uav_phase_time_s": round(solution.summary.uav_phase_time_s, 2),
            "total_energy_j": round(solution.summary.total_energy_j, 2),
            "load_std_s": round(solution.summary.load_std_s, 2),
            "route_count": len(solution.routes),
        })
    _write_csv(output / "problem1_k_comparison.csv", k_rows)

    swap_rows = []
    for tau in (0, 150, 300, 450, 600):
        solution = solve_problem1_for_k(data, k=3, battery_swap_time_s=tau, improve=True)
        swap_rows.append({
            "battery_swap_time_s": tau,
            "uav_phase_time_s": round(solution.summary.uav_phase_time_s, 2),
            "total_energy_j": round(solution.summary.total_energy_j, 2),
            "load_std_s": round(solution.summary.load_std_s, 2),
        })
    _write_csv(output / "problem1_swap_sensitivity.csv", swap_rows)

    joint_k_rows = []
    best_joint = None
    for k in range(1, data.params.k_max + 1):
        joint = solve_joint_problem_for_k(data, k=k, direct_threshold_multiplier=1.0)
        if best_joint is None or joint.closed_loop.closed_loop_time_s < best_joint.closed_loop.closed_loop_time_s:
            best_joint = joint
        joint_k_rows.append({
            "k": k,
            "closed_loop_time_s": round(joint.closed_loop.closed_loop_time_s, 2),
            "uav_phase_time_s": round(joint.closed_loop.uav_phase_time_s, 2),
            "ground_review_time_s": round(joint.closed_loop.ground_review_time_s, 2),
            "manual_count": joint.closed_loop.manual_count,
            "direct_confirm_count": len(joint.closed_loop.direct_confirmed_nodes),
        })
    _write_csv(output / "problem2_k_comparison.csv", joint_k_rows)

    threshold_rows = []
    for multiplier in (0.70, 0.85, 1.00, 1.15, 1.30):
        joint = solve_joint_problem_for_k(data, k=3, direct_threshold_multiplier=multiplier)
        threshold_rows.append({
            "direct_threshold_multiplier": multiplier,
            "closed_loop_time_s": round(joint.closed_loop.closed_loop_time_s, 2),
            "manual_count": joint.closed_loop.manual_count,
            "direct_confirm_count": len(joint.closed_loop.direct_confirmed_nodes),
        })
    _write_csv(output / "problem2_threshold_sensitivity.csv", threshold_rows)

    assert best_joint is not None
    schedule = {
        "closed_loop_time_s": best_joint.closed_loop.closed_loop_time_s,
        "manual_nodes": best_joint.closed_loop.manual_nodes,
        "direct_confirmed_nodes": best_joint.closed_loop.direct_confirmed_nodes,
        "ground_path": best_joint.closed_loop.ground_path,
        "routes": [
            {
                "uav_id": route.uav_id,
                "sortie_id": route.sortie_id,
                "node_sequence": route.node_sequence,
                "hover_times_s": dict(route.hover_times_s),
            }
            for route in best_joint.routes
        ],
    }
    (output / "recommended_solution.json").write_text(
        json.dumps(schedule, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
```

- [ ] **Step 4: Run experiment tests**

Run:

```bash
python3 -m pytest tests/test_experiments.py -q
```

Expected: `1 passed`.

- [ ] **Step 5: Run all tests**

Run:

```bash
python3 -m pytest tests -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add c_uav_inspection/experiments.py tests/test_experiments.py
git commit -m "feat: export c problem experiments"
```

---

### Task 11: Generate Official Experiment Results

**Files:**
- Modify generated outputs under: `outputs/c_uav_inspection/`

- [ ] **Step 1: Run the experiment command**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
from c_uav_inspection.experiments import run_all_experiments

run_all_experiments(
    Path("2026同济数学建模竞赛赛题/2026C数据.xlsx"),
    Path("outputs/c_uav_inspection"),
)
print("done")
PY
```

Expected: stdout contains `done`.

- [ ] **Step 2: Inspect generated result files**

Run:

```bash
find outputs/c_uav_inspection -maxdepth 1 -type f | sort
```

Expected file list includes:

```text
outputs/c_uav_inspection/data_validation.json
outputs/c_uav_inspection/problem1_k_comparison.csv
outputs/c_uav_inspection/problem1_swap_sensitivity.csv
outputs/c_uav_inspection/problem2_k_comparison.csv
outputs/c_uav_inspection/problem2_threshold_sensitivity.csv
outputs/c_uav_inspection/recommended_solution.json
```

- [ ] **Step 3: Check result tables are non-empty**

Run:

```bash
python3 - <<'PY'
from pathlib import Path

for path in sorted(Path("outputs/c_uav_inspection").glob("*.csv")):
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    print(path.name, len(lines))
    assert len(lines) >= 2
PY
```

Expected: each CSV prints a line count of at least 2.

- [ ] **Step 4: Commit generated tabular results**

```bash
git add outputs/c_uav_inspection/*.csv outputs/c_uav_inspection/*.json
git commit -m "data: generate c problem experiment results"
```

---

### Task 12: Create Visualization Generator

**Files:**
- Create: `c_uav_inspection/plots.py`
- Test: `tests/test_plots.py`

- [ ] **Step 1: Write figure generation smoke test**

Create `tests/test_plots.py`:

```python
from pathlib import Path

from c_uav_inspection.experiments import run_all_experiments
from c_uav_inspection.plots import generate_all_figures


DATA_PATH = Path("2026同济数学建模竞赛赛题/2026C数据.xlsx")


def test_generate_all_figures_creates_png_files(tmp_path):
    run_all_experiments(DATA_PATH, tmp_path)
    generate_all_figures(DATA_PATH, tmp_path)

    assert (tmp_path / "problem1_k_comparison.png").exists()
    assert (tmp_path / "problem2_threshold_sensitivity.png").exists()
    assert (tmp_path / "recommended_routes.png").exists()
```

- [ ] **Step 2: Run figure test to verify it fails**

Run:

```bash
python3 -m pytest tests/test_plots.py -q
```

Expected: import failure for `c_uav_inspection.plots`.

- [ ] **Step 3: Implement plotting functions**

Create `c_uav_inspection/plots.py`:

```python
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt

from c_uav_inspection.data import load_problem_data


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _save_line_chart(path: Path, x_values: list[float], y_values: list[float], title: str, xlabel: str, ylabel: str) -> None:
    plt.figure(figsize=(7, 4))
    plt.plot(x_values, y_values, marker="o", linewidth=2)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()


def _save_route_map(data_path: Path | str, result_dir: Path) -> None:
    data = load_problem_data(data_path)
    schedule = json.loads((result_dir / "recommended_solution.json").read_text(encoding="utf-8"))
    by_id = {target.node_id: target for target in data.targets}
    plt.figure(figsize=(7, 6))
    plt.scatter([0], [0], c="black", marker="s", label="Depot/P0")
    plt.scatter([target.x_m for target in data.targets], [target.y_m for target in data.targets], c="tab:blue", label="Targets")
    for target in data.targets:
        plt.text(target.x_m + 3, target.y_m + 3, str(target.node_id), fontsize=8)
    colors = ["tab:red", "tab:green", "tab:orange", "tab:purple"]
    for index, route in enumerate(schedule["routes"]):
        nodes = route["node_sequence"]
        xs = [0 if node == 0 else by_id[int(node)].x_m for node in nodes]
        ys = [0 if node == 0 else by_id[int(node)].y_m for node in nodes]
        plt.plot(xs, ys, color=colors[index % len(colors)], alpha=0.55, linewidth=1)
    plt.title("Recommended UAV Routes")
    plt.xlabel("x_m")
    plt.ylabel("y_m")
    plt.legend()
    plt.axis("equal")
    plt.tight_layout()
    plt.savefig(result_dir / "recommended_routes.png", dpi=200)
    plt.close()


def generate_all_figures(data_path: Path | str, result_dir: Path | str) -> None:
    result_path = Path(result_dir)
    k_rows = _read_csv(result_path / "problem1_k_comparison.csv")
    _save_line_chart(
        result_path / "problem1_k_comparison.png",
        [float(row["k"]) for row in k_rows],
        [float(row["uav_phase_time_s"]) for row in k_rows],
        "Problem 1 UAV Count Comparison",
        "K",
        "UAV phase time (s)",
    )

    threshold_rows = _read_csv(result_path / "problem2_threshold_sensitivity.csv")
    _save_line_chart(
        result_path / "problem2_threshold_sensitivity.png",
        [float(row["direct_threshold_multiplier"]) for row in threshold_rows],
        [float(row["manual_count"]) for row in threshold_rows],
        "Direct-Confirm Threshold Sensitivity",
        "Threshold multiplier",
        "Manual review count",
    )

    _save_route_map(data_path, result_path)
```

- [ ] **Step 4: Run plot tests**

Run:

```bash
python3 -m pytest tests/test_plots.py -q
```

Expected: `1 passed`.

- [ ] **Step 5: Generate official figures**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
from c_uav_inspection.plots import generate_all_figures

generate_all_figures(
    Path("2026同济数学建模竞赛赛题/2026C数据.xlsx"),
    Path("outputs/c_uav_inspection"),
)
print("figures done")
PY
```

Expected: stdout contains `figures done`.

- [ ] **Step 6: Commit plotting code and figures**

```bash
git add c_uav_inspection/plots.py tests/test_plots.py outputs/c_uav_inspection/*.png
git commit -m "feat: generate c problem figures"
```

---

### Task 13: Write Paper-Ready Results Note

**Files:**
- Create: `report/c_uav_inspection_results.md`

- [ ] **Step 1: Create the report directory**

Run:

```bash
mkdir -p report
```

Expected: command exits successfully.

- [ ] **Step 2: Draft the results note**

Create `report/c_uav_inspection_results.md` with this structure:

```markdown
# C题：面向智慧社区的多无人机-物业人员联合巡检优化结果说明

## 1. 数据与约束核验

本文使用附件 `2026C数据.xlsx`。目标点数量为 16，候选无人机数量为 1 到 4 架，单趟有效能耗上限为 135000 J，换电时间基准值为 300 s，无人机阶段运营时长上限为 2600 s。基础悬停总时间为 790 s，若全部由无人机直接确认则累计悬停时间为 5210 s，说明问题 2 中存在明显的无人机悬停与物业复核替代关系。

## 2. 问题1模型说明

问题 1 建立多无人机、多趟次、带单趟能耗约束的路径与悬停时间联合优化模型。决策变量包括无人机任务分配、每趟访问顺序、各目标点累计悬停时间和各无人机完成时间。目标函数综合系统完成时间、高优先级点提前完成、总能耗和负载均衡。

核心约束为：

```text
每个目标点累计悬停时间 >= base_hover_time_s
每趟任务飞行能耗 + 悬停能耗 <= effective_energy_limit_J
每趟任务从节点 0 出发并回到节点 0
无人机多趟任务之间计入 battery_swap_time_s
无人机阶段完成时间 <= operating_horizon_s
```

## 3. 问题2模型说明

问题 2 在问题 1 的基础上引入直接确认变量。若目标点累计悬停时间达到 `direct_confirm_time_s`，则该点由无人机直接确认；否则进入物业复核集合。物业人员从 P0 出发，访问全部待复核点后返回 P0，形成地面 TSP 子问题。闭环总完成时间定义为无人机阶段完成时间与物业复核阶段完成时间之和。

## 4. 算法说明

算法采用“可行路径构造 + 局部搜索 + 物业 TSP 精确动态规划”的组合。首先按飞行时间最近邻生成基础巡检顺序，并按单趟能耗上限切分为可行出航任务；随后使用 2-opt 改善单趟访问顺序；最后通过边际替代收益判断哪些目标点值得增加无人机悬停以减少物业复核。全流程不引入 ML 或 DL。

## 5. 输出文件

- `outputs/c_uav_inspection/problem1_k_comparison.csv`：不同无人机数量下的问题 1 对比。
- `outputs/c_uav_inspection/problem1_swap_sensitivity.csv`：换电时间敏感性结果。
- `outputs/c_uav_inspection/problem2_k_comparison.csv`：不同无人机数量下的问题 2 闭环结果。
- `outputs/c_uav_inspection/problem2_threshold_sensitivity.csv`：直接确认阈值敏感性结果。
- `outputs/c_uav_inspection/recommended_solution.json`：推荐巡检方案。
- `outputs/c_uav_inspection/*.png`：论文图表。

## 6. 论文写作建议

论文主线应强调：问题 1 解决最短基础空中覆盖，问题 2 解决无人机直接确认与物业复核的替代权衡，最终通过边际收益递减与敏感性分析给出无人机配置建议。创新点集中在连续悬停时间分配、空地替代收益、闭环 Pareto 权衡和配置规模边际收益分析。
```

- [ ] **Step 3: Verify report references generated files**

Run:

```bash
python3 - <<'PY'
from pathlib import Path

text = Path("report/c_uav_inspection_results.md").read_text(encoding="utf-8")
required = [
    "problem1_k_comparison.csv",
    "problem1_swap_sensitivity.csv",
    "problem2_k_comparison.csv",
    "problem2_threshold_sensitivity.csv",
    "recommended_solution.json",
]
for item in required:
    assert item in text
print("report references ok")
PY
```

Expected: stdout contains `report references ok`.

- [ ] **Step 4: Commit report note**

```bash
git add report/c_uav_inspection_results.md
git commit -m "docs: summarize c problem modeling results"
```

---

### Task 14: Final Verification and Paper Handoff

**Files:**
- Verify: all created code, tests, outputs, and report files.

- [ ] **Step 1: Run full test suite**

Run:

```bash
python3 -m pytest tests -q
```

Expected: all tests pass.

- [ ] **Step 2: Regenerate all outputs from scratch**

Run:

```bash
rm -rf outputs/c_uav_inspection
python3 - <<'PY'
from pathlib import Path
from c_uav_inspection.experiments import run_all_experiments
from c_uav_inspection.plots import generate_all_figures

data_path = Path("2026同济数学建模竞赛赛题/2026C数据.xlsx")
out = Path("outputs/c_uav_inspection")
run_all_experiments(data_path, out)
generate_all_figures(data_path, out)
print("rebuild ok")
PY
```

Expected: stdout contains `rebuild ok`.

- [ ] **Step 3: Check official output inventory**

Run:

```bash
python3 - <<'PY'
from pathlib import Path

expected = {
    "data_validation.json",
    "problem1_k_comparison.csv",
    "problem1_swap_sensitivity.csv",
    "problem2_k_comparison.csv",
    "problem2_threshold_sensitivity.csv",
    "recommended_solution.json",
    "problem1_k_comparison.png",
    "problem2_threshold_sensitivity.png",
    "recommended_routes.png",
}
actual = {path.name for path in Path("outputs/c_uav_inspection").iterdir() if path.is_file()}
missing = sorted(expected - actual)
assert not missing, missing
print("inventory ok")
PY
```

Expected: stdout contains `inventory ok`.

- [ ] **Step 4: Commit final regenerated outputs**

```bash
git add outputs/c_uav_inspection report/c_uav_inspection_results.md
git commit -m "chore: finalize c problem reproducible outputs"
```

- [ ] **Step 5: Prepare final handoff summary**

Write a short Chinese summary for the paper team containing:

```text
已完成 C 题可复现实验流程。
主模型：多无人机多趟能耗约束 VRP + 悬停时间分配 + 物业复核 TSP。
未引入 ML/DL。
核心输出：K 对比、换电敏感性、阈值敏感性、推荐巡检方案、路径图。
论文重点：连续悬停时间分配、空地替代收益、边际收益递减配置建议。
```

## Self-Review

- Spec coverage: The plan covers data loading, consistency checks, Problem 1, Problem 2, no-ML assumption, algorithm design, sensitivity experiments, figures, and report output.
- Placeholder scan: No placeholder markers, no unspecified implementation step, and no undefined final deliverable.
- Type consistency: `ProblemData`, `Target`, `UAVRoute`, `Problem1Solution`, `ClosedLoopResult`, and `JointSolution` are introduced before use and reused consistently.
- Scope check: This is one coherent research workflow, not multiple independent subsystems. The implementation can be completed task by task.
