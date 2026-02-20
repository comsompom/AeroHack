"""
Aircraft constraints: endurance, maneuver limits, geofencing.
All implement the core Constraint interface.
"""
from typing import Any, List, Tuple

from src.core.constraints import Constraint
from src.aircraft.model import AircraftModel, AircraftState, distance_m, turn_angle_deg


def _get_waypoints(plan: Any) -> List[Tuple[float, float]]:
    """Extract list of (lat, lon) from aircraft plan. Plan is dict with 'waypoints' key."""
    if not isinstance(plan, dict):
        return []
    return list(plan.get("waypoints", []))


def _get_model(plan: Any) -> AircraftModel:
    """Extract AircraftModel from plan (planner attaches it)."""
    return plan.get("_model")


def _simulate_plan(plan: Any) -> Tuple[float, float, List[float], List[float], bool]:
    """
    Simulate plan with model's wind_nominal.
    Return (total_time, total_energy, turn_angles, segment_times, ok).
    If model missing, return (0, 0, [], [], True).
    """
    model = _get_model(plan)
    waypoints = _get_waypoints(plan)
    if not model or len(waypoints) < 2:
        return 0.0, 0.0, [], [], True
    initial = AircraftState(
        waypoints[0][0], waypoints[0][1], 0.0, 0.0, 0.0
    )
    states, total_time, total_energy = model.simulate_path(
        waypoints, initial, model.wind_nominal
    )
    turn_angles = []
    segment_times = []
    for i in range(1, len(states)):
        turn = abs(
            turn_angle_deg(states[i - 1].heading_deg, states[i].heading_deg)
        )
        turn_angles.append(turn)
        segment_times.append(states[i].t - states[i - 1].t)
    return total_time, total_energy, turn_angles, segment_times, True


class EnduranceConstraint(Constraint):
    """Total energy consumption must not exceed budget."""

    def __init__(self, model: AircraftModel):
        self.model = model

    def check(self, plan: Any) -> Tuple[bool, float]:
        model = _get_model(plan)
        waypoints = _get_waypoints(plan)
        if not model or len(waypoints) < 2:
            return True, 0.0
        _, total_energy, _, _, _ = _simulate_plan(plan)
        if total_energy <= self.model.energy_budget:
            return True, 0.0
        return False, total_energy - self.model.energy_budget


class ManeuverConstraint(Constraint):
    """Turn rate (deg/s) per segment must be within limit."""

    def __init__(self, model: AircraftModel):
        self.model = model

    def check(self, plan: Any) -> Tuple[bool, float]:
        model = _get_model(plan)
        waypoints = _get_waypoints(plan)
        if not model or len(waypoints) < 2:
            return True, 0.0
        _, _, turn_angles, segment_times, _ = _simulate_plan(plan)
        max_rate = model.max_turn_rate_degs
        for ta, dt in zip(turn_angles, segment_times):
            if dt < 1e-9:
                continue
            rate = ta / dt
            if rate > max_rate:
                return False, rate - max_rate
        return True, 0.0


def _point_in_polygon(lat: float, lon: float, polygon: List[Tuple[float, float]]) -> bool:
    """Ray-casting: point (lat,lon) inside polygon (list of (lat,lon))."""
    n = len(polygon)
    if n < 3:
        return False
    inside = False
    j = n - 1
    for i in range(n):
        yi, xi = polygon[i][0], polygon[i][1]  # lat, lon
        yj, xj = polygon[j][0], polygon[j][1]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


class GeofenceConstraint(Constraint):
    """Path must not enter no-fly polygon(s)."""

    def __init__(self, no_fly_polygons: List[List[Tuple[float, float]]]):
        self.no_fly_polygons = no_fly_polygons

    def check(self, plan: Any) -> Tuple[bool, float]:
        waypoints = _get_waypoints(plan)
        if not waypoints:
            return True, 0.0
        violations = 0
        for lat, lon in waypoints:
            for poly in self.no_fly_polygons:
                if _point_in_polygon(lat, lon, poly):
                    violations += 1
        if violations > 0:
            return False, float(violations)
        return True, 0.0
