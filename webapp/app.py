"""
Mission visualization Flask app (Windows + macOS).
Reads from outputs/ and serves aircraft route + spacecraft schedule.
"""
import json
import os

from flask import Flask, render_template, send_from_directory

_webapp_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    static_folder=os.path.join(_webapp_dir, "static"),
    template_folder=os.path.join(_webapp_dir, "templates"),
)

# Path to outputs (project root = parent of webapp)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUTS = os.path.join(ROOT, "outputs")


def _load_json(name: str):
    path = os.path.join(OUTPUTS, name)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/aircraft")
def api_aircraft():
    data = _load_json("aircraft_mission.json")
    if data is None:
        return {"error": "No aircraft mission found. Run the pipeline first."}, 404
    return data


@app.route("/api/spacecraft")
def api_spacecraft():
    data = _load_json("spacecraft_mission.json")
    if data is None:
        return {"error": "No spacecraft mission found. Run the pipeline first."}, 404
    return data


@app.route("/static/<path:path>")
def serve_static(path):
    return send_from_directory(app.static_folder, path)


def main():
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()
