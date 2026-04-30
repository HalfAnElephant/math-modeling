# Changes: Task-004

## Files
- [mod] c_uav_inspection/experiments.py
- [mod] tests/test_problem1.py
- [mod] tests/test_experiments.py
- [mod] report/c_uav_inspection_paper.md
- [mod] working/artifacts/task-004/implement-review-results.md

## Summary
Fixed all 5 Pending issues (SR-002 through SR-006) per IMPROVEMENT_PLAN subplan 04 specification:

- **SR-002**: Added `_add_normalized_objective(rows, PROBLEM2_WEIGHTS)` call in `_run_problem2_split_hover_ablation` with infeasible-row handling, adding the `normalized_objective` (C_M) column to the ablation CSV output.
- **SR-003**: Changed paper section title from `可拆分悬停对照实验` to `可拆分悬停的必要性` per subplan Step 14.
- **SR-004**: Added mandatory mathematical notation (split: $0\le h_{ir}\le q_i$, $\sum_r h_{ir}=q_i$; no-split: $h_{ir}\in\{0,q_i\}$) at the start of paper section 7.2.
- **SR-005**: Changed `_run_problem2_split_hover_ablation` to use `k = data.params.k_max` (K=4 only), removing the inner k-loop that expanded to K=1..4. Updated paper Table 11 to K=4-only comparison.
- **SR-006**: Changed test parameters in `test_problem1_no_split_keeps_target_in_one_route` from k=2 to k=4 with `improve=True` per subplan Step 12.
