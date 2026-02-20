# Pygame mission visualization

Separate Python/Pygame window with **the same functionality as the main project**: aircraft mission (plan, simulate, save to outputs/, constraint checks, Monte-Carlo) and spacecraft 7-day mission (plan, save, constraint checks), plus real-time flight on a map.

## Modes (tabs)

- **Aircraft:** Plan aircraft mission from waypoints, run planner + simulation, save to `outputs/aircraft_mission.json` and `aircraft_mission_plot.png`, see constraint checks and Monte-Carlo success rate; real-time flight replay on map.
- **Spacecraft:** Use current waypoints as observation targets; plan 7-day schedule (observations + downlinks), save to `outputs/spacecraft_mission.json` and `spacecraft_schedule.csv`, see mission value and constraint checks (slew, power).
- **Run full:** Run both aircraft and spacecraft pipeline (same as `python -m src.run_all`); saves all outputs to `outputs/`.

## Features (Aircraft)

- **Real-world map:** OSM tiles, zoom (scroll wheel), pan (drag).
- **Start & waypoints:** Set start by clicking map or add waypoints by clicking. Clear and redo. Last waypoint = end of mission.
- **Elevation:** Fetched per waypoint via Open-Elevation API when you start the mission. ArduPilot terrain from [terrain.ardupilot.org/continentsdat3/](https://terrain.ardupilot.org/continentsdat3/) can be used offline with a local loader.
- **Real-time weather:** Open-Meteo (no API key) per waypoint; shown in panel.
- **Drone type:** UAV, Plane, Spacecraft, Quadcopter.
- **Weight (kg) and size (m):** [-] / [+] or predefined plane model (War / Civil).
- **Start mission:** Runs planner, saves to `outputs/`, shows constraint checks and Monte-Carlo; yellow marker replays path on map.

## Run (Windows or macOS)

From project root:

```bash
# Install
pip install pygame

# Run (set PYTHONPATH so planner can be imported)
# Windows PowerShell:
$env:PYTHONPATH = (Get-Location)
python pygame_viz/main.py

# macOS/Linux:
export PYTHONPATH=$(pwd)
python pygame_viz/main.py
```

## Usage

1. **Set start:** Click "Set start (click)", then click on the map.
2. **Add waypoints:** Click "Add waypoint (click)", then click on the map for each waypoint. The last one you add is the mission end.
3. **Zoom:** Scroll wheel over the map. **Pan:** Drag with left mouse.
4. **Drone type:** Use &lt; &gt; to pick UAV / Plane / Spacecraft / Quadcopter.
5. **Weight / Size:** Use [-] [+] or, for Plane, pick a War/Civil model (then &lt; &gt; for model).
6. **Start mission:** Click "Start mission". Elevation and weather are fetched; the planned path is replayed with a yellow marker. To run another mission, use "Clear all" and set waypoints again.

## Requirements

- Python 3.8+, pygame, and the rest of the project (so `src.aircraft` planner runs). Map tiles and APIs need internet.
