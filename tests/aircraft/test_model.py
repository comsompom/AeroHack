"""Tests for aircraft kinematics and energy model."""
import math
import pytest

from src.aircraft.model import (
    AircraftModel,
    AircraftState,
    bearing_deg,
    distance_m,
    turn_angle_deg,
    waypoint_altitude,
    correct_waypoint_altitudes,
)


def test_bearing_same_point():
    assert bearing_deg(52.0, 4.0, 52.0, 4.0) == 0.0


def test_bearing_north():
    # North: from (50,4) to (51,4)
    b = bearing_deg(50.0, 4.0, 51.0, 4.0)
    assert abs(b - 0.0) < 1.0 or abs(b - 360.0) < 1.0


def test_distance_m():
    d = distance_m(52.0, 4.0, 52.001, 4.0)
    assert d > 0
    assert d < 2000  # ~111km per degree lat, so 0.001 deg ~ 111m


def test_turn_angle_deg():
    assert turn_angle_deg(0, 90) == 90
    assert turn_angle_deg(90, 0) == -90 or abs(turn_angle_deg(90, 0) + 90) < 1


def test_segment_time_no_wind():
    model = AircraftModel(cruise_speed_ms=10.0)
    wind = model.wind_nominal
    t = model.segment_time_s(52.0, 4.0, 52.001, 4.0, wind)
    assert t > 0
    dist = distance_m(52.0, 4.0, 52.001, 4.0)
    assert abs(t - dist / 10.0) < 1.0  # roughly dist/speed


def test_fly_segment():
    model = AircraftModel(cruise_speed_ms=20.0, consumption_per_second=10.0)
    state = AircraftState(lat=52.0, lon=4.0, heading_deg=0.0, t=0.0, energy_used=0.0)
    new_state, dt, de = model.fly_segment(state, 52.01, 4.0, model.wind_nominal)
    assert new_state.lat == 52.01
    assert new_state.lon == 4.0
    assert dt > 0
    assert de > 0
    assert new_state.energy_used == de


def test_simulate_path():
    model = AircraftModel(cruise_speed_ms=25.0)
    waypoints = [(52.0, 4.0), (52.05, 4.0), (52.1, 4.05)]
    initial = AircraftState(52.0, 4.0, 0.0, 0.0, 0.0)
    states, total_time, total_energy = model.simulate_path(waypoints, initial, model.wind_nominal)
    assert len(states) == 3
    assert states[0].lat == 52.0
    assert states[-1].lat == 52.1
    assert total_time > 0
    assert total_energy > 0


def test_waypoint_altitude_with_alt():
    assert waypoint_altitude((52.0, 4.0, 200.0)) == 200.0


def test_waypoint_altitude_without_alt():
    assert waypoint_altitude((52.0, 4.0)) == 100.0


def test_correct_waypoint_altitudes_fills_default():
    out = correct_waypoint_altitudes([(52.0, 4.0), (52.1, 4.0)], 0.0, 4000.0, 150.0)
    assert out == [(52.0, 4.0, 150.0), (52.1, 4.0, 150.0)]


def test_correct_waypoint_altitudes_clamps():
    out = correct_waypoint_altitudes([(52.0, 4.0, 5000.0), (52.1, 4.0, -100.0)], 0.0, 4000.0, 100.0)
    assert out[0][2] == 4000.0
    assert out[1][2] == 0.0


def test_correct_waypoint_altitudes_preserves_valid():
    out = correct_waypoint_altitudes([(52.0, 4.0, 200.0)], 0.0, 4000.0, 100.0)
    assert out == [(52.0, 4.0, 200.0)]
