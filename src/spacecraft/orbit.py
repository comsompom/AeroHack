"""
Simplified two-body orbit and pass/visibility for LEO.
Circular orbit; ground track; visibility = target within max range of sub-satellite point.
"""
import math
from dataclasses import dataclass
from typing import List, Tuple

# Earth radius km; mu for Earth km^3/s^2
EARTH_R_KM = 6371.0
MU_EARTH = 398600.44  # km^3/s^2


def orbit_period_sec(altitude_km: float) -> float:
    """Period of circular orbit at altitude (km). T = 2*pi*sqrt((R+h)^3/mu)."""
    r = EARTH_R_KM + altitude_km
    return 2 * math.pi * math.sqrt(r ** 3 / MU_EARTH)


def position_at_t(altitude_km: float, t: float) -> Tuple[float, float]:
    """
    Sub-satellite point (lat_deg, lon_deg) at time t (seconds from epoch).
    Circular orbit, inclination 51.6 deg (ISS-like); ascending node at 0.
    """
    period = orbit_period_sec(altitude_km)
    # Mean motion
    n = 2 * math.pi / period
    # True anomaly = n*t (circular)
    inc_rad = math.radians(51.6)
    lat = math.asin(math.sin(inc_rad) * math.sin(n * t))
    lon = math.atan2(math.tan(lat), math.cos(inc_rad)) + (n * t) - math.radians(0)
    lat_deg = math.degrees(lat)
    lon_deg = math.degrees(lon)
    while lon_deg > 180:
        lon_deg -= 360
    while lon_deg < -180:
        lon_deg += 360
    return lat_deg, lon_deg


def distance_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Angular distance in degrees (approx)."""
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(min(1.0, math.sqrt(a)))
    return math.degrees(c)


def is_visible(
    sat_lat: float,
    sat_lon: float,
    target_lat: float,
    target_lon: float,
    max_angle_deg: float = 60.0,
) -> bool:
    """True if target is within max_angle_deg of nadir (simplified visibility)."""
    return distance_deg(sat_lat, sat_lon, target_lat, target_lon) <= max_angle_deg


@dataclass
class PassWindow:
    start_t: float
    end_t: float
    lat: float
    lon: float
    id: str


def compute_pass_windows(
    altitude_km: float,
    lat: float,
    lon: float,
    t_start: float,
    t_end: float,
    dt: float = 30.0,
    max_angle_deg: float = 60.0,
) -> List[Tuple[float, float]]:
    """
    Return list of (start_t, end_t) pass windows when (lat, lon) is visible.
    t_start, t_end in seconds; dt sampling step.
    """
    windows = []
    in_pass = False
    pass_start = t_start
    t = t_start
    while t <= t_end:
        sat_lat, sat_lon = position_at_t(altitude_km, t)
        vis = is_visible(sat_lat, sat_lon, lat, lon, max_angle_deg)
        if vis and not in_pass:
            pass_start = t
            in_pass = True
        elif not vis and in_pass:
            windows.append((pass_start, t))
            in_pass = False
        t += dt
    if in_pass:
        windows.append((pass_start, t_end))
    return windows


def observation_windows(
    altitude_km: float,
    targets: List[Tuple[float, float, float]],  # (lat, lon, value)
    t_start: float,
    t_end: float,
    dt: float = 30.0,
) -> List[dict]:
    """
    For each target (lat, lon, value), compute pass windows. Return list of
    { "target_idx": i, "lat": lat, "lon": lon, "value": value, "windows": [(s,e), ...] }.
    """
    result = []
    for i, (tlat, tlon, value) in enumerate(targets):
        wins = compute_pass_windows(altitude_km, tlat, tlon, t_start, t_end, dt)
        result.append({
            "target_idx": i,
            "lat": tlat,
            "lon": tlon,
            "value": value,
            "windows": wins,
        })
    return result
