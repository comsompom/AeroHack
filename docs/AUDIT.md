# Plan & description compliance audit

Checklist of PLAN.md and description.md requirements vs implementation.

## Unified architecture (description C, plan §1)

| Requirement | Status | Location |
|-------------|--------|----------|
| Common decision variables | ✓ | `src/core/variables.py`; `AircraftVariables`, `SpacecraftVariables` |
| Common constraints interface | ✓ | `src/core/constraints.py`; aircraft/spacecraft constraints implement it |
| Common objective interface | ✓ | `src/core/objective.py`; `MinTimeObjective`, `ScienceValueObjective` |
| One planning method for both | ✓ | `src/core/solver.py`; both planners call `solve()` |

## Aircraft (description A, plan §3)

| Requirement | Status | Location |
|-------------|--------|----------|
| Route with timing | ✓ | `run_all.py` → `outputs/aircraft_mission.json` (planned_route, timestamps) |
| Point-mass + turn/bank + energy | ✓ | `src/aircraft/model.py` |
| Wind (time/spatial) | ✓ | Model accepts `wind_fn(t, lat, lon)`; nominal zero, Monte-Carlo uses random wind |
| Endurance, maneuver, geofence constraints | ✓ | `src/aircraft/constraints.py` |
| Min time/energy objective | ✓ | `MinTimeObjective` in planner |
| Monte-Carlo robustness | ✓ | `simulate.monte_carlo_mission()`; reported in JSON and `validation/run_monte_carlo.py` |
| Constraint check summary | ✓ | `constraint_checks` in aircraft_mission.json (energy_ok, endurance_respected, maneuver_limits_ok, geofence_violations) |
| At least one plot | ✓ | `outputs/aircraft_mission_plot.png` (path + state vs time) |

## Spacecraft (description B, plan §4)

| Requirement | Status | Location |
|-------------|--------|----------|
| Orbit/visibility (two-body + pass) | ✓ | `src/spacecraft/orbit.py` |
| 7-day schedule (observations + downlinks) | ✓ | `plan_spacecraft_mission()`, activities in JSON |
| Slew, power/duty constraints | ✓ | `src/spacecraft/constraints.py` |
| Maximize science value | ✓ | `ScienceValueObjective`, schedule.science_value() |
| Constraint check summary | ✓ | `constraint_checks` in spacecraft_mission.json (slew_feasible, power_duty_ok) |
| Visibility/contact evidence | ✓ | `visibility_contact_evidence` in JSON; activities have start_t/end_t |
| At least one plot or table | ✓ | `outputs/spacecraft_schedule.csv` (table) |

## Mission visualization (plan §6)

| Requirement | Status | Location |
|-------------|--------|----------|
| Flask app, Windows + macOS | ✓ | `webapp/app.py`, pathlib/portable paths |
| Reads from outputs/ | ✓ | `/api/aircraft`, `/api/spacecraft` serve JSON from outputs |
| Aircraft route on a map | ✓ | Leaflet map in `webapp/templates/index.html` |
| Spacecraft schedule (timeline/table) | ✓ | HTML table of activities in index.html |
| Tabs Aircraft \| Spacecraft | ✓ | index.html |

## Unit tests (plan §7)

| Requirement | Status | Location |
|-------------|--------|----------|
| Core (variables, constraints, objective, solver) | ✓ | `tests/core/` |
| Aircraft (model, constraints, planner, simulate) | ✓ | `tests/aircraft/` |
| Spacecraft (orbit, constraints, planner, schedule) | ✓ | `tests/spacecraft/` (incl. test_constraints.py for Slew/Power) |
| Webapp (routes, JSON) | ✓ | `tests/webapp/test_app.py` |
| pytest, coverage command in README | ✓ | README §3 |

## Reproducibility & deliverables (plan §8, description §1–2)

| Requirement | Status | Location |
|-------------|--------|----------|
| README with setup and run | ✓ | README.md |
| Reproduce Results section | ✓ | README: install, run pipeline, tests, webapp, regenerate |
| One primary run command | ✓ | `python -m src.run_all` |
| Where results are saved | ✓ | README: outputs/aircraft_mission.json, spacecraft_mission.json, plot, CSV |
| Expected runtime & hardware | ✓ | README “Expected runtime and hardware” |
| Project structure /src, /data, /outputs, /validation, /docs | ✓ | All present |

## Validation evidence (plan §8.4, description §5)

| Requirement | Status | Location |
|-------------|--------|----------|
| Monte-Carlo with success rate | ✓ | In pipeline output; `validation/run_monte_carlo.py` |
| Unit tests | ✓ | 50 tests in tests/ |

## Not in code (submission-time)

- Technical report PDF (4–8 pages): to be written; content guidance in plan §8.3.
- Devpost summary: to be filled from README + report.
- Results bundle: use `outputs/` (or zip) as per description §3.
