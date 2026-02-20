"""
Generate the short technical report PDF for DroneMission — AeroHack.
Run from project root: python docs/generate_technical_report.py
Output: docs/technical_report.pdf
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer


def add_para(story, text, style_name="Normal"):
    story.append(Paragraph(text.replace("\n", "<br/>"), styles[style_name]))


def add_bullets(story, items, style_name="Normal"):
    for item in items:
        story.append(Paragraph("&#8226; " + item.replace("\n", "<br/>"), styles[style_name]))


def build_report():
    global styles
    out_path = os.path.join(ROOT, "docs", "technical_report.pdf")
    doc = SimpleDocTemplate(
        out_path,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Body", fontSize=10, spaceAfter=6, leading=14))
    story = []

    # Title
    story.append(Paragraph("DroneMission — AeroHack", styles["Title"]))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(
        "Short technical report: unified mission planning and simulation for aircraft and spacecraft.",
        styles["Normal"],
    ))
    story.append(Spacer(1, 0.6 * cm))

    # 1. Overview
    story.append(Paragraph("1. Overview", styles["Heading1"]))
    add_para(
        story,
        "The framework provides a single planning engine used for both aircraft (UAV / fixed-wing) "
        "and spacecraft (CubeSat-style LEO) missions. Both domains share: decision variables, "
        "constraints interface, objective interface, and one solver. Mission configuration is "
        "centralized in <i>src/mission_settings.py</i>; the full pipeline is run via "
        "<i>python -m src.run_all</i>.",
        "Body",
    )
    story.append(Spacer(1, 0.3 * cm))

    # 2. Architecture
    story.append(Paragraph("2. Architecture", styles["Heading1"]))
    story.append(Paragraph("2.1 Core planning engine (src/core/)", styles["Heading2"]))
    add_para(
        story,
        "Shared abstractions used by both aircraft and spacecraft planners:",
        "Body",
    )
    add_bullets(
        story,
        [
            "<b>Decision variables</b> (variables.py): what the planner chooses (e.g. waypoint order, segment times, observation/downlink windows).",
            "<b>Constraints</b> (constraints.py): common interface returning feasible/violation; each domain registers its constraint set.",
            "<b>Objective</b> (objective.py): single interface to score a plan (minimize time/energy or maximize science value).",
            "<b>Solver</b> (solver.py): one planning method (constraint-based search/heuristic) for both domains.",
        ],
        "Body",
    )
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("2.2 Aircraft module (src/aircraft/)", styles["Heading2"]))
    add_bullets(
        story,
        [
            "<b>Model</b> (model.py): point-mass kinematics, turn rate/bank limits, energy (fuel for planes, battery for drones). Wind as callable; waypoint altitude correction and depletion detection.",
            "<b>Constraints</b>: energy/endurance, maneuver limits, geofencing (no-fly polygons), altitude envelope.",
            "<b>Planner</b>: builds variables, constraints, objective; corrects waypoint altitudes; returns ordered route with timestamps and energy remaining per waypoint.",
            "<b>Simulation</b>: runs planned trajectory; Monte-Carlo over wind seeds for robustness (success rate, total-time range).",
        ],
        "Body",
    )
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("2.3 Spacecraft module (src/spacecraft/)", styles["Heading2"]))
    add_bullets(
        story,
        [
            "<b>Orbit & visibility</b> (orbit.py): two-body propagation; ground-track and pass computation; observation and contact time windows.",
            "<b>Constraints</b>: pointing/slew (min time between activities), power/duty (max active time per orbit).",
            "<b>Planner</b>: builds variables, constraints, science-value objective; returns 7-day schedule.",
            "<b>Schedule</b> (schedule.py): time-ordered activities (observations, downlinks); science value from targets observed and downlinked.",
        ],
        "Body",
    )
    story.append(Spacer(1, 0.5 * cm))

    # 3. Mission settings (summary)
    story.append(Paragraph("3. Mission settings (summary)", styles["Heading1"]))
    add_para(story, "All configurable parameters live in <i>src/mission_settings.py</i>.", "Body")
    story.append(Paragraph("Aircraft", styles["Heading2"]))
    add_bullets(
        story,
        [
            "Default route: Vilnius Airport → Warsaw Chopin → Berlin Brandenburg → Lisbon Portela (waypoints with optional altitude).",
            "Vehicle type: Plane or UAV; fuel tank or battery capacity (J); consumption (J/s); min/max/default altitude (m).",
            "No-fly zones (list of polygons); Monte-Carlo: number of seeds and RNG seed.",
        ],
        "Body",
    )
    story.append(Paragraph("Spacecraft", styles["Heading2"]))
    add_bullets(
        story,
        [
            "Orbit altitude (km); ground targets (lat, lon, science value); ground station (lat, lon).",
            "Schedule duration (days); min slew time (s); max active time per orbit (s).",
        ],
        "Body",
    )
    story.append(Spacer(1, 0.5 * cm))

    # 4. Outputs and validation
    story.append(Paragraph("4. Outputs and validation", styles["Heading1"]))
    add_para(story, "Full pipeline (<i>python -m src.run_all</i>) writes:", "Body")
    add_bullets(
        story,
        [
            "<b>outputs/aircraft_mission.json</b>: planned route (lat, lon, alt_m, t, energy_used), energy_remaining_at_waypoints, crash_depletion if any, constraint_checks, Monte-Carlo robustness.",
            "<b>outputs/aircraft_mission_plot.png</b>: flight path and state vs time.",
            "<b>outputs/spacecraft_mission.json</b>: 7-day schedule, activities, mission_value_metrics, constraint_checks (slew, power).",
            "<b>outputs/spacecraft_schedule.csv</b>: activities table (type, start_t, end_t, duration_s, target_idx).",
        ],
        "Body",
    )
    add_para(story, "Validation:", "Body")
    add_bullets(
        story,
        [
            "Monte-Carlo: <i>python validation/run_monte_carlo.py</i> prints success rate and total-time range over wind seeds.",
            "Unit tests: <i>pytest tests/ -v</i>; coverage: <i>pytest tests/ --cov=src --cov=pygame_viz --cov=webapp --cov-report=html</i> (htmlcov/index.html).",
        ],
        "Body",
    )
    story.append(Spacer(1, 0.5 * cm))

    # 5. Interfaces
    story.append(Paragraph("5. User interfaces", styles["Heading1"]))
    add_bullets(
        story,
        [
            "<b>Web app</b> (Flask): http://127.0.0.1:5000 — Aircraft and Spacecraft tabs; editable waypoints/params; Plan + Save; map and globe; APIs for planning and mission start.",
            "<b>Pygame viz</b>: map with OSM tiles, waypoints, Start mission, replay; spacecraft Full Earth globe; same planning/simulation logic as run_all.",
        ],
        "Body",
    )

    doc.build(story)
    print("Generated:", out_path)
    return out_path


if __name__ == "__main__":
    build_report()
