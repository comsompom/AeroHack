"""Skeleton sanity test: project layout and imports."""
import pytest


def test_project_structure():
    """Verify we can run tests from project root."""
    assert True


def test_sample_waypoints_fixture(sample_waypoints):
    """Verify conftest fixture is available."""
    assert len(sample_waypoints) == 3
    assert sample_waypoints[0] == (52.0, 4.0)
