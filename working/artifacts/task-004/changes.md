# Changes: Task-004

## Files
- [mod] c_uav_inspection/problem2.py
- [mod] c_uav_inspection/search.py
- [mod] tests/test_problem2.py
- [mod] working/artifacts/task-004/implement-review-results.md

## Summary
Fixed 4 pending review issues:
- SR-001: Added extra-hover cost calculation to `_direct_confirm_score` — now uses all three plan-specified components (extra hover, ground savings, energy penalty)
- CR-001: Added `InfeasibleError(ValueError)` in search.py for legitimate infeasibility; `_rebuild_for_direct_set` now catches only `InfeasibleError` instead of broad `ValueError`
- CR-002: Added `test_effective_direct_threshold_raises_on_non_positive_multiplier` for multiplier <= 0 validation
- CR-003: Added `test_solve_ground_tsp_empty_manual_points` for empty manual_points edge case
