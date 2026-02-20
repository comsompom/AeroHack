"""
Run mission from waypoints using aircraft planner; return path with timestamps for replay.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def run_mission(waypoints: list, drone_params: dict) -> dict | None:
    """
    waypoints: [(lat, lon), ...] or [(lat, lon, alt_m), ...]. Altitudes checked and corrected to aircraft envelope.
    drone_params: from DroneConfig.to_aircraft_params() + energy_budget, min_altitude_m, max_altitude_m, default_altitude_m.
    Returns plan with 'waypoints', 'waypoints_with_altitude', 'timestamps', 'states', or None on failure.
    """
    if len(waypoints) < 2:
        return None
    try:
        from src.aircraft.model import AircraftModel
        from src.aircraft.planner import plan_aircraft_mission

        model = AircraftModel(
            cruise_speed_ms=drone_params.get("cruise_speed_ms", 25.0),
            max_turn_rate_degs=drone_params.get("max_turn_rate_degs", 15.0),
            energy_budget=drone_params.get("energy_budget", 2e6),
            consumption_per_second=drone_params.get("consumption_per_second", 80.0),
            min_altitude_m=drone_params.get("min_altitude_m", 0.0),
            max_altitude_m=drone_params.get("max_altitude_m", 4000.0),
            default_altitude_m=drone_params.get("default_altitude_m", 100.0),
        )
        plan = plan_aircraft_mission(waypoints, model)
        return plan
    except Exception:
        return None


def interpolate_position(plan: dict, t: float) -> tuple | None:
    """Return (lat, lon) at time t (seconds). Linear interpolation between states."""
    states = plan.get("states")
    if not states:
        waypoints = plan.get("waypoints", [])
        timestamps = plan.get("timestamps", [])
        if not waypoints or not timestamps or len(waypoints) != len(timestamps):
            return None
        if t <= timestamps[0]:
            return (waypoints[0][0], waypoints[0][1])
        if t >= timestamps[-1]:
            return (waypoints[-1][0], waypoints[-1][1])
        for i in range(len(timestamps) - 1):
            if timestamps[i] <= t <= timestamps[i + 1]:
                a = (t - timestamps[i]) / (timestamps[i + 1] - timestamps[i])
                lat = waypoints[i][0] + a * (waypoints[i + 1][0] - waypoints[i][0])
                lon = waypoints[i][1] + a * (waypoints[i + 1][1] - waypoints[i][1])
                return (lat, lon)
        return None
    if t <= states[0].t:
        return (states[0].lat, states[0].lon)
    if t >= states[-1].t:
        return (states[-1].lat, states[-1].lon)
    for i in range(len(states) - 1):
        if states[i].t <= t <= states[i + 1].t:
            a = (t - states[i].t) / (states[i + 1].t - states[i].t)
            lat = states[i].lat + a * (states[i + 1].lat - states[i].lat)
            lon = states[i].lon + a * (states[i + 1].lon - states[i].lon)
            return (lat, lon)
    return None
