About the challenge
AeroHack is an advanced aerospace engineering challenge where teams build a single, unified mission planning + simulation framework that works for both aircraft and spacecraft. Your system must model real constraints, produce feasible mission plans, and demonstrate robustness through validation.

Your solution must complete two linked tasks:

1) Aircraft Mission Task (UAV / Fixed-Wing)
Plan and simulate a constrained flight mission that visits required waypoints while respecting:

wind (time-varying and/or spatial)

endurance / energy limits

turn-rate / bank-angle limits (or equivalent manoeuvre constraints)

geofencing / no-fly polygons and altitude restrictions
Objective: minimise mission time or energy while keeping constraint violations at zero and showing robustness under wind uncertainty (e.g., Monte-Carlo).

2) Spacecraft Mission Task (CubeSat-style LEO Ops)
Generate a 7-day mission plan that schedules:

target observations (Earth imaging / sensing opportunities)

downlinks during ground-station contact windows (or computed passes)
Subject to simplified spacecraft constraints such as:

pointing / slew-rate limits (attitude feasibility)

power/battery budget proxy

maximum operations per orbit / thermal-like duty cycle proxy
Objective: maximise total “science value” delivered (targets successfully observed and downlinked) while avoiding constraint violations.

 

Core requirement: Both tasks must use the same underlying planning concept (constraints + objective + solver/heuristic), not two unrelated scripts. The goal is to evaluate advanced skill in aerospace systems thinking, modelling, optimisation, and reproducible engineering.

Requirements
What to Build
Build a single, unified mission planning + simulation framework that handles both aircraft and spacecraft missions using the same underlying approach (constraints + objective + planning method). Your system must run end-to-end, produce mission plans, and demonstrate feasibility and robustness.

A) Aircraft Mission Module (UAV / fixed-wing)
Your software must:

Plan a route to complete a mission (e.g., visit required waypoints/targets) and output an ordered plan with timing.

Simulate the mission using a clearly defined model (at minimum: kinematic/point-mass; ideally includes turn limits/bank limits and energy/endurance).

Respect constraints, such as:

Wind (time-varying and/or spatial; show how you incorporate it)

Endurance/energy (battery or fuel budget; include a consumption model)

Maneuver limits (turn rate / bank angle / climb rate or equivalent)

Geofencing (no-fly zones as polygons) and optional altitude bands

Optimise an objective, such as:

minimum time, minimum energy, or maximum mission value

Robustness requirement: demonstrate the plan remains feasible and performs acceptably under uncertainty (e.g., multiple wind seeds / parameter variations).

Minimum outputs: flight path/waypoints with timestamps, constraint checks, and performance metrics (time/energy).

B) Spacecraft Mission Module (CubeSat-style LEO ops)
Your software must:

Model orbit/visibility at a usable level (simplified two-body + pass/visibility logic is acceptable if consistent).

Generate a 7-day mission plan that schedules:

observations of ground targets (lat/long) with time windows

downlinks to ground station(s) during contact windows (either provided or computed)

Respect constraints, such as:

pointing/slew-rate feasibility (even simplified)

power/battery proxy constraints (charging/discharge or duty cycle)

optional limits like max operations per orbit / cooldown times

Optimise an objective, such as:

maximise science value delivered (targets successfully observed and downlinked)

penalise missed downlinks, infeasible slews, or power violations

Minimum outputs: a time-ordered schedule for 7 days, contact/visibility evidence, constraint checks, and mission value metrics.

C) Unified Architecture Requirement (the key filter)
You must implement a shared planning concept across both domains:

a common way to define decision variables

a common way to define constraints

a common way to score an objective

one planning method (optimisation solver, search, heuristics + constraint repair, etc.)

 

This should not be two unrelated scripts. The goal is to evaluate systems-level engineering and reusable design.

What to Submit
1) Runnable Code (required)
A public repository link (GitHub/GitLab) or downloadable project.

A clear README that includes:

setup steps (recommended: Python + requirements.txt or equivalent)

one primary run command or notebook that executes end-to-end and produces outputs for both the aircraft and spacecraft modules

expected runtime and any hardware assumptions

A clean project structure (suggested but not required): /src, /data, /outputs, /validation, /docs.

2) Reproducible Run Steps (required)
Your README must include a “Reproduce Results” section with:

exact commands to install dependencies

exact command(s) to run the full pipeline

where the results will be saved (file paths)

how to regenerate all plots/metrics from scratch

If judges cannot reproduce outputs using your instructions, the submission may be scored lower for reproducibility.

3) Results Bundle (required — replaces video)
Provide a results bundle that demonstrates both domains (aircraft + spacecraft). This can be a zipped folder in your repo release, an /outputs folder in the repo, or linked from the Devpost submission.

Your results bundle must include:

Aircraft (required)

planned route/trajectory output (CSV/JSON or plotted figure)

constraint check summary (e.g., geofence violations = 0, energy/endurance respected)

performance metrics (e.g., total time, total energy, mission success rate)

at least one plot that shows the path and/or key state over time

Spacecraft (required)

7-day schedule output (CSV/JSON/table)

visibility/contact evidence (pass windows used or computed)

constraint check summary (e.g., pointing/power feasibility or your proxy constraints)

mission value metrics (e.g., targets captured and successfully downlinked)

at least one plot or table that makes the schedule understandable

4) Technical Report PDF (required, 4–8 pages)
Upload a PDF that explains:

problem statement (aircraft + spacecraft)

modelling assumptions and core equations

constraints and objective(s)

planning/optimisation approach (solver/heuristic/search) and justification

validation method + key results (include numbers/plots)

limitations and next steps

5) Validation Evidence (required)
Provide validation for both modules. Include at least one of the following (more is better):

Monte-Carlo / multiple-seed runs (wind and/or parameter uncertainty) with success rate

baseline comparison (simple heuristic vs your approach)

unit tests / sanity checks (e.g., conservation/limits checks, edge cases)

stress tests (harder scenarios) and how performance changes

You may place validation code/results in a /validation folder and summarise the results in the report.

6) Devpost Project Page Summary (required)
On your Devpost submission page, include:

 

a clear description of what you built

the main features and technical approach

links to the repo and the report

a short “How to Run” section (copy from README)

3–6 headline results (key metrics for aircraft + spacecraft)

