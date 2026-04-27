"""Shared fixtures for black-box tests of c_uav_inspection package."""

from __future__ import annotations

from pathlib import Path

import pytest

from c_uav_inspection.data import ProblemData, load_problem_data

DATA_PATH = Path("2026同济数学建模竞赛赛题/2026C数据.xlsx")


@pytest.fixture(scope="session")
def data_path() -> Path:
    """Return the absolute path to the competition Excel workbook."""
    return DATA_PATH


@pytest.fixture(scope="session")
def problem_data(data_path: Path) -> ProblemData:
    """Load the full problem data once per test session (read-only)."""
    return load_problem_data(data_path)


@pytest.fixture(scope="session")
def targets_by_id(problem_data: ProblemData) -> dict[int, object]:
    """Index targets by node_id for convenient lookup."""
    return {t.node_id: t for t in problem_data.targets}
