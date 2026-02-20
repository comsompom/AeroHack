"""Tests for webapp routes and data loading."""
import importlib.util
import os
import sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def client():
    # Load app by path so we don't rely on webapp package being on path
    app_path = os.path.join(ROOT, "webapp", "app.py")
    spec = importlib.util.spec_from_file_location("webapp_app", app_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["webapp_app"] = mod
    spec.loader.exec_module(mod)
    app = mod.app
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_index_returns_200(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.content_type


def test_api_aircraft_returns_json(client):
    r = client.get("/api/aircraft")
    assert r.content_type and "json" in r.content_type
    if r.status_code == 200:
        data = r.get_json()
        assert "waypoints" in data or "planned_route" in data or "error" in data
    else:
        assert r.status_code == 404


def test_api_spacecraft_returns_json(client):
    r = client.get("/api/spacecraft")
    assert r.content_type and "json" in r.content_type
    if r.status_code == 200:
        data = r.get_json()
        assert "activities" in data or "mission_value" in data or "error" in data
    else:
        assert r.status_code == 404


def test_api_settings_returns_json(client):
    r = client.get("/api/settings")
    assert r.status_code == 200
    assert r.content_type and "json" in r.content_type
    data = r.get_json()
    assert "aircraft" in data and "spacecraft" in data
    assert "waypoints" in data["aircraft"]
    assert "energy_budget" in data["aircraft"]
    assert "station" in data["spacecraft"]
