"""
Full-Earth spacecraft view: globe, launch point, orbit, and spacecraft position.
"""
import math
import time

try:
    import pygame
except ImportError:
    pygame = None

# Earth radius km (for scale)
EARTH_R_KM = 6371.0


def orbit_period_sec(altitude_km: float) -> float:
    """Period of circular orbit at altitude (km)."""
    mu = 398600.44  # km^3/s^2
    r = EARTH_R_KM + altitude_km
    return 2 * math.pi * math.sqrt(r ** 3 / mu)


def draw_spacecraft_view(
    surface,
    width: int,
    height: int,
    launch_lat: float,
    launch_lon: float,
    orbit_altitude_km: float = 400.0,
) -> None:
    """
    Draw full Earth (globe), launch point on the surface, orbit circle, and spacecraft moving along orbit.
    """
    if not pygame:
        return
    cx = width // 2
    cy = height // 2
    earth_r_px = min(width, height) // 2 - 40
    # Earth: blue-green globe
    pygame.draw.circle(surface, (30, 60, 120), (cx, cy), earth_r_px)
    pygame.draw.circle(surface, (80, 120, 180), (cx, cy), earth_r_px, 2)
    # Launch point on Earth surface (lat/lon -> point on circle)
    lat_rad = math.radians(launch_lat)
    lon_rad = math.radians(launch_lon)
    lx = cx + int(earth_r_px * math.cos(lat_rad) * math.sin(lon_rad))
    ly = cy - int(earth_r_px * math.sin(lat_rad))
    pygame.draw.circle(surface, (255, 200, 0), (lx, ly), 8)
    pygame.draw.circle(surface, (255, 255, 255), (lx, ly), 8, 2)
    # Label
    try:
        font = pygame.font.Font(None, 22)
        t = font.render("Launch", True, (255, 255, 200))
        surface.blit(t, (lx - 20, ly - 24))
    except Exception:
        pass
    # Orbit circle (spacecraft path)
    orbit_r_px = earth_r_px * (EARTH_R_KM + orbit_altitude_km) / EARTH_R_KM
    orbit_r_px = min(orbit_r_px, min(width, height) // 2 - 10)
    pygame.draw.circle(surface, (100, 100, 140), (cx, cy), int(orbit_r_px), 2)
    # Spacecraft position on orbit (animated)
    period = orbit_period_sec(orbit_altitude_km)
    angle = 2 * math.pi * (time.time() % period) / period
    sx = cx + int(orbit_r_px * math.cos(angle))
    sy = cy - int(orbit_r_px * math.sin(angle))
    pygame.draw.circle(surface, (200, 220, 255), (sx, sy), 6)
    pygame.draw.circle(surface, (255, 255, 255), (sx, sy), 6, 2)
    try:
        t = font.render("Spacecraft", True, (200, 220, 255))
        surface.blit(t, (sx - 28, sy - 18))
    except Exception:
        pass
