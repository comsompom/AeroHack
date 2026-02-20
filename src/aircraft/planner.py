"""
Aircraft mission planner: builds decision variables, constraints, objective; calls core solver.
Returns ordered plan with waypoints and timestamps.
"""
from typing import Any, List, Tuple

from src.core import Constraint, DecisionVariables, Objective, solve
from src.aircraft.model import AircraftModel, AircraftState, correct_waypoint_altitudes
from src.aircraft.constraints import EnduranceConstraint, GeofenceConstraint, ManeuverConstraint, AltitudeConstraint


class AircraftVariables(DecisionVariables):
    """Decision variables: visit waypoints in some order. Plan = dict with 'waypoints' and '_model'."""

    def __init__(self, waypoints: List[Tuple[float, float]], model: AircraftModel):
        self.waypoints = waypoints
        self.model = model

    def initial_plan(self) -> Any:
        if not self.waypoints:
            return {"waypoints": [], "_model": self.model}
        return {
            "waypoints": [self.waypoints[0]],
            "_model": self.model,
        }

    def candidates(self, plan: Any) -> List[int]:
        """Candidate = next waypoint index to visit (any unvisited)."""
        wps = plan.get("waypoints", [])
        n = len(self.waypoints)
        if len(wps) >= n:
            return []
        visited = set(wps)
        return [i for i in range(n) if self.waypoints[i] not in visited]

    def add(self, plan: Any, choice: int) -> Any:
        wps = list(plan.get("waypoints", []))
        wps.append(self.waypoints[choice])
        return {"waypoints": wps, "_model": self.model}

    def is_complete(self, plan: Any) -> bool:
        return len(plan.get("waypoints", [])) >= len(self.waypoints)


class MinTimeObjective(Objective):
    """Minimize total time = maximize -total_time. Needs plan with _model and waypoints."""

    def evaluate(self, plan: Any) -> float:
        from src.aircraft.constraints import _get_model, _get_waypoints
        from src.aircraft.model import AircraftState

        model = _get_model(plan)
        waypoints = _get_waypoints(plan)
        if not model or len(waypoints) < 2:
            return 0.0
        initial = AircraftState(waypoints[0][0], waypoints[0][1], 0.0, 0.0, 0.0)
        _, total_time, _ = model.simulate_path(waypoints, initial, model.wind_nominal)
        return -total_time


def plan_aircraft_mission(
    waypoints: List[Tuple],
    model: AircraftModel,
    no_fly_polygons: List[List[Tuple[float, float]]] | None = None,
) -> dict:
    """
    Plan a route through waypoints minimizing time, respecting constraints.
    Waypoints: (lat, lon) or (lat, lon, alt_m). Altitudes are checked and corrected to model min/max.
    Returns dict with 'waypoints', 'waypoints_with_altitude', 'timestamps', 'total_time', 'total_energy', '_model'.
    """
    # Check and correct waypoint altitudes to aircraft envelope
    waypoints_3d = correct_waypoint_altitudes(
        waypoints,
        model.min_altitude_m,
        model.max_altitude_m,
        model.default_altitude_m,
    )
    waypoints_2d = [(p[0], p[1]) for p in waypoints_3d]

    no_fly = no_fly_polygons or []
    variables = AircraftVariables(waypoints_2d, model)
    constraints: List[Constraint] = [
        EnduranceConstraint(model),
        ManeuverConstraint(model),
        AltitudeConstraint(model),
    ]
    if no_fly:
        constraints.append(GeofenceConstraint(no_fly))
    objective = MinTimeObjective()
    plan = solve(variables, constraints, objective)
    waypoints_out = plan.get("waypoints", [])
    if len(waypoints_out) < 2:
        return {
            "waypoints": waypoints_out,
            "waypoints_with_altitude": [(p[0], p[1], waypoints_3d[i][2] if i < len(waypoints_3d) else model.default_altitude_m) for i, p in enumerate(waypoints_out)],
            "timestamps": [0.0] if waypoints_out else [],
            "total_time": 0.0,
            "total_energy": 0.0,
            "_model": model,
        }
    # Rebuild waypoints_with_altitude in planned order (solver may reorder)
    wp_alt_by_pos = {(p[0], p[1]): p[2] for p in waypoints_3d}
    ordered_3d = [(p[0], p[1], wp_alt_by_pos.get((p[0], p[1]), model.default_altitude_m)) for p in waypoints_out]
    plan["waypoints_with_altitude"] = ordered_3d

    initial = AircraftState(waypoints_out[0][0], waypoints_out[0][1], 0.0, 0.0, 0.0)
    states, total_time, total_energy = model.simulate_path(
        waypoints_out, initial, model.wind_nominal
    )
    timestamps = [s.t for s in states]
    return {
        "waypoints": waypoints_out,
        "waypoints_with_altitude": ordered_3d,
        "timestamps": timestamps,
        "total_time": total_time,
        "total_energy": total_energy,
        "states": states,
        "_model": model,
    }
