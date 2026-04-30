# Test Results: Task-006

## Status
EXPECTED

## Test Results

| Test | Result | Expected | Blocked | Details |
|------|--------|----------|---------|---------|
| test_ground_tsp_all_manual_starts_and_ends_at_p0 | PASS | PASS | no | - |
| test_closed_loop_marks_all_base_only_targets_manual | PASS | PASS | no | - |
| test_direct_threshold_multiplier_is_floored_by_base_hover_time | PASS | PASS | no | - |
| test_joint_solver_reduces_or_matches_manual_count_against_base_only | PASS | PASS | no | - |
| test_joint_solver_direct_confirmed_nodes_meet_effective_thresholds | PASS | PASS | no | - |
| test_effective_direct_threshold_raises_on_non_positive_multiplier | PASS | PASS | no | - |
| test_solve_ground_tsp_empty_manual_points | PASS | PASS | no | - |
| test_closed_loop_reports_weighted_manual_cost_for_all_manual_case | PASS | PASS | no | - |
| test_joint_solver_rejects_tolerance_below_one | PASS | PASS | no | ValueError raised for 0.99 and 0.5, 1.0 accepted |
| test_direct_confirm_score_multiplies_priority_weight | PASS | PASS | no | - |
| test_run_all_experiments_writes_expected_files | PASS | PASS | no | all 13 expected files exist |
| test_add_normalized_objective_does_not_mutate_input | PASS | PASS | no | - |
| test_problem2_baseline_comparison_base_only_row | PASS | PASS | no | - |
| test_problem1_swap_sensitivity_k1_uses_critical_path | PASS | PASS | no | - |
| test_problem2_split_hover_ablation_csv_has_expected_schema | PASS | PASS | no | - |
| test_include_expensive_false_does_not_create_enum_files | PASS | PASS | no | - |
| test_task006_new_sensitivity_csv_files_exist_and_valid | PASS | PASS | no | 3 CSVs exist, tolerance values [1.0, 1.03, 1.05, 1.10], energy baseline 135000.0, hover baseline 220.0; route_count present in energy/hover rows |
| test_run_problem2_exact_enumeration_writes_expected_files_small_data | PASS | PASS | no | - |

## Summary
- EXPECTED (Result=Expected, Blocked=no): 18
- UNEXPECTED (Result≠Expected, Blocked=no): 0
- Blocked (Blocked=yes): 0
