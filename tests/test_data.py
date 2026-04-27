from __future__ import annotations

from pathlib import Path

import pytest

from c_uav_inspection.data import ProblemData, load_problem_data, validate_problem_data

DATA_PATH = Path("2026同济数学建模竞赛赛题/2026C数据.xlsx")


# ---------------------------------------------------------------------------
# Original plan tests (positive scenarios – basic interface coverage)
# ---------------------------------------------------------------------------


def test_load_problem_data_counts_targets_and_params():
    data = load_problem_data(DATA_PATH)

    assert len(data.targets) == 16
    assert data.params.k_max == 4
    assert data.params.effective_energy_limit_j == 135000
    assert data.params.hover_power_j_per_s == 220
    assert data.params.battery_swap_time_s == 300
    assert data.params.operating_horizon_s == 2600


def test_loaded_targets_preserve_key_values():
    data = load_problem_data(DATA_PATH)
    by_id = {target.node_id: target for target in data.targets}

    assert by_id[1].node_name == "B1-东立面裂缝"
    assert by_id[1].base_hover_time_s == 50
    assert by_id[1].direct_confirm_time_s == 200
    assert by_id[16].priority_weight == 3
    assert by_id[16].direct_confirm_time_s == 560


def test_matrices_include_depot_and_target_pairs():
    data = load_problem_data(DATA_PATH)

    assert data.flight_time_s[(0, 1)] > 0
    assert data.flight_energy_j[(0, 16)] > 0
    assert data.ground_time_s[("P0", "MP01")] > 0
    assert data.flight_time_s[(3, 3)] == 0


def test_validate_problem_data_returns_expected_summary():
    data = load_problem_data(DATA_PATH)
    summary = validate_problem_data(data)

    assert summary["target_count"] == 16
    assert summary["base_hover_sum_s"] == 790
    assert summary["direct_hover_sum_s"] == 5210
    assert summary["confirm_thresholds_valid"] is True
    assert summary["max_single_direct_confirm_energy_j"] <= data.params.effective_energy_limit_j


# ---------------------------------------------------------------------------
# Black-box supplementary tests – data integrity & boundary conditions
# ---------------------------------------------------------------------------


class TestFlightMatrixStructure:
    """Black-box: flight time/energy matrices must be 17x17, zero-diagonal,
    positive-valued elsewhere."""

    MATRIX_ATTRS = ("flight_time_s", "flight_energy_j")

    @pytest.mark.parametrize("attr_name", MATRIX_ATTRS)
    def test_flight_matrix_is_17_by_17(
        self, problem_data: ProblemData, attr_name: str
    ) -> None:
        matrix: dict[tuple[int, int], float] = getattr(problem_data, attr_name)
        ids_present = sorted({k[0] for k in matrix} | {k[1] for k in matrix})
        assert ids_present == list(range(0, 17)), (
            f"{attr_name}: expected nodes 0..16, got {ids_present}"
        )

    @pytest.mark.parametrize("attr_name", MATRIX_ATTRS)
    def test_flight_diagonal_is_zero(
        self, problem_data: ProblemData, attr_name: str
    ) -> None:
        matrix: dict[tuple[int, int], float] = getattr(problem_data, attr_name)
        for i in range(0, 17):
            assert matrix.get((i, i), -1.0) == 0.0, (
                f"{attr_name}[({i},{i})] expected 0.0"
            )

    @pytest.mark.parametrize("attr_name", MATRIX_ATTRS)
    def test_flight_non_diagonal_entries_are_positive(
        self, problem_data: ProblemData, attr_name: str
    ) -> None:
        matrix: dict[tuple[int, int], float] = getattr(problem_data, attr_name)
        for (i, j), val in matrix.items():
            if i == j:
                continue
            assert val > 0, f"{attr_name}[({i},{j})] = {val}, expected > 0"

    def test_flight_time_and_energy_share_same_key_set(
        self, problem_data: ProblemData
    ) -> None:
        ft_keys = set(problem_data.flight_time_s.keys())
        fe_keys = set(problem_data.flight_energy_j.keys())
        assert ft_keys == fe_keys, (
            f"Key mismatch: flight_time_s has {len(ft_keys)} keys, "
            f"flight_energy_j has {len(fe_keys)} keys"
        )


class TestGroundMatrixStructure:
    """Black-box: ground time matrix must include P0 and MP01–MP16."""

    def test_ground_matrix_is_17_by_17(self, problem_data: ProblemData) -> None:
        matrix = problem_data.ground_time_s
        from_ids = sorted({k[0] for k in matrix})
        to_ids = sorted({k[1] for k in matrix})
        assert from_ids == to_ids, "ground matrix should be square"
        assert len(from_ids) == 17, f"expected 17 ground points, got {len(from_ids)}"
        assert "P0" in from_ids, f"P0 missing from ground matrix points: {from_ids}"

    def test_ground_diagonal_is_zero(self, problem_data: ProblemData) -> None:
        matrix = problem_data.ground_time_s
        point_ids = sorted({k[0] for k in matrix})
        for pid in point_ids:
            assert matrix.get((pid, pid), -1.0) == 0.0, (
                f"ground_time_s[({pid},{pid})] expected 0.0"
            )

    def test_all_ground_non_diagonal_entries_are_positive(
        self, problem_data: ProblemData
    ) -> None:
        matrix = problem_data.ground_time_s
        for (src, dst), val in matrix.items():
            if src == dst:
                continue
            assert val > 0, f"ground_time_s[({src},{dst})] = {val}, expected > 0"


class TestTargetIntegrity:
    """Black-box: targets must be self-consistent and match the Checks sheet."""

    def test_all_sixteen_unique_ids(self, problem_data: ProblemData) -> None:
        ids = sorted([t.node_id for t in problem_data.targets])
        assert ids == list(range(1, 17)), f"Expected node_id 1..16, got {ids}"

    def test_all_base_hover_times_are_positive(
        self, problem_data: ProblemData
    ) -> None:
        for t in problem_data.targets:
            assert t.base_hover_time_s > 0, (
                f"Target {t.node_id}: base_hover_time_s = {t.base_hover_time_s}"
            )

    def test_all_direct_confirm_not_less_than_base(
        self, problem_data: ProblemData
    ) -> None:
        for t in problem_data.targets:
            assert t.direct_confirm_time_s >= t.base_hover_time_s, (
                f"Target {t.node_id}: direct_confirm={t.direct_confirm_time_s} "
                f"< base_hover={t.base_hover_time_s}"
            )

    def test_priority_weights_are_valid(self, problem_data: ProblemData) -> None:
        for t in problem_data.targets:
            assert t.priority_weight in {1, 2, 3}, (
                f"Target {t.node_id}: unexpected priority_weight {t.priority_weight}"
            )

    def test_all_coordinates_are_reasonable(self, problem_data: ProblemData) -> None:
        for t in problem_data.targets:
            assert isinstance(t.x_m, (int, float)) and isinstance(t.y_m, (int, float))
            assert isinstance(t.z_m, (int, float)) and t.z_m >= 0

    def test_manual_point_references_are_valid(
        self, problem_data: ProblemData
    ) -> None:
        for t in problem_data.targets:
            assert t.manual_point_id.startswith("MP"), (
                f"Target {t.node_id}: manual_point_id={t.manual_point_id}"
            )
            assert t.manual_service_time_s > 0, (
                f"Target {t.node_id}: manual_service_time_s={t.manual_service_time_s}"
            )


class TestChecksSheetCrossValidation:
    """Black-box: cross-validate loaded data against the reference Checks sheet.

    The Checks sheet in the workbook contains independently computed reference
    values (e.g. total base hover sum = 790 s).  Every external consumer should
    be able to reproduce these.
    """

    def test_total_base_hover_sum_matches_checks(self, problem_data: ProblemData) -> None:
        total = sum(t.base_hover_time_s for t in problem_data.targets)
        assert total == 790, f"Checks sheet says 790 s, computed {total}"

    def test_total_direct_confirm_sum_matches_checks(
        self, problem_data: ProblemData
    ) -> None:
        total = sum(t.direct_confirm_time_s for t in problem_data.targets)
        assert total == 5210, f"Checks sheet says 5210 s, computed {total}"

    def test_total_manual_service_time_matches_checks(
        self, problem_data: ProblemData
    ) -> None:
        total = sum(t.manual_service_time_s for t in problem_data.targets)
        assert total == 2670, f"Checks sheet says 2670 s, computed {total}"

    def test_max_single_direct_confirm_energy_matches_checks(
        self, problem_data: ProblemData
    ) -> None:
        summary = validate_problem_data(problem_data)
        # Checks sheet: 132986 J (rounded to integer Joule)
        assert summary["max_single_direct_confirm_energy_j"] <= 133000
        assert summary["max_single_direct_confirm_energy_j"] > 100000


class TestValidateCompleteness:
    """Black-box: validate_problem_data must return all documented keys."""

    REQUIRED_KEYS = frozenset(
        [
            "target_count",
            "base_hover_sum_s",
            "direct_hover_sum_s",
            "confirm_thresholds_valid",
            "max_single_direct_confirm_energy_j",
        ]
    )

    def test_summary_contains_all_required_keys(
        self, problem_data: ProblemData
    ) -> None:
        summary = validate_problem_data(problem_data)
        missing = self.REQUIRED_KEYS - set(summary.keys())
        assert not missing, f"Missing summary keys: {missing}"

    def test_summary_types_are_expected(self, problem_data: ProblemData) -> None:
        summary = validate_problem_data(problem_data)
        assert isinstance(summary["target_count"], int)
        assert isinstance(summary["base_hover_sum_s"], (int, float))
        assert isinstance(summary["direct_hover_sum_s"], (int, float))
        assert isinstance(summary["confirm_thresholds_valid"], bool)
        assert isinstance(summary["max_single_direct_confirm_energy_j"], (int, float))


class TestFlightEnergyTimeCorrelation:
    """Black-box: longer flight times should generally mean higher energy.

    This is a basic physical consistency check — any consumer of the data
    would expect energy and time to be monotonically related.
    """

    def test_position_time_energy_correlation(
        self, problem_data: ProblemData
    ) -> None:
        time_mat = problem_data.flight_time_s
        energy_mat = problem_data.flight_energy_j

        # Pick a few representative pairs and verify correlation
        pairs: list[tuple[tuple[int, int], tuple[int, int]]] = [
            ((0, 1), (0, 3)),   # 1 and 3 are in same building B1
            ((0, 1), (0, 16)),  # 16 is farthest
            ((0, 15), (0, 16)), # both B7, 16 slightly farther
        ]
        for (a_from, a_to), (b_from, b_to) in pairs:
            dt_a = time_mat[(a_from, a_to)]
            dt_b = time_mat[(b_from, b_to)]
            de_a = energy_mat[(a_from, a_to)]
            de_b = energy_mat[(b_from, b_to)]
            # longer time → higher energy (strictly monotonic for these pairs)
            if dt_a < dt_b:
                assert de_a < de_b, (
                    f"Time {(a_from,a_to)}={dt_a} < {(b_from,b_to)}={dt_b} "
                    f"but energy {de_a} >= {de_b}"
                )


# ---------------------------------------------------------------------------
# Black-box error handling (negative scenarios)
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Black-box: the public API must fail explicitly, never silently."""

    def test_nonexistent_file_raises(self) -> None:
        ghost = Path("/nonexistent/not_a_real_file_2026.xlsx")
        with pytest.raises(Exception):
            load_problem_data(ghost)

    def test_directory_instead_of_file_raises(self) -> None:
        with pytest.raises(Exception):
            load_problem_data(Path("."))

    def test_str_path_accepted(self) -> None:
        """load_problem_data must accept a plain str path (not only Path)."""
        data = load_problem_data(str(DATA_PATH))
        assert len(data.targets) == 16

    def test_workbook_closed_on_exception(self) -> None:
        """Workbook must be closed even when sheet reading raises mid-way."""
        from unittest.mock import MagicMock, patch

        import openpyxl as _openpyxl

        mock_wb = MagicMock()
        mock_wb.__getitem__.side_effect = KeyError("SheetMissing")

        with patch.object(
            _openpyxl, "load_workbook", return_value=mock_wb
        ):
            with pytest.raises((KeyError, Exception)):
                load_problem_data(DATA_PATH)

        mock_wb.close.assert_called_once()
