"""Tests for spacecraft planner."""
import pytest

from src.spacecraft.planner import plan_spacecraft_mission


def test_plan_spacecraft_returns_dict():
    result = plan_spacecraft_mission(
        altitude_km=400.0,
        targets=[(52.5, 4.5, 1.0)],
        schedule_days=1,
    )
    assert "activities" in result
    assert "mission_value" in result
    assert "schedule_days" in result


def test_plan_spacecraft_short_horizon():
    result = plan_spacecraft_mission(
        altitude_km=400.0,
        targets=[(52.5, 4.5, 1.0), (53.0, 5.0, 1.0)],
        station=(52.0, 4.0),
        schedule_days=1,
    )
    assert result["schedule_days"] == 1
    assert isinstance(result["activities"], list)
