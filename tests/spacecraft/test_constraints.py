"""Tests for spacecraft SlewConstraint and PowerConstraint."""
import pytest

from src.spacecraft.constraints import SlewConstraint, PowerConstraint


def test_slew_feasible():
    c = SlewConstraint(min_slew_time_s=60)
    plan = {
        "activities": [
            {"type": "observe", "start_t": 0, "end_t": 100},
            {"type": "downlink", "start_t": 200, "end_t": 300},
        ]
    }
    ok, v = c.check(plan)
    assert ok is True
    assert v == 0.0


def test_slew_infeasible():
    c = SlewConstraint(min_slew_time_s=60)
    plan = {
        "activities": [
            {"type": "observe", "start_t": 0, "end_t": 100},
            {"type": "downlink", "start_t": 130, "end_t": 200},
        ]
    }
    ok, v = c.check(plan)
    assert ok is False
    assert v > 0


def test_power_feasible():
    c = PowerConstraint(orbit_period_s=1000, max_active_per_orbit_s=500)
    plan = {
        "activities": [
            {"type": "observe", "start_t": 0, "end_t": 200},
            {"type": "downlink", "start_t": 300, "end_t": 450},
        ]
    }
    ok, v = c.check(plan)
    assert ok is True
    assert v == 0.0


def test_power_infeasible():
    c = PowerConstraint(orbit_period_s=1000, max_active_per_orbit_s=100)
    plan = {
        "activities": [
            {"type": "observe", "start_t": 0, "end_t": 150},
            {"type": "downlink", "start_t": 200, "end_t": 400},
        ]
    }
    ok, v = c.check(plan)
    assert ok is False
    assert v > 0
