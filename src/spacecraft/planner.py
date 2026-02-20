"""
Spacecraft mission planner: 7-day schedule of observations + downlinks using core solver.
"""
from typing import Any, List

from src.core import Constraint, DecisionVariables, Objective, solve
from src.spacecraft.orbit import (
    orbit_period_sec,
    observation_windows,
    compute_pass_windows,
)
from src.spacecraft.constraints import PowerConstraint, SlewConstraint
from src.spacecraft.schedule import science_value, build_schedule_output


def _generate_opportunities(
    altitude_km: float,
    targets: List[tuple],
    station_lat: float,
    station_lon: float,
    t_start: float,
    t_end: float,
) -> List[dict]:
    """Build list of possible activities (observe or downlink) with time windows."""
    period = orbit_period_sec(altitude_km)
    obs = observation_windows(altitude_km, targets, t_start, t_end)
    opportunities = []
    for o in obs:
        for start_t, end_t in o["windows"]:
            if end_t - start_t < 30:
                continue
            opportunities.append({
                "type": "observe",
                "start_t": start_t,
                "end_t": end_t,
                "target_idx": o["target_idx"],
                "value": o["value"],
            })
    down_windows = compute_pass_windows(altitude_km, station_lat, station_lon, t_start, t_end)
    for start_t, end_t in down_windows:
        if end_t - start_t < 60:
            continue
        opportunities.append({
            "type": "downlink",
            "start_t": start_t,
            "end_t": end_t,
            "targets_downlinked": [],  # filled when we know what was observed
        })
    return sorted(opportunities, key=lambda x: x["start_t"])


class SpacecraftVariables(DecisionVariables):
    """Plan = list of activities. Candidates = opportunities that don't overlap and are after last."""

    def __init__(self, opportunities: List[dict], params: dict):
        self.opportunities = opportunities
        self.params = params

    def initial_plan(self) -> Any:
        return {"activities": [], "_params": self.params, "_chosen": set()}

    def candidates(self, plan: Any) -> List[int]:
        activities = plan.get("activities", [])
        chosen = plan.get("_chosen") or set()
        last_end = -1.0
        for a in activities:
            last_end = max(last_end, a["end_t"])
        min_gap = self.params.get("min_slew_s", 60)
        return [
            i for i, opp in enumerate(self.opportunities)
            if i not in chosen and opp["start_t"] >= last_end + min_gap
        ]

    def add(self, plan: Any, choice: int) -> Any:
        activities = list(plan.get("activities", []))
        chosen = set(plan.get("_chosen") or set())
        opp = self.opportunities[choice].copy()
        if opp["type"] == "observe":
            activities.append(opp)
        else:
            observed = {a["target_idx"] for a in activities if a.get("type") == "observe"}
            opp["targets_downlinked"] = list(observed)
            activities.append(opp)
        chosen.add(choice)
        return {"activities": activities, "_params": self.params, "_chosen": chosen}

    def is_complete(self, plan: Any) -> bool:
        schedule_days = self.params.get("schedule_days", 7) * 86400
        activities = plan.get("activities", [])
        if not activities:
            return False
        return activities[-1]["end_t"] >= schedule_days or len(activities) >= len(self.opportunities)


class ScienceValueObjective(Objective):
    """Maximize science value (targets observed and downlinked)."""

    def __init__(self, plan_ref: Any = None):
        self._plan_ref = plan_ref

    def evaluate(self, plan: Any) -> float:
        return science_value(plan)


def plan_spacecraft_mission(
    altitude_km: float = 400.0,
    targets: List[tuple] | None = None,
    station: tuple = (52.0, 4.0),
    schedule_days: int = 7,
    min_slew_s: float = 60.0,
    max_active_per_orbit_s: float = 600.0,
) -> dict:
    """
    Plan 7-day mission: observations + downlinks. Returns schedule dict.
    targets: list of (lat, lon, value) per target.
    """
    targets = targets or [(52.5, 4.5, 1.0), (53.0, 5.0, 1.0)]
    t_start = 0.0
    t_end = schedule_days * 86400
    period = orbit_period_sec(altitude_km)
    params = {
        "altitude_km": altitude_km,
        "orbit_period_s": period,
        "schedule_days": schedule_days,
        "min_slew_s": min_slew_s,
    }
    opportunities = _generate_opportunities(
        altitude_km, targets, station[0], station[1], t_start, t_end
    )
    if not opportunities:
        return build_schedule_output({"activities": [], "_params": params}, params)

    variables = SpacecraftVariables(opportunities, params)
    constraints: List[Constraint] = [
        SlewConstraint(min_slew_time_s=min_slew_s),
        PowerConstraint(orbit_period_s=period, max_active_per_orbit_s=max_active_per_orbit_s),
    ]
    objective = ScienceValueObjective()
    plan = solve(variables, constraints, objective, max_steps=500)
    return build_schedule_output(plan, params)
