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
- **Status**: Resolved
- **Description**: File `tests/test_blackbox.py` (476 lines) exists as an untracked file in the working tree. This file is not mentioned in the plan for Task 001 or any subsequent task. Its imports (`from c_uav_inspection import ProblemData, Target, UAVParams`) are incompatible with the plan-conformant `__init__.py` (which exports only `__version__`), so the file is non-functional in its current state. This represents extra/unneeded work built outside the plan scope, likely a leftover from an attempt to add supplementary black-box tests that were subsequently stripped from `test_data.py` (SR-003) but the separate file was never cleaned up. The file should be removed to keep the working tree clean and aligned with the plan deliverables.
- **Decision Reason**: 

### SR-006: CR-004 fix and regression tests uncommitted
- **Status**: Resolved
- **Description**: The CR-004 fix (adding `_EXPECTED_PARAM_KEYS` validation to `_read_uav_params`) and its two regression tests (`test_read_uav_params_raises_on_unexpected_parameter`, `test_read_uav_params_raises_on_missing_parameter`) exist only in the working tree and are NOT committed. Verified: `git stash` removes these changes and tests drop from 7 passed to 5 passed. The committed code at HEAD (`3a2e111`) lacks the CR-004 validation — `_read_uav_params` in the committed code does not detect unexpected or missing Excel parameters. Additionally, `test-results.md` reports 7 tests passed reflecting the working tree state, not the committed deliverable. A reviewer checking out the committed code would find only 5 passing tests and the CR-004 bug still present in `data.py`. The plan Step 6 requires committing the final implementation; the committed deliverable is outdated with respect to the CR-004 resolution.
- **Decision Reason**: Committed at `8d404ec`. Working tree and HEAD now match; all 7 tests pass from committed code.

### SR-007: CR-005 fix and regression tests uncommitted
- **Status**: Resolved
- **Description**: The CR-005 fix (adding `_EXPECTED_TARGET_COUNT` constant, None-row skipping, count validation, `all(cell is None) break` detection, explanatory comment for column 11 skip, and flexible `max_row=max(ws.max_row, 5)`) and its 4 regression tests (`test_read_targets_skips_none_rows`, `test_read_targets_raises_on_too_few_targets`, `test_read_targets_raises_on_too_many_targets`, `test_read_targets_with_empty_rows_still_validates_count`) exist only in the working tree and are NOT committed. Verified: `git stash` drops from 11 passed to 7 passed, and the committed `_read_targets` at HEAD (`8d404ec`) still uses `max_row=20` with no None-row skipping, no count validation, and no explanatory comments. Additionally, `changes.md` claims "Resolved CR-005 (the last remaining Pending issue)" and `test-results.md` reports 11 tests with EXPECTED status, both reflecting only the working tree state — not the committed deliverable. A reviewer checking out the committed code at `8d404ec` would find only 7 passing tests and the CR-005 bugs still present in `c_uav_inspection/data.py`. The plan Step 6 requires committing the final implementation; the committed deliverable is outdated with respect to the CR-005 resolution.
- **Decision Reason**: 

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
