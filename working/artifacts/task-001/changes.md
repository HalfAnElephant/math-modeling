# Changes: Task-001

## Files
- [mod] c_uav_inspection/data.py
- [mod] tests/test_data.py

## Summary
Resolved CR-006 (the last Pending issue): added input validation to `_read_matrix_sheet` consistent with `_read_uav_params` and `_read_targets`. Changes include: None-row skipping (prevents TypeError on empty rows), break on fully empty rows (end-of-data signal), flexible `max_row=max(ws.max_row, 4)` (instead of hardcoded 20). Added 2 regression tests for CR-006. Fixed a SyntaxWarning in test docstring. All 13 tests pass and all changes are committed. All Pending issues from implement-review-results.md are now resolved.
