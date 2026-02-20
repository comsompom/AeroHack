"""Tests for spacecraft schedule and science value."""
import pytest

from src.spacecraft.schedule import science_value, build_schedule_output


def test_science_value_empty():
    assert science_value({"activities": []}) == 0.0


def test_science_value_observed_and_downlinked():
    plan = {
        "activities": [
            {"type": "observe", "target_idx": 0},
            {"type": "downlink", "targets_downlinked": [0]},
        ]
    }
    assert science_value(plan) == 1.0


def test_build_schedule_output():
    plan = {"activities": [], "_params": {"schedule_days": 7, "orbit_period_s": 5500}}
    out = build_schedule_output(plan, plan["_params"])
    assert out["schedule_days"] == 7
    assert out["mission_value"] == 0.0
