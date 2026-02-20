"""
Mission visualization Flask app (Windows + macOS).
Reads from outputs/ and serves aircraft route + spacecraft schedule.
Start mission runs the pipeline from mission_settings and writes to outputs/.
"""
import json
import os
import sys

from flask import Flask, render_template, send_from_directory, request, jsonify

_webapp_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    static_folder=os.path.join(_webapp_dir, "static"),
    template_folder=os.path.join(_webapp_dir, "templates"),
)

# Path to outputs and project root (parent of webapp)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUTS = os.path.join(ROOT, "outputs")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _load_json(name: str):
    path = os.path.join(OUTPUTS, name)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None


def _run_pipeline():
    """Run aircraft + spacecraft from mission_settings; write to outputs/."""
    from src.run_all import run_aircraft, run_spacecraft
    run_aircraft()
    run_spacecraft()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/aircraft")
def api_aircraft():
    data = _load_json("aircraft_mission.json")
    if data is None:
        return {"error": "No aircraft mission found. Click Start mission to run the mission from settings."}, 404
    return data


@app.route("/api/spacecraft")
def api_spacecraft():
    data = _load_json("spacecraft_mission.json")
    if data is None:
        return {"error": "No spacecraft mission found. Click Start mission to run the mission from settings."}, 404
    return data


@app.route("/api/weather")
def api_weather():
    """Return current weather at lat, lon (query params). Same as Pygame weather at launch."""
    try:
        lat = float(request.args.get("lat", 52))
        lon = float(request.args.get("lon", 4))
        from pygame_viz.weather import get_weather
        w = get_weather(lat, lon)
        if w is None:
            return jsonify({"error": "Weather unavailable"}), 503
        return jsonify(w)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/plan_spacecraft", methods=["POST"])
def api_plan_spacecraft():
    """Run spacecraft plan with given station and altitude_km; save to outputs/. Same as Pygame Plan 7-day + Save."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        station = tuple(data.get("station") or [52.0, 4.0])[:2]
        station = (float(station[0]), float(station[1]))
        altitude_km = float(data.get("altitude_km", 400))
        targets = data.get("targets")
        if not targets:
            from src.mission_settings import SPACECRAFT_TARGETS
            targets = [list(t) for t in SPACECRAFT_TARGETS]
        from pygame_viz.pipeline import run_spacecraft_to_outputs
        out = run_spacecraft_to_outputs(
            targets=targets,
            station=station,
            schedule_days=7,
            save=True,
            altitude_km=altitude_km,
        )
        if out is None:
            return jsonify({"ok": False, "error": "Spacecraft plan failed"}), 500
        return jsonify({"ok": True, "mission_value": out.get("mission_value")})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/settings")
def api_settings():
    """Return current mission settings (same as Pygame: waypoints, model, spacecraft) from mission_settings."""
    try:
        from src.mission_settings import (
            AIRCRAFT_WAYPOINTS,
            AIRCRAFT_CRUISE_SPEED_MS,
            AIRCRAFT_MAX_TURN_RATE_DEGS,
            AIRCRAFT_ENERGY_BUDGET,
            AIRCRAFT_VEHICLE_TYPE,
            AIRCRAFT_CONSUMPTION_PER_SECOND,
            AIRCRAFT_MIN_ALTITUDE_M,
            AIRCRAFT_MAX_ALTITUDE_M,
            AIRCRAFT_DEFAULT_ALTITUDE_M,
            SPACECRAFT_ALTITUDE_KM,
            SPACECRAFT_TARGETS,
            SPACECRAFT_STATION,
            SPACECRAFT_SCHEDULE_DAYS,
        )
        waypoints = [list(w) for w in AIRCRAFT_WAYPOINTS]
        return jsonify({
            "aircraft": {
                "waypoints": waypoints,
                "cruise_speed_ms": AIRCRAFT_CRUISE_SPEED_MS,
                "max_turn_rate_degs": AIRCRAFT_MAX_TURN_RATE_DEGS,
                "energy_budget": AIRCRAFT_ENERGY_BUDGET,
                "vehicle_type": AIRCRAFT_VEHICLE_TYPE,
                "consumption_per_second": AIRCRAFT_CONSUMPTION_PER_SECOND,
                "min_altitude_m": AIRCRAFT_MIN_ALTITUDE_M,
                "max_altitude_m": AIRCRAFT_MAX_ALTITUDE_M,
                "default_altitude_m": AIRCRAFT_DEFAULT_ALTITUDE_M,
            },
            "spacecraft": {
                "altitude_km": SPACECRAFT_ALTITUDE_KM,
                "targets": [list(t) for t in SPACECRAFT_TARGETS],
                "station": list(SPACECRAFT_STATION),
                "schedule_days": SPACECRAFT_SCHEDULE_DAYS,
            },
            "drone_types": ["UAV", "Plane", "Spacecraft", "Quadcopter"],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/plan_aircraft", methods=["POST"])
def api_plan_aircraft():
    """Run aircraft plan with user-provided waypoints and params; save to outputs/. Same as Pygame Plan + Save."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        waypoints = data.get("waypoints")
        if not waypoints or len(waypoints) < 2:
            return jsonify({"ok": False, "error": "At least 2 waypoints required"}), 400
        waypoints = [list(w)[:3] for w in waypoints]
        for w in waypoints:
            if len(w) == 2:
                w.append(float(data.get("default_altitude_m", 100)))
            w[0], w[1] = float(w[0]), float(w[1])
            w[2] = float(w[2]) if len(w) > 2 else float(data.get("default_altitude_m", 100))

        default_alt = float(data.get("default_altitude_m", 100))
        vehicle_type = (data.get("vehicle_type") or "Plane").strip()
        is_plane = vehicle_type.lower() in ("plane", "fixed-wing")
        energy_budget = float(data.get("fuel_tank_capacity_j") or data.get("battery_capacity_j") or data.get("energy_budget") or 2e6)
        consumption = float(data.get("consumption_per_second") or 80)

        from src.mission_settings import (
            AIRCRAFT_CRUISE_SPEED_MS,
            AIRCRAFT_MAX_TURN_RATE_DEGS,
            AIRCRAFT_MIN_ALTITUDE_M,
            AIRCRAFT_MAX_ALTITUDE_M,
        )
        drone_params = {
            "cruise_speed_ms": float(data.get("cruise_speed_ms") or AIRCRAFT_CRUISE_SPEED_MS),
            "max_turn_rate_degs": float(data.get("max_turn_rate_degs") or AIRCRAFT_MAX_TURN_RATE_DEGS),
            "energy_budget": energy_budget,
            "consumption_per_second": consumption,
            "min_altitude_m": float(data.get("min_altitude_m") or AIRCRAFT_MIN_ALTITUDE_M),
            "max_altitude_m": float(data.get("max_altitude_m") or AIRCRAFT_MAX_ALTITUDE_M),
            "default_altitude_m": default_alt,
        }
        from pygame_viz.pipeline import run_aircraft_to_outputs
        out = run_aircraft_to_outputs(waypoints, drone_params, save=True)
        if out is None:
            return jsonify({"ok": False, "error": "Aircraft plan failed"}), 500
        return jsonify({"ok": True, "total_time_s": out.get("total_time_s"), "total_energy": out.get("total_energy")})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/start_mission", methods=["POST"])
def api_start_mission():
    """Run the pipeline from mission_settings; write to outputs/. Returns JSON { ok: true } or error."""
    try:
        _run_pipeline()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/static/<path:path>")
def serve_static(path):
    return send_from_directory(app.static_folder, path)


def main():
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()
