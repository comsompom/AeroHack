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


@app.route("/api/settings")
def api_settings():
    """Return current mission settings (same as Pygame: waypoints, model, spacecraft) from mission_settings."""
    try:
        from src.mission_settings import (
            AIRCRAFT_WAYPOINTS,
            AIRCRAFT_CRUISE_SPEED_MS,
            AIRCRAFT_MAX_TURN_RATE_DEGS,
            AIRCRAFT_ENERGY_BUDGET,
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
