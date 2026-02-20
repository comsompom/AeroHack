"""Tests for mission_settings constants."""
import pytest

from src.mission_settings import (
    AIRCRAFT_WAYPOINTS,
    AIRCRAFT_CRUISE_SPEED_MS,
    AIRCRAFT_MAX_ALTITUDE_M,
    AIRCRAFT_MIN_ALTITUDE_M,
    AIRCRAFT_NO_FLY_ZONES,
    MONTE_CARLO_NUM_SEEDS,
    MONTE_CARLO_SEED,
    SPACECRAFT_ALTITUDE_KM,
    SPACECRAFT_TARGETS,
    SPACECRAFT_STATION,
    SPACECRAFT_SCHEDULE_DAYS,
)


def test_aircraft_waypoints_non_empty():
    assert len(AIRCRAFT_WAYPOINTS) >= 2
    for wp in AIRCRAFT_WAYPOINTS:
        assert len(wp) >= 2
        assert -90 <= wp[0] <= 90
        assert -180 <= wp[1] <= 180


def test_aircraft_model_params_positive():
    assert AIRCRAFT_CRUISE_SPEED_MS > 0
    assert AIRCRAFT_MIN_ALTITUDE_M >= 0
    assert AIRCRAFT_MAX_ALTITUDE_M > AIRCRAFT_MIN_ALTITUDE_M


def test_aircraft_no_fly_zones_is_list():
    assert isinstance(AIRCRAFT_NO_FLY_ZONES, list)


def test_monte_carlo_params():
    assert MONTE_CARLO_NUM_SEEDS >= 1
    assert MONTE_CARLO_SEED is not None


def test_spacecraft_params():
    assert SPACECRAFT_ALTITUDE_KM > 0
    assert len(SPACECRAFT_TARGETS) >= 1
    assert len(SPACECRAFT_STATION) == 2
    assert SPACECRAFT_SCHEDULE_DAYS >= 1
