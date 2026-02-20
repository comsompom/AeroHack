# DroneMission — AeroHack

Unified mission planning and simulation framework for **aircraft** (UAV/fixed-wing) and **spacecraft** (CubeSat-style LEO). Both use the same core planning concept: decision variables, constraints, objective, and a single solver.

---

## Functionality overview

### Mission settings (`src/mission_settings.py`)

All configurable mission variables live in one file so you can change missions without editing code:

- **Aircraft** — Waypoints `(lat, lon)` or `(lat, lon, alt_m)`; cruise speed, turn rate, energy budget, consumption; min/max/default altitude (m); no-fly zones (list of polygons); Monte-Carlo seed and number of runs.
- **Spacecraft** — Orbit altitude (km); ground targets `(lat, lon, value)`; ground station `(lat, lon)`; schedule days; min slew time (s); max active time per orbit (s).
- Default aircraft route: **Vilnius Airport → Warsaw Chopin → Berlin Brandenburg → Lisbon Portela**. Edit `AIRCRAFT_WAYPOINTS` and other constants to change the mission.

### Core planning engine (`src/core/`)

- **Decision variables** (`variables.py`) — Shared abstraction for what the planner chooses (e.g. waypoint order, segment times, observation/downlink windows).
- **Constraints** (`constraints.py`) — Common interface: each constraint returns feasible/violation; both aircraft and spacecraft register domain-specific constraints.
- **Objective** (`objective.py`) — Single interface to score a plan (minimize time/energy or maximize science value).
- **Solver** (`solver.py`) — One planning method used for both domains (constraint-based search/heuristic), so the system is a single engine with two problem formulations.

### Aircraft mission module (`src/aircraft/`)

- **Model** (`model.py`) — Point-mass kinematics, turn rate / bank limits, energy/battery consumption. Wind as callable `wind(t, lat, lon)`; nominal zero, used in segment time and simulation. **Waypoint altitude**: waypoints can include altitude (m); `correct_waypoint_altitudes()` fills missing altitudes and clamps to aircraft min/max envelope.
- **Constraints** (`constraints.py`) — Endurance/energy budget, maneuver limits (turn/bank), geofencing (no-fly polygons), **altitude** (waypoints within min/max altitude; impossible values checked and corrected).
- **Planner** (`planner.py`) — Builds variables, constraints, and objective; corrects waypoint altitudes; calls core solver; returns ordered route with timestamps and `waypoints_with_altitude`.
- **Simulation** (`simulate.py`) — Runs planned trajectory through the same model and wind; reports total time, energy, and constraint checks.
- **Monte-Carlo** — Multiple wind (and parameter) seeds; reports success rate and robustness (see `mission_settings`: `MONTE_CARLO_NUM_SEEDS`, `MONTE_CARLO_SEED`).
- **Outputs** — Planned route with timestamps and altitude; constraint-check summary (energy, endurance, maneuver, geofence, altitude); performance metrics; path/state plot.

### Spacecraft mission module (`src/spacecraft/`)

- **Orbit & visibility** (`orbit.py`) — Simplified two-body propagation; ground-track and pass computation for ground stations and target lat/lon; observation and contact time windows.
- **Constraints** (`constraints.py`) — Pointing/slew (min time between activities), power/duty (max active time per orbit).
- **Planner** (`planner.py`) — Builds variables, constraints, and objective (science value); calls same core solver; returns 7-day schedule.
- **Schedule** (`schedule.py`) — Time-ordered activities (observations, downlinks); science value = targets observed and successfully downlinked.
- **Outputs** — 7-day schedule (JSON + CSV); orbit/visibility description; constraint checks; mission value metrics; visibility/contact evidence.

### Full pipeline (`src/run_all.py`)

- Single entry point: runs aircraft then spacecraft using **mission_settings** (waypoints, model params, no-fly zones, Monte-Carlo, spacecraft targets, station, schedule days).
- **Aircraft output** (`outputs/aircraft_mission.json`): module, objective, model description/parameters, wind incorporation, constraints (descriptions), no_fly_zones, waypoints, waypoints_corrected_altitude, planned_route (lat, lon, alt_m, t), flight_path_with_timestamps, total_time_s, total_energy, performance_metrics, constraint_checks (energy_ok, endurance_respected, maneuver_limits_ok, geofence_violations, altitude_within_envelope), robustness (Monte-Carlo success_rate, runs, total_times, total_energies), monte_carlo.
- **Aircraft plot** (`outputs/aircraft_mission_plot.png`): flight path and state vs time.
- **Spacecraft output** (`outputs/spacecraft_mission.json`): module, objective, orbit_visibility_model, orbit_parameters, ground_targets, ground_station, constraints, constraint_checks, time_ordered_schedule, activities, visibility_contact_evidence, mission_value_metrics, mission_value.
- **Spacecraft table** (`outputs/spacecraft_schedule.csv`): type, start_t, end_t, duration_s, target_idx.

### Web app (`webapp/`)

- **Flask** app (Windows and macOS) at http://127.0.0.1:5000.
- **Aircraft tab** — Leaflet map with planned route; metrics: total time, total energy, Monte-Carlo success rate. Reads `outputs/aircraft_mission.json`.
- **Spacecraft tab** — 7-day schedule table and mission value; reads `outputs/spacecraft_mission.json` and `outputs/spacecraft_schedule.csv`.
- Run the pipeline first to generate `outputs/`; then start the app and refresh to see data.

### Pygame mission visualization (`pygame_viz/`)

- Separate Pygame window that uses the **same plan/simulate logic** as the main project. Clicking **Start mission** produces the **same** `outputs/aircraft_mission.json` and `outputs/aircraft_mission_plot.png` as `run_all` (full structure: module, objective, model params, constraints, waypoints_corrected_altitude, robustness, etc.).
- **Layout** — Settings panel on the **left**; map on the **right**. **Pan:** hold **left** mouse and drag on the map. **Zoom:** scroll wheel over the map.
- **Tabs** — **Aircraft** (set waypoints on map, run mission, save to `outputs/`, replay on map); **Spacecraft** (use waypoints as targets, plan 7-day, save to `outputs/`); **Run full** (same as `python -m src.run_all`).
- **Map** — Real-world OSM tiles; click to set start and waypoints; clear and redo.
- **Waypoint altitude** — Dropdown **Altitude (m)** (50–4000 m) applied to new waypoints; altitudes checked and corrected to aircraft envelope when running the mission.
- **Settings (dropdowns)** — **Drone type** (UAV, Plane, Spacecraft, Quadcopter); **Weight (kg)** and **Size (m)** from preset lists; **Plane type** (War/Civil) and **Plane model** (e.g. Global Hawk, Cessna 172). All use normal dropdown lists.
- **Elevation** — Fetched per waypoint (Open-Elevation API; ArduPilot terrain can be used with local data).
- **Weather** — Real-time per waypoint (Open-Meteo, no API key).
- **Start mission** — Runs planner with current waypoints and aircraft params, saves to `outputs/`, shows constraint checks and Monte-Carlo; yellow marker replays path on map in real time.

### Validation (`validation/`)

- **Monte-Carlo script** (`run_monte_carlo.py`) — Runs aircraft mission with multiple wind seeds; prints success rate and total-time range. Run from project root with `PYTHONPATH` set.

### Tests (`tests/`)

- **pytest** covers: **core** (variables, constraints, objective, solver); **aircraft** (model including waypoint altitude/correct, constraints including altitude, planner, simulate); **spacecraft** (orbit, constraints, planner, schedule); **webapp** (routes, API JSON); **mission_settings** (constants); **run_all** (aircraft and spacecraft return structure and file writes); **pygame_viz** (config, mission_runner, pipeline, elevation, weather, map_view); **validation** (run_monte_carlo main).
- Run: `pytest tests/ -v`
- Coverage: `pytest tests/ --cov=src --cov=pygame_viz --cov=webapp --cov-report=html` (report in `htmlcov/index.html`).

---

## Project layout

- `src/` — Core planning engine and domain modules
  - `mission_settings.py` — **Single source of mission config**: aircraft waypoints, model params, no-fly zones, Monte-Carlo; spacecraft targets, station, schedule days, slew/power
  - `core/` — Decision variables, constraints, objective, solver (shared)
  - `aircraft/` — Kinematics, wind, constraints (incl. altitude), planner, simulation
  - `spacecraft/` — Orbit/visibility, constraints, planner, 7-day schedule
  - `run_all.py` — Single entry: run both missions from mission_settings and write outputs
- `webapp/` — Mission visualization (Flask; Windows + macOS)
- `pygame_viz/` — Pygame map viz (waypoints with altitude, mission run, replay; settings left, map right; same output as run_all)
- `data/` — Input data (waypoints, wind, targets)
- `outputs/` — Generated plans (JSON), plots, CSV
- `tests/` — Unit tests (core, aircraft, spacecraft, webapp, mission_settings, run_all, pygame_viz, validation)
- `validation/` — Monte-Carlo script
- `docs/` — Report, figures

---

## Reproduce results

### 1. Install (Windows or macOS)

```bash
cd AeroHack
python -m venv .venv
# Windows:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run the full pipeline

From the project root (`AeroHack`):

```bash
set PYTHONPATH=%cd%   # Windows cmd
# or: $env:PYTHONPATH=(Get-Location)  # PowerShell
# or: export PYTHONPATH=$(pwd)         # macOS/Linux
python -m src.run_all
```

This produces:

- `outputs/aircraft_mission.json` — Planned route, timestamps, total time/energy, constraint checks, Monte-Carlo success rate
- `outputs/aircraft_mission_plot.png` — Flight path and state vs time
- `outputs/spacecraft_mission.json` — 7-day schedule, activities, mission value, constraint checks
- `outputs/spacecraft_schedule.csv` — Schedule table (type, start_t, end_t, duration_s, target_idx)

### 3. Run unit tests

```bash
pytest tests/ -v
```

Optional coverage report:

```bash
pytest tests/ --cov=src --cov=pygame_viz --cov=webapp --cov-report=html
```

Report is written to `htmlcov/index.html`.

### 4. Start the mission visualization web app (Windows + macOS)

```bash
pip install flask   # if not already installed
python webapp/app.py
```

Then open **http://127.0.0.1:5000** in a browser. The app reads from `outputs/` and shows aircraft route (map + metrics) and spacecraft schedule (table + mission value).

- **Windows:** Same commands in PowerShell or Command Prompt (use `.\\.venv\\Scripts\\activate` if needed).
- **macOS:** Use `source .venv/bin/activate` and the same `python` commands.

### 5. Regenerate plots/metrics from scratch

1. Run `python -m src.run_all` again (overwrites `outputs/*.json` and plot/CSV).
2. Restart the web app and refresh the page to see updated data.

### 6. Pygame mission visualization (optional)

```bash
pip install pygame
# From project root, with PYTHONPATH set (see §2):
python pygame_viz/main.py
```

Settings panel on the left; map on the right; **left mouse drag** to pan (grab and move). See `pygame_viz/README.md` for full usage.

### 7. Validation (Monte-Carlo)

```bash
# From project root, with PYTHONPATH set:
python validation/run_monte_carlo.py
```

Prints success rate and total-time range over multiple wind seeds.

---

## Quick reference

| Command | Purpose |
|--------|---------|
| `python -m src.run_all` | Run aircraft + spacecraft planning; write `outputs/` |
| `pytest tests/ -v` | Run all unit tests |
| `pytest tests/ --cov=src --cov=pygame_viz --cov=webapp --cov-report=html` | Tests + coverage report |
| `python webapp/app.py` | Start Flask visualization at http://127.0.0.1:5000 |
| `python pygame_viz/main.py` | Start Pygame map viz (settings left, map right; left-drag to pan) |
| `python validation/run_monte_carlo.py` | Monte-Carlo validation (wind uncertainty) |

---

## Requirements

- Python 3.8+
- See `requirements.txt`: numpy, matplotlib, pytest, pytest-cov, flask, pygame (for viz)

---

## Expected runtime and hardware

- **Full pipeline** (`python -m src.run_all`): typically 5–30 seconds (aircraft planning + simulation + Monte-Carlo, then spacecraft 7-day schedule).
- **Unit tests** (`pytest tests/ -v`): under a few seconds.
- **Hardware:** No GPU required. Standard CPU and a few hundred MB RAM. Web app runs in the browser; Pygame runs in a single window.
