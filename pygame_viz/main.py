"""
Pygame mission visualization: real-world map, zoom, click waypoints, drone type/settings, real-time flight.
Run from project root with PYTHONPATH set: python pygame_viz/main.py
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pygame

from pygame_viz.map_view import MapView, TILE_SIZE
from pygame_viz.elevation import get_elevations_bulk
from pygame_viz.weather import get_weather_for_waypoints
from pygame_viz.config import DRONE_TYPES, PLANE_MODELS_WAR, PLANE_MODELS_CIVIL, DroneConfig
from pygame_viz.mission_runner import run_mission, interpolate_position
from pygame_viz.pipeline import run_aircraft_to_outputs, run_spacecraft_to_outputs, run_full_pipeline

# Layout
MAP_WIDTH = 900
PANEL_WIDTH = 320
WIN_W = MAP_WIDTH + PANEL_WIDTH
WIN_H = 700
FPS = 60
FONT_SIZE = 18


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
    waypoints = []
    start_lat, start_lon = None, None
    mode = "add_waypoint"  # add_waypoint | set_start | idle
    drone_type_idx = 0
    weight_kg = 10.0
    size_m = 2.0
    plane_war = True
    plane_model_idx = 0
    custom_weight = 1000.0
    custom_size = 10.0
    mission_plan = None
    mission_start_time = None
    flight_speed = 1.0  # time multiplier
    waypoint_elevations = []
    waypoint_weather = []
    aircraft_result = None  # full output (constraint_checks, monte_carlo) after run + save
    spacecraft_result = None  # 7-day schedule result
    pipeline_message = ""  # "Run full" status
    viz_mode = 0  # 0=Aircraft, 1=Spacecraft, 2=Run full
    station_lat, station_lon = 52.0, 4.0  # ground station for spacecraft

    def panel_rect():
        return pygame.Rect(map_width, 0, PANEL_WIDTH, win_h)

    def draw_panel():
        surf = screen.subsurface(panel_rect())
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
            y += 6
            t = font.render(f"Station: {station_lat:.2f}, {station_lon:.2f}", True, (180, 180, 180))
            surf.blit(t, (10, y))
            y += 24
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
            return buttons

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
            return buttons

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
        for i, wp in enumerate(waypoints[:8]):
            t = font.render(f"  {i+1}. {wp[0]:.4f}, {wp[1]:.4f}", True, (200, 200, 200))
            surf.blit(t, (10, y))
            y += 18
        if len(waypoints) > 8:
            t = font.render(f"  ... +{len(waypoints)-8} more", True, (150, 150, 150))
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
        y += btn_h + 20
        # Drone type
        t = font.render("Drone type:", True, (180, 180, 180))
        surf.blit(t, (10, y))
        y += 22
        dt = DRONE_TYPES[drone_type_idx]
        t = font.render(f"  [{dt}] < >", True, (200, 200, 200))
        surf.blit(t, (10, y))
        b_left = pygame.Rect(10, y - 2, 24, 22)
        b_right = pygame.Rect(36, y - 2, 24, 22)
        buttons.append(("drone_left", b_left))
        buttons.append(("drone_right", b_right))
        y += 28
        # Weight / Size (with +/-)
        t = font.render(f"Weight (kg): {weight_kg:.1f}  [-] [+]", True, (200, 200, 200))
        surf.blit(t, (10, y))
        b_wmin = pygame.Rect(130, y - 2, 22, 20)
        b_wplus = pygame.Rect(158, y - 2, 22, 20)
        buttons.append(("weight_min", b_wmin))
        buttons.append(("weight_plus", b_wplus))
        y += 24
        t = font.render(f"Size (m): {size_m:.1f}  [-] [+]", True, (200, 200, 200))
        surf.blit(t, (10, y))
        b_smin = pygame.Rect(110, y - 2, 22, 20)
        b_splus = pygame.Rect(138, y - 2, 22, 20)
        buttons.append(("size_min", b_smin))
        buttons.append(("size_plus", b_splus))
        y += 28
        # Plane model (if Plane)
        if dt == "Plane":
            t = font.render("Plane: [War] [Civil]", True, (180, 180, 180))
            surf.blit(t, (10, y))
            b_war = pygame.Rect(10, y + 18, 60, 22)
            b_civil = pygame.Rect(74, y + 18, 60, 22)
            buttons.append(("plane_war", b_war))
            buttons.append(("plane_civil", b_civil))
            y += 44
            models = PLANE_MODELS_WAR if plane_war else PLANE_MODELS_CIVIL
            name = models[plane_model_idx][0] if plane_model_idx < len(models) else "Custom"
            t = font.render(f"  {name} < >", True, (200, 200, 200))
            surf.blit(t, (10, y))
            b_pleft = pygame.Rect(10, y - 2, 24, 22)
            b_pright = pygame.Rect(36, y - 2, 24, 22)
            buttons.append(("plane_left", b_pleft))
            buttons.append(("plane_right", b_pright))
            y += 28
        y += 10
        # Start mission
        b_go = pygame.Rect(10, y, 180, 36)
        if mission_plan is None:
            pygame.draw.rect(surf, (0, 150, 80), b_go)
            t = font.render("Start mission", True, (255, 255, 255))
        else:
            pygame.draw.rect(surf, (80, 80, 80), b_go)
            t = font.render("Mission running...", True, (200, 200, 200))
        surf.blit(t, (b_go.x + 20, b_go.y + 10))
        buttons.append(("start_mission", b_go))
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
        return buttons

    def global_buttons(buttons_list, panel_y_offset=0):
        """Convert panel-relative buttons to screen coords."""
        out = []
        px = map_width
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
                    if x < map_width and not mission_plan:
                        if mode == "set_start":
                            start_lat, start_lon = map_view.screen_to_lat_lon(x, y)
                            waypoints = [(start_lat, start_lon)]
                            mode = "add_waypoint"
                        elif mode == "add_waypoint":
                            lat, lon = map_view.screen_to_lat_lon(x, y)
                            if start_lat is None:
                                start_lat, start_lon = lat, lon
                                waypoints = [(lat, lon)]
                            else:
                                waypoints.append((lat, lon))
                    else:
                        for name, r in global_buttons(buttons, 0):
                            if r.collidepoint(x, y):
                                if name == "tab_0":
                                    viz_mode = 0
                                elif name == "tab_1":
                                    viz_mode = 1
                                elif name == "tab_2":
                                    viz_mode = 2
                                elif name == "plan_spacecraft":
                                    tgt = [(wp[0], wp[1], 1.0) for wp in waypoints] if waypoints else [(52.5, 4.5, 1.0), (53.0, 5.0, 1.0)]
                                    spacecraft_result = run_spacecraft_to_outputs(tgt, station=(station_lat, station_lon), schedule_days=7, save=True)
                                elif name == "run_full":
                                    cfg = DroneConfig(DRONE_TYPES[drone_type_idx], weight_kg, size_m, "Custom", plane_war)
                                    params = cfg.to_aircraft_params()
                                    params["energy_budget"] = 2e6
                                    params["consumption_per_second"] = 80.0
                                    tgt = [(wp[0], wp[1], 1.0) for wp in waypoints] if len(waypoints) >= 2 else [(52.5, 4.5, 1.0), (53.0, 5.0, 1.0)]
                                    ac, sc = run_full_pipeline(waypoints, params, spacecraft_targets=tgt, station=(station_lat, station_lon))
                                    pipeline_message = "Aircraft: " + ("saved" if ac else "skip (need 2+ waypoints)") + "\nSpacecraft: saved to outputs/"
                                elif name == "set_start":
                                    mode = "set_start"
                                elif name == "add_wp":
                                    mode = "add_waypoint"
                                elif name == "clear":
                                    waypoints = []
                                    start_lat = start_lon = None
                                    mission_plan = None
                                    aircraft_result = None
                                elif name == "drone_left":
                                    drone_type_idx = (drone_type_idx - 1) % len(DRONE_TYPES)
                                elif name == "drone_right":
                                    drone_type_idx = (drone_type_idx + 1) % len(DRONE_TYPES)
                                elif name == "plane_left":
                                    models = PLANE_MODELS_WAR if plane_war else PLANE_MODELS_CIVIL
                                    plane_model_idx = (plane_model_idx - 1) % max(len(models), 1)
                                    if models:
                                        weight_kg, size_m = models[plane_model_idx][1], models[plane_model_idx][2]
                                elif name == "plane_right":
                                    models = PLANE_MODELS_WAR if plane_war else PLANE_MODELS_CIVIL
                                    plane_model_idx = (plane_model_idx + 1) % max(len(models), 1)
                                    if models:
                                        weight_kg, size_m = models[plane_model_idx][1], models[plane_model_idx][2]
                                elif name == "weight_min":
                                    weight_kg = max(0.1, weight_kg - 1)
                                elif name == "weight_plus":
                                    weight_kg = min(50000, weight_kg + 1)
                                elif name == "size_min":
                                    size_m = max(0.1, size_m - 0.5)
                                elif name == "size_plus":
                                    size_m = min(100, size_m + 0.5)
                                elif name == "plane_war":
                                    plane_war = True
                                    plane_model_idx = 0
                                elif name == "plane_civil":
                                    plane_war = False
                                    plane_model_idx = 0
                                elif name == "start_mission" and mission_plan is None and len(waypoints) >= 2:
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
                                    mission_plan = run_mission(waypoints, params)
                                    if mission_plan:
                                        mission_start_time = time.time()
                                        try:
                                            waypoint_elevations = get_elevations_bulk(waypoints)
                                            waypoint_weather = get_weather_for_waypoints(waypoints)
                                        except Exception:
                                            waypoint_elevations = []
                                            waypoint_weather = []
                                        aircraft_result = run_aircraft_to_outputs(waypoints, params, save=True)
                                    else:
                                        mission_plan = {}
                                        aircraft_result = None
                                break
                elif e.button == 4 and x < map_width:
                    map_view.zoom_in()
                elif e.button == 5 and x < map_width:
                    map_view.zoom_out()
            if e.type == pygame.MOUSEMOTION and e.buttons[0] and 0 <= e.pos[0] < map_width:
                map_view.pan(-e.rel[0], -e.rel[1])

        # Update flight position for replay
        if mission_plan and mission_start_time is not None and mission_plan.get("timestamps"):
            elapsed = (time.time() - mission_start_time) * flight_speed
            total_t = mission_plan["timestamps"][-1]
            if elapsed >= total_t:
                current_flight_pos = (mission_plan["waypoints"][-1][0], mission_plan["waypoints"][-1][1])
                current_flight_idx = len(mission_plan["waypoints"]) - 1
            else:
                current_flight_pos = interpolate_position(mission_plan, elapsed)
                current_flight_idx = -1
        else:
            current_flight_pos = None
            current_flight_idx = -1

        # Draw
        screen.fill((30, 30, 30))
        map_view.draw(screen)
        all_wps = waypoints if waypoints else []
        if mission_plan and mission_plan.get("waypoints"):
            map_view.draw_waypoints(screen, mission_plan["waypoints"], start_idx=0, current_idx=current_flight_idx)
        else:
            map_view.draw_waypoints(screen, all_wps, start_idx=0, current_idx=-1)
        if current_flight_pos:
            pt = map_view.lat_lon_to_screen(current_flight_pos[0], current_flight_pos[1])
            pygame.draw.circle(screen, (255, 200, 0), pt, 12)
            pygame.draw.circle(screen, (255, 255, 255), pt, 12, 3)
        buttons = draw_panel()
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
