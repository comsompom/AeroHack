"""Tests for aircraft planner."""
import pytest

from src.aircraft.model import AircraftModel
from src.aircraft.planner import plan_aircraft_mission


def test_plan_empty_waypoints():
    model = AircraftModel()
    result = plan_aircraft_mission([], model)
    assert result["waypoints"] == []
    assert result["total_time"] == 0.0


def test_plan_single_waypoint():
    model = AircraftModel()
    result = plan_aircraft_mission([(52.0, 4.0)], model)
    assert len(result["waypoints"]) == 1
    assert result["timestamps"] == [0.0]


def test_plan_two_waypoints():
    model = AircraftModel(cruise_speed_ms=20.0)
    waypoints = [(52.0, 4.0), (52.05, 4.0)]
    result = plan_aircraft_mission(waypoints, model)
    assert len(result["waypoints"]) == 2
    assert result["total_time"] > 0
    assert result["total_energy"] > 0
    assert len(result["timestamps"]) == 2


def test_plan_three_waypoints():
    model = AircraftModel(cruise_speed_ms=25.0)
    waypoints = [(52.0, 4.0), (52.1, 4.0), (52.1, 4.1)]
    result = plan_aircraft_mission(waypoints, model)
    assert len(result["waypoints"]) == 3
    assert result["total_time"] > 0
