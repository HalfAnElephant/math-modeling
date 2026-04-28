# C题 UAV Inspection Plan

## Goal
Establish reproducible experiment workflow for Problem C: multi-UAV aerial inspection + ground personnel review closed-loop.

## Tasks

### Task 001: Environment & Data Loading
- File: PLAN/01-环境与数据加载.md
- Create package c_uav_inspection, read Excel data, validate data consistency
- Tests: tests/test_package.py, tests/test_data.py
- Target: 5 tests passed

### Task 002: Core Model & Normalized Objective
- File: PLAN/02-核心模型与归一化目标.md
- Implement UAV route evaluation, solution summary, normalized multi-objective scoring
- Tests: tests/test_model.py, tests/test_objective.py
- Target: 5 tests passed (cumulative all tests)

### Task 003: Divisible Hover & Problem 1
- File: PLAN/03-可拆分悬停与问题1.md
- Nearest-neighbor ordering, divisible hover bin-packing, Problem 1 multi-UAV solver
- Tests: tests/test_search.py, tests/test_problem1.py
- Target: all tests passed

### Task 004: Problem 2 Closed-Loop & Rebuild Search
- File: PLAN/04-问题2闭环与重建搜索.md
- Ground TSP, direct confirm threshold, closed-loop evaluation, rebuild search
- Tests: tests/test_problem2.py
- Target: all tests passed

### Task 005: Experiments, Plots & Paper
- File: PLAN/05-实验图表与论文说明.md
- Generate CSV/JSON results, PNG charts, write paper results
- Tests: tests/test_experiments.py, tests/test_plots.py
- Target: all tests passed, all outputs exist

### Task 006: Final Verification
- File: PLAN/06-最终验收.md
- Rebuild from zero, check all outputs, verify constraints
- Target: all tests passed, inventory complete

## Core Constraints (must preserve)
1. Multi-objective normalized before weighted sum
2. Hover time is divisible across UAVs and sorties
3. Problem 2 uses rebuild search (not greedy single-point)
4. Direct confirm threshold = max(base_hover_time_s, direct_confirm_time_s * multiplier)
5. Ground personnel depart after ALL UAV tasks complete
6. Closed-loop time = T_u + T_g
