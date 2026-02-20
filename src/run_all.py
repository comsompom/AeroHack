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
    """Plan and simulate aircraft mission; save to outputs/ (JSON + plot)."""
    from src.aircraft.model import AircraftModel
    from src.aircraft.planner import plan_aircraft_mission
    from src.aircraft.simulate import simulate_mission, monte_carlo_mission
    from src.aircraft.constraints import EnduranceConstraint, ManeuverConstraint, GeofenceConstraint

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

    # Full constraint check summary (plan/description requirement)
    endurance_ok, endurance_v = EnduranceConstraint(model).check(plan)
    maneuver_ok, maneuver_v = ManeuverConstraint(model).check(plan)
    geofence_ok, geofence_v = True, 0.0  # no no-fly zones in this run
    constraint_checks = {
        "energy_ok": checks["energy_ok"],
        "endurance_respected": endurance_ok,
        "maneuver_limits_ok": maneuver_ok,
        "geofence_violations": int(geofence_v) if geofence_ok else 1,
    }

    out = {
        "waypoints": waypoints,
        "planned_route": [
            {"lat": p[0], "lon": p[1], "t": plan["timestamps"][i]}
            for i, p in enumerate(plan["waypoints"])
        ],
        "total_time_s": plan["total_time"],
        "total_energy": plan["total_energy"],
        "constraint_checks": constraint_checks,
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

    # At least one plot (path and/or state vs time) — plan §3.3, description
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6))
        lats = [p[0] for p in plan["waypoints"]]
        lons = [p[1] for p in plan["waypoints"]]
        ax1.plot(lons, lats, "b-o")
        ax1.set_xlabel("Lon (deg)")
        ax1.set_ylabel("Lat (deg)")
        ax1.set_title("Planned flight path")
        ax1.grid(True)
        times = plan["timestamps"]
        ax2.plot(times, lats, "b-", label="Lat")
        ax2.plot(times, lons, "g-", label="Lon")
        ax2.set_xlabel("Time (s)")
        ax2.set_ylabel("Position (deg)")
        ax2.set_title("State vs time")
        ax2.legend()
        ax2.grid(True)
        plt.tight_layout()
        plot_path = os.path.join(ROOT, "outputs", "aircraft_mission_plot.png")
        plt.savefig(plot_path)
        plt.close()
        print(f"Aircraft plot saved to {plot_path}")
    except Exception as e:
        print(f"Warning: could not save aircraft plot: {e}")

    return out


def run_spacecraft():
    """Plan 7-day spacecraft mission; save to outputs/ (JSON + CSV table)."""
    from src.spacecraft.planner import plan_spacecraft_mission
    from src.spacecraft.constraints import SlewConstraint, PowerConstraint

    result = plan_spacecraft_mission(
        altitude_km=400.0,
        targets=[(52.5, 4.5, 1.0), (53.0, 5.0, 1.0), (51.0, 3.0, 1.0)],
        station=(52.0, 4.0),
        schedule_days=7,
    )
    # Constraint check summary (plan/description)
    plan_dict = {
        "activities": result["activities"],
        "_params": {"orbit_period_s": result.get("orbit_period_s") or 5500},
    }
    slew_ok, slew_v = SlewConstraint(min_slew_time_s=60).check(plan_dict)
    power_ok, power_v = PowerConstraint(
        orbit_period_s=result.get("orbit_period_s") or 5500,
        max_active_per_orbit_s=600,
    ).check(plan_dict)
    visibility_evidence = [
        {"type": a["type"], "start_t": a["start_t"], "end_t": a["end_t"], "target_idx": a.get("target_idx")}
        for a in result["activities"]
    ]

    out = {
        "schedule_days": result["schedule_days"],
        "activities": result["activities"],
        "mission_value": result["mission_value"],
        "orbit_period_s": result.get("orbit_period_s"),
        "constraint_checks": {
            "slew_feasible": slew_ok,
            "power_duty_ok": power_ok,
        },
        "visibility_contact_evidence": visibility_evidence,
    }
    os.makedirs(os.path.join(ROOT, "outputs"), exist_ok=True)
    path = os.path.join(ROOT, "outputs", "spacecraft_mission.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Spacecraft mission saved to {path}")

    # At least one plot or table — description: "at least one plot or table"
    csv_path = os.path.join(ROOT, "outputs", "spacecraft_schedule.csv")
    with open(csv_path, "w") as f:
        f.write("type,start_t,end_t,duration_s,target_idx\n")
        for a in result["activities"]:
            dur = a["end_t"] - a["start_t"]
            tidx = a.get("target_idx", "")
            f.write(f"{a['type']},{a['start_t']},{a['end_t']},{dur},{tidx}\n")
    print(f"Spacecraft schedule table saved to {csv_path}")

    return out


def main():
    print("Running aircraft mission...")
    run_aircraft()
    print("Running spacecraft mission...")
    run_spacecraft()
    print("Done. Check outputs/")


if __name__ == "__main__":
    main()
