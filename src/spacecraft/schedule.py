"""
7-day schedule builder and science value.
Value = 1 per target that was observed and later downlinked.
"""
from typing import Any, List


def science_value(plan: Any) -> float:
    """
    Compute science value: each target that has both an observation and a downlink
    (after the observation) counts as 1.
    """
    activities = plan.get("activities", [])
    observed = set()
    downlinked = set()
    for a in activities:
        if a.get("type") == "observe" and "target_idx" in a:
            observed.add(a["target_idx"])
        if a.get("type") == "downlink":
            for idx in a.get("targets_downlinked", []):
                if idx in observed:
                    downlinked.add(idx)
    return float(len(downlinked))


def build_schedule_output(plan: Any, params: dict) -> dict:
    """Build output dict: time-ordered schedule, visibility evidence, metrics."""
    activities = sorted(plan.get("activities", []), key=lambda a: a["start_t"])
    return {
        "activities": activities,
        "mission_value": science_value(plan),
        "orbit_period_s": params.get("orbit_period_s"),
        "schedule_days": params.get("schedule_days", 7),
    }
