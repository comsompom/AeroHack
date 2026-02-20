"""Tests for pygame_viz.elevation."""
import json
from unittest.mock import patch, MagicMock
import pytest

from pygame_viz.elevation import get_elevation, get_elevations_bulk, OPEN_ELEVATION_URL


def test_get_elevation_success():
    mock_data = {"results": [{"elevation": 42.0}]}
    with patch("urllib.request.urlopen") as mock_open:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_data).encode()
        mock_resp.__enter__ = lambda self: self
        mock_resp.__exit__ = lambda *a: None
        mock_open.return_value = mock_resp
        out = get_elevation(52.0, 4.0)
    assert out == 42.0


def test_get_elevation_empty_results():
    with patch("urllib.request.urlopen") as mock_open:
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"results": []}'
        mock_resp.__enter__ = lambda self: self
        mock_resp.__exit__ = lambda *a: None
        mock_open.return_value = mock_resp
        out = get_elevation(52.0, 4.0)
    assert out is None


def test_get_elevation_handles_exception():
    with patch("urllib.request.urlopen", side_effect=Exception("network error")):
        out = get_elevation(52.0, 4.0)
    assert out is None


def test_get_elevations_bulk():
    with patch("pygame_viz.elevation.get_elevation") as mock_get:
        mock_get.side_effect = [10.0, 20.0, None]
        out = get_elevations_bulk([(52.0, 4.0), (52.1, 4.0), (52.2, 4.0)])
    assert out == [10.0, 20.0, None]
    assert mock_get.call_count == 3
