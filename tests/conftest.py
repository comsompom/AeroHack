"""
Shared pytest fixtures for DroneMission tests.
"""
import pytest


@pytest.fixture
def sample_waypoints():
    """Minimal list of (lat, lon) waypoints for aircraft tests."""
    return [
        (52.0, 4.0),
        (52.1, 4.1),
        (52.2, 4.0),
    ]
