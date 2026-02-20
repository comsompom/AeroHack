"""Tests for pygame_viz.weather."""
import json
from unittest.mock import patch, MagicMock
import pytest

from pygame_viz.weather import get_weather, get_weather_for_waypoints


def test_get_weather_success():
    mock_data = {"current_weather": {"temperature": 15.0, "windspeed": 10.0}}
    with patch("urllib.request.urlopen") as mock_open:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_data).encode()
        mock_resp.__enter__ = lambda self: self
        mock_resp.__exit__ = lambda *a: None
        mock_open.return_value = mock_resp
        out = get_weather(52.0, 4.0)
    assert out == mock_data["current_weather"]


def test_get_weather_no_current_weather():
    with patch("urllib.request.urlopen") as mock_open:
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{}'
        mock_resp.__enter__ = lambda self: self
        mock_resp.__exit__ = lambda *a: None
        mock_open.return_value = mock_resp
        out = get_weather(52.0, 4.0)
    assert out is None


def test_get_weather_handles_exception():
    with patch("urllib.request.urlopen", side_effect=Exception("network error")):
        out = get_weather(52.0, 4.0)
    assert out is None


def test_get_weather_for_waypoints():
    with patch("pygame_viz.weather.get_weather") as mock_get:
        mock_get.side_effect = [{"temperature": 10}, {"temperature": 20}]
        out = get_weather_for_waypoints([(52.0, 4.0), (52.1, 4.0)])
    assert out == [{"temperature": 10}, {"temperature": 20}]
    assert mock_get.call_count == 2
