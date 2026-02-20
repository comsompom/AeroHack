"""
Real-world map in Pygame using OSM tiles. Zoom, pan, lat/lon <-> screen conversion.
"""
import math
import os
import threading
import urllib.request
from pathlib import Path

import pygame

# OSM tile server (use tile.openstreetmap.org; respect usage policy)
TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
TILE_SIZE = 256
CACHE_DIR = Path(__file__).resolve().parent / "tile_cache"
USER_AGENT = "DroneMission-Viz/1.0"


def lat_lon_to_tile(lat: float, lon: float, zoom: int) -> tuple:
    """Convert WGS84 lat, lon to OSM tile x, y at given zoom."""
    n = 2 ** zoom
    x = (lon + 180) / 360 * n
    lat_rad = math.radians(lat)
    y = (1 - math.asinh(math.tan(lat_rad)) / math.pi) / 2 * n
    return (x, y)


def tile_to_screen(tx: float, ty: float, tile_origin_screen, zoom_scale) -> tuple:
    """Tile coords to screen pixel (float)."""
    sx = (tx - tile_origin_screen[0]) * TILE_SIZE * zoom_scale
    sy = (ty - tile_origin_screen[1]) * TILE_SIZE * zoom_scale
    return (sx, sy)


def lat_lon_to_screen(lat: float, lon: float, center_lat: float, center_lon: float, zoom: int, screen_center) -> tuple:
    """Convert lat/lon to screen pixel given map center and zoom."""
    cx_t, cy_t = lat_lon_to_tile(center_lat, center_lon, zoom)
    px_t, py_t = lat_lon_to_tile(lat, lon, zoom)
    sx = screen_center[0] + (px_t - cx_t) * TILE_SIZE
    sy = screen_center[1] + (py_t - cy_t) * TILE_SIZE
    return (int(sx), int(sy))


def screen_to_lat_lon(sx: float, sy: float, center_lat: float, center_lon: float, zoom: int, screen_center) -> tuple:
    """Convert screen pixel to lat/lon."""
    cx_t, cy_t = lat_lon_to_tile(center_lat, center_lon, zoom)
    dx = (sx - screen_center[0]) / TILE_SIZE
    dy = (sy - screen_center[1]) / TILE_SIZE
    px_t = cx_t + dx
    py_t = cy_t + dy
    n = 2 ** zoom
    lon = px_t / n * 360 - 180
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * py_t / n)))
    lat = math.degrees(lat_rad)
    return (lat, lon)


def fetch_tile(z: int, x: int, y: int) -> pygame.Surface | None:
    """Load tile image; use cache if present. Returns None on failure."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    sub = CACHE_DIR / str(z) / str(x)
    sub.mkdir(parents=True, exist_ok=True)
    path = sub / f"{y}.png"
    if path.exists():
        try:
            return pygame.image.load(str(path)).convert()
        except Exception:
            pass
    url = TILE_URL.format(z=z, x=x, y=y)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = resp.read()
        with open(path, "wb") as f:
            f.write(data)
        return pygame.image.load(str(path)).convert()
    except Exception:
        return None


class MapView:
    """Pygame map: OSM tiles, zoom, pan, draw waypoints and drone."""

    MAX_LOAD_PER_FRAME = 2  # load at most this many tiles per draw to keep UI responsive

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.center_lat = 52.0
        self.center_lon = 4.0
        self.zoom = 6
        self.screen_center = (width // 2, height // 2)
        self._tile_cache = {}
        self._load_queue = []  # list of (z, x, y) to load; we load a few per frame

    def pan(self, dx_px: float, dy_px: float):
        """Pan map by dx_px, dy_px (screen pixels)."""
        self.center_lat, self.center_lon = screen_to_lat_lon(
            self.screen_center[0] - dx_px,
            self.screen_center[1] - dy_px,
            self.center_lat,
            self.center_lon,
            self.zoom,
            self.screen_center,
        )
        self.center_lat = max(-85, min(85, self.center_lat))

    def zoom_in(self):
        if self.zoom < 18:
            self.zoom += 1

    def zoom_out(self):
        if self.zoom > 2:
            self.zoom -= 1

    def lat_lon_to_screen(self, lat: float, lon: float) -> tuple:
        return lat_lon_to_screen(lat, lon, self.center_lat, self.center_lon, self.zoom, self.screen_center)

    def screen_to_lat_lon(self, sx: float, sy: float) -> tuple:
        return screen_to_lat_lon(sx, sy, self.center_lat, self.center_lon, self.zoom, self.screen_center)

    def _tiles_visible(self):
        """Yield (z, x, y) for tiles that cover the current view."""
        cx_t, cy_t = lat_lon_to_tile(self.center_lat, self.center_lon, self.zoom)
        tiles_wide = (self.width // TILE_SIZE) + 2
        tiles_high = (self.height // TILE_SIZE) + 2
        x0 = int(cx_t - tiles_wide / 2)
        y0 = int(cy_t - tiles_high / 2)
        n = 2 ** self.zoom
        for dx in range(tiles_wide + 1):
            for dy in range(tiles_high + 1):
                x = (x0 + dx) % n
                y = max(0, min(2 ** self.zoom - 1, y0 + dy))
                yield (self.zoom, int(x), int(y))

    def draw(self, surface: pygame.Surface):
        cx_t, cy_t = lat_lon_to_tile(self.center_lat, self.center_lon, self.zoom)
        visible = list(self._tiles_visible())
        # Queue visible tiles that aren't cached (avoid blocking: don't fetch all in one frame)
        for (z, tx, ty) in visible:
            key = (z, tx, ty)
            if key not in self._tile_cache and key not in self._load_queue:
                self._load_queue.append(key)
        self._load_queue = self._load_queue[:40]  # cap queue size
        # Load at most MAX_LOAD_PER_FRAME tiles this frame (keeps map responsive)
        for _ in range(self.MAX_LOAD_PER_FRAME):
            if not self._load_queue:
                break
            z, tx, ty = self._load_queue.pop(0)
            key = (z, tx, ty)
            if key in self._tile_cache:
                continue
            tile = fetch_tile(z, tx, ty)
            if tile:
                self._tile_cache[key] = tile
        # Draw: use cache or gray placeholder
        for (z, tx, ty) in visible:
            key = (z, tx, ty)
            sx = int(self.screen_center[0] + (tx - cx_t) * TILE_SIZE)
            sy = int(self.screen_center[1] + (ty - cy_t) * TILE_SIZE)
            if key in self._tile_cache:
                surface.blit(self._tile_cache[key], (sx, sy))
            else:
                surface.fill((60, 60, 60), (sx, sy, TILE_SIZE, TILE_SIZE))

    def _get_lat_lon(self, wp):
        if isinstance(wp, (list, tuple)):
            return wp[0], wp[1]
        return wp.get("lat", 0), wp.get("lon", 0)

    def draw_path_line(self, surface: pygame.Surface, waypoints: list):
        """Draw only the path line (no markers). Waypoints in (lat, lon) or (lat, lon, alt) form."""
        if len(waypoints) < 2:
            return
        pts = [self.lat_lon_to_screen(*self._get_lat_lon(wp)) for wp in waypoints]
        for j in range(len(pts) - 1):
            pygame.draw.line(surface, (100, 100, 255), pts[j], pts[j + 1], 2)

    def draw_waypoint_markers(self, surface: pygame.Surface, waypoints: list, start_idx: int = 0, current_idx: int = -1):
        """Draw only waypoint circles (no line). start_idx = green, current_idx = yellow, else blue."""
        for i, wp in enumerate(waypoints):
            lat, lon = self._get_lat_lon(wp)
            pt = self.lat_lon_to_screen(lat, lon)
            if not (0 <= pt[0] < self.width and 0 <= pt[1] < self.height):
                continue
            if i == start_idx:
                color = (0, 200, 0)
            elif i == current_idx:
                color = (255, 200, 0)
            else:
                color = (50, 150, 255)
            pygame.draw.circle(surface, color, pt, 8)
            pygame.draw.circle(surface, (255, 255, 255), pt, 8, 2)

    def draw_waypoints(self, surface: pygame.Surface, waypoints: list, start_idx: int = 0, current_idx: int = -1):
        """Draw waypoint markers and path line. start_idx = which is start; current_idx = current in flight (-1 = none)."""
        self.draw_waypoint_markers(surface, waypoints, start_idx, current_idx)
        self.draw_path_line(surface, waypoints)
