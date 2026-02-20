# Pygame mission visualization

Separate Python/Pygame window for mission setup and real-time flight on a real-world map.

## Features

- **Real-world map:** OSM tiles, zoom (scroll wheel), pan (drag).
- **Start & waypoints:** Set start by clicking map or add waypoints by clicking. Clear and redo. Last waypoint = end of mission.
- **Elevation:** Fetched per waypoint via Open-Elevation API when you start the mission. ArduPilot terrain data from [terrain.ardupilot.org/continentsdat3/](https://terrain.ardupilot.org/continentsdat3/) can be used offline by adding a local loader for unpacked continent grids.
- **Real-time weather:** Open-Meteo (no API key) for each waypoint when mission starts; shown in panel.
- **Drone type:** UAV, Plane, Spacecraft, Quadcopter.
- **Weight (kg) and size (m):** Adjust with [-] / [+] or choose a predefined plane model.
- **Plane models:** War (e.g. MQ-9 Reaper, Global Hawk) and Civil (e.g. Cessna 172, DJI Agras); predefined list or custom weight/size.
- **Start mission:** Runs the aircraft planner on your waypoints and replays the path in real time on the map (yellow marker).

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
