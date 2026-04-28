# Implement Review Results: Task-005

## Spec Review Issues

## Code Review Issues

### CR-001: `_add_normalized_objective` mutates input rows in-place
- **Status**: Resolved
- **Description**: The function at `c_uav_inspection/experiments.py:58-69` directly adds a `normalized_objective` key to each dict in the input `rows` list (`row["normalized_objective"] = round(score, 6)`). This violates the immutable data pattern required by the coding style ("ALWAYS create new objects, NEVER mutate existing ones"). While the rows are constructed locally in the calling functions and not reused afterward, mutation of input parameters creates a hidden side effect that could cause bugs if the caller later reuses the rows. The function should return new dicts instead.
- **Decision Reason**:

### CR-002: Duplicate `summarize_uav_solution` calls in Problem 2 experiments
- **Status**: Resolved
- **Description**: In `c_uav_inspection/experiments.py`, both `_run_problem2_k_comparison` (lines 135, 138) and `_run_problem2_threshold_sensitivity` (lines 158, 161) call `summarize_uav_solution(sol.routes, data, data.params.battery_swap_time_s)` twice — once to extract `.total_energy_j` and once for `.load_std_s`. The function iterates over all routes, evaluates flight time/energy and hover time/energy for each route, and computes summary statistics. Calling it twice with identical arguments wastes computation and is a code smell. The summary should be computed once and destructured.
- **Decision Reason**:

### CR-003: `generate_all_figures` silently succeeds when no input data exists
- **Status**: Resolved
- **Description**: In `c_uav_inspection/plots.py`, each internal plot helper (`_plot_problem1_k_comparison:29-30`, `_plot_problem2_threshold_sensitivity:70-71`, `_plot_recommended_routes:120-121`) checks `if not csv_path.exists(): return` and silently exits. This means if `generate_all_figures` is called before `run_all_experiments`, it silently returns without producing any PNGs and without raising an error. A user would have no indication that no figures were generated. The function should either validate prerequisites up front or raise an error when expected input files are missing.
- **Decision Reason**:

### CR-004: Missing type annotations on helper function parameters
- **Status**: Resolved
- **Description**: `_serialize_route` at `c_uav_inspection/experiments.py:175` has an untyped `route` parameter (should be `UAVRoute`). `_write_recommended_solution` at line 187 has an untyped `data` parameter (should be `ProblemData`). The rest of the codebase consistently uses type annotations on all function signatures. Missing annotations reduce type safety and IDE support.
- **Decision Reason**:
