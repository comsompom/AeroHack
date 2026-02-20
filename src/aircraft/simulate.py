"""
Aircraft mission simulation and robustness (Monte-Carlo with wind/parameter uncertainty).
"""
import random
from typing import Any, Callable, List, Tuple

from src.aircraft.model import AircraftModel, AircraftState


def simulate_mission(
    plan: dict,
    wind_fn: Callable[[float, float, float], Tuple[float, float]] | None = None,
) -> Tuple[List[AircraftState], float, float, dict]:
    """
    Simulate a planned mission (waypoints + model) with optional custom wind.
    Returns (states, total_time, total_energy, constraint_checks).
    """
    model = plan.get("_model")
    waypoints = plan.get("waypoints", [])
    if not model or len(waypoints) < 2:
        return [], 0.0, 0.0, {"ok": True}
    wind = wind_fn or model.wind_nominal
    initial = AircraftState(waypoints[0][0], waypoints[0][1], 0.0, 0.0, 0.0)
    states, total_time, total_energy = model.simulate_path(waypoints, initial, wind)
    checks = {
        "energy_ok": total_energy <= model.energy_budget,
        "total_time": total_time,
        "total_energy": total_energy,
    }
    return states, total_time, total_energy, checks


def monte_carlo_mission(
    plan: dict,
    num_seeds: int = 10,
    wind_scale: float = 2.0,
    seed: int | None = 42,
) -> dict:
    """
    Run mission under multiple wind perturbations; report success rate and metrics.
    Each seed adds random constant wind (wind_scale m/s).
    """
    if seed is not None:
        random.seed(seed)
    model = plan.get("_model")
    waypoints = plan.get("waypoints", [])
    if not model or len(waypoints) < 2:
        return {"success_rate": 1.0, "runs": 0, "total_times": [], "total_energies": []}

    results = []
    for _ in range(num_seeds):
        v_n = random.uniform(-wind_scale, wind_scale)
        v_e = random.uniform(-wind_scale, wind_scale)

        def wind(_t: float, lat: float, lon: float):
            return (v_n, v_e)

        states, total_time, total_energy, checks = simulate_mission(plan, wind_fn=wind)
        success = checks.get("energy_ok", True) and total_energy <= model.energy_budget
        results.append(
            {"success": success, "total_time": total_time, "total_energy": total_energy}
        )

    successes = sum(1 for r in results if r["success"])
    return {
        "success_rate": successes / len(results) if results else 1.0,
        "runs": len(results),
        "total_times": [r["total_time"] for r in results],
        "total_energies": [r["total_energy"] for r in results],
    }
