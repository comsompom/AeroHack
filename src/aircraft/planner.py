"""
Aircraft mission planner: builds decision variables, constraints, objective; calls core solver.
Returns ordered plan with waypoints and timestamps.
"""
from typing import Any, List, Tuple

from src.core import Constraint, DecisionVariables, Objective, solve
from src.aircraft.model import AircraftModel, AircraftState
from src.aircraft.constraints import EnduranceConstraint, GeofenceConstraint, ManeuverConstraint


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
    waypoints: List[Tuple[float, float]],
    model: AircraftModel,
    no_fly_polygons: List[List[Tuple[float, float]]] | None = None,
) -> dict:
    """
    Plan a route through waypoints minimizing time, respecting constraints.
    Returns dict with 'waypoints', 'timestamps', 'total_time', 'total_energy', '_model'.
    """
    no_fly = no_fly_polygons or []
    variables = AircraftVariables(waypoints, model)
    constraints: List[Constraint] = [
        EnduranceConstraint(model),
        ManeuverConstraint(model),
    ]
    if no_fly:
        constraints.append(GeofenceConstraint(no_fly))
    objective = MinTimeObjective()
    plan = solve(variables, constraints, objective)
    waypoints = plan.get("waypoints", [])
    if len(waypoints) < 2:
        return {
            "waypoints": waypoints,
            "timestamps": [0.0] if waypoints else [],
            "total_time": 0.0,
            "total_energy": 0.0,
            "_model": model,
        }
    initial = AircraftState(waypoints[0][0], waypoints[0][1], 0.0, 0.0, 0.0)
    states, total_time, total_energy = model.simulate_path(
        waypoints, initial, model.wind_nominal
    )
    timestamps = [s.t for s in states]
    return {
        "waypoints": waypoints,
        "timestamps": timestamps,
        "total_time": total_time,
        "total_energy": total_energy,
        "states": states,
        "_model": model,
    }
