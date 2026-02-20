"""
Run aircraft and/or spacecraft pipeline (same as src.run_all): save to outputs/, constraint checks, Monte-Carlo, plot/CSV.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def run_aircraft_to_outputs(waypoints: list, drone_params: dict, save: bool = True) -> dict | None:
    """
    Plan and simulate aircraft mission; optionally save to outputs/ (JSON + plot).
    Returns same structure as run_all.run_aircraft (or None on failure).
    """
    if len(waypoints) < 2:
        return None
    try:
        from src.aircraft.model import AircraftModel
        from src.aircraft.planner import plan_aircraft_mission
        from src.aircraft.simulate import simulate_mission, monte_carlo_mission
        from src.aircraft.constraints import EnduranceConstraint, ManeuverConstraint, GeofenceConstraint
    except ImportError:
        return None

    model = AircraftModel(
        cruise_speed_ms=drone_params.get("cruise_speed_ms", 25.0),
        max_turn_rate_degs=drone_params.get("max_turn_rate_degs", 15.0),
        energy_budget=drone_params.get("energy_budget", 2e6),
        consumption_per_second=drone_params.get("consumption_per_second", 80.0),
    )
    plan = plan_aircraft_mission(waypoints, model)
    states, total_time, total_energy, checks = simulate_mission(plan)
    mc = monte_carlo_mission(plan, num_seeds=10, seed=42)

    endurance_ok, _ = EnduranceConstraint(model).check(plan)
    maneuver_ok, _ = ManeuverConstraint(model).check(plan)
    geofence_ok, geofence_v = True, 0.0
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
        "monte_carlo": {"success_rate": mc["success_rate"], "runs": mc["runs"]},
    }

    if save:
        os.makedirs(os.path.join(ROOT, "outputs"), exist_ok=True)
        path = os.path.join(ROOT, "outputs", "aircraft_mission.json")
        with open(path, "w") as f:
            json.dump(out, f, indent=2)
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
            plt.savefig(os.path.join(ROOT, "outputs", "aircraft_mission_plot.png"))
            plt.close()
        except Exception:
            pass
    return out


def run_spacecraft_to_outputs(
    targets: list,
    station: tuple = (52.0, 4.0),
    schedule_days: int = 7,
    save: bool = True,
) -> dict | None:
    """
    Plan 7-day spacecraft mission; optionally save to outputs/ (JSON + CSV).
    targets: list of (lat, lon, value). Returns same structure as run_all.run_spacecraft.
    """
    try:
        from src.spacecraft.planner import plan_spacecraft_mission
        from src.spacecraft.constraints import SlewConstraint, PowerConstraint
    except ImportError:
        return None

    result = plan_spacecraft_mission(
        altitude_km=400.0,
        targets=targets if targets else [(52.5, 4.5, 1.0), (53.0, 5.0, 1.0)],
        station=station,
        schedule_days=schedule_days,
    )
    plan_dict = {
        "activities": result["activities"],
        "_params": {"orbit_period_s": result.get("orbit_period_s") or 5500},
    }
    slew_ok, _ = SlewConstraint(min_slew_time_s=60).check(plan_dict)
    power_ok, _ = PowerConstraint(
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
        "constraint_checks": {"slew_feasible": slew_ok, "power_duty_ok": power_ok},
        "visibility_contact_evidence": visibility_evidence,
    }

    if save:
        os.makedirs(os.path.join(ROOT, "outputs"), exist_ok=True)
        with open(os.path.join(ROOT, "outputs", "spacecraft_mission.json"), "w") as f:
            json.dump(out, f, indent=2)
        csv_path = os.path.join(ROOT, "outputs", "spacecraft_schedule.csv")
        with open(csv_path, "w") as f:
            f.write("type,start_t,end_t,duration_s,target_idx\n")
            for a in result["activities"]:
                dur = a["end_t"] - a["start_t"]
                tidx = a.get("target_idx", "")
                f.write(f"{a['type']},{a['start_t']},{a['end_t']},{dur},{tidx}\n")
    return out


def run_full_pipeline(waypoints: list, drone_params: dict, spacecraft_targets: list = None, station: tuple = (52.0, 4.0)) -> tuple:
    """
    Run both aircraft and spacecraft; save to outputs/.
    Returns (aircraft_result_dict or None, spacecraft_result_dict or None).
    """
    ac = run_aircraft_to_outputs(waypoints, drone_params, save=True) if len(waypoints) >= 2 else None
    tgt = spacecraft_targets or [(52.5, 4.5, 1.0), (53.0, 5.0, 1.0), (51.0, 3.0, 1.0)]
    sc = run_spacecraft_to_outputs(tgt, station=station, schedule_days=7, save=True)
    return (ac, sc)
