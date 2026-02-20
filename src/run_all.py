"""
Single entry point: run aircraft and spacecraft mission planning end-to-end.
Saves plans and metrics to outputs/ with full requirement coverage (A) Aircraft, (B) Spacecraft.
All mission variables (waypoints, model, targets, etc.) are defined in src.mission_settings.
"""
import json
import os
import sys

# Add project root so "src" imports work
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.mission_settings import (
    AIRCRAFT_WAYPOINTS,
    AIRCRAFT_CRUISE_SPEED_MS,
    AIRCRAFT_MAX_TURN_RATE_DEGS,
    AIRCRAFT_ENERGY_BUDGET,
    AIRCRAFT_VEHICLE_TYPE,
    AIRCRAFT_FUEL_TANK_CAPACITY_J,
    AIRCRAFT_BATTERY_CAPACITY_J,
    AIRCRAFT_CONSUMPTION_PER_SECOND,
    AIRCRAFT_MIN_ALTITUDE_M,
    AIRCRAFT_MAX_ALTITUDE_M,
    AIRCRAFT_DEFAULT_ALTITUDE_M,
    AIRCRAFT_NO_FLY_ZONES,
    MONTE_CARLO_NUM_SEEDS,
    MONTE_CARLO_SEED,
    SPACECRAFT_ALTITUDE_KM,
    SPACECRAFT_TARGETS,
    SPACECRAFT_STATION,
    SPACECRAFT_SCHEDULE_DAYS,
    SPACECRAFT_MIN_SLEW_TIME_S,
    SPACECRAFT_MAX_ACTIVE_PER_ORBIT_S,
)


def run_aircraft():
    """Plan and simulate aircraft mission; save to outputs/ (JSON + plot).
    Output satisfies Aircraft Mission Module requirements: ordered plan with timing,
    point-mass model with turn/energy, wind, endurance, maneuver, geofence, objective,
    robustness (Monte-Carlo), flight path with timestamps, constraint checks, metrics.
    Uses mission_settings for waypoints, model parameters, and no-fly zones.
    """
    from src.aircraft.model import AircraftModel
    from src.aircraft.planner import plan_aircraft_mission
    from src.aircraft.simulate import simulate_mission, monte_carlo_mission
    from src.aircraft.constraints import EnduranceConstraint, ManeuverConstraint, GeofenceConstraint, AltitudeConstraint

    waypoints = list(AIRCRAFT_WAYPOINTS)
    # Use fuel tank capacity for planes, battery capacity for drones (UAV)
    is_plane = (AIRCRAFT_VEHICLE_TYPE or "Plane").strip().lower() in ("plane", "fixed-wing")
    energy_budget = AIRCRAFT_FUEL_TANK_CAPACITY_J if is_plane else AIRCRAFT_BATTERY_CAPACITY_J
    if energy_budget is None or energy_budget <= 0:
        energy_budget = AIRCRAFT_ENERGY_BUDGET

    model = AircraftModel(
        cruise_speed_ms=AIRCRAFT_CRUISE_SPEED_MS,
        max_turn_rate_degs=AIRCRAFT_MAX_TURN_RATE_DEGS,
        energy_budget=energy_budget,
        consumption_per_second=AIRCRAFT_CONSUMPTION_PER_SECOND,
        min_altitude_m=AIRCRAFT_MIN_ALTITUDE_M,
        max_altitude_m=AIRCRAFT_MAX_ALTITUDE_M,
        default_altitude_m=AIRCRAFT_DEFAULT_ALTITUDE_M,
    )
    plan = plan_aircraft_mission(waypoints, model)
    states, total_time, total_energy, checks = simulate_mission(plan)
    crash_depletion = checks.get("crash_depletion")
    mc = monte_carlo_mission(plan, num_seeds=MONTE_CARLO_NUM_SEEDS, seed=MONTE_CARLO_SEED)

    no_fly_zones = list(AIRCRAFT_NO_FLY_ZONES)
    endurance_ok, endurance_v = EnduranceConstraint(model).check(plan)
    maneuver_ok, maneuver_v = ManeuverConstraint(model).check(plan)
    geofence_ok, geofence_v = (True, 0.0) if not no_fly_zones else GeofenceConstraint(no_fly_zones).check(plan)
    altitude_ok, altitude_v = AltitudeConstraint(model).check(plan)
    constraint_checks = {
        "energy_ok": checks["energy_ok"],
        "endurance_respected": endurance_ok,
        "maneuver_limits_ok": maneuver_ok,
        "geofence_violations": int(geofence_v) if geofence_ok else int(geofence_v),
        "altitude_within_envelope": altitude_ok,
    }

    # Ordered plan with timing, altitude, energy_used, and remaining energy (battery/fuel level)
    wp_alt = plan.get("waypoints_with_altitude") or [
        (p[0], p[1], model.default_altitude_m) for p in plan["waypoints"]
    ]
    states = plan.get("states") or []
    planned_route = []
    energy_remaining_at_waypoints = []
    for i, p in enumerate(wp_alt):
        e_used = getattr(states[i], "energy_used", None) if i < len(states) else None
        entry = {"lat": p[0], "lon": p[1], "alt_m": p[2], "t": plan["timestamps"][i]}
        if e_used is not None:
            entry["energy_used"] = e_used
            energy_remaining_at_waypoints.append(model.energy_budget - e_used)
        planned_route.append(entry)

    # Crash depletion: where and why (no fuel / no battery)
    crash_depletion_out = None
    if crash_depletion:
        alt_at_crash = wp_alt[crash_depletion["segment_from_waypoint_index"]][2] if crash_depletion["segment_from_waypoint_index"] < len(wp_alt) else model.default_altitude_m
        crash_depletion_out = {
            "occurred": True,
            "reason": "no_fuel" if is_plane else "no_battery",
            "at_position": {
                "lat": crash_depletion["crash_lat"],
                "lon": crash_depletion["crash_lon"],
                "alt_m": alt_at_crash,
            },
            "at_time_s": crash_depletion["crash_t_s"],
            "segment_from_waypoint_index": crash_depletion["segment_from_waypoint_index"],
            "segment_to_waypoint_index": crash_depletion["segment_to_waypoint_index"],
            "energy_used_at_depletion": crash_depletion["energy_used_at_depletion"],
        }

    out = {
        "module": "Aircraft (UAV / fixed-wing)",
        "vehicle_type": AIRCRAFT_VEHICLE_TYPE,
        "objective": "minimize_time",
        "model_description": (
            "Point-mass kinematics; turn rate limit (deg/s) and bank equivalent; "
            "energy consumption model (per-second + turn penalty). "
            "Planes use fuel tank capacity; drones (UAV) use battery capacity."
        ),
        "model_parameters": {
            "cruise_speed_ms": model.cruise_speed_ms,
            "max_turn_rate_degs": model.max_turn_rate_degs,
            "energy_budget": model.energy_budget,
            "fuel_tank_capacity_J": energy_budget if is_plane else None,
            "battery_capacity_J": energy_budget if not is_plane else None,
            "consumption_per_second": model.consumption_per_second,
            "min_altitude_m": model.min_altitude_m,
            "max_altitude_m": model.max_altitude_m,
            "default_altitude_m": model.default_altitude_m,
        },
        "wind_incorporation": (
            "Wind as callable wind(t, lat, lon) -> (v_north, v_east) m/s. "
            "Used in segment time and simulation (groundspeed = airspeed + wind along track). "
            "Nominal run: zero wind. Robustness: Monte-Carlo with multiple wind seeds."
        ),
        "constraints": {
            "endurance_energy": "Total energy <= energy_budget; consumption_per_second + turn penalty.",
            "maneuver_limits": "Turn rate (deg/s) <= max_turn_rate_degs per segment.",
            "geofencing": "Path must not enter no-fly polygons (optional altitude bands via polygons).",
            "altitude": "Waypoint altitudes within [min_altitude_m, max_altitude_m]; impossible values checked and corrected.",
        },
        "no_fly_zones": no_fly_zones,
        "waypoints": waypoints,
        "waypoints_corrected_altitude": wp_alt,
        "planned_route": planned_route,
        "flight_path_with_timestamps": planned_route,
        "energy_remaining_at_waypoints": energy_remaining_at_waypoints,
        "crash_depletion": crash_depletion_out,
        "total_time_s": plan["total_time"],
        "total_energy": plan["total_energy"],
        "performance_metrics": {
            "total_time_s": plan["total_time"],
            "total_energy": plan["total_energy"],
        },
        "constraint_checks": constraint_checks,
        "robustness": {
            "description": "Monte-Carlo: multiple wind seeds (random constant wind); plan feasible and performance acceptable.",
            "monte_carlo": {
                "success_rate": mc["success_rate"],
                "runs": mc["runs"],
                "total_times": mc.get("total_times", []),
                "total_energies": mc.get("total_energies", []),
            },
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
    """Plan 7-day spacecraft mission; save to outputs/ (JSON + CSV table).
    Output satisfies Spacecraft Mission Module requirements: orbit/visibility model,
    7-day schedule (observations + downlinks), slew and power constraints, objective,
    time-ordered schedule, contact/visibility evidence, constraint checks, mission value.
    Uses mission_settings for altitude, targets, station, schedule days, and constraint params.
    """
    from src.spacecraft.planner import plan_spacecraft_mission
    from src.spacecraft.constraints import SlewConstraint, PowerConstraint

    altitude_km = SPACECRAFT_ALTITUDE_KM
    targets = list(SPACECRAFT_TARGETS)
    station = SPACECRAFT_STATION
    schedule_days = SPACECRAFT_SCHEDULE_DAYS
    result = plan_spacecraft_mission(
        altitude_km=altitude_km,
        targets=targets,
        station=station,
        schedule_days=schedule_days,
        min_slew_s=SPACECRAFT_MIN_SLEW_TIME_S,
        max_active_per_orbit_s=SPACECRAFT_MAX_ACTIVE_PER_ORBIT_S,
    )
    period = result.get("orbit_period_s") or 5500
    plan_dict = {
        "activities": result["activities"],
        "_params": {"orbit_period_s": period},
    }
    slew_ok, slew_v = SlewConstraint(min_slew_time_s=SPACECRAFT_MIN_SLEW_TIME_S).check(plan_dict)
    power_ok, power_v = PowerConstraint(
        orbit_period_s=period,
        max_active_per_orbit_s=SPACECRAFT_MAX_ACTIVE_PER_ORBIT_S,
    ).check(plan_dict)
    visibility_contact_evidence = [
        {
            "type": a["type"],
            "start_t": a["start_t"],
            "end_t": a["end_t"],
            "target_idx": a.get("target_idx"),
            "duration_s": a["end_t"] - a["start_t"],
        }
        for a in result["activities"]
    ]

    out = {
        "module": "Spacecraft (CubeSat-style LEO)",
        "objective": "maximize_science_value",
        "orbit_visibility_model": (
            "Simplified two-body circular orbit; ground track and pass/visibility logic; "
            "observation windows for ground targets (lat/lon), contact windows for ground station."
        ),
        "orbit_parameters": {
            "altitude_km": altitude_km,
            "orbit_period_s": period,
            "schedule_days": schedule_days,
        },
        "ground_targets": [{"lat": t[0], "lon": t[1], "value": t[2]} for t in targets],
        "ground_station": {"lat": station[0], "lon": station[1]},
        "constraints": {
            "pointing_slew": "Minimum time between pointing changes (min_slew_time_s) between consecutive activities.",
            "power_duty": "Max active time per orbit (duty cycle proxy); charging/discharge balance.",
        },
        "constraint_checks": {
            "slew_feasible": slew_ok,
            "power_duty_ok": power_ok,
        },
        "time_ordered_schedule": result["activities"],
        "activities": result["activities"],
        "visibility_contact_evidence": visibility_contact_evidence,
        "mission_value_metrics": {
            "mission_value": result["mission_value"],
            "targets_observed_and_downlinked": result.get("mission_value", 0),
        },
        "schedule_days": result["schedule_days"],
        "mission_value": result["mission_value"],
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
