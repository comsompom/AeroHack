"""
Mission settings constants for plan and simulate (run_all.py).
Edit this file to change waypoints, aircraft model, spacecraft targets, and related parameters.
"""

from typing import List, Tuple

# ---------------------------------------------------------------------------
# Aircraft mission
# ---------------------------------------------------------------------------

# Waypoints: list of (lat_deg, lon_deg) or (lat_deg, lon_deg, alt_m). Altitudes checked/corrected to aircraft envelope.
# Default route: Vilnius Airport -> Warsaw -> Berlin -> Lisbon Airport
AIRCRAFT_WAYPOINTS: List[Tuple[float, ...]] = [
    (54.6341, 25.2858, 100.0),   # Vilnius Airport (VNO)
    (52.1657, 20.9671, 100.0),   # Warsaw Chopin Airport (WAW)
    (52.3625, 13.5006, 100.0),   # Berlin Brandenburg (BER)
    (38.7813, -9.1359, 100.0),   # Lisbon Portela Airport (LIS)
]

# Aircraft model parameters
AIRCRAFT_CRUISE_SPEED_MS = 25.0
AIRCRAFT_MAX_TURN_RATE_DEGS = 15.0
# Energy: use battery for drones (UAV) and fuel tank for planes. Consumption applied to both.
AIRCRAFT_ENERGY_BUDGET = 2e6  # fallback if type-specific not set
AIRCRAFT_VEHICLE_TYPE = "Plane"  # "Plane" | "UAV" (drone)
AIRCRAFT_FUEL_TANK_CAPACITY_J = 2e6   # fuel capacity (J) for planes
AIRCRAFT_BATTERY_CAPACITY_J = 2e6    # battery capacity (J) for drones
AIRCRAFT_CONSUMPTION_PER_SECOND = 80.0
AIRCRAFT_MIN_ALTITUDE_M = 0.0
AIRCRAFT_MAX_ALTITUDE_M = 4000.0
AIRCRAFT_DEFAULT_ALTITUDE_M = 100.0

# No-fly zones: list of polygons, each polygon = list of (lat, lon). Empty = none.
AIRCRAFT_NO_FLY_ZONES: List[List[Tuple[float, float]]] = []

# Monte-Carlo robustness: number of wind seeds and RNG seed
MONTE_CARLO_NUM_SEEDS = 10
MONTE_CARLO_SEED = 42

# ---------------------------------------------------------------------------
# Spacecraft mission
# ---------------------------------------------------------------------------

# Orbit altitude (km)
SPACECRAFT_ALTITUDE_KM = 400.0

# Ground targets: list of (lat_deg, lon_deg, science_value)
SPACECRAFT_TARGETS: List[Tuple[float, float, float]] = [
    (52.5, 4.5, 1.0),
    (53.0, 5.0, 1.0),
    (51.0, 3.0, 1.0),
]

# Ground station (lat_deg, lon_deg)
SPACECRAFT_STATION: Tuple[float, float] = (52.0, 4.0)

# Schedule duration (days)
SPACECRAFT_SCHEDULE_DAYS = 7

# Constraint parameters
SPACECRAFT_MIN_SLEW_TIME_S = 60.0
SPACECRAFT_MAX_ACTIVE_PER_ORBIT_S = 600.0
