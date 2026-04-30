# Changes: Task-005

## Files
- [new] tests/conftest.py
- [mod] tests/test_exact.py
- [mod] tests/test_experiments.py
- [mod] tests/test_plots.py
- [mod] c_uav_inspection/experiments.py
- [mod] c_uav_inspection/plots.py

## Summary
Fixed all Pending issues from implement-review-results.md:
- SR-001: Extracted _make_small_data to tests/conftest.py as a pytest fixture (make_small_data). Updated test_exact.py and test_experiments.py to use the fixture. Removed unused imports.
- SR-004: Removed the _add_normalized_objective call in _run_problem2_exact_enumeration that was re-normalizing against only the top-20 subset. Each DirectSetEvaluation already carries the correct normalized_objective computed against all feasible evaluations.
- CR-005: Fixed plots.py _plot_problem1_k_comparison to read problem1_k_comparison_current_packed.csv (matching what experiments.py writes). Updated test_plots.py error match pattern accordingly.
- CR-007: Replaced brittle exact float assertions in test_problem2_baseline_comparison_base_only_row and test_problem1_swap_sensitivity_k1_uses_critical_path with property-based assertions (closed_loop = uav + ground, swap delta = time delta).
- SR-002, SR-003, CR-006: Marked Don't Fix (plan/implementation mismatch per IMPROVEMENT_PLAN subplan 05).
