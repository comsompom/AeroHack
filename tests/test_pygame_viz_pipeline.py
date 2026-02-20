"""Tests for pygame_viz.pipeline."""
import os
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_run_aircraft_to_outputs_returns_none_for_few_waypoints():
    from pygame_viz.pipeline import run_aircraft_to_outputs
    assert run_aircraft_to_outputs([(52.0, 4.0)], {}, save=False) is None


def test_run_aircraft_to_outputs_returns_full_structure():
    from pygame_viz.pipeline import run_aircraft_to_outputs
    waypoints = [(52.0, 4.0, 100.0), (52.01, 4.0, 100.0)]
    params = {"cruise_speed_ms": 25.0, "max_turn_rate_degs": 15.0, "energy_budget": 2e6, "consumption_per_second": 80.0}
    out = run_aircraft_to_outputs(waypoints, params, save=False)
    assert out is not None
    assert "planned_route" in out
    assert "constraint_checks" in out
    assert "monte_carlo" in out
    assert "module" in out
    assert "waypoints_corrected_altitude" in out
    assert "robustness" in out


def test_run_aircraft_to_outputs_save_writes_json(tmp_path, monkeypatch):
    from pygame_viz import pipeline
    monkeypatch.setattr(pipeline, "ROOT", str(tmp_path))
    waypoints = [(52.0, 4.0, 100.0), (52.01, 4.0, 100.0)]
    params = {"cruise_speed_ms": 25.0, "max_turn_rate_degs": 15.0, "energy_budget": 2e6, "consumption_per_second": 80.0}
    out = pipeline.run_aircraft_to_outputs(waypoints, params, save=True)
    assert out is not None
    path = tmp_path / "outputs" / "aircraft_mission.json"
    assert path.exists()


def test_run_spacecraft_to_outputs_returns_structure():
    from pygame_viz.pipeline import run_spacecraft_to_outputs
    targets = [(52.5, 4.5, 1.0), (53.0, 5.0, 1.0)]
    out = run_spacecraft_to_outputs(targets, station=(52.0, 4.0), schedule_days=7, save=False)
    assert out is not None
    assert "activities" in out
    assert "mission_value" in out
    assert "constraint_checks" in out


def test_run_full_pipeline():
    from pygame_viz.pipeline import run_full_pipeline
    waypoints = [(52.0, 4.0, 100.0), (52.01, 4.0, 100.0)]
    params = {"cruise_speed_ms": 25.0, "max_turn_rate_degs": 15.0, "energy_budget": 2e6, "consumption_per_second": 80.0}
    ac, sc = run_full_pipeline(waypoints, params, spacecraft_targets=[(52.5, 4.5, 1.0), (53.0, 5.0, 1.0)], station=(52.0, 4.0))
    assert ac is not None
    assert sc is not None
