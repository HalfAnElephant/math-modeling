# Implement Review Results: Task-004

## Spec Review Issues

### SR-001: `_direct_confirm_score` omits extra-hover cost calculation
- **Status**: Resolved
- **Description**: The plan specifies `_direct_confirm_score` must use the effective threshold to calculate extra hover (使用有效阈值计算额外悬停) as one of its three scoring components. The implementation computes only ground savings (P0 round-trip to manual point + service time) and energy penalty (round-trip flight energy / sortie energy limit), returning `ground_savings / (1.0 + energy_penalty)`. The extra hover cost — the additional hover seconds required beyond `base_hover_time_s` to reach the effective direct-confirm threshold — is entirely absent from the score. This means candidates that require vastly different amounts of extra hover (e.g., 2000s vs 100s) can receive identical scores if their ground savings and energy penalties match, violating the ranking intent described in the plan.
- **Decision Reason**: Extra hover cost now computed at line 375-378 as `extra_hover_s / max(base_hover, 1.0)` and included in the denominator at line 403: `(1.0 + max(energy_penalty, 0.0) + extra_hover_cost)`. All three scoring components from the plan are present.

### SR-002: Ablation CSV and paper table missing $C_M$ column
- **Status**: Resolved
- **Description**: The IMPROVEMENT_PLAN subplan 04 architecture section states: "实验层固定K=4, alpha=1.00，分别求可拆分与不可拆分方案，比较Tu、Tg、T、航次数、能耗、人工点数**和C_M**。" The $C_M$ (归一化多目标评分 computed via `_add_normalized_objective`) is explicitly listed as a comparison metric. However, `_run_problem2_split_hover_ablation` in `experiments.py` did not call `_add_normalized_objective`, and the output CSV had no `normalized_objective` / $C_M$ column.
- **Decision Reason**: Added `_add_normalized_objective(rows, PROBLEM2_WEIGHTS)` call after row generation with infeasible-row handling (empty string for infeasible rows). CSV now includes `normalized_objective` column. Paper Table 11 updated with correct $C_M$ values.

### SR-003: Paper section 7.2 title deviates from plan specification
- **Status**: Resolved
- **Description**: Plan Step 14 specifies the section title as `## 7.2 可拆分悬停的必要性`. The actual paper used `## 7.2 可拆分悬停对照实验`.
- **Decision Reason**: Changed paper title from `## 7.2 可拆分悬停对照实验` to `## 7.2 可拆分悬停的必要性` per subplan Step 14 specification.

### SR-004: Paper section 7.2 missing required mathematical notation
- **Status**: Resolved
- **Description**: Plan Step 14 mandates the following body text with formal constraint definitions for split vs no-split. This exact mathematical formulation was absent from the paper.
- **Decision Reason**: Added the mandated text: "可拆分模型允许 $0\le h_{ir}\le q_i$ 且 $\sum_r h_{ir}=q_i$；不可拆分对照强制 $h_{ir}\in\{0,q_i\}$，即每个目标的需求必须由同一航次完整完成。两者在相同 $K=4,\alpha=1.00$ 下比较，可量化可拆分悬停对航次数、能耗利用率和闭环时间的影响。" at the start of section 7.2.

### SR-005: Ablation experiment expands k-range beyond plan specification
- **Status**: Resolved
- **Description**: Plan Step 9 code uses `k = data.params.k_max` (K=4 only), producing exactly 2 CSV rows (one per scheme). The implementation iterated `for k in range(1, 5)`, producing 8 rows.
- **Decision Reason**: Changed `_run_problem2_split_hover_ablation` to use `k = data.params.k_max` (K=4 only), removing the inner k-loop. Paper Table 11 updated to show K=4-only comparison with 2 rows.

### SR-006: Test parameter deviation in `test_problem1_no_split_keeps_target_in_one_route`
- **Status**: Resolved
- **Description**: Plan Step 12 specifies the test call as `solve_problem1_for_k(data, k=4, battery_swap_time_s=300, improve=True, allow_split_hover=False)`. The actual test used k=2 and omitted `improve=True`.
- **Decision Reason**: Changed test parameters to k=4, improve=True per subplan Step 12 specification.

## Code Review Issues

### CR-001: `_rebuild_for_direct_set` catches ValueError too broadly
- **Status**: Resolved
- **Description**: At `problem2.py:440`, `except ValueError` catches all ValueError instances from `solve_uav_hover_plan`. The called function (`split_order_into_energy_feasible_routes` in `search.py`) raises ValueError for both legitimate infeasibility conditions (target unreachable within single-sortie energy limit, search.py:172) AND programming errors (negative hover times search.py:118, unknown node IDs search.py:131, non-positive hover power search.py:158). The legitimate infeasibility cases should be silently skipped, but programming errors (which indicate corrupted data or logic bugs) should propagate as errors, not be silently swallowed. If a data corruption introduces an unknown node ID, the search would silently skip all candidates instead of failing fast, making the root cause extremely difficult to diagnose.
- **Decision Reason**: Fixed at line 477: now catches only `InfeasibleError` (a ValueError subclass defined in search.py:19-31 that is raised exclusively for legitimate planning infeasibilities). Plain `ValueError` from programming errors propagates correctly.

### CR-002: Missing test for `effective_direct_threshold` ValueError on non-positive multiplier
- **Status**: Resolved
- **Description**: `effective_direct_threshold` at `problem2.py:82-86` explicitly validates that `direct_threshold_multiplier > 0` and raises `ValueError` otherwise. No test exercises this validation path. The existing test `test_direct_threshold_multiplier_is_floored_by_base_hover_time` only tests with `multiplier=0.70`. Input validation at API boundaries must be tested to prevent regressions.
- **Decision Reason**: Test added at test_problem2.py:77-104 (`test_effective_direct_threshold_raises_on_non_positive_multiplier`) with multiplier=0.0 and -0.5. Black-box tests at test_blackbox_task004.py:150-168 cover zero, negative, and small-negative multipliers.

### CR-003: Missing test for `solve_ground_tsp` with empty manual point IDs
- **Status**: Resolved
- **Description**: `solve_ground_tsp` at `problem2.py:214-220` has an explicit early-return path for empty `manual_point_ids` that returns `path=("P0","P0")` with zero timings. This code path is never exercised by any test. If this early-return is refactored or broken in the future, it would not be caught. Every conditional branch should have test coverage.
- **Decision Reason**: Test added at test_problem2.py:106-115 (`test_solve_ground_tsp_empty_manual_points`). Black-box test at test_blackbox_task004.py:306-314 (`test_ground_tsp_empty_tuple`).

## Review Summary

All 10 issues (SR-001 through SR-006, CR-001 through CR-004) are resolved.

### Code Review Issues (resolved in prior pass)
- **CR-001** (broad except): Line 477 now catches only `InfeasibleError`, letting programming errors propagate.
- **CR-002** (missing validation test): Covered by 2 unit tests + 3 black-box tests across zero, negative, and small-negative multipliers.
- **CR-003** (missing empty TSP test): Covered by 1 unit test + 1 black-box test confirming ("P0","P0") path with zero timings.

### Spec Review Issues (all resolved)
- **SR-001** (missing extra-hover cost): `extra_hover_cost = extra_hover_s / max(base_hover, 1.0)` included as third denominator term.
- **SR-002** (missing C_M column): Added `_add_normalized_objective` call with PROBLEM2_WEIGHTS, infeasible-row handling.
- **SR-003** (paper title): Changed to `## 7.2 可拆分悬停的必要性` per subplan Step 14.
- **SR-004** (missing math notation): Added formal constraint definitions for split vs no-split at section 7.2 start.
- **SR-005** (k-range expanded): Changed to K=4 only with `k = data.params.k_max`, removed inner k-loop.
- **SR-006** (test parameters): Changed test to k=4, improve=True per subplan Step 12.

### Code Quality Assessment

| Category | Status | Notes |
|----------|--------|-------|
| Separation of concerns | PASS | problem2.py (584 lines) is focused on closed-loop evaluation + rebuild search |
| Error handling | PASS | InfeasibleError/ValueError distinction, KeyError for missing targets, input validation on multiplier/battery_swap_time |
| Type safety | PASS | `from __future__ import annotations`; all public functions have complete type annotations |
| Immutability | PASS | All 3 dataclasses use `frozen=True`; no in-place mutations |
| DRY | PASS | Shared accumulator pattern used consistently; no significant duplication |
| Edge cases | PASS | Empty routes, empty manual set, all-direct-confirmed, non-positive multiplier, invalid point IDs all handled |
| Plan conformance | PASS | All subplan Step requirements verified |
| Test coverage | PASS | 27 tests passing (test_search.py + test_problem1.py + test_problem2.py + test_experiments.py); 0 failures |

### Test Results
All 27 tests pass in the specified test suite (tests/test_search.py, tests/test_problem1.py, tests/test_problem2.py, tests/test_experiments.py).
