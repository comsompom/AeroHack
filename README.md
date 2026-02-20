# DroneMission — AeroHack

Unified mission planning and simulation framework for **aircraft** (UAV/fixed-wing) and **spacecraft** (CubeSat-style LEO). Both use the same core planning concept: decision variables, constraints, objective, and a single solver.

---

## Functionality overview

### Mission settings (`src/mission_settings.py`)

All configurable mission variables live in one file so you can change missions without editing code:

- **Aircraft** — Waypoints `(lat, lon)` or `(lat, lon, alt_m)`; cruise speed, turn rate; **vehicle type** (Plane / UAV); **fuel tank capacity (J)** for planes and **battery capacity (J)** for drones; consumption (J/s); min/max/default altitude (m); no-fly zones (list of polygons); Monte-Carlo seed and number of runs.
- **Spacecraft** — Orbit altitude (km); ground targets `(lat, lon, value)`; ground station `(lat, lon)`; schedule days; min slew time (s); max active time per orbit (s).
- Default aircraft route: **Vilnius Airport → Warsaw Chopin → Berlin Brandenburg → Lisbon Portela**. Edit `AIRCRAFT_WAYPOINTS` and other constants to change the mission.

### Core planning engine (`src/core/`)

- **Decision variables** (`variables.py`) — Shared abstraction for what the planner chooses (e.g. waypoint order, segment times, observation/downlink windows).
- **Constraints** (`constraints.py`) — Common interface: each constraint returns feasible/violation; both aircraft and spacecraft register domain-specific constraints.
- **Objective** (`objective.py`) — Single interface to score a plan (minimize time/energy or maximize science value).
- **Solver** (`solver.py`) — One planning method used for both domains (constraint-based search/heuristic), so the system is a single engine with two problem formulations.

### Aircraft mission module (`src/aircraft/`)

- **Model** (`model.py`) — Point-mass kinematics, turn rate / bank limits, energy consumption (fuel for planes, battery for drones). Wind as callable `wind(t, lat, lon)`; nominal zero, used in segment time and simulation. **Waypoint altitude**: waypoints can include altitude (m); `correct_waypoint_altitudes()` fills missing altitudes and clamps to aircraft min/max envelope. **Depletion detection**: simulation reports if energy runs out mid-flight and interpolates crash position (lat, lon, segment).
- **Constraints** (`constraints.py`) — Endurance/energy budget, maneuver limits (turn/bank), geofencing (no-fly polygons), **altitude** (waypoints within min/max altitude; impossible values checked and corrected).
- **Planner** (`planner.py`) — Builds variables, constraints, and objective; corrects waypoint altitudes; calls core solver; returns ordered route with timestamps and `waypoints_with_altitude`.
- **Simulation** (`simulate.py`) — Runs planned trajectory through the same model and wind; reports total time, energy, and constraint checks.
- **Monte-Carlo** — Multiple wind (and parameter) seeds; reports success rate and robustness (see `mission_settings`: `MONTE_CARLO_NUM_SEEDS`, `MONTE_CARLO_SEED`).
- **Outputs** — Planned route with timestamps, altitude, and **energy_used** per waypoint; **energy_remaining_at_waypoints** (fuel/battery level); **crash_depletion** (if energy runs out: reason no_fuel/no_battery, at_position, at_time_s, segment indices); constraint-check summary (energy, endurance, maneuver, geofence, altitude); performance metrics; path/state plot.

### Spacecraft mission module (`src/spacecraft/`)

- **Orbit & visibility** (`orbit.py`) — Simplified two-body propagation; ground-track and pass computation for ground stations and target lat/lon; observation and contact time windows.
- **Constraints** (`constraints.py`) — Pointing/slew (min time between activities), power/duty (max active time per orbit).
- **Planner** (`planner.py`) — Builds variables, constraints, and objective (science value); calls same core solver; returns 7-day schedule.
- **Schedule** (`schedule.py`) — Time-ordered activities (observations, downlinks); science value = targets observed and successfully downlinked.
- **Outputs** — 7-day schedule (JSON + CSV); orbit/visibility description; constraint checks; mission value metrics; visibility/contact evidence.

### Full pipeline (`src/run_all.py`)

- Single entry point: runs aircraft then spacecraft using **mission_settings** (waypoints, model params, no-fly zones, Monte-Carlo, spacecraft targets, station, schedule days).
- **Aircraft output** (`outputs/aircraft_mission.json`): vehicle_type, model_parameters (fuel_tank_capacity_J / battery_capacity_J by type), waypoints, planned_route (lat, lon, alt_m, t, energy_used), flight_path_with_timestamps, **energy_remaining_at_waypoints**, **crash_depletion** (occurred, reason no_fuel/no_battery, at_position, at_time_s, segment indices), total_time_s, total_energy, constraint_checks, robustness (Monte-Carlo), monte_carlo.
- **Aircraft plot** (`outputs/aircraft_mission_plot.png`): flight path and state vs time.
- **Spacecraft output** (`outputs/spacecraft_mission.json`): module, objective, orbit_visibility_model, orbit_parameters, ground_targets, ground_station, constraints, constraint_checks, time_ordered_schedule, activities, visibility_contact_evidence, mission_value_metrics, mission_value.
- **Spacecraft table** (`outputs/spacecraft_schedule.csv`): type, start_t, end_t, duration_s, target_idx.

### Web app (`webapp/`)

- **Flask** app (Windows and macOS) at http://127.0.0.1:5000.
- **Aircraft tab** — **Editable inputs**: waypoints (textarea, one per line: `lat, lon` or `lat, lon, alt_m`), default altitude (m), vehicle type (Plane / UAV), fuel/battery capacity (J), consumption (J/s). **Plan aircraft + Save** runs the aircraft pipeline with these values and writes `outputs/aircraft_mission.json`; map and metrics refresh. **Start mission (from file)** runs the full pipeline from `mission_settings`. Leaflet map shows planned route and real-time replay; crash/fail shown if fuel/battery depletes.
- **Spacecraft tab** — **Editable inputs**: launch point (lat, lon), orbit altitude (km), **Set from start**; **Weather at launch** (Open-Meteo). **Plan 7-day + Save** runs spacecraft plan with current values. **Full Earth** canvas: textured globe, **drag to rotate**, **click on globe to set launch**; launch marker and orbit/spacecraft animate. Schedule table and mission value (Slew OK, Power OK) from `outputs/spacecraft_mission.json`.
- **APIs** — `GET /api/settings`, `GET /api/aircraft`, `GET /api/spacecraft`, `GET /api/weather?lat=&lon=`, `POST /api/plan_aircraft` (body: waypoints, default_altitude_m, vehicle_type, energy_budget, consumption_per_second), `POST /api/plan_spacecraft` (body: station, altitude_km, targets), `POST /api/start_mission` (run from file).

### Pygame mission visualization (`pygame_viz/`)

- Separate Pygame window that uses the **same plan/simulate logic** as the main project. Clicking **Start mission** produces the **same** `outputs/aircraft_mission.json` and `outputs/aircraft_mission_plot.png` as `run_all` (full structure: module, objective, model params, constraints, waypoints_corrected_altitude, robustness, etc.).
- **Layout** — Settings panel on the **left**; map on the **right**. **Pan:** hold **left** mouse and drag on the map. **Zoom:** scroll wheel over the map.
- **Tabs** — **Aircraft** (set waypoints on map, run mission, save to `outputs/`, replay on map); **Spacecraft** (use waypoints as targets, plan 7-day, save to `outputs/`); **Run full** (same as `python -m src.run_all`).
- **Map** — Real-world OSM tiles; click to set start and waypoints; clear and redo.
- **Waypoint altitude** — Dropdown **Altitude (m)** (50–4000 m) applied to new waypoints; altitudes checked and corrected to aircraft envelope when running the mission.
- **Settings (dropdowns)** — **Drone type** (UAV, Plane, Spacecraft, Quadcopter); **Weight (kg)** and **Size (m)** from preset lists; **Plane type** (War/Civil) and **Plane model** (e.g. Global Hawk, Cessna 172). All use normal dropdown lists.
- **Elevation** — Fetched per waypoint (Open-Elevation API; ArduPilot terrain can be used with local data).
- **Weather** — Real-time per waypoint (Open-Meteo, no API key).
- **Start mission** — Runs planner with current waypoints and aircraft params, saves to `outputs/`, shows constraint checks and Monte-Carlo; yellow marker replays path on map in real time; crash/fail marker if fuel or battery depletes.
- **Spacecraft view** — **Full Earth**: textured globe (or procedural fallback), **drag to rotate**, **click on globe to set launch point**. Launch point and orbit altitude editable in panel (lat±/lon±, **Set from start**, orbit ±); **Weather at launch** (cached). Plan 7-day + Save uses current launch and altitude; ascent animation then orbit.

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

## Install

1. Clone or unpack the project and go to the project root:
   ```bash
   cd AeroHack
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .venv\Scripts\Activate.ps1
   # Windows CMD:
   .venv\Scripts\activate.bat
   # macOS/Linux:
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   This installs: numpy, matplotlib, pytest, pytest-cov, flask, pygame.

## Run

All commands below are from the **project root** (`AeroHack`). Set `PYTHONPATH` so the `src` and `pygame_viz` modules resolve:

- **Windows PowerShell:** `$env:PYTHONPATH = (Get-Location)`
- **Windows CMD:** `set PYTHONPATH=%cd%`
- **macOS/Linux:** `export PYTHONPATH=$(pwd)`

### Run the full pipeline (aircraft + spacecraft)

```bash
python -m src.run_all
```

This writes:

- `outputs/aircraft_mission.json` — Route, timestamps, energy remaining per waypoint, crash_depletion (if any), constraint checks, Monte-Carlo
- `outputs/aircraft_mission_plot.png` — Flight path and state vs time
- `outputs/spacecraft_mission.json` — 7-day schedule, activities, mission value, Slew/Power checks
- `outputs/spacecraft_schedule.csv` — Schedule table (type, start_t, end_t, duration_s, target_idx)

### Run the web app

```bash
python webapp/app.py
```

Open **http://127.0.0.1:5000** in a browser. Use **Aircraft** tab to edit waypoints and params and click **Plan aircraft + Save**; use **Spacecraft** tab to set launch/orbit and **Plan 7-day + Save**; drag the globe to rotate, click to set launch.

### Run the Pygame visualization

```bash
python pygame_viz/main.py
```

Left panel: settings and tabs (Aircraft / Spacecraft / Run full). Right: map or Earth globe. Aircraft: set waypoints on map, Start mission, replay. Spacecraft: set launch (lat/lon ± or click globe), orbit altitude, Plan 7-day + Save; drag globe to rotate.

### Run validation (Monte-Carlo)

```bash
python validation/run_monte_carlo.py
```

Prints success rate and total-time range over multiple wind seeds.

## Check

### Run unit tests

```bash
pytest tests/ -v
```

All tests should pass. Optional coverage:

```bash
pytest tests/ --cov=src --cov=pygame_viz --cov=webapp --cov-report=html
```

Open `htmlcov/index.html` for the report.

### Quick sanity check

1. **Install** — `pip install -r requirements.txt` completes without error.
2. **Pipeline** — `python -m src.run_all` creates `outputs/aircraft_mission.json` and `outputs/spacecraft_mission.json`.
3. **Tests** — `pytest tests/ -v` reports all passed.
4. **Web app** — `python webapp/app.py` and open http://127.0.0.1:5000; Aircraft and Spacecraft tabs load; Plan aircraft + Save and Plan 7-day + Save run without error.
5. **Pygame** — `python pygame_viz/main.py` opens the window; Aircraft map and Spacecraft Earth view render; mission run and plan buttons work.

---

## Quick reference

| Command | Purpose |
|--------|---------|
| `pip install -r requirements.txt` | Install dependencies (after activating venv) |
| `python -m src.run_all` | Run aircraft + spacecraft from `mission_settings`; write `outputs/` |
| `pytest tests/ -v` | Run all unit tests |
| `pytest tests/ --cov=src --cov=pygame_viz --cov=webapp --cov-report=html` | Tests + HTML coverage report |
| `python webapp/app.py` | Start Flask app at http://127.0.0.1:5000 (edit aircraft/spacecraft, Plan + Save) |
| `python pygame_viz/main.py` | Start Pygame viz (map + Earth globe; drag to rotate, click to set launch) |
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
