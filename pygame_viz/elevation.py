"""
Elevation at (lat, lon). Uses Open-Elevation API by default (no key, global coverage).
ArduPilot terrain from https://terrain.ardupilot.org/continentsdat3/ (e.g. Africa.zip,
Eurasia.zip, North_America.zip) provides SRTM-based grids; use those for offline
or higher-resolution elevation by adding a local loader that reads unpacked .dat blocks.
"""
import urllib.request
import json

OPEN_ELEVATION_URL = "https://api.open-elevation.com/api/v1/lookup?locations={lat},{lon}"


def get_elevation(lat: float, lon: float) -> float | None:
    """
    Return elevation in meters (MSL) at (lat, lon), or None on failure.
    Uses Open-Elevation API (no key required).
    """
    url = OPEN_ELEVATION_URL.format(lat=lat, lon=lon)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DroneMission-Viz/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        results = data.get("results", [])
        if results:
            return float(results[0].get("elevation", 0))
    except Exception:
        pass
    return None


def get_elevations_bulk(points: list) -> list:
    """points = [(lat, lon), ...]. Returns [elev_m or None, ...]."""
    out = []
    for lat, lon in points:
        out.append(get_elevation(lat, lon))
    return out
