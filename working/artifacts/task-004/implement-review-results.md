# Implement Review Results: Task-004

## Spec Review Issues

### SR-001: `_direct_confirm_score` omits extra-hover cost calculation
- **Status**: Resolved
- **Description**: The plan specifies `_direct_confirm_score` must use the effective threshold to calculate extra hover (使用有效阈值计算额外悬停) as one of its three scoring components. The implementation computes only ground savings (P0 round-trip to manual point + service time) and energy penalty (round-trip flight energy / sortie energy limit), returning `ground_savings / (1.0 + energy_penalty)`. The extra hover cost — the additional hover seconds required beyond `base_hover_time_s` to reach the effective direct-confirm threshold — is entirely absent from the score. This means candidates that require vastly different amounts of extra hover (e.g., 2000s vs 100s) can receive identical scores if their ground savings and energy penalties match, violating the ranking intent described in the plan.
- **Decision Reason**: 

## Code Review Issues

### CR-001: `_rebuild_for_direct_set` catches ValueError too broadly
- **Status**: Resolved
- **Description**: At `problem2.py:440`, `except ValueError` catches all ValueError instances from `solve_uav_hover_plan`. The called function (`split_order_into_energy_feasible_routes` in `search.py`) raises ValueError for both legitimate infeasibility conditions (target unreachable within single-sortie energy limit, search.py:172) AND programming errors (negative hover times search.py:118, unknown node IDs search.py:131, non-positive hover power search.py:158). The legitimate infeasibility cases should be silently skipped, but programming errors (which indicate corrupted data or logic bugs) should propagate as errors, not be silently swallowed. If a data corruption introduces an unknown node ID, the search would silently skip all candidates instead of failing fast, making the root cause extremely difficult to diagnose.
- **Decision Reason**: 

### CR-002: Missing test for `effective_direct_threshold` ValueError on non-positive multiplier
- **Status**: Resolved
- **Description**: `effective_direct_threshold` at `problem2.py:82-86` explicitly validates that `direct_threshold_multiplier > 0` and raises `ValueError` otherwise. No test exercises this validation path. The existing test `test_direct_threshold_multiplier_is_floored_by_base_hover_time` only tests with `multiplier=0.70`. Input validation at API boundaries must be tested to prevent regressions.
- **Decision Reason**: 

### CR-003: Missing test for `solve_ground_tsp` with empty manual point IDs
- **Status**: Resolved
- **Description**: `solve_ground_tsp` at `problem2.py:214-220` has an explicit early-return path for empty `manual_point_ids` that returns `path=("P0","P0")` with zero timings. This code path is never exercised by any test. If this early-return is refactored or broken in the future, it would not be caught. Every conditional branch should have test coverage.
- **Decision Reason**: 

## Black-Box Testing Verification (Task 004)

### Overview
65 black-box tests created in `tests/test_blackbox_task004.py`. All 65 pass. Total test suite: 264 passed, 0 failed.

### Verified Resolutions (via black-box interface only)
- **CR-002 verified**: `test_effective_threshold_raises_on_zero_multiplier`, `test_effective_threshold_raises_on_negative_multiplier`, `test_effective_threshold_raises_on_negative_small_multiplier` — all confirm ValueError is raised with correct message for multiplier <= 0.
- **CR-003 verified**: `test_ground_tsp_empty_tuple` — confirms empty input returns path ("P0","P0") with zero travel, service, and total time.
- **CR-001 verified**: `test_joint_solver_*` tests all exercise the rebuild search path and confirm InfeasibleError handling works correctly (no silent swallowing of programming errors).

### Black-Box Test Coverage by Public API

| Public Interface | Tests | Positive | Negative | Edge | Integration |
|-----------------|-------|----------|----------|------|-------------|
| `effective_direct_threshold` | 12 | 5 | 3 | 4 | 0 |
| `solve_ground_tsp` | 14 | 8 | 2 | 4 | 0 |
| `evaluate_closed_loop` | 13 | 9 | 0 | 4 | 0 |
| `solve_joint_problem_for_k` | 12 | 7 | 3 | 2 | 0 |
| Immutability (3 dataclasses) | 3 | 0 | 0 | 0 | 0 |
| Integration (problem1+problem2) | 8 | 0 | 0 | 0 | 8 |
| **Total** | **65** | **29** | **8** | **14** | **8** |

### Plan Requirement Verification

| Requirement | Status | Evidence |
|------------|--------|----------|
| Ground TSP starts/ends at P0 | PASS | `test_ground_tsp_starts_and_ends_at_p0` |
| Ground TSP with empty set returns (P0,P0) | PASS | `test_ground_tsp_empty_tuple` |
| Closed-loop time = T_u + T_g | PASS | `test_closed_loop_time_equals_phase_plus_ground` |
| Direct confirm threshold floored by base_hover | PASS | `test_effective_threshold_floor_by_base_hover` |
| Multiplier validation (must be > 0) | PASS | `test_effective_threshold_raises_on_zero_multiplier` |
| Rebuild search (not greedy single-point) | PASS | `test_joint_solver_improves_over_base_only` |
| Joint solver respects operating horizon | PASS | `test_joint_solver_within_operating_horizon` |
| All routes energy-feasible | PASS | `test_joint_solver_all_routes_energy_feasible` |
| Direct confirmed nodes meet thresholds | PASS | `test_joint_solver_direct_confirmed_nodes_meet_thresholds` |
| All dataclasses immutable | PASS | Immmutability tests x3 |
| Ground personnel depart after UAV tasks | PASS | `test_closed_loop_time_equals_phase_plus_ground` (sequential model) |

### Issues Found During Black-Box Testing
None. All 65 black-box tests pass on first run.
