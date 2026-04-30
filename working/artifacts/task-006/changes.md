# Changes: Task-006

## Files
- [mod] c_uav_inspection/__init__.py
- [mod] c_uav_inspection/experiments.py
- [mod] c_uav_inspection/plots.py
- [mod] c_uav_inspection/problem1.py
- [mod] c_uav_inspection/problem2.py
- [mod] c_uav_inspection/search.py
- [mod] report/c_uav_inspection_paper.md
- [mod] tests/test_experiments.py
- [mod] tests/test_plots.py
- [mod] tests/test_problem1.py
- [mod] tests/test_problem2.py
- [mod] tests/test_search.py

## Summary

### problem2.py — Closed-loop model refinements
- Added `manual_target_nodes` and `weighted_manual_cost` fields to `ClosedLoopResult` dataclass
- Updated `evaluate_closed_loop()` to populate `manual_target_nodes` (sorted tuple) and `weighted_manual_cost` (sum of priority_weight over manual targets)
- Modified `_direct_confirm_score()` to multiply benefit by `max(target.priority_weight, 1)`, making high-priority targets more likely to be direct-confirmed
- Restructured `PROBLEM2_WEIGHTS` from 5 terms `{0.50, 0.20, 0.10, 0.10, 0.10}` to 6 terms `{0.45, 0.20, 0.15, 0.10, 0.05, 0.05}` with new `weighted_manual_cost` term
- Plumbed `allow_split_hover` parameter through `_rebuild_for_direct_set()` and `solve_joint_problem_for_k()`
- Added `manual_reduction_time_tolerance` parameter to `solve_joint_problem_for_k()` (default 1.03) replacing hardcoded 1.03x tolerance; validated (>= 1.0)
- Updated acceptance criterion: now also accepts candidates where `weighted_manual_cost` decreases (in addition to `manual_count`) within tolerance

### search.py — No-split hover variant
- Added `split_order_into_energy_feasible_routes_no_split()` function: energy-feasible bin-packing where each target's full hover demand must fit within a single sortie (no splitting across sorties)

### problem1.py — allow_split_hover plumbing
- Updated `solve_uav_hover_plan()` to accept `allow_split_hover` parameter, dispatching to either split or no-split route builder

### __init__.py — Public API exports
- Added public exports for `SubsetRouteCandidate`, `TimePriorityProblem1Solution`, `precompute_problem1_subset_routes`, `solve_problem1_time_priority_for_k`

### experiments.py — Full experiment suite
- Renamed output: `problem1_k_comparison.csv` → `problem1_k_comparison_current_packed.csv`
- Renamed output: `problem1_swap_sensitivity.csv` → `problem1_swap_sensitivity_k1.csv`
- Added `run_all_experiments(include_expensive=False)` parameter to gate exact enumeration
- Added experiment functions:
  - `_run_problem1_time_priority_k_comparison()` — time-priority DP solver K-comparison (K=1..4)
  - `_run_problem1_parallel_route_count_ablation()` — route budget ablation (1..4 routes)
  - `_run_problem1_swap_sensitivity_k4_reference()` — swap sensitivity at K=4 reference
  - `_run_problem2_baseline_comparison()` — base-only vs joint solver comparison
  - `_run_problem2_k_comparison()` — K=1..4 closed-loop comparison
  - `_run_problem2_threshold_sensitivity()` — direct-threshold multiplier sweep 0.70..1.30
  - `_run_problem2_split_hover_ablation()` — split vs no-split hover ablation
  - `_run_problem2_acceptance_tolerance_sensitivity()` — tolerance sweep 1.00..1.10
  - `_run_problem2_energy_limit_sensitivity()` — energy budget 0.90x..1.10x with `route_count`
  - `_run_problem2_hover_power_sensitivity()` — hover power 0.90x..1.10x with `route_count`
  - `_run_problem2_exact_enumeration()` — brute-force enumeration (2^num_targets) for small data verification

### plots.py — Updated input file reference
- Updated `_plot_problem1_k_comparison()` to read from renamed `problem1_k_comparison_current_packed.csv`

### Tests — Comprehensive coverage
- Added tests for: weighted_manual_cost reporting, manual_reduction_time_tolerance rejection, direct_confirm_score priority_weight multiplication, no-split route splitting, Problem 1 time-priority DP K-comparison, all new experiment CSV outputs, exact enumeration (small data), and baseline comparison structure

### Paper — New sections
- Added two new paper sections: acceptance tolerance sensitivity analysis and energy parameter sensitivity analysis
