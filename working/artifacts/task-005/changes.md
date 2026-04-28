# Changes: Task-005

## Files
- [new] tests/test_experiments.py
- [new] c_uav_inspection/experiments.py
- [new] tests/test_plots.py
- [new] c_uav_inspection/plots.py
- [new] report/c_uav_inspection_results.md
- [new] outputs/c_uav_inspection/data_validation.json
- [new] outputs/c_uav_inspection/problem1_k_comparison.csv
- [new] outputs/c_uav_inspection/problem1_swap_sensitivity.csv
- [new] outputs/c_uav_inspection/problem2_k_comparison.csv
- [new] outputs/c_uav_inspection/problem2_threshold_sensitivity.csv
- [new] outputs/c_uav_inspection/recommended_solution.json
- [new] outputs/c_uav_inspection/problem1_k_comparison.png
- [new] outputs/c_uav_inspection/problem2_threshold_sensitivity.png
- [new] outputs/c_uav_inspection/recommended_routes.png

## Summary
Implemented experiments, plots, and paper results for Problem C multi-UAV inspection. The experiments module generates CSV comparison tables (K=1..4, swap sensitivity, threshold sensitivity), JSON data validation, and a recommended solution. The plots module produces PNG charts (K-comparison bar chart, threshold sensitivity line chart, route map). The report document provides a complete results writeup for paper inclusion.

## Review Fixes
- CR-001: `_add_normalized_objective` now returns new rows instead of mutating input
- CR-002: Removed duplicate `summarize_uav_solution` calls in Problem 2 experiments
- CR-003: `generate_all_figures` now raises `FileNotFoundError` when input files are missing
- CR-004: Added `UAVRoute` and `ProblemData` type annotations on helper functions
