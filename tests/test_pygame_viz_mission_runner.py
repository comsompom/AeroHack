"""Tests for pygame_viz.mission_runner."""
import pytest

from pygame_viz.mission_runner import run_mission, interpolate_position


def test_run_mission_returns_none_for_few_waypoints():
    assert run_mission([], {}) is None
    assert run_mission([(52.0, 4.0)], {}) is None


def test_run_mission_returns_plan_for_two_waypoints():
    waypoints = [(52.0, 4.0, 100.0), (52.01, 4.0, 100.0)]
    params = {"cruise_speed_ms": 25.0, "max_turn_rate_degs": 15.0, "energy_budget": 2e6, "consumption_per_second": 80.0}
    plan = run_mission(waypoints, params)
    assert plan is not None
    assert "waypoints" in plan
    assert "timestamps" in plan
    assert len(plan["waypoints"]) == 2
    assert len(plan["timestamps"]) == 2


def test_interpolate_position_with_states():
    from src.aircraft.model import AircraftState
    plan = {
        "states": [
            AircraftState(52.0, 4.0, 0.0, 0.0, 0.0),
            AircraftState(52.1, 4.0, 0.0, 100.0, 0.0),
        ],
    }
    assert interpolate_position(plan, 0.0) == (52.0, 4.0)
    assert interpolate_position(plan, 100.0) == (52.1, 4.0)
    mid = interpolate_position(plan, 50.0)
    assert 52.0 <= mid[0] <= 52.1
    assert mid[1] == 4.0


def test_interpolate_position_with_waypoints_timestamps():
    plan = {
        "waypoints": [(52.0, 4.0), (52.1, 4.0)],
        "timestamps": [0.0, 200.0],
    }
    assert interpolate_position(plan, 0.0) == (52.0, 4.0)
    assert interpolate_position(plan, 200.0) == (52.1, 4.0)
    mid = interpolate_position(plan, 100.0)
    assert 52.0 <= mid[0] <= 52.1


def test_interpolate_position_returns_none_for_invalid_plan():
    assert interpolate_position({}, 0.0) is None
    assert interpolate_position({"waypoints": [(52, 4)], "timestamps": []}, 0.0) is None
