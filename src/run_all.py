"""
Single entry point: run aircraft and spacecraft mission planning end-to-end.
Saves plans and metrics to outputs/.
"""
import json
import os
import sys

# Add project root so "src" imports work
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def run_aircraft():
    """Plan and simulate aircraft mission; save to outputs/."""
    from src.aircraft.model import AircraftModel
    from src.aircraft.planner import plan_aircraft_mission
    from src.aircraft.simulate import simulate_mission, monte_carlo_mission

    waypoints = [
        (52.0, 4.0),
        (52.05, 4.02),
        (52.1, 4.0),
        (52.08, 3.98),
    ]
    model = AircraftModel(
        cruise_speed_ms=25.0,
        max_turn_rate_degs=15.0,
        energy_budget=2e6,
        consumption_per_second=80.0,
    )
    plan = plan_aircraft_mission(waypoints, model)
    states, total_time, total_energy, checks = simulate_mission(plan)
    mc = monte_carlo_mission(plan, num_seeds=10, seed=42)

    out = {
        "waypoints": waypoints,
        "planned_route": [
            {"lat": p[0], "lon": p[1], "t": plan["timestamps"][i]}
            for i, p in enumerate(plan["waypoints"])
        ],
        "total_time_s": plan["total_time"],
        "total_energy": plan["total_energy"],
        "constraint_checks": {
            "energy_ok": checks["energy_ok"],
        },
        "monte_carlo": {
            "success_rate": mc["success_rate"],
            "runs": mc["runs"],
        },
    }
    os.makedirs(os.path.join(ROOT, "outputs"), exist_ok=True)
    path = os.path.join(ROOT, "outputs", "aircraft_mission.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Aircraft mission saved to {path}")
    return out


def run_spacecraft():
    """Plan 7-day spacecraft mission; save to outputs/."""
    from src.spacecraft.planner import plan_spacecraft_mission

    result = plan_spacecraft_mission(
        altitude_km=400.0,
        targets=[(52.5, 4.5, 1.0), (53.0, 5.0, 1.0), (51.0, 3.0, 1.0)],
        station=(52.0, 4.0),
        schedule_days=7,
    )
    out = {
        "schedule_days": result["schedule_days"],
        "activities": result["activities"],
        "mission_value": result["mission_value"],
        "orbit_period_s": result.get("orbit_period_s"),
    }
    os.makedirs(os.path.join(ROOT, "outputs"), exist_ok=True)
    path = os.path.join(ROOT, "outputs", "spacecraft_mission.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Spacecraft mission saved to {path}")
    return out


def main():
    print("Running aircraft mission...")
    run_aircraft()
    print("Running spacecraft mission...")
    run_spacecraft()
    print("Done. Check outputs/")


if __name__ == "__main__":
    main()
