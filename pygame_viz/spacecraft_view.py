"""
Full-Earth spacecraft view: real Earth texture, launch point, orbit, ascent from Earth.
Uses weather and constraints from mission; launch point and altitude are configurable.
"""
import math
import time
import os
from pathlib import Path

try:
    import pygame
except ImportError:
    pygame = None

# Earth radius km (for scale)
EARTH_R_KM = 6371.0
# NASA Blue Marble (equirectangular, small) - public domain / use for viz
EARTH_TEXTURE_URL = "https://unpkg.com/three-globe/example/img/earth-day.jpg"
CACHE_DIR = Path(__file__).resolve().parent / "cache"
_earth_texture_cache = None
_circular_earth_cache = {}
ASCENT_DURATION_REAL_SEC = 6.0  # seconds of real time for spacecraft to "lift off" from surface to orbit


def screen_to_earth_lat_lon(
    map_x: float, map_y: float, width: int, height: int, earth_rotation_rad: float = 0.0
) -> tuple[float, float] | None:
    """If (map_x, map_y) is on the Earth circle, return (lat_deg, lon_deg); else None.
    Matches draw: lx = cx + r*cos(lat)*sin(lon), ly = cy - r*sin(lat)."""
    cx = width / 2.0
    cy = height / 2.0
    earth_r_px = min(width, height) / 2.0 - 40
    dx = map_x - cx
    dy = map_y - cy
    if dx * dx + dy * dy > earth_r_px * earth_r_px:
        return None
    lat_rad = math.asin(max(-1, min(1, -dy / earth_r_px)))
    cos_lat = math.cos(lat_rad)
    if cos_lat < 1e-9:
        lon_view_rad = 0.0
    else:
        lon_view_rad = math.atan2(dx, cos_lat * earth_r_px)
    lon_rad = lon_view_rad + earth_rotation_rad
    lat_deg = math.degrees(lat_rad)
    lon_deg = math.degrees(lon_rad)
    if lon_deg > 180:
        lon_deg -= 360
    elif lon_deg < -180:
        lon_deg += 360
    return (lat_deg, lon_deg)


def _load_earth_texture():
    """Load Earth texture (equirectangular). Cache to disk; fallback to procedural."""
    global _earth_texture_cache
    if _earth_texture_cache is not None:
        return _earth_texture_cache
    if not pygame:
        return None
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / "earth_texture.jpg"
    if path.exists():
        try:
            _earth_texture_cache = pygame.image.load(str(path)).convert()
            return _earth_texture_cache
        except Exception:
            pass
    try:
        import urllib.request
        req = urllib.request.Request(EARTH_TEXTURE_URL, headers={"User-Agent": "DroneMission-Viz/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
        with open(path, "wb") as f:
            f.write(data)
        _earth_texture_cache = pygame.image.load(str(path)).convert()
        return _earth_texture_cache
    except Exception:
        pass
    # Procedural fallback: ocean blue with simple land masses (looks more like Earth than solid blue)
    W, H = 512, 256
    surf = pygame.Surface((W, H))
    surf.fill((30, 80, 150))
    for _ in range(24):
        cx = int(math.sin(_ * 0.7) * 120 + W // 2)
        cy = int(math.cos(_ * 0.5) * 60 + H // 2)
        r = 15 + _ % 20
        pygame.draw.ellipse(surf, (40, 120, 60), (cx - r, cy - r // 2, r * 2, r))
    for _ in range(12):
        cx = int(math.sin(_ * 1.1 + 1) * 100 + W // 2)
        cy = int(math.cos(_ * 0.8) * 50 + H // 2)
        pygame.draw.ellipse(surf, (60, 100, 50), (cx - 12, cy - 6, 24, 12))
    _earth_texture_cache = surf
    return _earth_texture_cache


def _make_circular_earth(surface, cx: int, cy: int, earth_r_px: int, texture, rotation_rad: float = 0.0):
    """Draw Earth as a circle with texture mapped (spherical projection). rotation_rad rotates longitude. Cached by (cx, cy, r, rot)."""
    rot_key = round(rotation_rad * 100) % (2 * 314)  # cache by 0.01 rad steps
    key = (cx, cy, earth_r_px, rot_key)
    if key in _circular_earth_cache and pygame:
        surface.blit(_circular_earth_cache[key], (cx - earth_r_px, cy - earth_r_px))
        pygame.draw.circle(surface, (80, 120, 180), (cx, cy), earth_r_px, 2)
        return
    if not pygame or texture is None:
        pygame.draw.circle(surface, (30, 60, 120), (cx, cy), earth_r_px)
        pygame.draw.circle(surface, (80, 120, 180), (cx, cy), earth_r_px, 2)
        return
    tw, th = texture.get_width(), texture.get_height()
    out = pygame.Surface((earth_r_px * 2, earth_r_px * 2))
    out.fill((0, 0, 0))
    for dy in range(-earth_r_px, earth_r_px + 1):
        for dx in range(-earth_r_px, earth_r_px + 1):
            if dx * dx + dy * dy > earth_r_px * earth_r_px:
                continue
            r = math.sqrt(dx * dx + dy * dy)
            if r < 1e-6:
                lat = 0.0
                lon = 0.0
            else:
                lat = math.asin(max(-1, min(1, dy / earth_r_px)))
                cos_lat = math.cos(lat)
                if cos_lat < 1e-6:
                    continue
                lon = math.atan2(dx, cos_lat * earth_r_px)
            lon_tex = lon + rotation_rad
            u = (lon_tex / (2 * math.pi) + 0.5) % 1.0
            v = 0.5 - lat / math.pi
            tx = int(u * tw) % tw
            ty = max(0, min(th - 1, int(v * th)))
            try:
                c = texture.get_at((tx, ty))
                out.set_at((dx + earth_r_px, dy + earth_r_px), c)
            except Exception:
                pass
    if key not in _circular_earth_cache:
        _circular_earth_cache[key] = out.copy()
    surface.blit(out, (cx - earth_r_px, cy - earth_r_px))
    pygame.draw.circle(surface, (80, 120, 180), (cx, cy), earth_r_px, 2)


def orbit_period_sec(altitude_km: float) -> float:
    """Period of circular orbit at altitude (km)."""
    mu = 398600.44
    r = EARTH_R_KM + altitude_km
    return 2 * math.pi * math.sqrt(r ** 3 / mu)


def draw_spacecraft_view(
    surface,
    width: int,
    height: int,
    launch_lat: float,
    launch_lon: float,
    orbit_altitude_km: float = 400.0,
    earth_rotation_rad: float = 0.0,
) -> None:
    """
    Draw real Earth (textured), launch point, orbit, and spacecraft.
    earth_rotation_rad: drag to rotate Earth (longitude offset in radians).
    Spacecraft animates: starts at launch point (on Earth), ascends to orbit, then orbits.
    """
    if not pygame:
        return
    cx = width // 2
    cy = height // 2
    earth_r_px = min(width, height) // 2 - 40
    orbit_r_px = earth_r_px * (EARTH_R_KM + orbit_altitude_km) / EARTH_R_KM
    orbit_r_px = min(orbit_r_px, min(width, height) // 2 - 10)

    # Earth with real-looking texture (or procedural if load fails); rotation applied
    texture = _load_earth_texture()
    _make_circular_earth(surface, cx, cy, earth_r_px, texture, rotation_rad=earth_rotation_rad)

    # Launch point on Earth surface (rotate with Earth: viewer sees lon - rotation)
    lat_rad = math.radians(launch_lat)
    lon_rad = math.radians(launch_lon) - earth_rotation_rad
    lx = cx + int(earth_r_px * math.cos(lat_rad) * math.sin(lon_rad))
    ly = cy - int(earth_r_px * math.sin(lat_rad))
    pygame.draw.circle(surface, (255, 200, 0), (lx, ly), 8)
    pygame.draw.circle(surface, (255, 255, 255), (lx, ly), 8, 2)
    try:
        font = pygame.font.Font(None, 22)
        t = font.render("Launch", True, (255, 255, 200))
        surface.blit(t, (lx - 20, ly - 24))
    except Exception:
        pass

    # Orbit circle (rotates with Earth)
    pygame.draw.circle(surface, (100, 100, 140), (cx, cy), int(orbit_r_px), 2)

    # Spacecraft: ascent phase then orbit; orbit angle rotates with Earth
    t_real = time.time()
    period = orbit_period_sec(orbit_altitude_km)
    orbit_angle = 2 * math.pi * (t_real % period) / period + earth_rotation_rad
    sx_orbit = cx + int(orbit_r_px * math.cos(orbit_angle))
    sy_orbit = cy - int(orbit_r_px * math.sin(orbit_angle))

    if t_real < ASCENT_DURATION_REAL_SEC:
        # Ascent: interpolate from launch point (on Earth) to orbit position
        f = t_real / ASCENT_DURATION_REAL_SEC
        f = f * f  # ease-in
        sx = int(lx + f * (sx_orbit - lx))
        sy = int(ly + f * (sy_orbit - ly))
        # Trajectory line from launch to current
        pygame.draw.line(surface, (180, 180, 220), (lx, ly), (sx, sy), 2)
    else:
        sx, sy = sx_orbit, sy_orbit
        # Optional: thin line from launch to spacecraft to show "from Earth"
        pygame.draw.line(surface, (80, 80, 100), (lx, ly), (sx, sy), 1)

    pygame.draw.circle(surface, (200, 220, 255), (sx, sy), 6)
    pygame.draw.circle(surface, (255, 255, 255), (sx, sy), 6, 2)
    try:
        t = font.render("Spacecraft", True, (200, 220, 255))
        surface.blit(t, (sx - 28, sy - 18))
    except Exception:
        pass
