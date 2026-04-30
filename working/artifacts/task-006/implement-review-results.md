# Implement Review Results: Task-006

## Spec Review Issues

### SR-001: Step 8 (Final Commit) was not executed
- **Status**: Resolved
- **Description**: The plan explicitly requires step 8 — committing all implementation artifacts with `git add PLAN docs/superpowers/plans c_uav_inspection tests outputs/c_uav_inspection report` followed by `git commit -m "chore: finalize c problem execution plans and outputs"`. Independent verification shows no such commit exists in `git log` (latest commit is `77c51de fix: add input validation` from a prior task). All files listed in the plan's git-add command remain untracked (`??` in `git status --short`): `c_uav_inspection/experiments.py`, `c_uav_inspection/model.py`, `c_uav_inspection/objective.py`, `c_uav_inspection/plots.py`, `c_uav_inspection/problem1.py`, `c_uav_inspection/problem2.py`, `c_uav_inspection/search.py`, `outputs/`, `report/`, `PLAN/`, and multiple test files. The implementer's test-results.md omits this step entirely from its 7-item checklist and reports all steps as "PASS" despite this omission.
- **Decision Reason**:

### SR-002: route_count field missing from energy/hover sensitivity CSV outputs
- **Status**: Resolved
- **Description**: Subplan 06 Step 7 (`_run_problem2_energy_limit_sensitivity`) and Step 8 (`_run_problem2_hover_power_sensitivity`) both specify `"route_count": len(sol.routes)` in the feasible row dict and `"route_count": ""` in the infeasible row dict. The implementation in `c_uav_inspection/experiments.py` lines 461-564 omits this field from both CSV outputs. This means the CSVs cannot track how energy/hover parameter changes affect the number of UAV routes, which is a meaningful sensitivity dimension the plan intended to capture.
- **Decision Reason**:

## Code Review Issues

### CR-001: changes.md understates actual scope of modifications
- **Status**: Resolved
- **Description**: The task-006 `changes.md` claims only 3 new experiment functions (acceptance tolerance, energy limit, hover power sensitivity) and a `manual_reduction_time_tolerance` parameter were added across 5 files. However, the actual uncommitted diff (`git diff --stat`) shows 12 files changed with +1426/-61 lines, including significant changes not mentioned: (a) `ClosedLoopResult` gained `manual_target_nodes` and `weighted_manual_cost` fields; (b) `_direct_confirm_score` now multiplies by `priority_weight`, changing candidate ranking; (c) `PROBLEM2_WEIGHTS` was restructured from 5 terms `{0.50, 0.20, 0.10, 0.10, 0.10}` to 6 terms `{0.45, 0.20, 0.15, 0.10, 0.05, 0.05}` with the new `weighted_manual_cost` term; (d) `allow_split_hover` parameter was plumbed through `_rebuild_for_direct_set` and `solve_joint_problem_for_k`; (e) additional experiment functions were added beyond the 3 listed (time-priority DP comparison, route count ablation, baseline comparison, split-hover ablation, exact enumeration); (f) output file names changed (`problem1_k_comparison.csv` → `problem1_k_comparison_current_packed.csv`, `problem1_swap_sensitivity.csv` → `problem1_swap_sensitivity_k1.csv`); (g) `include_expensive` parameter added to `run_all_experiments`. An incomplete changes.md makes it harder for reviewers to trace which changes belong to which task, understand side effects (e.g., file renames break backward compatibility for anyone referencing old filenames), and assess whether all changes were intentional.
- **Decision Reason**:
