"""
Real-time weather at (lat, lon). Uses Open-Meteo (no API key).
"""
import urllib.request
import json

BASE = "https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"


def get_weather(lat: float, lon: float) -> dict | None:
    """
    Return current weather at (lat, lon). Keys: temperature (C), windspeed (km/h), winddirection (deg), weathercode.
    Or None on failure.
    """
    url = BASE.format(lat=lat, lon=lon)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DroneMission-Viz/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        return data.get("current_weather")
    except Exception:
        return None


def get_weather_for_waypoints(waypoints: list) -> list:
    """waypoints = [(lat, lon), ...]. Returns list of weather dicts (or None)."""
    return [get_weather(wp[0], wp[1]) for wp in waypoints]
