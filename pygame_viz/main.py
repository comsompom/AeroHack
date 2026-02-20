"""
Pygame mission visualization: real-world map, zoom, click waypoints, drone type/settings, real-time flight.
Run from project root with PYTHONPATH set: python pygame_viz/main.py
"""
import os
import sys
import time
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pygame

from pygame_viz.map_view import MapView, TILE_SIZE
from pygame_viz.elevation import get_elevations_bulk
from pygame_viz.weather import get_weather_for_waypoints
from pygame_viz.config import DRONE_TYPES, PLANE_MODELS_WAR, PLANE_MODELS_CIVIL, DroneConfig
from pygame_viz.mission_runner import run_mission, interpolate_position, interpolate_energy
from pygame_viz.pipeline import run_aircraft_to_outputs, run_spacecraft_to_outputs, run_full_pipeline
from pygame_viz.spacecraft_view import draw_spacecraft_view, screen_to_earth_lat_lon

# Layout
MAP_WIDTH = 900
PANEL_WIDTH = 320
WIN_W = MAP_WIDTH + PANEL_WIDTH
WIN_H = 700
FPS = 60
FONT_SIZE = 18
MAX_PANEL_CONTENT_HEIGHT = 6000  # scrollable panel content
SCROLL_STEP = 40


def main():
    pygame.init()
    # Use locals for current size so resize can update them without UnboundLocalError
    map_width = MAP_WIDTH
    win_h = WIN_H
    screen = pygame.display.set_mode((map_width + PANEL_WIDTH, win_h), pygame.RESIZABLE)
    pygame.display.set_caption("DroneMission — Pygame Viz")
    font = pygame.font.Font(None, FONT_SIZE)
    clock = pygame.time.Clock()

    map_view = MapView(map_width, win_h)
    waypoints = []  # list of (lat, lon, alt_m)
    start_lat, start_lon = None, None
    mode = "add_waypoint"  # add_waypoint | set_start | idle
    default_altitude_m = 100.0  # altitude for new waypoints; checked/corrected to aircraft envelope
    drone_type_idx = 0
    weight_kg = 10.0
    size_m = 2.0
    plane_war = True
    plane_model_idx = 0
    custom_weight = 1000.0
    custom_size = 10.0
    mission_plan = None
    mission_start_time = None
    flight_speed = 40.0  # replay speed (1 sec real = 40 sec mission) so plane movement is visible
    waypoint_elevations = []
    waypoint_weather = []
    aircraft_result = None  # full output (constraint_checks, monte_carlo) after run + save
    spacecraft_result = None  # 7-day schedule result
    pipeline_message = ""  # "Run full" status
    viz_mode = 0  # 0=Aircraft, 1=Spacecraft, 2=Run full
    station_lat, station_lon = 52.0, 4.0  # launch point (ground station) for spacecraft
    spacecraft_orbit_alt_km = 400.0  # orbit altitude in km (editable in spacecraft panel)
    spacecraft_launch_weather = None  # cached weather at launch; refreshed when showing spacecraft tab
    spacecraft_weather_ts = 0.0  # time of last weather fetch
    spacecraft_earth_rotation_rad = 0.0  # drag to rotate Earth (longitude offset)
    dropdown_open = None  # None | "drone_type" | "weight" | "size" | "plane_type" | "plane_model"
    panel_scroll_y = 0  # scroll offset for left settings panel
    panel_content_height = WIN_H  # set by draw_panel
    save_in_progress = False  # True while background thread is saving mission
    mission_saved_message = ""  # "Mission created and saved. ..." after save completes
    mission_crashed = False  # True when fuel/battery depleted during replay
    mission_crash_pos = None  # (lat, lon) where vehicle crashed or failed
    mission_crash_is_plane = True  # True = plane (crash), False = drone/UAV (failing down)

    # Dropdown option values (weight kg, size m, altitude m)
    WEIGHT_OPTS = [1, 5, 10, 25, 50, 100, 500, 1100, 2200, 11600, 79000]
    SIZE_OPTS = [0.5, 1.2, 2.4, 5, 10, 11, 14.8, 20, 35.4, 35.8]
    ALTITUDE_OPTS = [50, 100, 150, 200, 300, 500, 1000, 2000, 4000]

    def panel_rect():
        return pygame.Rect(0, 0, PANEL_WIDTH, win_h)

    def map_rect():
        return pygame.Rect(PANEL_WIDTH, 0, map_width, win_h)

    def draw_panel(surf):
        """Draw panel content to surf (content space). Returns (buttons, content_height). Buttons use content-space coords."""
        surf.fill((40, 42, 46))
        buttons = []
        y = 10
        # Mode tabs: Aircraft | Spacecraft | Run full
        tab_w = 95
        tabs = [
            ("Aircraft", 0),
            ("Spacecraft", 1),
            ("Run full", 2),
        ]
        for i, (label, idx) in enumerate(tabs):
            rx = 10 + i * (tab_w + 4)
            r = pygame.Rect(rx, y, tab_w, 26)
            col = (0, 120, 80) if viz_mode == idx else (60, 60, 65)
            pygame.draw.rect(surf, col, r)
            t = font.render(label, True, (255, 255, 255))
            surf.blit(t, (rx + 6, y + 5))
            buttons.append((f"tab_{idx}", r))
        y += 32

        if viz_mode == 1:
            # --- Spacecraft panel ---
            t = font.render("7-day spacecraft mission", True, (230, 230, 230))
            surf.blit(t, (10, y))
            y += 24
            t = font.render("Targets (from waypoints):", True, (180, 180, 180))
            surf.blit(t, (10, y))
            y += 20
            tgt = [(wp[0], wp[1], 1.0) for wp in waypoints] if waypoints else [(52.5, 4.5, 1.0), (53.0, 5.0, 1.0)]
            for i, (lat, lon, v) in enumerate(tgt[:4]):
                t = font.render(f"  {lat:.2f}, {lon:.2f}", True, (200, 200, 200))
                surf.blit(t, (10, y))
                y += 18
            y += 8
            t = font.render("Drag globe to rotate. Click globe to set launch.", True, (140, 160, 180))
            surf.blit(t, (10, y))
            y += 18
            t = font.render("Launch point (lat, lon):", True, (180, 180, 180))
            surf.blit(t, (10, y))
            y += 20
            t = font.render(f"  {station_lat:.2f}, {station_lon:.2f}", True, (200, 220, 200))
            surf.blit(t, (10, y))
            y += 18
            # Lat/Lon adjust buttons: lat- lat+ lon- lon+
            bw, bh = 36, 22
            by = y
            b_la = pygame.Rect(10, by, bw, bh)
            b_lb = pygame.Rect(10 + bw + 2, by, bw, bh)
            b_lo = pygame.Rect(10 + (bw + 2) * 2, by, bw, bh)
            b_lp = pygame.Rect(10 + (bw + 2) * 3, by, bw, bh)
            for r, label in [(b_la, "lat-"), (b_lb, "lat+"), (b_lo, "lon-"), (b_lp, "lon+")]:
                pygame.draw.rect(surf, (70, 90, 110), r)
                surf.blit(font.render(label, True, (255, 255, 255)), (r.x + 2, r.y + 3))
            buttons.append(("launch_lat_down", b_la))
            buttons.append(("launch_lat_up", b_lb))
            buttons.append(("launch_lon_down", b_lo))
            buttons.append(("launch_lon_up", b_lp))
            y += bh + 4
            b_set_launch = pygame.Rect(10, y, 140, 24)
            pygame.draw.rect(surf, (60, 100, 80), b_set_launch)
            t = font.render("Set from start", True, (255, 255, 255))
            surf.blit(t, (b_set_launch.x + 8, b_set_launch.y + 4))
            buttons.append(("set_launch_from_start", b_set_launch))
            y += 30
            t = font.render("Orbit altitude (km):", True, (180, 180, 180))
            surf.blit(t, (10, y))
            y += 20
            r_alt = pygame.Rect(10, y, 80, 22)
            pygame.draw.rect(surf, (50, 52, 56), r_alt)
            pygame.draw.rect(surf, (100, 102, 106), r_alt, 1)
            surf.blit(font.render(f"{spacecraft_orbit_alt_km:.0f}", True, (220, 220, 220)), (14, y + 3))
            b_alt_up = pygame.Rect(92, y, 24, 22)
            b_alt_dn = pygame.Rect(118, y, 24, 22)
            pygame.draw.rect(surf, (70, 90, 110), b_alt_up)
            pygame.draw.rect(surf, (70, 90, 110), b_alt_dn)
            surf.blit(font.render("+", True, (255, 255, 255)), (b_alt_up.x + 7, b_alt_up.y + 2))
            surf.blit(font.render("-", True, (255, 255, 255)), (b_alt_dn.x + 8, b_alt_dn.y + 2))
            buttons.append(("orbit_alt_up", b_alt_up))
            buttons.append(("orbit_alt_dn", b_alt_dn))
            y += 28
            # Weather at launch (cached)
            t = font.render("Weather at launch:", True, (180, 180, 180))
            surf.blit(t, (10, y))
            y += 18
            if spacecraft_launch_weather:
                w = spacecraft_launch_weather
                line = f"  {w.get('temperature', '—')}°C, wind {w.get('windspeed', 0):.0f} km/h"
                t = font.render(line, True, (200, 220, 200))
                surf.blit(t, (10, y))
            else:
                t = font.render("  (fetching…)", True, (150, 150, 150))
                surf.blit(t, (10, y))
            y += 22
            b_plan = pygame.Rect(10, y, 160, 30)
            pygame.draw.rect(surf, (80, 60, 120), b_plan)
            t = font.render("Plan 7-day + Save", True, (255, 255, 255))
            surf.blit(t, (b_plan.x + 20, b_plan.y + 8))
            buttons.append(("plan_spacecraft", b_plan))
            y += 38
            if spacecraft_result is not None:
                t = font.render(f"Mission value: {spacecraft_result.get('mission_value', 0)}", True, (180, 220, 180))
                surf.blit(t, (10, y))
                y += 20
                cc = spacecraft_result.get("constraint_checks", {})
                t = font.render(f"Slew OK: {cc.get('slew_feasible', '—')}", True, (200, 200, 200))
                surf.blit(t, (10, y))
                y += 18
                t = font.render(f"Power OK: {cc.get('power_duty_ok', '—')}", True, (200, 200, 200))
                surf.blit(t, (10, y))
                y += 18
                n = len(spacecraft_result.get("activities", []))
                t = font.render(f"Activities: {n} (saved to outputs/)", True, (150, 200, 150))
                surf.blit(t, (10, y))
            return (buttons, y + 20)

        if viz_mode == 2:
            # --- Run full pipeline panel ---
            t = font.render("Run full pipeline", True, (230, 230, 230))
            surf.blit(t, (10, y))
            y += 24
            t = font.render("Aircraft: current waypoints.", True, (180, 180, 180))
            surf.blit(t, (10, y))
            y += 20
            t = font.render("Spacecraft: default targets.", True, (180, 180, 180))
            surf.blit(t, (10, y))
            y += 28
            b_full = pygame.Rect(10, y, 180, 36)
            pygame.draw.rect(surf, (100, 60, 140), b_full)
            t = font.render("Run aircraft + spacecraft", True, (255, 255, 255))
            surf.blit(t, (b_full.x + 12, b_full.y + 10))
            buttons.append(("run_full", b_full))
            y += 44
            if pipeline_message:
                for line in pipeline_message.split("\n")[:6]:
                    t = font.render(line[:38], True, (180, 220, 180))
                    surf.blit(t, (10, y))
                    y += 18
            return (buttons, y + 20)

        # --- Aircraft panel ---
        t = font.render("Aircraft mission", True, (230, 230, 230))
        surf.blit(t, (10, y))
        y += 28
        # Start
        t = font.render("Start (click map or set below):", True, (180, 180, 180))
        surf.blit(t, (10, y))
        y += 22
        if start_lat is not None:
            t = font.render(f"  {start_lat:.5f}, {start_lon:.5f}", True, (150, 255, 150))
        else:
            t = font.render("  Not set", True, (200, 100, 100))
        surf.blit(t, (10, y))
        y += 24
        # Waypoints
        t = font.render(f"Waypoints ({len(waypoints)}):", True, (180, 180, 180))
        surf.blit(t, (10, y))
        y += 22
        for i, wp in enumerate(waypoints[:30]):
            alt = wp[2] if len(wp) >= 3 else default_altitude_m
            t = font.render(f"  {i+1}. {wp[0]:.4f}, {wp[1]:.4f} @ {alt:.0f}m", True, (200, 200, 200))
            surf.blit(t, (10, y))
            y += 18
        if len(waypoints) > 30:
            t = font.render(f"  ... +{len(waypoints)-30} more", True, (150, 150, 150))
            surf.blit(t, (10, y))
            y += 18
        y += 8
        # Buttons
        btn_h = 28
        b1 = pygame.Rect(10, y, 140, btn_h)
        pygame.draw.rect(surf, (60, 120, 60), b1)
        t = font.render("Set start (click)", True, (255, 255, 255))
        surf.blit(t, (b1.x + 8, b1.y + 6))
        buttons.append(("set_start", b1))
        y += btn_h + 6
        b2 = pygame.Rect(10, y, 140, btn_h)
        pygame.draw.rect(surf, (60, 80, 120), b2)
        t = font.render("Add waypoint (click)", True, (255, 255, 255))
        surf.blit(t, (b2.x + 8, b2.y + 6))
        buttons.append(("add_wp", b2))
        y += btn_h + 6
        b3 = pygame.Rect(10, y, 140, btn_h)
        pygame.draw.rect(surf, (100, 60, 60), b3)
        t = font.render("Clear all", True, (255, 255, 255))
        surf.blit(t, (b3.x + 8, b3.y + 6))
        buttons.append(("clear", b3))
        y += btn_h + 12
        # Altitude (m) for waypoints — checked and corrected to aircraft min/max when running mission
        t = font.render("Altitude (m):", True, (180, 180, 180))
        surf.blit(t, (10, y))
        y += 20
        r_alt = pygame.Rect(10, y, 200, 24)
        pygame.draw.rect(surf, (50, 52, 56), r_alt)
        pygame.draw.rect(surf, (100, 102, 106), r_alt, 1)
        surf.blit(font.render(f"{default_altitude_m:.0f}", True, (220, 220, 220)), (14, y + 4))
        buttons.append(("dropdown_altitude", r_alt))
        y += 28
        if dropdown_open == "altitude":
            for i, a in enumerate(ALTITUDE_OPTS):
                ropt = pygame.Rect(10, y + i * 22, 200, 22)
                col = (70, 120, 80) if abs(default_altitude_m - a) < 0.01 else (50, 52, 56)
                pygame.draw.rect(surf, col, ropt)
                pygame.draw.rect(surf, (80, 82, 86), ropt, 1)
                surf.blit(font.render(f"{a:.0f} m", True, (220, 220, 220)), (14, ropt.y + 3))
                buttons.append((f"choice_altitude_{i}", ropt))
            y += len(ALTITUDE_OPTS) * 22
        y += 12
        # --- Dropdowns: Drone type, Weight, Size, Plane type, Plane model ---
        dd_box_w = 200
        dd_box_h = 24
        dd_option_h = 22
        dd_bg = (50, 52, 56)
        dd_highlight = (70, 120, 80)
        def draw_dropdown_box(ry, label_text, value_text):
            surf.blit(font.render(label_text, True, (180, 180, 180)), (10, ry - 20))
            r = pygame.Rect(10, ry, dd_box_w, dd_box_h)
            pygame.draw.rect(surf, dd_bg, r)
            pygame.draw.rect(surf, (100, 102, 106), r, 1)
            surf.blit(font.render(value_text, True, (220, 220, 220)), (14, ry + 4))
            # Arrow
            cx, cy = 10 + dd_box_w - 14, ry + dd_box_h // 2
            pygame.draw.polygon(surf, (180, 180, 180), [(cx - 4, cy - 3), (cx + 4, cy - 3), (cx, cy + 3)])
            return r
        # Drone type
        dt = DRONE_TYPES[drone_type_idx]
        r_drone = draw_dropdown_box(y + 20, "Drone type:", dt)
        buttons.append(("dropdown_drone_type", r_drone))
        y += 20 + dd_box_h
        if dropdown_open == "drone_type":
            for i, d in enumerate(DRONE_TYPES):
                ropt = pygame.Rect(10, y + i * dd_option_h, dd_box_w, dd_option_h)
                col = dd_highlight if i == drone_type_idx else dd_bg
                pygame.draw.rect(surf, col, ropt)
                pygame.draw.rect(surf, (80, 82, 86), ropt, 1)
                surf.blit(font.render(d, True, (220, 220, 220)), (14, ropt.y + 3))
                buttons.append((f"choice_drone_{i}", ropt))
            y += len(DRONE_TYPES) * dd_option_h
        y += 8
        # Weight
        r_weight = draw_dropdown_box(y + 20, "Weight (kg):", f"{weight_kg:.1f}")
        buttons.append(("dropdown_weight", r_weight))
        y += 20 + dd_box_h
        if dropdown_open == "weight":
            for i, w in enumerate(WEIGHT_OPTS):
                ropt = pygame.Rect(10, y + i * dd_option_h, dd_box_w, dd_option_h)
                col = dd_highlight if abs(weight_kg - w) < 0.01 else dd_bg
                pygame.draw.rect(surf, col, ropt)
                pygame.draw.rect(surf, (80, 82, 86), ropt, 1)
                surf.blit(font.render(f"{w} kg", True, (220, 220, 220)), (14, ropt.y + 3))
                buttons.append((f"choice_weight_{i}", ropt))
            y += len(WEIGHT_OPTS) * dd_option_h
        y += 8
        # Size
        r_size = draw_dropdown_box(y + 20, "Size (m):", f"{size_m:.1f}")
        buttons.append(("dropdown_size", r_size))
        y += 20 + dd_box_h
        if dropdown_open == "size":
            for i, s in enumerate(SIZE_OPTS):
                ropt = pygame.Rect(10, y + i * dd_option_h, dd_box_w, dd_option_h)
                col = dd_highlight if abs(size_m - s) < 0.01 else dd_bg
                pygame.draw.rect(surf, col, ropt)
                pygame.draw.rect(surf, (80, 82, 86), ropt, 1)
                surf.blit(font.render(f"{s} m", True, (220, 220, 220)), (14, ropt.y + 3))
                buttons.append((f"choice_size_{i}", ropt))
            y += len(SIZE_OPTS) * dd_option_h
        y += 8
        # Plane type and model (if Plane)
        if dt == "Plane":
            r_ptype = draw_dropdown_box(y + 20, "Plane type:", "War" if plane_war else "Civil")
            buttons.append(("dropdown_plane_type", r_ptype))
            y += 20 + dd_box_h
            if dropdown_open == "plane_type":
                for i, (label) in enumerate(["War", "Civil"]):
                    ropt = pygame.Rect(10, y + i * dd_option_h, dd_box_w, dd_option_h)
                    sel = (i == 0 and plane_war) or (i == 1 and not plane_war)
                    pygame.draw.rect(surf, dd_highlight if sel else dd_bg, ropt)
                    pygame.draw.rect(surf, (80, 82, 86), ropt, 1)
                    surf.blit(font.render(label, True, (220, 220, 220)), (14, ropt.y + 3))
                    buttons.append((f"choice_plane_type_{i}", ropt))
                y += 2 * dd_option_h
            y += 8
            models = PLANE_MODELS_WAR if plane_war else PLANE_MODELS_CIVIL
            model_name = models[plane_model_idx][0] if plane_model_idx < len(models) else "Custom"
            r_model = draw_dropdown_box(y + 20, "Plane model:", model_name)
            buttons.append(("dropdown_plane_model", r_model))
            y += 20 + dd_box_h
            if dropdown_open == "plane_model":
                for i in range(len(models)):
                    ropt = pygame.Rect(10, y + i * dd_option_h, dd_box_w, dd_option_h)
                    pygame.draw.rect(surf, dd_highlight if i == plane_model_idx else dd_bg, ropt)
                    pygame.draw.rect(surf, (80, 82, 86), ropt, 1)
                    surf.blit(font.render(models[i][0], True, (220, 220, 220)), (14, ropt.y + 3))
                    buttons.append((f"choice_plane_model_{i}", ropt))
                y += len(models) * dd_option_h
            y += 8
        y += 8
        # Fuel (plane) / Battery (drone, UAV): capacity and consumption — checked during mission; depletion = crash/fail
        is_plane = (dt == "Plane")
        cap_label = "Fuel capacity (J):" if is_plane else "Battery capacity (J):"
        cons_label = "Fuel consumption (J/s):" if is_plane else "Battery consumption (J/s):"
        surf.blit(font.render(cap_label, True, (180, 180, 180)), (10, y))
        surf.blit(font.render("  2e6 (used in mission)", True, (200, 200, 200)), (10, y + 18))
        y += 36
        surf.blit(font.render(cons_label, True, (180, 180, 180)), (10, y))
        surf.blit(font.render("  80 J/s (used in mission)", True, (200, 200, 200)), (10, y + 18))
        y += 28
        if mission_crashed:
            surf.blit(font.render("CRASHED (fuel out)" if mission_crash_is_plane else "FAILING DOWN (battery out)", True, (255, 100, 80)), (10, y))
            y += 20
        y += 6
        # Start mission
        b_go = pygame.Rect(10, y, 180, 36)
        if mission_plan is None and not save_in_progress:
            pygame.draw.rect(surf, (0, 150, 80), b_go)
            t = font.render("Start mission", True, (255, 255, 255))
        elif save_in_progress:
            pygame.draw.rect(surf, (100, 100, 60), b_go)
            t = font.render("Saving...", True, (220, 220, 180))
        else:
            pygame.draw.rect(surf, (80, 80, 80), b_go)
            t = font.render("Mission running", True, (200, 200, 200))
        surf.blit(t, (b_go.x + 20, b_go.y + 10))
        buttons.append(("start_mission", b_go))
        y += 44
        # Mission created and saved message (prominent)
        if mission_saved_message:
            for line in mission_saved_message.split("\n")[:4]:
                t = font.render(line[:42], True, (150, 255, 150))
                surf.blit(t, (10, y))
                y += 18
            y += 8
        if waypoint_elevations and waypoints:
            y += 44
            e0 = waypoint_elevations[0]
            t = font.render("Elev (WP1): " + (f"{e0:.0f}m" if e0 is not None else "—"), True, (180, 220, 180))
            surf.blit(t, (10, y))
            y += 20
        if waypoint_weather and waypoints:
            w0 = waypoint_weather[0]
            if w0:
                t = font.render(f"Weather: {w0.get('temperature', '—')}C, wind {w0.get('windspeed', 0)}km/h", True, (180, 220, 220))
            else:
                t = font.render("Weather: —", True, (150, 150, 150))
            surf.blit(t, (10, y))
        if aircraft_result:
            y += 24
            t = font.render("Constraint checks:", True, (180, 180, 180))
            surf.blit(t, (10, y))
            y += 18
            cc = aircraft_result.get("constraint_checks", {})
            t = font.render(f"  Energy: {cc.get('energy_ok', '—')}", True, (200, 200, 200))
            surf.blit(t, (10, y))
            y += 16
            t = font.render(f"  Maneuver: {cc.get('maneuver_limits_ok', '—')}", True, (200, 200, 200))
            surf.blit(t, (10, y))
            y += 16
            mc = aircraft_result.get("monte_carlo", {})
            t = font.render(f"Monte-Carlo: {mc.get('success_rate', 0)*100:.0f}% ({mc.get('runs', 0)} runs)", True, (180, 220, 180))
            surf.blit(t, (10, y))
            y += 18
            t = font.render("Saved: outputs/aircraft_mission.json", True, (150, 200, 150))
            surf.blit(t, (10, y))
        return (buttons, y + 24)

    def global_buttons(buttons_list, panel_y_offset=0):
        """Convert panel-relative buttons to screen coords (panel on left at x=0)."""
        out = []
        px = 0
        for name, r in buttons_list:
            out.append((name, pygame.Rect(px + r.x, r.y + panel_y_offset, r.w, r.h)))
        return out

    running = True
    buttons = []
    current_flight_idx = -1
    current_flight_pos = None

    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
                break
            if e.type == pygame.VIDEORESIZE:
                new_w, new_h = e.w, e.h
                if new_w > PANEL_WIDTH and new_h > 100:
                    map_width = new_w - PANEL_WIDTH
                    win_h = new_h
                    map_view.width = map_width
                    map_view.height = win_h
                    map_view.screen_center = (map_width // 2, win_h // 2)
                    screen = pygame.display.set_mode((new_w, new_h), pygame.RESIZABLE)
            if e.type == pygame.MOUSEBUTTONDOWN:
                x, y = e.pos
                if e.button == 1:
                    # Map is on the right: x in [PANEL_WIDTH, PANEL_WIDTH + map_width]
                    map_x, map_y = x - PANEL_WIDTH, y
                    if PANEL_WIDTH <= x < PANEL_WIDTH + map_width:
                        if viz_mode == 1:
                            # Spacecraft tab: click on Earth to set launch point
                            pt = screen_to_earth_lat_lon(
                                map_x, map_y, map_width, win_h, spacecraft_earth_rotation_rad
                            )
                            if pt is not None:
                                station_lat, station_lon = pt[0], pt[1]
                                spacecraft_launch_weather = None
                        elif not mission_plan and mode == "set_start":
                            start_lat, start_lon = map_view.screen_to_lat_lon(map_x, map_y)
                            waypoints = [(start_lat, start_lon, default_altitude_m)]
                            mode = "add_waypoint"
                        elif not mission_plan and mode == "add_waypoint":
                            lat, lon = map_view.screen_to_lat_lon(map_x, map_y)
                            if start_lat is None:
                                start_lat, start_lon = lat, lon
                                waypoints = [(lat, lon, default_altitude_m)]
                            else:
                                waypoints.append((lat, lon, default_altitude_m))
                    elif x < PANEL_WIDTH:
                        # Panel: buttons are in content-space; click (x,y) is screen, so content y = y + panel_scroll_y
                        content_y = y + panel_scroll_y
                        for name, r in buttons:
                            if r.collidepoint(x, content_y):
                                if name == "tab_0":
                                    viz_mode = 0
                                    dropdown_open = None
                                elif name == "tab_1":
                                    viz_mode = 1
                                    dropdown_open = None
                                elif name == "tab_2":
                                    viz_mode = 2
                                    dropdown_open = None
                                elif name == "set_launch_from_start":
                                    if start_lat is not None and start_lon is not None:
                                        station_lat, station_lon = start_lat, start_lon
                                        spacecraft_launch_weather = None
                                    dropdown_open = None
                                elif name == "orbit_alt_up":
                                    spacecraft_orbit_alt_km = min(2000.0, spacecraft_orbit_alt_km + 50.0)
                                    dropdown_open = None
                                elif name == "orbit_alt_dn":
                                    spacecraft_orbit_alt_km = max(200.0, spacecraft_orbit_alt_km - 50.0)
                                    dropdown_open = None
                                elif name == "launch_lat_up":
                                    station_lat = min(90.0, station_lat + 0.5)
                                    spacecraft_launch_weather = None
                                    dropdown_open = None
                                elif name == "launch_lat_down":
                                    station_lat = max(-90.0, station_lat - 0.5)
                                    spacecraft_launch_weather = None
                                    dropdown_open = None
                                elif name == "launch_lon_up":
                                    station_lon = (station_lon + 0.5) % 360.0
                                    if station_lon > 180:
                                        station_lon -= 360
                                    spacecraft_launch_weather = None
                                    dropdown_open = None
                                elif name == "launch_lon_down":
                                    station_lon = (station_lon - 0.5) % 360.0
                                    if station_lon > 180:
                                        station_lon -= 360
                                    spacecraft_launch_weather = None
                                    dropdown_open = None
                                elif name == "plan_spacecraft":
                                    dropdown_open = None
                                    tgt = [(wp[0], wp[1], 1.0) for wp in waypoints] if waypoints else [(52.5, 4.5, 1.0), (53.0, 5.0, 1.0)]
                                    spacecraft_result = run_spacecraft_to_outputs(tgt, station=(station_lat, station_lon), schedule_days=7, save=True)
                                elif name == "run_full":
                                    dropdown_open = None
                                    cfg = DroneConfig(DRONE_TYPES[drone_type_idx], weight_kg, size_m, "Custom", plane_war)
                                    params = cfg.to_aircraft_params()
                                    params["energy_budget"] = 2e6
                                    params["consumption_per_second"] = 80.0
                                    params["min_altitude_m"] = 0.0
                                    params["max_altitude_m"] = 4000.0
                                    params["default_altitude_m"] = default_altitude_m
                                    wps_full = [(wp[0], wp[1], wp[2] if len(wp) >= 3 else default_altitude_m) for wp in waypoints]
                                    tgt = [(wp[0], wp[1], 1.0) for wp in waypoints] if len(waypoints) >= 2 else [(52.5, 4.5, 1.0), (53.0, 5.0, 1.0)]
                                    ac, sc = run_full_pipeline(wps_full, params, spacecraft_targets=tgt, station=(station_lat, station_lon))
                                    pipeline_message = "Aircraft: " + ("saved" if ac else "skip (need 2+ waypoints)") + "\nSpacecraft: saved to outputs/"
                                elif name == "set_start":
                                    mode = "set_start"
                                    dropdown_open = None
                                elif name == "add_wp":
                                    mode = "add_waypoint"
                                    dropdown_open = None
                                elif name == "clear":
                                    waypoints = []
                                    start_lat = start_lon = None
                                    mission_plan = None
                                    aircraft_result = None
                                    mission_crashed = False
                                    mission_crash_pos = None
                                    dropdown_open = None
                                elif name == "dropdown_drone_type":
                                    dropdown_open = "drone_type" if dropdown_open != "drone_type" else None
                                elif name.startswith("choice_drone_"):
                                    drone_type_idx = int(name.split("_")[-1])
                                    dropdown_open = None
                                elif name == "dropdown_weight":
                                    dropdown_open = "weight" if dropdown_open != "weight" else None
                                elif name.startswith("choice_weight_"):
                                    weight_kg = WEIGHT_OPTS[int(name.split("_")[-1])]
                                    dropdown_open = None
                                elif name == "dropdown_size":
                                    dropdown_open = "size" if dropdown_open != "size" else None
                                elif name.startswith("choice_size_"):
                                    size_m = SIZE_OPTS[int(name.split("_")[-1])]
                                    dropdown_open = None
                                elif name == "dropdown_plane_type":
                                    dropdown_open = "plane_type" if dropdown_open != "plane_type" else None
                                elif name.startswith("choice_plane_type_"):
                                    plane_war = int(name.split("_")[-1]) == 0
                                    plane_model_idx = 0
                                    if PLANE_MODELS_WAR if plane_war else PLANE_MODELS_CIVIL:
                                        weight_kg = (PLANE_MODELS_WAR if plane_war else PLANE_MODELS_CIVIL)[0][1]
                                        size_m = (PLANE_MODELS_WAR if plane_war else PLANE_MODELS_CIVIL)[0][2]
                                    dropdown_open = None
                                elif name == "dropdown_plane_model":
                                    dropdown_open = "plane_model" if dropdown_open != "plane_model" else None
                                elif name.startswith("choice_plane_model_"):
                                    plane_model_idx = int(name.split("_")[-1])
                                    models = PLANE_MODELS_WAR if plane_war else PLANE_MODELS_CIVIL
                                    if plane_model_idx < len(models):
                                        weight_kg, size_m = models[plane_model_idx][1], models[plane_model_idx][2]
                                    dropdown_open = None
                                elif name == "dropdown_altitude":
                                    dropdown_open = "altitude" if dropdown_open != "altitude" else None
                                elif name.startswith("choice_altitude_"):
                                    default_altitude_m = ALTITUDE_OPTS[int(name.split("_")[-1])]
                                    dropdown_open = None
                                elif name == "start_mission" and mission_plan is None and not save_in_progress and len(waypoints) >= 2:
                                    dropdown_open = None
                                    cfg = DroneConfig(
                                        drone_type=DRONE_TYPES[drone_type_idx],
                                        weight_kg=weight_kg,
                                        size_m=size_m,
                                        plane_model="Custom",
                                        is_war=plane_war,
                                    )
                                    params = cfg.to_aircraft_params()
                                    params["energy_budget"] = 2e6
                                    params["consumption_per_second"] = 80.0
                                    params["min_altitude_m"] = 0.0
                                    params["max_altitude_m"] = 4000.0
                                    params["default_altitude_m"] = default_altitude_m
                                    wps_for_mission = [(wp[0], wp[1], wp[2] if len(wp) >= 3 else default_altitude_m) for wp in waypoints]
                                    # Run plan first so plane can move immediately; save in background
                                    mission_plan = run_mission(wps_for_mission, params, use_user_order=True)
                                    if mission_plan:
                                        mission_start_time = time.time()
                                        save_in_progress = True
                                        mission_saved_message = ""
                                        wps_copy = list(wps_for_mission)
                                        params_copy = dict(params)

                                        def save_mission_background():
                                            nonlocal aircraft_result, waypoint_elevations, waypoint_weather, save_in_progress, mission_saved_message
                                            try:
                                                el = get_elevations_bulk([(wp[0], wp[1]) for wp in wps_copy])
                                                wth = get_weather_for_waypoints([(wp[0], wp[1]) for wp in wps_copy])
                                                waypoint_elevations.clear()
                                                waypoint_elevations.extend(el)
                                                waypoint_weather.clear()
                                                waypoint_weather.extend(wth)
                                            except Exception:
                                                waypoint_elevations.clear()
                                                waypoint_weather.clear()
                                            aircraft_result = run_aircraft_to_outputs(wps_copy, params_copy, save=True)
                                            save_in_progress = False
                                            mission_saved_message = (
                                                "Mission created and saved.\n"
                                                "outputs/aircraft_mission.json\n"
                                                "outputs/aircraft_mission_plot.png\n"
                                                f"Waypoints: {len(wps_copy)}, Alt: {params_copy.get('default_altitude_m', 100):.0f}m, {DRONE_TYPES[drone_type_idx]}"
                                            )
                                        threading.Thread(target=save_mission_background, daemon=True).start()
                                    else:
                                        mission_plan = {}
                                        aircraft_result = None
                                break
                elif e.button == 4:
                    if x < PANEL_WIDTH:
                        panel_scroll_y = max(0, panel_scroll_y - SCROLL_STEP)
                    elif PANEL_WIDTH <= x < PANEL_WIDTH + map_width:
                        map_view.zoom_in()
                elif e.button == 5:
                    if x < PANEL_WIDTH:
                        panel_scroll_y = min(max(0, panel_content_height - win_h), panel_scroll_y + SCROLL_STEP)
                    elif PANEL_WIDTH <= x < PANEL_WIDTH + map_width:
                        map_view.zoom_out()
            # Left or right mouse button: drag to pan map (Aircraft) or rotate Earth (Spacecraft)
            if e.type == pygame.MOUSEMOTION and PANEL_WIDTH <= e.pos[0] < PANEL_WIDTH + map_width:
                if e.buttons[0] or e.buttons[2]:
                    if viz_mode == 1:
                        spacecraft_earth_rotation_rad += e.rel[0] * 0.008
                        spacecraft_earth_rotation_rad = spacecraft_earth_rotation_rad % (2 * 3.14159265359)
                    else:
                        map_view.pan(-e.rel[0], -e.rel[1])

        # Update flight position for replay (plane/drone moves along planned route; check fuel/battery)
        if mission_plan and mission_start_time is not None and mission_plan.get("timestamps"):
            elapsed = (time.time() - mission_start_time) * flight_speed
            total_t = mission_plan["timestamps"][-1]
            if not mission_crashed:
                energy_result = interpolate_energy(mission_plan, elapsed)
                if energy_result is not None:
                    energy_used, energy_budget = energy_result
                    if energy_used >= energy_budget:
                        mission_crashed = True
                        mission_crash_pos = interpolate_position(mission_plan, elapsed) or (mission_plan["waypoints"][-1][0], mission_plan["waypoints"][-1][1])
                        mission_crash_is_plane = (DRONE_TYPES[drone_type_idx] == "Plane")
            if total_t <= 0:
                current_flight_pos = (mission_plan["waypoints"][0][0], mission_plan["waypoints"][0][1]) if mission_plan.get("waypoints") else None
                current_flight_idx = 0
            elif mission_crashed and mission_crash_pos:
                current_flight_pos = mission_crash_pos
                current_flight_idx = -1
            elif elapsed >= total_t:
                current_flight_pos = (mission_plan["waypoints"][-1][0], mission_plan["waypoints"][-1][1])
                current_flight_idx = len(mission_plan["waypoints"]) - 1
            else:
                current_flight_pos = interpolate_position(mission_plan, elapsed)
                current_flight_idx = -1
            if current_flight_pos is None and mission_plan.get("waypoints"):
                current_flight_pos = (mission_plan["waypoints"][0][0], mission_plan["waypoints"][0][1])
        else:
            current_flight_pos = None
            current_flight_idx = -1

        # Refresh weather at launch when on spacecraft tab (cached 120s)
        if viz_mode == 1 and (spacecraft_launch_weather is None or time.time() - spacecraft_weather_ts > 120):
            try:
                wlist = get_weather_for_waypoints([(station_lat, station_lon)])
                if wlist:
                    spacecraft_launch_weather = wlist[0]
                    spacecraft_weather_ts = time.time()
            except Exception:
                pass
        # Draw: panel on left, map or spacecraft view on right
        screen.fill((40, 42, 46))
        map_surf = screen.subsurface(map_rect())
        map_surf.fill((30, 30, 30))
        if viz_mode == 1:
            # Spacecraft tab: full Earth with launch point and spacecraft in orbit
            draw_spacecraft_view(
                map_surf, map_width, win_h, station_lat, station_lon,
                orbit_altitude_km=spacecraft_orbit_alt_km,
                earth_rotation_rad=spacecraft_earth_rotation_rad,
            )
        else:
            # Aircraft or Run full: 2D map
            map_view.draw(map_surf)
            all_wps = waypoints if waypoints else []
            if mission_plan and mission_plan.get("waypoints"):
                map_view.draw_path_line(map_surf, mission_plan["waypoints"])
                map_view.draw_waypoint_markers(map_surf, all_wps, start_idx=0, current_idx=-1)
            else:
                map_view.draw_waypoints(map_surf, all_wps, start_idx=0, current_idx=-1)
            if current_flight_pos:
                pt = map_view.lat_lon_to_screen(current_flight_pos[0], current_flight_pos[1])
                if mission_crashed and mission_crash_pos:
                    if mission_crash_is_plane:
                        pygame.draw.circle(map_surf, (180, 40, 40), pt, 14)
                        pygame.draw.line(map_surf, (255, 255, 255), (pt[0] - 10, pt[1] - 10), (pt[0] + 10, pt[1] + 10), 3)
                        pygame.draw.line(map_surf, (255, 255, 255), (pt[0] + 10, pt[1] - 10), (pt[0] - 10, pt[1] + 10), 3)
                    else:
                        pygame.draw.circle(map_surf, (200, 80, 40), pt, 14)
                        pygame.draw.polygon(map_surf, (255, 255, 255), [(pt[0], pt[1] - 12), (pt[0] - 8, pt[1] + 10), (pt[0] + 8, pt[1] + 10)])
                else:
                    pygame.draw.circle(map_surf, (255, 200, 0), pt, 12)
                    pygame.draw.circle(map_surf, (255, 255, 255), pt, 12, 3)
        # Panel (left side): draw to tall surface, then blit visible region with scroll
        panel_content_surf = pygame.Surface((PANEL_WIDTH, MAX_PANEL_CONTENT_HEIGHT))
        buttons, panel_content_height = draw_panel(panel_content_surf)
        panel_scroll_y = max(0, min(panel_scroll_y, max(0, panel_content_height - win_h)))
        panel_visible = screen.subsurface(panel_rect())
        panel_visible.fill((40, 42, 46))
        if panel_content_height <= win_h:
            panel_visible.blit(panel_content_surf.subsurface((0, 0, PANEL_WIDTH, panel_content_height)), (0, 0))
        else:
            panel_visible.blit(panel_content_surf, (0, 0), (0, panel_scroll_y, PANEL_WIDTH, win_h))
            # Scrollbar
            sb_x = PANEL_WIDTH - 8
            thumb_h = max(24, int(win_h * win_h / panel_content_height))
            thumb_y = int((panel_scroll_y / max(1, panel_content_height - win_h)) * (win_h - thumb_h))
            pygame.draw.rect(panel_visible, (60, 62, 66), (sb_x, 0, 6, win_h))
            pygame.draw.rect(panel_visible, (100, 104, 108), (sb_x, thumb_y, 6, thumb_h))
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
