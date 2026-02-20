"""Tests for pygame_viz.config."""
import pytest

from pygame_viz.config import DRONE_TYPES, PLANE_MODELS_WAR, PLANE_MODELS_CIVIL, DroneConfig


def test_drone_types_non_empty():
    assert len(DRONE_TYPES) >= 4
    assert "UAV" in DRONE_TYPES
    assert "Plane" in DRONE_TYPES


def test_plane_models_structure():
    for name, weight, size in PLANE_MODELS_WAR:
        assert isinstance(name, str)
        assert weight > 0
        assert size > 0
    for name, weight, size in PLANE_MODELS_CIVIL:
        assert isinstance(name, str)
        assert weight > 0
        assert size > 0


def test_drone_config_to_aircraft_params_quadcopter():
    cfg = DroneConfig("Quadcopter", 10.0, 2.0, "Custom", False)
    p = cfg.to_aircraft_params()
    assert p["cruise_speed_ms"] == 15.0
    assert p["max_turn_rate_degs"] == 90.0


def test_drone_config_to_aircraft_params_plane():
    cfg = DroneConfig("Plane", 100.0, 10.0, "Custom", True)
    p = cfg.to_aircraft_params()
    assert p["cruise_speed_ms"] == 25.0
    assert p["max_turn_rate_degs"] == 15.0


def test_drone_config_to_aircraft_params_uav():
    cfg = DroneConfig("UAV", 5.0, 1.0, "Custom", False)
    p = cfg.to_aircraft_params()
    assert p["cruise_speed_ms"] == 20.0
    assert p["max_turn_rate_degs"] == 20.0
