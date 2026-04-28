# Changes: Task-002

## Files
- [new] c_uav_inspection/model.py
- [new] c_uav_inspection/objective.py
- [new] tests/test_model.py
- [new] tests/test_objective.py

## Black-box tests
- [new] tests/test_blackbox_task002.py (53 tests)

### Coverage
- model: 24 tests (positive, edge, negative, immutability)
- objective: 26 tests (positive, edge, negative, immutability)
- integration: 3 tests (model + objective pipeline)

## Summary
Implemented core model (UAVRoute, RouteMetrics, UAVSolutionSummary) with route evaluation and solution summarization including battery swap time and load standard deviation. Implemented normalized multi-objective scoring (min-max normalization with degenerate bounds handling and weighted sum) to prevent unit-dominance in optimization. All 97 tests pass (18 unit + 26 existing black-box + 53 new black-box).
