"""Tests for aircraft simulation and Monte-Carlo."""
import pytest

from src.aircraft.model import AircraftModel
from src.aircraft.planner import plan_aircraft_mission
from src.aircraft.simulate import simulate_mission, monte_carlo_mission


def test_simulate_mission():
    model = AircraftModel()
    waypoints = [(52.0, 4.0), (52.05, 4.0)]
    plan = plan_aircraft_mission(waypoints, model)
    states, total_time, total_energy, checks = simulate_mission(plan)
    assert len(states) == 2
    assert checks["energy_ok"] is True
    assert total_time > 0


def test_monte_carlo_deterministic_seed():
    model = AircraftModel()
    waypoints = [(52.0, 4.0), (52.02, 4.0)]
    plan = plan_aircraft_mission(waypoints, model)
    result = monte_carlo_mission(plan, num_seeds=5, seed=123)
    assert result["runs"] == 5
    assert 0 <= result["success_rate"] <= 1.0
    assert len(result["total_times"]) == 5
