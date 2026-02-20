"""
Aircraft point-mass kinematics, turn/bank limits, and energy model.
Flat-earth 2D; positions in (lat, lon) degrees; heading in degrees; time in seconds.
"""
import math
from dataclasses import dataclass, field
from typing import Callable, List, Tuple

# Earth radius approx for m/deg conversion at mid-latitudes
EARTH_R_M = 111_320.0  # m per degree lat (approx); lon scaled by cos(lat)


@dataclass
class AircraftState:
    """State at one instant: position, heading, time, energy used."""

    lat: float
    lon: float
    heading_deg: float
    t: float
    energy_used: float

    def copy(self) -> "AircraftState":
        return AircraftState(
            self.lat, self.lon, self.heading_deg, self.t, self.energy_used
        )


def _norm_angle_deg(a: float) -> float:
    """Normalize angle to [-180, 180]."""
    while a > 180:
        a -= 360
    while a < -180:
        a += 360
    return a


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Bearing from (lat1,lon1) to (lat2,lon2) in degrees [0, 360)."""
    if abs(lat2 - lat1) < 1e-9 and abs(lon2 - lon1) < 1e-9:
        return 0.0
    dlon = math.radians(lon2 - lon1)
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    x = math.sin(dlon) * math.cos(lat2_r)
    y = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(lat2_r) * math.cos(dlon)
    br = math.atan2(x, y)
    return _norm_angle_deg(math.degrees(br)) % 360.0


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Approximate distance in meters (haversine-style flat approx for small distances)."""
    dlat = (lat2 - lat1) * EARTH_R_M
    dlon = (lon2 - lon1) * EARTH_R_M * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot(dlat, dlon)


def turn_angle_deg(heading_from: float, heading_to: float) -> float:
    """Smallest signed turn from heading_from to heading_to in degrees."""
    d = _norm_angle_deg(heading_to - heading_from)
    return d


def waypoint_altitude(wp: Tuple) -> float:
    """Return altitude in meters from waypoint (lat, lon) or (lat, lon, alt_m). Default 100 m."""
    if len(wp) >= 3:
        return float(wp[2])
    return 100.0


def correct_waypoint_altitudes(
    waypoints: List[Tuple],
    min_altitude_m: float,
    max_altitude_m: float,
    default_altitude_m: float = 100.0,
) -> List[Tuple[float, float, float]]:
    """
    Normalize waypoints to (lat, lon, alt_m) and clamp altitudes to aircraft envelope.
    If altitude is missing or outside [min_altitude_m, max_altitude_m], it is set to the nearest limit or default.
    Waypoint = (lat, lon) or (lat, lon, alt_m). Returns list of (lat, lon, alt_m).
    """
    out = []
    for wp in waypoints:
        lat, lon = float(wp[0]), float(wp[1])
        alt = waypoint_altitude(wp) if len(wp) >= 3 else default_altitude_m
        alt = max(min_altitude_m, min(max_altitude_m, alt))
        out.append((lat, lon, alt))
    return out


class AircraftModel:
    """
    Point-mass kinematics with turn rate limit and energy consumption.
    Wind is provided by a callable wind(t, lat, lon) -> (v_north, v_east) m/s.
    Altitude limits define the operating envelope; waypoint altitudes are checked and corrected to stay within them.
    """

    def __init__(
        self,
        cruise_speed_ms: float = 25.0,
        max_turn_rate_degs: float = 15.0,
        energy_budget: float = 1e6,
        consumption_per_second: float = 100.0,
        turn_penalty_per_deg: float = 2.0,
        min_altitude_m: float = 0.0,
        max_altitude_m: float = 4000.0,
        default_altitude_m: float = 100.0,
    ):
        self.cruise_speed_ms = cruise_speed_ms
        self.max_turn_rate_degs = max_turn_rate_degs
        self.energy_budget = energy_budget
        self.consumption_per_second = consumption_per_second
        self.turn_penalty_per_deg = turn_penalty_per_deg
        self.min_altitude_m = min_altitude_m
        self.max_altitude_m = max_altitude_m
        self.default_altitude_m = default_altitude_m

    def wind_nominal(self, t: float, lat: float, lon: float) -> Tuple[float, float]:
        """Default wind: zero. Override or pass different callable for time/spatial wind."""
        return 0.0, 0.0

    def segment_time_s(
        self,
        lat0: float,
        lon0: float,
        lat1: float,
        lon1: float,
        wind_fn: Callable[[float, float, float], Tuple[float, float]],
        t0: float = 0.0,
    ) -> float:
        """
        Time to fly straight from (lat0,lon0) to (lat1,lon1) with wind.
        Uses average position for wind; airspeed = cruise_speed_ms; groundspeed = airspeed + wind.
        """
        dist = distance_m(lat0, lon0, lat1, lon1)
        if dist < 1e-6:
            return 0.0
        v_n, v_e = wind_fn(t0, (lat0 + lat1) / 2, (lon0 + lon1) / 2)
        br = math.radians(bearing_deg(lat0, lon0, lat1, lon1))
        # Ground velocity component along track
        v_along = self.cruise_speed_ms * math.cos(0) + (v_n * math.cos(br) + v_e * math.sin(br))
        v_along = max(v_along, 1.0)  # avoid zero/negative
        return dist / v_along

    def segment_energy(self, dt: float, turn_deg: float = 0.0) -> float:
        """Energy consumed in dt seconds with turn_deg change in heading."""
        return dt * self.consumption_per_second + abs(turn_deg) * self.turn_penalty_per_deg

    def turn_time_s(self, turn_deg: float) -> float:
        """Time required to turn by turn_deg at max_turn_rate."""
        if abs(turn_deg) < 1e-6:
            return 0.0
        return abs(turn_deg) / self.max_turn_rate_degs

    def fly_segment(
        self,
        state: AircraftState,
        lat1: float,
        lon1: float,
        wind_fn: Callable[[float, float, float], Tuple[float, float]],
    ) -> Tuple[AircraftState, float, float]:
        """
        Advance state from current position to (lat1, lon1).
        Returns (new_state, segment_time_s, segment_energy).
        """
        turn = turn_angle_deg(state.heading_deg, bearing_deg(state.lat, state.lon, lat1, lon1))
        turn_t = self.turn_time_s(turn)
        fly_t = self.segment_time_s(
            state.lat, state.lon, lat1, lon1, wind_fn, state.t + turn_t
        )
        dt = turn_t + fly_t
        energy = self.segment_energy(fly_t, turn) + turn_t * self.consumption_per_second

        new_state = AircraftState(
            lat=lat1,
            lon=lon1,
            heading_deg=bearing_deg(state.lat, state.lon, lat1, lon1),
            t=state.t + dt,
            energy_used=state.energy_used + energy,
        )
        return new_state, dt, energy

    def simulate_path(
        self,
        waypoints: List[Tuple[float, float]],
        initial_state: AircraftState,
        wind_fn: Callable[[float, float, float], Tuple[float, float]],
    ) -> Tuple[List[AircraftState], float, float]:
        """
        Simulate flying through waypoints in order.
        Returns (list of states at each waypoint, total_time, total_energy).
        """
        states = [initial_state]
        for i in range(1, len(waypoints)):
            lat1, lon1 = waypoints[i]
            new_state, _dt, _de = self.fly_segment(states[-1], lat1, lon1, wind_fn)
            states.append(new_state)
        total_time = states[-1].t - initial_state.t
        total_energy = states[-1].energy_used - initial_state.energy_used
        return states, total_time, total_energy
