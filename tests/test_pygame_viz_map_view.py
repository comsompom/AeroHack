"""Tests for pygame_viz.map_view (pure functions and MapView logic, no display)."""
import os
import pytest

from pygame_viz.map_view import (
    lat_lon_to_tile,
    tile_to_screen,
    lat_lon_to_screen,
    screen_to_lat_lon,
    TILE_SIZE,
)


def test_lat_lon_to_tile_zoom_zero():
    x, y = lat_lon_to_tile(0.0, 0.0, 0)
    assert x == 0.5
    assert 0 <= y <= 1


def test_lat_lon_to_tile_consistency():
    lat, lon = 52.0, 4.0
    zoom = 10
    x, y = lat_lon_to_tile(lat, lon, zoom)
    assert 0 <= x <= 2 ** zoom
    assert 0 <= y <= 2 ** zoom


def test_tile_to_screen():
    sx, sy = tile_to_screen(1.0, 2.0, (0.0, 0.0), 1.0)
    assert sx == TILE_SIZE * 1.0
    assert sy == TILE_SIZE * 2.0


def test_lat_lon_to_screen_center():
    center_lat, center_lon = 52.0, 4.0
    zoom = 10
    screen_center = (400, 300)
    sx, sy = lat_lon_to_screen(center_lat, center_lon, center_lat, center_lon, zoom, screen_center)
    assert sx == screen_center[0]
    assert sy == screen_center[1]


def test_screen_to_lat_lon_roundtrip():
    lat, lon = 52.5, 4.5
    zoom = 8
    screen_center = (320, 240)
    sx, sy = lat_lon_to_screen(lat, lon, 52.0, 4.0, zoom, screen_center)
    lat2, lon2 = screen_to_lat_lon(sx, sy, 52.0, 4.0, zoom, screen_center)
    assert abs(lat2 - lat) < 0.01
    assert abs(lon2 - lon) < 0.01


def test_map_view_pan_zoom():
    """Test MapView pan/zoom without creating display."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame
    pygame.init()
    try:
        from pygame_viz.map_view import MapView
        m = MapView(800, 600)
        orig_lat, orig_lon = m.center_lat, m.center_lon
        m.pan(10, 20)
        assert (m.center_lat, m.center_lon) != (orig_lat, orig_lon)
        z = m.zoom
        m.zoom_in()
        assert m.zoom == z + 1
        m.zoom_out()
        assert m.zoom == z
    finally:
        pygame.quit()
