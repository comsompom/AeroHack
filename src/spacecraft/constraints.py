"""
Spacecraft constraints: slew rate, power/duty cycle.
All implement the core Constraint interface.
"""
from typing import Any, List, Tuple

from src.core.constraints import Constraint


def _get_activities(plan: Any) -> List[dict]:
    """Plan has 'activities': list of { type, start_t, end_t, target_idx? }."""
    if not isinstance(plan, dict):
        return []
    return list(plan.get("activities", []))


def _get_params(plan: Any) -> dict:
    return plan.get("_params", {})


class SlewConstraint(Constraint):
    """Minimum time between pointing changes (simplified slew rate)."""

    def __init__(self, min_slew_time_s: float = 60.0):
        self.min_slew_time_s = min_slew_time_s

    def check(self, plan: Any) -> Tuple[bool, float]:
        activities = _get_activities(plan)
        if len(activities) < 2:
            return True, 0.0
        violation = 0.0
        for i in range(1, len(activities)):
            gap = activities[i]["start_t"] - activities[i - 1]["end_t"]
            if gap < self.min_slew_time_s and gap >= 0:
                violation += self.min_slew_time_s - gap
        return (violation == 0.0, violation)


class PowerConstraint(Constraint):
    """Duty cycle: total active time per orbit must not exceed max_ops_time_s per orbit."""

    def __init__(self, orbit_period_s: float, max_active_per_orbit_s: float = 600.0):
        self.orbit_period_s = orbit_period_s
        self.max_active_per_orbit_s = max_active_per_orbit_s

    def check(self, plan: Any) -> Tuple[bool, float]:
        activities = _get_activities(plan)
        if not activities:
            return True, 0.0
        orbit_active = {}
        for a in activities:
            start, end = a["start_t"], a["end_t"]
            orbit_id = int(start // self.orbit_period_s)
            orbit_active[orbit_id] = orbit_active.get(orbit_id, 0) + (end - start)
        violation = 0.0
        for oid, active in orbit_active.items():
            if active > self.max_active_per_orbit_s:
                violation += active - self.max_active_per_orbit_s
        return (violation == 0.0, violation)
