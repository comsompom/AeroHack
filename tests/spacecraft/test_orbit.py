"""Tests for spacecraft orbit and visibility."""
import math
import pytest

from src.spacecraft.orbit import (
    orbit_period_sec,
    position_at_t,
    is_visible,
    distance_deg,
    compute_pass_windows,
)


def test_orbit_period():
    # ~400 km LEO ~ 90 min
    T = orbit_period_sec(400.0)
    assert 5000 < T < 6000


def test_position_at_t():
    lat, lon = position_at_t(400.0, 0.0)
    assert -90 <= lat <= 90
    assert -180 <= lon <= 180


def test_distance_deg():
    d = distance_deg(52.0, 4.0, 52.0, 4.0)
    assert d == 0.0
    d2 = distance_deg(52.0, 4.0, 53.0, 4.0)
    assert d2 > 0


def test_is_visible():
    assert is_visible(52.0, 4.0, 52.0, 4.0) is True
    # Target > 60 deg from nadir is not visible
    assert is_visible(52.0, 4.0, -30.0, 4.0) is False


def test_compute_pass_windows():
    # 7 days
    windows = compute_pass_windows(400.0, 52.0, 4.0, 0, 7 * 86400, dt=60.0)
    assert isinstance(windows, list)
