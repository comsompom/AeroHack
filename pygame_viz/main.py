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
from pygame_viz.elevation import get_elevation, get_elevations_bulk
from pygame_viz.weather import get_weather_for_waypoints
from pygame_viz.config import DRONE_TYPES, PLANE_MODELS_WAR, PLANE_MODELS_CIVIL, DroneConfig
from pygame_viz.mission_runner import run_mission, interpolate_position

# Layout
MAP_WIDTH = 900
PANEL_WIDTH = 320
WIN_W = MAP_WIDTH + PANEL_WIDTH
WIN_H = 700
FPS = 60
FONT_SIZE = 18


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIN_W, WIN_H), pygame.RESIZABLE)
    pygame.display.set_caption("DroneMission — Pygame Viz")
    font = pygame.font.Font(None, FONT_SIZE)
    clock = pygame.time.Clock()

    map_view = MapView(MAP_WIDTH, WIN_H)
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

    def panel_rect():
        return pygame.Rect(MAP_WIDTH, 0, PANEL_WIDTH, WIN_H)

    def draw_panel():
        surf = screen.subsurface(panel_rect())
        surf.fill((40, 42, 46))
        y = 10
        # Title
        t = font.render("Mission setup", True, (230, 230, 230))
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
        buttons = []
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
        return buttons

    def global_buttons(buttons_list, panel_y_offset=0):
        """Convert panel-relative buttons to screen coords."""
        out = []
        px = MAP_WIDTH
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
                    MAP_WIDTH = new_w - PANEL_WIDTH
                    map_view.width = MAP_WIDTH
                    map_view.height = new_h
                    map_view.screen_center = (MAP_WIDTH // 2, new_h // 2)
                    screen = pygame.display.set_mode((new_w, new_h), pygame.RESIZABLE)
            if e.type == pygame.MOUSEBUTTONDOWN:
                x, y = e.pos
                if e.button == 1:
                    if x < MAP_WIDTH and not mission_plan:
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
                                if name == "set_start":
                                    mode = "set_start"
                                elif name == "add_wp":
                                    mode = "add_waypoint"
                                elif name == "clear":
                                    waypoints = []
                                    start_lat = start_lon = None
                                    mission_plan = None
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
                                    else:
                                        mission_plan = {}
                                break
                elif e.button == 4 and x < MAP_WIDTH:
                    map_view.zoom_in()
                elif e.button == 5 and x < MAP_WIDTH:
                    map_view.zoom_out()
            if e.type == pygame.MOUSEMOTION and e.buttons[0] and 0 <= e.pos[0] < MAP_WIDTH:
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
