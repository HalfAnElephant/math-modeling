# Test Results: Task-001

## Status
EXPECTED

## Test Results

| Test | Result | Expected | Blocked | Details |
|------|--------|----------|---------|---------|
| test_subset_route_candidates_include_all_singletons | PASS | PASS | no | - |
| test_time_priority_k4_covers_all_targets_energy_feasible | PASS | PASS | no | - |
| test_time_priority_k4_not_worse_than_current_packed_solution | PASS | PASS | no | time-priority 268.90s << packed 639.33s |
| test_solve_time_priority_k0_raises_value_error | PASS | PASS | no | CR-009 |
| test_solve_time_priority_negative_k_raises_value_error | PASS | PASS | no | CR-009 |
| test_solve_time_priority_k1_raises_infeasible_error | PASS | PASS | no | CR-009 |
| test_problem1_solution_satisfies_base_hover_and_energy_for_k2 | PASS | PASS | no | existing regression |
| test_problem1_solution_uses_only_requested_uav_count | PASS | PASS | no | existing regression |
| test_problem1_local_search_keeps_solution_feasible | PASS | PASS | no | existing regression |
| test_run_all_experiments_writes_expected_files | PASS | PASS | no | updated for CR-008 merged output |
| test_add_normalized_objective_does_not_mutate_input | PASS | PASS | no | existing regression |

## Failed Tests (for self-debugging)

None.

## Summary
- EXPECTED (Result=Expected, Blocked=no): 11
- UNEXPECTED (Result≠Expected, Blocked=no): 0
- Blocked (Blocked=yes): 0
