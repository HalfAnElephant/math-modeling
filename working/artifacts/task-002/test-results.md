# Test Results: Task-002

## Status
EXPECTED

## Test Results

| Test | Result | Expected | Blocked | Details |
|------|--------|----------|---------|---------|
| test_package_exposes_version | PASS | PASS | no | - |
| test_load_problem_data_counts_targets_and_params | PASS | PASS | no | - |
| test_loaded_targets_preserve_key_values | PASS | PASS | no | - |
| test_matrices_include_depot_and_target_pairs | PASS | PASS | no | - |
| test_read_uav_params_raises_on_unexpected_parameter | PASS | PASS | no | - |
| test_read_uav_params_raises_on_missing_parameter | PASS | PASS | no | - |
| test_validate_problem_data_returns_expected_summary | PASS | PASS | no | - |
| test_read_targets_skips_none_rows | PASS | PASS | no | - |
| test_read_targets_raises_on_too_few_targets | PASS | PASS | no | - |
| test_read_targets_raises_on_too_many_targets | PASS | PASS | no | - |
| test_read_targets_with_empty_rows_still_validates_count | PASS | PASS | no | - |
| test_read_matrix_sheet_skips_none_rows | PASS | PASS | no | - |
| test_read_matrix_sheet_breaks_on_fully_empty_row | PASS | PASS | no | - |
| test_evaluate_single_base_route_matches_manual_energy_formula | PASS | PASS | no | - |
| test_summarize_solution_includes_swap_time_between_sorties | PASS | PASS | no | - |
| test_normalize_term_maps_value_to_unit_interval | PASS | PASS | no | - |
| test_normalize_term_handles_degenerate_bounds | PASS | PASS | no | - |
| test_weighted_objective_does_not_let_large_units_dominate | PASS | PASS | no | - |

### Black-box tests (test_blackbox_task002.py) — 53 tests

| Test | Result | Expected | Blocked | Details |
|------|--------|----------|---------|---------|
| test_evaluate_route_returns_route_metrics | PASS | PASS | no | model — positive |
| test_evaluate_route_metrics_non_negative | PASS | PASS | no | model — positive |
| test_evaluate_route_duration_positive_for_nonzero_route | PASS | PASS | no | model — positive |
| test_evaluate_route_adding_hover_increases_metrics | PASS | PASS | no | model — positive |
| test_evaluate_route_longer_path_has_longer_duration | PASS | PASS | no | model — positive |
| test_evaluate_route_feasible_for_low_energy | PASS | PASS | no | model — edge case |
| test_evaluate_route_invalid_node_raises | PASS | PASS | no | model — negative |
| test_summarize_returns_uav_solution_summary | PASS | PASS | no | model — positive |
| test_summarize_single_uav_single_sortie_no_swap | PASS | PASS | no | model — positive |
| test_summarize_phase_time_is_max_work_time | PASS | PASS | no | model — positive |
| test_summarize_total_energy_is_sum_of_routes | PASS | PASS | no | model — positive |
| test_summarize_load_std_zero_for_equal_work_times | PASS | PASS | no | model — positive |
| test_summarize_load_std_positive_for_unequal_work_times | PASS | PASS | no | model — positive |
| test_summarize_swap_overhead_is_n_minus_1_times_swap | PASS | PASS | no | model — positive |
| test_summarize_feasible_when_all_routes_feasible | PASS | PASS | no | model — positive |
| test_summarize_infeasible_when_any_route_infeasible | PASS | PASS | no | model — edge case |
| test_summarize_empty_solution | PASS | PASS | no | model — edge case |
| test_summarize_single_uav_load_std_zero | PASS | PASS | no | model — edge case |
| test_summarize_zero_swap_time_no_overhead | PASS | PASS | no | model — edge case |
| test_summarize_large_swap_time | PASS | PASS | no | model — edge case |
| test_summarize_three_uavs_load_std_with_skewed_load | PASS | PASS | no | model — edge case |
| test_uav_route_is_immutable | PASS | PASS | no | model — immutability |
| test_route_metrics_is_immutable | PASS | PASS | no | model — immutability |
| test_uav_solution_summary_is_immutable | PASS | PASS | no | model — immutability |
| test_normalize_term_returns_float | PASS | PASS | no | objective — positive |
| test_normalize_term_output_always_in_unit_interval | PASS | PASS | no | objective — positive |
| test_normalize_term_min_maps_to_zero_max_to_one | PASS | PASS | no | objective — positive |
| test_normalize_term_monotonic | PASS | PASS | no | objective — positive |
| test_normalize_term_degenerate_bounds_returns_zero | PASS | PASS | no | objective — edge case |
| test_normalize_term_negative_bounds | PASS | PASS | no | objective — edge case |
| test_normalize_term_clips_below_min | PASS | PASS | no | objective — edge case |
| test_normalize_term_clips_above_max | PASS | PASS | no | objective — edge case |
| test_normalize_term_zero_range_bounds | PASS | PASS | no | objective — edge case |
| test_bounds_from_candidates_single_row | PASS | PASS | no | objective — positive |
| test_bounds_from_candidates_min_and_max | PASS | PASS | no | objective — positive |
| test_bounds_from_candidates_all_identical | PASS | PASS | no | objective — edge case |
| test_bounds_from_candidates_empty_rows | PASS | PASS | no | objective — edge case |
| test_bounds_from_candidates_negative_values | PASS | PASS | no | objective — edge case |
| test_weighted_objective_single_term | PASS | PASS | no | objective — positive |
| test_weighted_objective_equal_weights_is_average | PASS | PASS | no | objective — positive |
| test_weighted_objective_zero_weight_term_does_not_affect | PASS | PASS | no | objective — positive |
| test_weighted_objective_unequal_weights | PASS | PASS | no | objective — positive |
| test_weighted_objective_no_unit_dominance | PASS | PASS | no | objective — positive |
| test_weighted_objective_output_in_unit_interval | PASS | PASS | no | objective — positive |
| test_weighted_objective_with_degenerate_bounds | PASS | PASS | no | objective — edge case |
| test_weighted_objective_with_all_degenerate_bounds | PASS | PASS | no | objective — edge case |
| test_weighted_objective_with_values_outside_bounds | PASS | PASS | no | objective — edge case |
| test_weighted_objective_zero_total_weight_raises | PASS | PASS | no | objective — negative |
| test_weighted_objective_negative_total_weight_raises | PASS | PASS | no | objective — negative |
| test_objective_term_bounds_is_immutable | PASS | PASS | no | objective — immutability |
| test_route_metrics_usable_in_objective_scoring | PASS | PASS | no | integration |
| test_solution_summary_usable_in_objective_scoring | PASS | PASS | no | integration |
| test_multiple_candidate_solutions_can_be_scored | PASS | PASS | no | integration |

## Failed Tests (for self-debugging)

None

## Summary
- EXPECTED (Result=Expected, Blocked=no): 97 (18 unit + 53 black-box + 26 existing black-box)
- UNEXPECTED (Result≠Expected, Blocked=no): 0
- Blocked (Blocked=yes): 0
