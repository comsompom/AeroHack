"""Tests for aircraft constraints."""
import pytest

from src.aircraft.model import AircraftModel
from src.aircraft.constraints import EnduranceConstraint, GeofenceConstraint, ManeuverConstraint


def test_endurance_feasible():
    model = AircraftModel(energy_budget=1e6, consumption_per_second=10.0)
    plan = {
        "waypoints": [(52.0, 4.0), (52.01, 4.0)],
        "_model": model,
    }
    c = EnduranceConstraint(model)
    ok, v = c.check(plan)
    assert ok is True
    assert v == 0.0


def test_endurance_infeasible():
    model = AircraftModel(energy_budget=1.0, consumption_per_second=1e6)
    plan = {
        "waypoints": [(52.0, 4.0), (52.1, 4.0)],
        "_model": model,
    }
    c = EnduranceConstraint(model)
    ok, v = c.check(plan)
    assert ok is False
    assert v > 0


def test_geofence_outside():
    poly = [(52.5, 4.5), (52.5, 5.0), (53.0, 5.0), (53.0, 4.5)]
    c = GeofenceConstraint([poly])
    plan = {"waypoints": [(52.0, 4.0), (52.1, 4.0)]}
    ok, v = c.check(plan)
    assert ok is True
    assert v == 0.0


def test_geofence_inside():
    # Triangle containing (52.1, 4.1)
    poly = [(52.0, 4.0), (52.2, 4.0), (52.1, 4.2)]
    c = GeofenceConstraint([poly])
    plan = {"waypoints": [(52.0, 4.0), (52.1, 4.1)]}
    ok, v = c.check(plan)
    assert ok is False
    assert v >= 1
