# Test Results: Task-004

## Status
EXPECTED

## Test Results

| Test | Result | Expected | Blocked | Details |
|------|--------|----------|---------|---------|
| test_nearest_neighbor_order_visits_each_target_once | PASS | PASS | no | - |
| test_nearest_neighbor_order_raises_on_duplicates | PASS | PASS | no | - |
| test_split_order_raises_on_zero_hover_power | PASS | PASS | no | - |
| test_partial_hover_ends_sortie_immediately | PASS | PASS | no | - |
| test_split_order_energy_accounting_matches_evaluate | PASS | PASS | no | - |
| test_split_order_into_energy_feasible_routes_satisfies_base_hover | PASS | PASS | no | - |
| test_split_order_allows_one_target_hover_to_span_multiple_sorties | PASS | PASS | no | - |
| test_no_split_routes_never_split_positive_hover | PASS | PASS | no | - |
| test_no_split_raises_infeasible_when_target_exceeds_energy | PASS | PASS | no | - |
| test_problem1_solution_satisfies_base_hover_and_energy_for_k2 | PASS | PASS | no | - |
| test_problem1_solution_uses_only_requested_uav_count | PASS | PASS | no | - |
| test_problem1_local_search_keeps_solution_feasible | PASS | PASS | no | - |
| test_problem1_no_split_keeps_target_in_one_route | PASS | PASS | no | - |
| test_ground_tsp_all_manual_starts_and_ends_at_p0 | PASS | PASS | no | - |
| test_closed_loop_marks_all_base_only_targets_manual | PASS | PASS | no | - |
| test_direct_threshold_multiplier_is_floored_by_base_hover_time | PASS | PASS | no | - |
| test_joint_solver_reduces_or_matches_manual_count_against_base_only | PASS | PASS | no | - |
| test_joint_solver_direct_confirmed_nodes_meet_effective_thresholds | PASS | PASS | no | - |
| test_effective_direct_threshold_raises_on_non_positive_multiplier | PASS | PASS | no | - |
| test_solve_ground_tsp_empty_manual_points | PASS | PASS | no | - |
| test_closed_loop_reports_weighted_manual_cost_for_all_manual_case | PASS | PASS | no | - |
| test_direct_confirm_score_multiplies_priority_weight | PASS | PASS | no | - |
| test_run_all_experiments_writes_expected_files | PASS | PASS | no | - |
| test_add_normalized_objective_does_not_mutate_input | PASS | PASS | no | - |
| test_problem2_baseline_comparison_base_only_row | PASS | PASS | no | - |
| test_problem1_swap_sensitivity_k1_uses_critical_path | PASS | PASS | no | - |
| test_problem2_split_hover_ablation_csv_has_expected_schema | PASS | PASS | no | - |

## Summary
- EXPECTED (Result=Expected, Blocked=no): 27
- UNEXPECTED (Result!=Expected, Blocked=no): 0
- Blocked (Blocked=yes): 0
