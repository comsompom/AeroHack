"""
Run mission from waypoints using aircraft planner; return path with timestamps for replay.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def run_mission(waypoints: list, drone_params: dict, use_user_order: bool = False) -> dict | None:
    """
    waypoints: [(lat, lon), ...] or [(lat, lon, alt_m), ...]. Altitudes checked and corrected to aircraft envelope.
    drone_params: from DroneConfig.to_aircraft_params() + energy_budget, min_altitude_m, max_altitude_m, default_altitude_m.
    use_user_order: if True, fly waypoints in the order given (no solver); ensures full path for visualization.
    Returns plan with 'waypoints', 'waypoints_with_altitude', 'timestamps', 'states', or None on failure.
    """
    if len(waypoints) < 2:
        return None
    try:
        from src.aircraft.model import AircraftModel, correct_waypoint_altitudes
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
        if use_user_order:
            # Fly all waypoints in user order (no solver) so viz always shows full route
            waypoints_3d = correct_waypoint_altitudes(
                waypoints,
                model.min_altitude_m,
                model.max_altitude_m,
                model.default_altitude_m,
            )
            waypoints_2d = [(p[0], p[1]) for p in waypoints_3d]
            from src.aircraft.model import AircraftState
            initial = AircraftState(waypoints_2d[0][0], waypoints_2d[0][1], 0.0, 0.0, 0.0)
            states, total_time, total_energy, _ = model.simulate_path(
                waypoints_2d, initial, model.wind_nominal
            )
            timestamps = [float(s.t) for s in states]
            return {
                "waypoints": waypoints_2d,
                "waypoints_with_altitude": waypoints_3d,
                "timestamps": timestamps,
                "total_time": total_time,
                "total_energy": total_energy,
                "states": states,
                "_model": model,
            }
        plan = plan_aircraft_mission(waypoints, model)
        return plan
    except Exception:
        return None


def interpolate_position(plan: dict, t: float) -> tuple | None:
    """Return (lat, lon) at time t (seconds). Linear interpolation; uses waypoints+timestamps (robust)."""
    waypoints = plan.get("waypoints", [])
    timestamps = plan.get("timestamps", [])
    if not waypoints or not timestamps or len(waypoints) != len(timestamps):
        return None
    t = float(t)
    timestamps = [float(ts) for ts in timestamps]
    if t <= timestamps[0]:
        return (float(waypoints[0][0]), float(waypoints[0][1]))
    if t >= timestamps[-1]:
        return (float(waypoints[-1][0]), float(waypoints[-1][1]))
    for i in range(len(timestamps) - 1):
        t0, t1 = timestamps[i], timestamps[i + 1]
        if t0 <= t <= t1:
            dt = t1 - t0
            if dt <= 0:
                return (float(waypoints[i + 1][0]), float(waypoints[i + 1][1]))
            a = (t - t0) / dt
            lat = waypoints[i][0] + a * (waypoints[i + 1][0] - waypoints[i][0])
            lon = waypoints[i][1] + a * (waypoints[i + 1][1] - waypoints[i][1])
            return (float(lat), float(lon))
    return None


def interpolate_energy(plan: dict, t: float) -> tuple[float, float] | None:
    """Return (energy_used, energy_budget) at time t. Returns None if plan has no states or model."""
    states = plan.get("states")
    model = plan.get("_model")
    if not states or not model:
        return None
    budget = getattr(model, "energy_budget", None)
    if budget is None:
        return None
    t = float(t)
    if t <= states[0].t:
        return (float(states[0].energy_used), float(budget))
    if t >= states[-1].t:
        return (float(states[-1].energy_used), float(budget))
    for i in range(len(states) - 1):
        t0, t1 = states[i].t, states[i + 1].t
        if t0 <= t <= t1:
            dt = t1 - t0
            if dt <= 0:
                return (float(states[i + 1].energy_used), float(budget))
            a = (t - t0) / dt
            e = states[i].energy_used + a * (states[i + 1].energy_used - states[i].energy_used)
            return (float(e), float(budget))
    return None
