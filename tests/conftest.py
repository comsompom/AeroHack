"""
Shared pytest fixtures for DroneMission tests.
Ensures project root is on sys.path so src.* and webapp.* import correctly.
"""
import os
import sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


@pytest.fixture
def sample_waypoints():
    """Minimal list of (lat, lon) waypoints for aircraft tests."""
    return [
        (52.0, 4.0),
        (52.1, 4.1),
        (52.2, 4.0),
    ]
