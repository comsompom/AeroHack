# DroneMission — Implementation Plan

Implementation plan for the AeroHack unified mission planning + simulation framework (aircraft + spacecraft) based on `description.md`.

---

## 1. High-Level Architecture

### 1.1 Unified Planning Concept (Core Requirement)

Both aircraft and spacecraft modules must share:

| Concept | Purpose | Implementation approach |
|--------|---------|--------------------------|
| **Decision variables** | What the planner chooses (e.g. waypoint order, observation times, downlink slots) | Abstract interface: `DecisionVariables` with domain-specific implementations (flight segments, observation windows, downlink windows). |
| **Constraints** | Hard/soft rules (wind, energy, geofence, slew, power, duty cycle) | Common `Constraint` interface: `check(state, plan) -> (feasible, violation)`. Each domain registers its constraint set. |
| **Objective** | What to optimize (time, energy, science value) | Single `Objective` interface: `evaluate(plan) -> float`. Wrapper for “minimize time” vs “maximize science value”. |
| **Planning method** | One solver/heuristic used for both | One entry point (e.g. constraint-based search, MIP, or heuristic + repair) that takes variables + constraints + objective and returns a plan. |

**Deliverable:** A shared core in `src/core/` (or equivalent) that both aircraft and spacecraft planners call. No two unrelated scripts; one planning “engine” with two problem formulations.

---

## 2. Project Structure

```
AeroHack/
├── src/
│   ├── core/                 # Unified planning engine
│   │   ├── variables.py      # Decision variable abstractions
│   │   ├── constraints.py    # Constraint interface + common helpers
│   │   ├── objective.py      # Objective interface
│   │   └── solver.py        # Single planning method (solver/heuristic)
│   ├── aircraft/             # Aircraft mission module
│   │   ├── model.py          # Kinematic/point-mass, turn/bank, energy
│   │   ├── constraints.py    # Wind, endurance, maneuver, geofence
│   │   ├── planner.py        # Aircraft formulation → core solver
│   │   └── simulate.py       # Mission simulation + robustness
│   ├── spacecraft/           # Spacecraft mission module
│   │   ├── orbit.py          # Two-body, passes, visibility
│   │   ├── constraints.py    # Pointing/slew, power, duty cycle
│   │   ├── planner.py        # Spacecraft formulation → core solver
│   │   └── schedule.py      # 7-day schedule builder
│   └── run_all.py            # Single entry: run both modules end-to-end
├── data/                     # Inputs (waypoints, wind, targets, TLEs, etc.)
├── outputs/                  # Generated plans, plots, metrics
├── webapp/                    # Mission visualization (Flask, cross-platform)
│   ├── app.py                # Flask entry point
│   ├── requirements.txt      # Flask, etc. (or use root requirements)
│   ├── static/               # JS, CSS, assets
│   └── templates/            # HTML pages
├── tests/                     # Unit tests (all modules); pytest
│   ├── core/                  # Tests for core/*.py
│   ├── aircraft/              # Tests for aircraft/*.py
│   ├── spacecraft/             # Tests for spacecraft/*.py
│   ├── webapp/                # Tests for webapp (routes, data loading)
│   └── conftest.py            # Shared fixtures, if needed
├── validation/                # Monte-Carlo, baselines, integration/stress
├── docs/                      # Report source, figures
├── requirements.txt           # Include pytest, pytest-cov
├── README.md
├── description.md
└── PLAN.md                   # This file
```

---

## 3. Aircraft Mission Module (UAV / Fixed-Wing)

### 3.1 Scope

- **Plan:** Route visiting required waypoints with timing.
- **Simulate:** Point-mass (min) + turn/bank limits + energy/endurance.
- **Constraints:** Wind (time/spatial), endurance/energy, maneuver limits, geofencing/altitude.
- **Objective:** Minimize time or energy; zero constraint violations.
- **Robustness:** Monte-Carlo (e.g. wind seeds) showing feasibility and acceptable performance.

### 3.2 Implementation Steps

1. **Motion & energy model (`aircraft/model.py`)**
   - Point-mass kinematics (position, heading, speed).
   - Turn rate / bank angle limits (or equivalent).
   - Optional: climb/descent rate limits.
   - Energy/battery consumption model (e.g. time + load dependent).

2. **Wind model**
   - Time-varying and/or spatial wind field (from `data/`).
   - Integration into dynamics: groundspeed = airspeed + wind; update ETA and energy.

3. **Constraint implementations (`aircraft/constraints.py`)**
   - Endurance/energy: total consumption ≤ budget.
   - Maneuver: turn rate/bank within limits at each segment.
   - Geofencing: path does not enter no-fly polygons; optional altitude bands.
   - All implemented against the core `Constraint` interface.

4. **Decision variables (aircraft)**
   - e.g. Waypoint order (or fixed order) + segment speeds/altitudes; or time at each waypoint.
   - Mapped to the shared variable abstraction used by the core solver.

5. **Aircraft planner (`aircraft/planner.py`)**
   - Builds decision variables, constraint set, and objective (min time or min energy).
   - Calls the unified solver; returns ordered plan with timestamps.

6. **Simulation & robustness**
   - Run planned trajectory through the same model + wind.
   - Monte-Carlo: multiple wind (and/or parameter) seeds; report success rate and metrics (time/energy).
   - Output: path with timestamps, constraint-check summary, performance metrics, at least one plot (path and/or state vs time).

### 3.3 Minimum Outputs (for results bundle)

- Planned route/trajectory (CSV/JSON or figure).
- Constraint check summary (geofence, energy, maneuver violations = 0).
- Performance metrics (total time, total energy, mission success rate).
- At least one plot: path and/or key state over time.

---

## 4. Spacecraft Mission Module (CubeSat LEO)

### 4.1 Scope

- **Orbit/visibility:** Simplified two-body + pass/visibility logic (consistent).
- **Plan:** 7-day schedule of target observations + downlinks in contact windows.
- **Constraints:** Pointing/slew (simplified), power/battery proxy, optional max ops per orbit / duty cycle.
- **Objective:** Maximize science value (observed + downlinked); penalize missed downlinks, infeasible slews, power violations.

### 4.2 Implementation Steps

1. **Orbit & visibility (`spacecraft/orbit.py`)**
   - Two-body propagation (SGP4 optional; simplified two-body acceptable).
   - Ground-track and pass computation for ground stations and target lat/lon.
   - Time windows: observation opportunities per target, contact windows per station.

2. **Constraint implementations (`spacecraft/constraints.py`)**
   - Pointing/slew: max slew rate; check feasibility between consecutive observations/downlinks.
   - Power/battery proxy: e.g. charge/discharge balance or duty cycle per orbit.
   - Optional: max operations per orbit, cooldown between activities.
   - All implemented against the core `Constraint` interface.

3. **Decision variables (spacecraft)**
   - e.g. Which observation windows to use, which downlink windows to use, and ordering.
   - Mapped to the shared variable abstraction.

4. **Spacecraft planner (`spacecraft/planner.py`)**
   - Builds variables, constraints, and objective (science value − penalties).
   - Calls the same unified solver; returns 7-day schedule.

5. **Schedule and value**
   - Science value: e.g. 1 per target observed and successfully downlinked; 0 if observed but not downlinked.
   - Output: time-ordered 7-day schedule, visibility/contact evidence, constraint checks, mission value metrics, at least one plot or table.

### 4.3 Minimum Outputs (for results bundle)

- 7-day schedule (CSV/JSON/table).
- Visibility/contact evidence (pass windows used or computed).
- Constraint check summary (pointing, power, etc.).
- Mission value metrics (targets captured and downlinked).
- At least one plot or table explaining the schedule.

---

## 5. Unified Solver / Planning Method

### 5.1 Options (choose one and use for both domains)

- **Discrete optimization:** MIP (e.g. PuLP, OR-Tools) with binary variables for “use this segment/window”.
- **Search:** A* or similar with state = (time, resource state, last activity); actions = next observation/downlink or next waypoint.
- **Heuristic + constraint repair:** Greedy construction (e.g. by value or time) then repair for constraints; iterate.
- **Other:** Any single method that accepts the same abstract variables + constraints + objective.

### 5.2 Implementation

- `core/solver.py` (or equivalent): one function or class that takes:
  - decision variable structure,
  - list of constraints,
  - objective function,
  and returns a feasible plan (and optionally status/metrics).
- Both `aircraft/planner.py` and `spacecraft/planner.py` call this; no duplicate solver logic.

---

## 6. Mission Visualization (Flask Web App)

Mission visualization is delivered as a **separate Flask web application** that runs on **Windows and macOS** (cross-platform). It consumes plan/schedule outputs from the core pipeline and presents them in an interactive browser UI.

### 6.1 Requirements

- **Platform:** Must run on **Windows PC** and **macOS** (Python + Flask are cross-platform; avoid OS-specific APIs).
- **Deployment:** Standalone Flask app (separate from the planning CLI/notebook); can be started with e.g. `python webapp/app.py` or `flask run` from `webapp/`.
- **Data source:** Reads from `outputs/` (or configurable path): aircraft trajectory/summary and spacecraft 7-day schedule in the same JSON/CSV formats produced by the pipeline.

### 6.2 Scope

- **Aircraft view:** Display planned route (waypoints + path) on a 2D map (e.g. Leaflet/OpenStreetMap or similar); optional altitude profile or time slider; show no-fly zones if available; display key metrics (time, energy).
- **Spacecraft view:** Display 7-day schedule (observations, downlinks) as a timeline or table; optional ground track or pass windows; mission value summary.
- **Unified entry:** Single web UI with navigation or tabs between “Aircraft mission” and “Spacecraft mission” (and optionally “Run pipeline” or “Load results” if file upload is supported).

### 6.3 Technical Approach

- **Backend:** Flask (Python 3); minimal API: serve static assets and one or more routes that return JSON for mission data (or serve pre-generated JSON from `outputs/`).
- **Frontend:** HTML/CSS/JS; use only portable libraries (no native OS bindings). For maps: Leaflet or Mapbox GL JS (both run in browser). For timelines/charts: Chart.js, D3, or similar. Ensure all assets load over HTTP from the app (no local filesystem paths in the frontend).
- **Portability:** Use `os.path` and pathlib for paths; avoid Windows/macOS-specific code. Document in README: “Run on Windows: …” and “Run on macOS: …” (same commands if possible, e.g. `pip install -r webapp/requirements.txt && python webapp/app.py`).
- **Optional:** Button or link to (re-)run the pipeline and refresh outputs, or “Load from file” to point at a different results folder.

### 6.4 Project Layout (webapp)

```
webapp/
├── app.py              # Flask app; routes for index, aircraft data, spacecraft data
├── requirements.txt    # flask, (optional: gunicorn for production)
├── static/
│   ├── css/
│   ├── js/             # Map + timeline logic, fetch mission JSON
│   └── ...
└── templates/
    ├── index.html      # Main page (tabs or nav: Aircraft | Spacecraft)
    ├── aircraft.html   # (optional) Aircraft-only view
    └── spacecraft.html # (optional) Spacecraft-only view
```

### 6.5 Deliverables

- Runnable Flask app in `webapp/` that works on Windows and macOS.
- README (or README section) describing how to install and run the web app on both platforms and where it expects `outputs/` (or equivalent).
- At least: aircraft route on a map, spacecraft schedule view, and headline metrics on the same UI.

---

## 7. Unit Test Coverage

All module logic that is created must be covered by **unit tests**. Tests live in a dedicated `tests/` directory and are run with a single test runner (e.g. pytest) on Windows and macOS.

### 7.1 Scope and Goal

- **Coverage target:** Unit tests for all non-trivial logic in `src/core/`, `src/aircraft/`, `src/spacecraft/`, and `webapp/` (backend routes and data loading). Aim for high coverage of decision logic, constraints, objectives, and solvers; exclude thin I/O or plotting where it adds little value.
- **Framework:** Use **pytest** (and optionally `pytest-cov` for coverage reports). No OS-specific test code; tests must pass on both Windows and macOS.
- **CI/local:** Document in README how to run the full test suite (e.g. `pytest tests/` or `python -m pytest tests/ -v`) and how to generate a coverage report (e.g. `pytest tests/ --cov=src --cov-report=html`).

### 7.2 Tests by Module

| Module | What to test |
|--------|----------------|
| **core/** | Decision variable interface (valid/invalid states); constraint interface (check returns feasible/violation as expected); objective interface (evaluate); solver (given mock variables/constraints/objective, returns a plan and respects constraints). Edge cases: empty plan, single-step plan. |
| **aircraft/** | **model.py:** Kinematics (position/heading update), turn/bank limits, energy consumption for known inputs. **constraints.py:** Endurance (under/over budget), maneuver limits (valid/invalid turn), geofence (inside/outside polygon, altitude band). **planner.py:** Builds valid problem for solver; output format. **simulate.py:** Simulation reproduces expected state for a simple trajectory; Monte-Carlo with fixed seed is deterministic. |
| **spacecraft/** | **orbit.py:** Two-body propagation (known position at t); pass/visibility windows for known geometry. **constraints.py:** Slew feasibility between two pointings; power/duty cycle (within/over limit). **planner.py:** Builds valid problem; schedule structure. **schedule.py:** Science value for known observation/downlink sets; time ordering. |
| **webapp/** | Flask app: routes return 200 and correct content-type; API/data routes return valid JSON for fixture data; handling of missing or malformed `outputs/` files (e.g. 404 or sensible error). No browser/JS tests required in this plan; focus on server-side logic. |

### 7.3 Test Layout and Conventions

- **Location:** `tests/core/`, `tests/aircraft/`, `tests/spacecraft/`, `tests/webapp/` mirroring `src/` and `webapp/`. Use `test_<module>.py` or `test_<feature>.py` naming (e.g. `test_constraints.py`, `test_solver.py`).
- **Fixtures:** Shared fixtures (e.g. sample waypoints, mock wind, minimal orbit state) in `tests/conftest.py` or per-package `conftest.py` to avoid duplication.
- **Data:** Use small in-code fixtures or files in `tests/fixtures/` (e.g. minimal JSON/CSV); do not depend on full `data/` or `outputs/` from a full run.
- **Isolation:** Tests must not rely on execution order. Mock external I/O (file, network) where appropriate so tests are fast and deterministic.
- **Documentation:** README “Reproduce Results” (or “Testing”) must include: install test deps (`pytest`, `pytest-cov`), command to run all unit tests, and optional command for coverage report and where it is written (e.g. `htmlcov/`).

### 7.4 Relationship to Validation

- **Unit tests** (this section): Exercise individual functions and classes in isolation; run on every change; required for all new module logic.
- **Validation** (section 8.4): Higher-level checks (Monte-Carlo, baselines, stress tests) live in `/validation` and may call the same code; they are not substitutes for unit tests. Unit test results can be summarized in the technical report under “Validation method”.

---

## 8. Reproducibility & Deliverables

### 8.1 Code & README

- **Setup:** Python + `requirements.txt` (or equivalent); clear install steps.
- **Run:** One primary command or notebook that runs both aircraft and spacecraft end-to-end.
- **Visualization:** Separate Flask web app in `/webapp`; README must include run instructions for Windows and macOS.
- **README “Reproduce Results” section:**
  - Exact install commands.
  - Exact run command(s).
  - Where results are saved (paths).
  - How to regenerate all plots/metrics from scratch.
  - How to start the mission visualization web app (Windows + macOS).
- **Project layout:** Prefer `/src`, `/data`, `/outputs`, `/webapp`, `/tests`, `/validation`, `/docs`.
- **Testing:** README must include how to run the unit test suite and (optionally) generate coverage reports (see §7).

### 8.2 Results Bundle (required)

- **Aircraft:** Route/trajectory output, constraint summary, metrics (time, energy, success rate), ≥1 plot.
- **Spacecraft:** 7-day schedule, visibility/contact evidence, constraint summary, mission value metrics, ≥1 plot/table.
- Deliver as `/outputs` in repo, or zipped release, or link from Devpost.

### 8.3 Technical Report (4–8 pages PDF)

- Problem statement (aircraft + spacecraft).
- Modelling assumptions and core equations.
- Constraints and objective(s).
- Planning/optimization approach and justification.
- Validation method and key results (numbers/plots).
- Limitations and next steps.

### 8.4 Validation Evidence

Include at least one (prefer more):

- Monte-Carlo / multi-seed runs (wind/parameter uncertainty) with success rate.
- Baseline comparison (simple heuristic vs proposed approach).
- **Unit tests:** All module logic covered by unit tests (see §7); report coverage or key test categories in the report.
- Sanity checks (conservation, limits, edge cases) — can be implemented as unit tests in `tests/`.
- Stress tests and performance under harder scenarios (in `/validation`).
- Keep integration/stress code and results in `/validation`; summarize in report.

### 8.5 Devpost Summary

- Short description of what was built.
- Main features and technical approach (including mission visualization Flask web app, Windows + macOS).
- Links to repo and report.
- “How to Run” (from README), including how to start the visualization web app.
- 3–6 headline results (aircraft + spacecraft metrics).

---

## 9. Suggested Implementation Order

1. **Core layer:** Define decision variable, constraint, and objective interfaces; implement one simple solver (e.g. greedy + constraint check). Add unit tests in `tests/core/`.
2. **Aircraft:** Model (kinematics, turn, energy), wind, constraints, then planner wired to core; simulation; then Monte-Carlo. Add unit tests in `tests/aircraft/` for each component.
3. **Spacecraft:** Orbit and visibility, constraints, planner wired to core; 7-day schedule and value computation. Add unit tests in `tests/spacecraft/`.
4. **Integration:** Single entry point (`run_all.py` or notebook) producing both outputs.
5. **Outputs & validation:** Save all required artifacts; add validation scripts and document in report.
6. **Mission visualization:** Implement Flask web app in `webapp/`; aircraft map + spacecraft schedule views; verify on Windows and macOS; add tests in `tests/webapp/` for routes and data loading; document run steps in README.
7. **Unit test coverage:** Review coverage (e.g. `pytest --cov`); add tests for any uncovered module logic; document test and coverage commands in README.
8. **Documentation:** README, “Reproduce Results”, report PDF, Devpost text.

---

## 10. Risk & Simplifications

- **Unified design:** Easiest to achieve if the solver is generic (e.g. search or MIP) and both domains express their problem in the same abstract form. Avoid domain-specific hacks inside the solver.
- **Aircraft:** If full trajectory optimization is heavy, consider discrete waypoint-to-waypoint segments with precomputed segment times/costs under nominal wind.
- **Spacecraft:** Simplified two-body + fixed altitude circular orbit is enough; SGP4 can be added later for realism. Slews can be approximated by minimum time between pointing changes.
- **Solver:** Start with a heuristic (greedy + repair) to get end-to-end quickly; swap to MIP or search later if needed for quality or constraints.
- **Visualization:** Keep the web app read-only on `outputs/` so it stays decoupled and cross-platform; avoid heavy server-side dependencies that differ between Windows and macOS.
- **Unit tests:** Add tests as each module is implemented to avoid a large test backlog; use `conftest.py` and small fixtures so tests stay fast and portable.

This plan keeps the “single underlying planning concept” requirement at the center and structures work so both aircraft and spacecraft modules are built on the same core while meeting all stated requirements and deliverables, including cross-platform mission visualization via the Flask web app and unit test coverage for all module logic.
