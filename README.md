# DroneMission — AeroHack

Unified mission planning + simulation framework for **aircraft** (UAV/fixed-wing) and **spacecraft** (CubeSat-style LEO). Both use the same core planning concept: decision variables, constraints, objective, and a single solver.

## Project layout

- `src/` — Core planning engine and domain modules
  - `core/` — Decision variables, constraints, objective, solver (shared)
  - `aircraft/` — Kinematics, wind, constraints, planner, simulation
  - `spacecraft/` — Orbit/visibility, constraints, planner, 7-day schedule
  - `run_all.py` — Single entry: run both missions and write outputs
- `webapp/` — Mission visualization (Flask; Windows + macOS)
- `data/` — Input data (waypoints, wind, targets)
- `outputs/` — Generated plans (JSON), plots, metrics
- `tests/` — Unit tests (core, aircraft, spacecraft, webapp)
- `validation/` — Monte-Carlo, baselines, stress
- `docs/` — Report, figures

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

- `outputs/aircraft_mission.json` — Planned route, timestamps, total time/energy, Monte-Carlo success rate
- `outputs/spacecraft_mission.json` — 7-day schedule, activities, mission value

### 3. Run unit tests

```bash
pytest tests/ -v
```

Optional coverage report:

```bash
pytest tests/ --cov=src --cov=webapp --cov-report=html
```

Report is written to `htmlcov/index.html`.

### 4. Start the mission visualization web app (Windows + macOS)

```bash
pip install flask   # if not already installed
python webapp/app.py
```

Then open **http://127.0.0.1:5000** in a browser. The app reads from `outputs/` and shows aircraft route and spacecraft schedule with metrics.

- **Windows:** Same commands in PowerShell or Command Prompt (use `.\\.venv\\Scripts\\activate` if needed).
- **macOS:** Use `source .venv/bin/activate` and the same `python` commands.

### 5. Regenerate plots/metrics from scratch

1. Run `python -m src.run_all` again (overwrites `outputs/*.json`).
2. Restart the web app and refresh the page to see updated data.

## Quick reference

| Command | Purpose |
|--------|---------|
| `python -m src.run_all` | Run aircraft + spacecraft planning; write `outputs/` |
| `pytest tests/ -v` | Run all unit tests |
| `pytest tests/ --cov=src --cov-report=html` | Tests + coverage report |
| `python webapp/app.py` | Start visualization at http://127.0.0.1:5000 |

## Requirements

- Python 3.8+
- See `requirements.txt` (numpy, matplotlib, pytest, pytest-cov, flask)

## Expected runtime and hardware

- **Full pipeline** (`python -m src.run_all`): typically 5–30 seconds depending on machine (aircraft planning + simulation + Monte-Carlo, then spacecraft 7-day schedule).
- **Unit tests** (`pytest tests/ -v`): under 1 second.
- **Hardware:** No GPU required. Standard CPU and a few hundred MB RAM are sufficient. The web app runs in the browser; no special hardware for visualization.
