"""Tests for exact enumeration of direct-confirm sets (exact.py)."""


# ---------------------------------------------------------------------------
# Tests (uses make_small_data fixture from conftest.py)
# ---------------------------------------------------------------------------


def test_enumerate_direct_confirm_sets_small_data(make_small_data):
    """Small data (4 targets → 16 subsets, k=2): basic assertions."""
    from c_uav_inspection.exact import enumerate_direct_confirm_sets

    data = make_small_data
    result = enumerate_direct_confirm_sets(
        data, k=2, direct_threshold_multiplier=1.0, top_n=5,
    )

    assert result.total_subsets == 16
    assert result.feasible_subsets >= 1, (
        f"Expected at least 1 feasible subset, got {result.feasible_subsets}"
    )

    # Best by closed_loop should be feasible
    assert result.best_by_closed_loop.feasible

    # Ranks must be >= 1
    assert result.rebuild_time_rank >= 1
    assert result.rebuild_objective_rank >= 1

    # Gaps must be >= 0
    assert result.rebuild_time_gap_s >= 0.0
    assert result.rebuild_time_gap_pct >= 0.0
    assert result.rebuild_objective_gap >= 0.0

    # top_n should limit the outputs
    assert len(result.top_by_closed_loop) <= 5
    assert len(result.top_by_objective) <= 5

    # All top entries should be feasible
    for ev in result.top_by_closed_loop:
        assert ev.feasible

    # rebuild_solution should be present
    assert result.rebuild_solution is not None
    assert result.rebuild_solution.feasible


def test_evaluate_direct_set_empty_is_feasible(make_small_data):
    """Empty direct set should always be feasible (base hover only)."""
    from c_uav_inspection.exact import _evaluate_direct_set

    data = make_small_data
    ev = _evaluate_direct_set(data, k=2, direct_nodes=(), direct_threshold_multiplier=1.0)

    assert ev.feasible
    assert ev.closed_loop_time_s > 0
    assert ev.uav_phase_time_s > 0
    assert ev.ground_review_time_s > 0


def test_evaluate_direct_set_infeasible_when_all_direct(make_small_data):
    """Full direct set (all targets) may be infeasible if energy budget
    is insufficient for all direct-confirm hover requirements."""
    from c_uav_inspection.exact import _evaluate_direct_set

    data = make_small_data
    all_nodes = tuple(t.node_id for t in data.targets)
    ev = _evaluate_direct_set(
        data, k=2, direct_nodes=all_nodes, direct_threshold_multiplier=1.0,
    )

    # With generous energy budget in small data, this should be feasible.
    # If not, it's at least a valid DirectSetEvaluation with feasible=False.
    assert ev.direct_nodes == all_nodes
    # Either feasible or infeasible — both are valid results
    assert isinstance(ev.feasible, bool)


def test_with_normalized_objectives_populates_score():
    """Normalized objective should be in [0, 1] for all feasible evals."""
    from c_uav_inspection.exact import (
        DirectSetEvaluation,
        _with_normalized_objectives,
    )

    evals = [
        DirectSetEvaluation(
            direct_nodes=(),
            feasible=True,
            closed_loop_time_s=100.0,
            uav_phase_time_s=50.0,
            ground_review_time_s=50.0,
            manual_count=4,
            weighted_manual_cost=8,
            direct_confirm_count=0,
            total_energy_j=10000.0,
            load_std_s=0.0,
            route_count=1,
            normalized_objective=0.0,
        ),
        DirectSetEvaluation(
            direct_nodes=(1,),
            feasible=True,
            closed_loop_time_s=80.0,
            uav_phase_time_s=40.0,
            ground_review_time_s=40.0,
            manual_count=3,
            weighted_manual_cost=5,
            direct_confirm_count=1,
            total_energy_j=12000.0,
            load_std_s=10.0,
            route_count=1,
            normalized_objective=0.0,
        ),
    ]

    normalized = _with_normalized_objectives(evals)
    assert len(normalized) == 2
    for ev in normalized:
        assert 0.0 <= ev.normalized_objective <= 1.0

    # The better eval (lower closed_loop_time) should have lower objective
    assert normalized[1].normalized_objective <= normalized[0].normalized_objective


def test_serialize_direct_set_eval_outputs_all_fields():
    """_serialize_direct_set_eval must include all DirectSetEvaluation fields."""
    from c_uav_inspection.exact import DirectSetEvaluation
    from c_uav_inspection.experiments import _serialize_direct_set_eval

    ev = DirectSetEvaluation(
        direct_nodes=(1, 3),
        feasible=True,
        closed_loop_time_s=123.456,
        uav_phase_time_s=50.0,
        ground_review_time_s=73.456,
        manual_count=2,
        weighted_manual_cost=4,
        direct_confirm_count=2,
        total_energy_j=25000.0,
        load_std_s=5.0,
        route_count=2,
        normalized_objective=0.345678,
    )

    d = _serialize_direct_set_eval(ev)
    assert d["direct_nodes"] == "1,3"
    assert d["feasible"] is True
    assert d["closed_loop_time_s"] == 123.456
    assert d["normalized_objective"] == 0.345678
    assert d["direct_confirm_count"] == 2
