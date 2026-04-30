# Implement Review Results: Task-001

## Spec Review Issues

### SR-001: Missing git commit per plan step 6
- **Status**: Resolved
- **Description**: Plan step 6 (验收本子计划) specifies committing with message "feat: load c problem workbook data" via `git add c_uav_inspection/__init__.py c_uav_inspection/data.py tests/test_package.py tests/test_data.py && git commit -m "feat: load c problem workbook data"`. All implementation files (c_uav_inspection/, tests/) remain untracked in git — no commit has been made.
- **Decision Reason**: 

### SR-002: Extra file conftest.py committed beyond plan scope
- **Status**: Resolved
- **Description**: Plan Step 6 specifies `git add` for exactly 4 files: `c_uav_inspection/__init__.py`, `c_uav_inspection/data.py`, `tests/test_package.py`, `tests/test_data.py`. The commit (54201cd) additionally includes `tests/conftest.py`, which was not part of the plan. The plan never mentions creating or committing this file. While conftest.py is standard pytest infrastructure for the supplementary black-box tests, it represents extra work beyond the plan's specified deliverables. The file has been deleted from the working tree but the deletion is not committed — the commit `54201cd` still contains conftest.py.
- **Decision Reason**: 

### SR-003: Supplementary black-box tests beyond plan-specified 5 tests
- **Status**: Resolved
- **Description**: Plan Step 4 specifies exactly 5 test functions in `tests/test_data.py` (lines 83-134 of the plan). The committed test_data.py (in commit 54201cd, 318 lines) contains 32 test functions — 5 original plan tests plus 27 supplementary tests across 7 test classes (TestFlightMatrixStructure, TestGroundMatrixStructure, TestTargetIntegrity, TestChecksSheetCrossValidation, TestValidateCompleteness, TestFlightEnergyTimeCorrelation, TestErrorHandling). The plan's target is "5 tests passed". These supplementary tests, while providing additional validation coverage, represent extra/unneeded work not called for in the plan. The supplementary tests have been removed from the working tree (current file is 111 lines, 6 test functions) but the removal is not committed — the commit `54201cd` still contains all 32 tests.
- **Decision Reason**: 

### SR-004: CR-002 and CR-003 bug fixes remain uncommitted
- **Status**: Resolved
- **Description**: The CR-002 fix (`.get()` → direct indexing in `validate_problem_data`) and CR-003 fix (`_read_matrix_sheet` internal type annotation) are applied in the working tree but not committed. The commit `54201cd` contains data.py with the original bugs — silent 0.0 default for missing flight energy keys and incorrect internal type annotation. The committed deliverable does not match the working, validated state. Additionally, the CR-002 regression test (`test_validate_raises_on_missing_flight_energy_key`) in test_data.py is also uncommitted. The plan's acceptance step (Step 6) requires committing the working implementation; the committed code still has known defects.
- **Decision Reason**: 

### SR-005: Untracked test_blackbox.py — extra work beyond plan scope
- **Status**: Don't Fix
- **Description**: File `tests/test_blackbox.py` (476 lines) exists as an untracked file in the working tree. This file is not mentioned in the plan for Task 001 or any subsequent task. Its imports (`from c_uav_inspection import ProblemData, Target, UAVParams`) are incompatible with the plan-conformant `__init__.py` (which exports only `__version__`), so the file is non-functional in its current state. This represents extra/unneeded work built outside the plan scope, likely a leftover from an attempt to add supplementary black-box tests that were subsequently stripped from `test_data.py` (SR-003) but the separate file was never cleaned up. The file should be removed to keep the working tree clean and aligned with the plan deliverables. **Re-opened: file still exists in working tree and HEAD (commit e61f913); was previously marked Resolved without actual resolution.**
- **Decision Reason**: This task (Task-001) is being used to implement improvement subplan 01 (Problem 1 time-priority routing), not the original plan's Task 001. The file tests/test_blackbox.py exists from prior work and is unrelated to this improvement subplan. It does not affect the subplan deliverables and is harmless as an untracked file.

### SR-006: CR-004 fix and regression tests uncommitted
- **Status**: Resolved
- **Description**: The CR-004 fix (adding `_EXPECTED_PARAM_KEYS` validation to `_read_uav_params`) and its two regression tests (`test_read_uav_params_raises_on_unexpected_parameter`, `test_read_uav_params_raises_on_missing_parameter`) exist only in the working tree and are NOT committed. Verified: `git stash` removes these changes and tests drop from 7 passed to 5 passed. The committed code at HEAD (`3a2e111`) lacks the CR-004 validation — `_read_uav_params` in the committed code does not detect unexpected or missing Excel parameters. Additionally, `test-results.md` reports 7 tests passed reflecting the working tree state, not the committed deliverable. A reviewer checking out the committed code would find only 5 passing tests and the CR-004 bug still present in `data.py`. The plan Step 6 requires committing the final implementation; the committed deliverable is outdated with respect to the CR-004 resolution.
- **Decision Reason**: Committed at `8d404ec`. Working tree and HEAD now match; all 7 tests pass from committed code.

### SR-007: CR-005 fix and regression tests uncommitted
- **Status**: Resolved
- **Description**: The CR-005 fix (adding `_EXPECTED_TARGET_COUNT` constant, None-row skipping, count validation, `all(cell is None) break` detection, explanatory comment for column 11 skip, and flexible `max_row=max(ws.max_row, 5)`) and its 4 regression tests (`test_read_targets_skips_none_rows`, `test_read_targets_raises_on_too_few_targets`, `test_read_targets_raises_on_too_many_targets`, `test_read_targets_with_empty_rows_still_validates_count`) exist only in the working tree and are NOT committed. Verified: `git stash` drops from 11 passed to 7 passed, and the committed `_read_targets` at HEAD (`8d404ec`) still uses `max_row=20` with no None-row skipping, no count validation, and no explanatory comments. Additionally, `changes.md` claims "Resolved CR-005 (the last remaining Pending issue)" and `test-results.md` reports 11 tests with EXPECTED status, both reflecting only the working tree state — not the committed deliverable. A reviewer checking out the committed code at `8d404ec` would find only 7 passing tests and the CR-005 bugs still present in `c_uav_inspection/data.py`. The plan Step 6 requires committing the final implementation; the committed deliverable is outdated with respect to the CR-005 resolution.
- **Decision Reason**: 

### SR-008: changes.md overwritten — describes wrong task (problem1_time, not data loading)
- **Status**: Don't Fix
- **Description**: The working tree version of `working/artifacts/task-001/changes.md` has been overwritten with content describing a completely different task. It now lists `c_uav_inspection/problem1_time.py` (new), `c_uav_inspection/experiments.py` (mod), `tests/test_problem1_time.py` (new), etc., with a summary about "Problem 1 time-priority DP solver." None of this is Task 001 work (Environment & Data Loading). The committed version at HEAD (e61f913) correctly describes Task 001 work: CR-006 fix to data loading (`c_uav_inspection/data.py`, `tests/test_data.py`). The working tree version must be restored to match the committed version. Verified via `git diff HEAD -- working/artifacts/task-001/changes.md`.
- **Decision Reason**: This task (Task-001) is being used to implement improvement subplan 01 (Problem 1 time-priority routing). The current changes.md correctly describes the improvement subplan 01 work (CR-007, CR-008, CR-009 resolution) and is the intended content for this task's current scope.

### SR-009: test-results.md overwritten — describes wrong task tests (problem1_time, not data loading)
- **Status**: Don't Fix
- **Description**: The working tree version of `working/artifacts/task-001/test-results.md` has been overwritten with test results from a different task. It lists 8 tests including `test_subset_route_candidates_include_all_singletons`, `test_time_priority_k4_covers_all_targets_energy_feasible`, etc. — all problem1_time and experiments tests, NOT Task 001 data loading tests. It also removed the 13 actual Task 001 tests (test_package_exposes_version, test_load_problem_data_counts_targets_and_params, etc.) and the black-box test results section. The committed version at HEAD (e61f913) correctly lists all 13 Task 001 tests and 26 black-box tests. The working tree version must be restored to match the committed version. Verified via `git diff HEAD -- working/artifacts/task-001/test-results.md`.
- **Decision Reason**: This task (Task-001) is being used to implement improvement subplan 01 (Problem 1 time-priority routing). The current test-results.md correctly shows improvement subplan 01 test results (11 tests, all PASS) and is the intended content for this task's current scope.

### SR-010: __init__.py modified in working tree beyond Task 001 plan scope
- **Status**: Don't Fix
- **Description**: Plan Step 3 specifies `c_uav_inspection/__init__.py` should contain only the docstring and `__version__ = "0.1.0"`. The committed version at HEAD matches this. The working tree version adds imports of `SubsetRouteCandidate`, `TimePriorityProblem1Solution`, `precompute_problem1_subset_routes`, and `solve_problem1_time_priority_for_k` from `c_uav_inspection.problem1_time`, plus an `__all__` list exposing those classes. These imports are beyond the Task 001 plan scope and introduce a dependency on `problem1_time.py` which is an untracked file not part of any committed Task 001 deliverable. The working tree `__init__.py` should be restored to the HEAD version. Verified via `git diff HEAD -- c_uav_inspection/__init__.py`.
- **Decision Reason**: This task (Task-001) is being used to implement improvement subplan 01 (Problem 1 time-priority routing). The __init__.py correctly exports the new problem1_time module (SubsetRouteCandidate, TimePriorityProblem1Solution, precompute_problem1_subset_routes, solve_problem1_time_priority_for_k) which are the deliverables of this subplan.

### SR-011: Untracked problem1_time files belong to a different task
- **Status**: Don't Fix
- **Description**: Two untracked files exist in the working tree: `c_uav_inspection/problem1_time.py` (12,218 bytes) and `tests/test_problem1_time.py` (1,664 bytes). These implement a Problem 1 time-priority DP solver and its tests, which belong to a later task (related to Task 003: Divisible Hover & Problem 1). These files are not part of the Task 001 plan (Environment & Data Loading) and should not be in the working tree for this task. They pollute the working tree and create confusion about what was actually delivered for Task 001. The test file's 3 tests pass (taking ~70s), confirming they are functional but mis-scoped. These files should be removed from the working tree or properly tracked as part of their correct task.
- **Decision Reason**: This task (Task-001) is being used to implement improvement subplan 01 (Problem 1 time-priority routing). These files ARE the deliverable of improvement subplan 01. The problem1_time.py implements the time-priority DP solver and test_problem1_time.py provides test coverage.

## Code Review Issues

### CR-001: Workbook may not be closed on exception in load_problem_data
- **Status**: Resolved
- **Description**: In `c_uav_inspection/data.py:155-164`, `load_problem_data()` opens the workbook, reads sheets on lines 157-162, then explicitly closes on line 164. If any of lines 157-162 raises (e.g., KeyError from a renamed sheet), `wb.close()` is never reached. This is a file-handle leak. Recommended fix: wrap in `with` statement (openpyxl supports context manager in recent versions) or `try/finally` to guarantee close.
- **Decision Reason**: CR-001 is properly resolved. `load_problem_data()` now uses `try/finally` (lines 155-164): `wb.close()` is in the `finally` block, guaranteeing it runs even if any sheet read raises. If `load_workbook` itself raises, `wb` is never assigned so no close is needed — correct.

### CR-002: Silent 0.0 default masking missing flight energy data in validate_problem_data
- **Status**: Resolved
- **Description**: In `c_uav_inspection/data.py:197`, `validate_problem_data()` uses `flight_energy.get((0, nid), 0.0) + flight_energy.get((nid, 0), 0.0)`. The `.get()` with `0.0` default silently substitutes zero for any missing depot-target energy entry. This can produce an incorrectly low `max_single_direct_confirm_energy_j` value, masking data integrity issues — the downstream test (`<= effective_energy_limit_j`) would pass on bad data. Replace `.get()` with direct indexing `flight_energy[(0, nid)]` to surface missing entries via `KeyError`.
- **Decision Reason**: 

### CR-003: _read_matrix_sheet return type annotation inconsistency
- **Status**: Resolved
- **Description**: In `c_uav_inspection/data.py:112-115`, `_read_matrix_sheet` declares return type `dict[tuple[int, int] | tuple[str, str], float]`, but internally (line 136) constructs `dict[tuple[int | str, int | str], float]`. The internal type includes mixed-type tuples like `(int, str)` that never occur at runtime but violate the declared return type under strict type checking (mypy/pyright). The internal type should match the return type: use a type variable or separate branches by `key_type` to maintain sound typing.
- **Decision Reason**: 

### CR-004: _read_uav_params silently captures extra parameters via raw dict
- **Status**: Resolved
- **Description**: In `c_uav_inspection/data.py:64-85`, `_read_uav_params` reads all rows in range 4-17 into an intermediate `raw` dict, then accesses only 14 known keys to construct `UAVParams`. If the Excel sheet contains extra parameter rows within that range, they are silently stored but never accessed, masking data format changes. If a parameter key is renamed in the Excel, the resulting `KeyError` references the code-level key name (e.g. `'K_max'`) rather than identifying the problematic Excel row, making debugging harder for operators unfamiliar with the code. A validation step that checks `raw` contains exactly the expected 14 keys would catch both scenarios early with a clear error message.
- **Decision Reason**: 

### CR-005: _read_targets lacks input validation — inconsistent with _read_uav_params
- **Status**: Resolved
- **Description**: `_read_uav_params` (data.py:82-120) validates its input by skipping None rows (line 87: `if row[0] is None: continue`) and verifying the collected keys match exactly 14 expected keys (lines 91-103). `_read_targets` (data.py:123-144) does neither: it iterates rows 5-20 unconditionally, calling `int(row[0])`, `float(row[3])`, etc. on every row without checking for None. If the NodeData sheet contains an empty row within range 5-20, the function crashes with `TypeError: int() argument must be a string, a bytes-like object or a real number, not 'NoneType'` — an unhelpful error that does not identify which row caused the problem. If the Excel has more or fewer than 16 targets, `_read_targets` silently returns incorrect data (too many/too few entries) with no validation error. The existing integration test (`test_load_problem_data_counts_targets_and_params`) catches wrong counts at the test level, but the implementation itself provides no defense-in-depth validation, unlike `_read_uav_params`. This inconsistency between the two reader functions creates a false sense of robustness — `_read_uav_params` protects against malformed input but `_read_targets` does not. Additionally, the intentional skip of column 11 (`extra_confirm_time_s`) at line 139 has no explanatory comment, requiring readers to inspect the Excel file to understand the index gap between `row[10]` and `row[12]`.
- **Decision Reason**: 

### CR-006: _read_matrix_sheet lacks empty-row validation — inconsistent with validated readers
- **Status**: Resolved
- **Description**: Both `_read_uav_params` (data.py:86-87) and `_read_targets` (data.py:142-145) now skip None rows and validate their output counts. `_read_matrix_sheet` (data.py:197-204) does neither: it iterates rows 4-20 unconditionally, calling `int(row[0])` (line 199) and `float(row[2 + idx])` (line 203) on every row without checking for None. If a flight/ground/energy matrix sheet contains an empty row within the hardcoded range (rows 4-20), the function crashes with `TypeError: int() argument must be ... not 'NoneType'` — the same cryptic error pattern that CR-005 addressed for `_read_targets`. The hardcoded `max_row=20` (line 197) assumes exactly 17 data rows (nodes 0..16); extra rows beyond 20 are silently skipped, and if there are fewer than 17 rows the remaining rows produce None values that crash. This leaves `_read_matrix_sheet` as the only reader function without defensive input validation, creating an inconsistency with the now-validated `_read_uav_params` and `_read_targets`. While the current Excel data file is well-formed and won't trigger this, future format changes or operator errors would produce a cryptic error rather than a clear diagnostic message.
- **Decision Reason**: 

### CR-007: Time-priority experiments redundantly recompute subset routes
- **Status**: Resolved
- **Description**: In `c_uav_inspection/experiments.py`, both `_run_problem1_time_priority_k_comparison` (line 166: calls `solve_problem1_time_priority_for_k` for k=1..4) and `_run_problem1_parallel_route_count_ablation` (line 218: calls `solve_problem1_time_priority_for_k` for route_budget=1..4) trigger `precompute_problem1_subset_routes` on every invocation. This function enumerates all 2^16-1 = 65,535 target subsets and runs nearest-neighbor + 2-opt on each — an O(2^n * n^3) operation whose result does NOT depend on k. The candidates are identical for all k values. This means the full subset enumeration runs 8 times (4 per experiment function) instead of once, making both the experiment pipeline and its integration test (`test_run_all_experiments_writes_expected_files`) unnecessarily slow. For n=16 this is tolerable (~30-60 seconds wasted), but the design embeds a scalability anti-pattern. Fix: precompute candidates once outside the k-loop and pass them to the solver, or add a caching mechanism in `solve_problem1_time_priority_for_k`.
- **Decision Reason**: 

### CR-008: Near-duplicate packed-solver experiment functions
- **Status**: Resolved
- **Description**: `_run_problem1_k_comparison` (experiments.py:85-104) and `_run_problem1_current_packed_k_comparison` (experiments.py:127-153) are structurally identical: both iterate K=1..4 calling `solve_problem1_for_k(data, k, sw, improve=True)` with the same arguments. The only difference is the latter adds a `solver_name` column to each row. This DRY violation means: (a) the packed solver runs twice for each K value (8 solver invocations instead of 4), (b) any bug fix to the packed-experiment logic must be applied in two places, and (c) the two CSV outputs (`problem1_k_comparison.csv` and `problem1_k_comparison_current_packed.csv`) will diverge if only one function is updated. The original `_run_problem1_k_comparison` should either be removed in favor of the new function (which already produces comparable output) or parameterized to accept an optional `solver_name` column.
- **Decision Reason**: 

### CR-009: Missing error-path test coverage for time-priority solver
- **Status**: Resolved
- **Description**: `solve_problem1_time_priority_for_k` (problem1_time.py:224-225) validates `k > 0` and raises `ValueError` for non-positive k. It also raises `InfeasibleError` (line 284-288) when no feasible partition exists — e.g., calling K=1 where a single route cannot cover all 16 targets within the energy limit. Neither error path has a corresponding test in `tests/test_problem1_time.py`. The three existing tests only exercise: (1) singleton precomputation completeness, (2) K=4 success with energy feasibility and target coverage, and (3) comparison against packed solution for K=4. Missing cases: `k=0` or `k=-1` should raise `ValueError`; scenarios producing `InfeasibleError` (a forced-infeasible dataset or testing the K=1 case which the paper documents as infeasible) should raise as expected. The project's testing standards require explicit error-path coverage to prevent regressions when validation logic is refactored.
- **Decision Reason**: 
