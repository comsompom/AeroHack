"""Tests for run_all entry point (aircraft and spacecraft outputs)."""
import os
import sys
import json
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def test_run_aircraft_returns_dict_with_required_keys():
    from src.run_all import run_aircraft
    out = run_aircraft()
    assert isinstance(out, dict)
    assert "waypoints" in out
    assert "planned_route" in out
    assert "flight_path_with_timestamps" in out
    assert "total_time_s" in out
    assert "total_energy" in out
    assert "constraint_checks" in out
    assert "monte_carlo" in out
    assert "module" in out
    assert out["module"] == "Aircraft (UAV / fixed-wing)"
    assert "waypoints_corrected_altitude" in out
    assert "robustness" in out


def test_run_aircraft_constraint_checks_structure():
    from src.run_all import run_aircraft
    out = run_aircraft()
    cc = out["constraint_checks"]
    assert "energy_ok" in cc
    assert "endurance_respected" in cc
    assert "maneuver_limits_ok" in cc
    assert "altitude_within_envelope" in cc


def test_run_aircraft_writes_json():
    from src.run_all import run_aircraft
    run_aircraft()
    path = os.path.join(ROOT, "outputs", "aircraft_mission.json")
    assert os.path.isfile(path)
    with open(path) as f:
        data = json.load(f)
    assert "planned_route" in data
    assert len(data["planned_route"]) == len(data["waypoints_corrected_altitude"])


def test_run_spacecraft_returns_dict_with_required_keys():
    from src.run_all import run_spacecraft
    out = run_spacecraft()
    assert isinstance(out, dict)
    assert "activities" in out
    assert "mission_value" in out
    assert "constraint_checks" in out
    assert "visibility_contact_evidence" in out
    assert "module" in out
    assert out["module"] == "Spacecraft (CubeSat-style LEO)"


def test_run_spacecraft_writes_json_and_csv():
    from src.run_all import run_spacecraft
    run_spacecraft()
    assert os.path.isfile(os.path.join(ROOT, "outputs", "spacecraft_mission.json"))
    assert os.path.isfile(os.path.join(ROOT, "outputs", "spacecraft_schedule.csv"))
