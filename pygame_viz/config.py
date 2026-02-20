"""
Drone types and plane models (war / civil). Weight (kg), size (m) for UI.
"""
from dataclasses import dataclass
from typing import List, Tuple

DRONE_TYPES = ["UAV", "Plane", "Spacecraft", "Quadcopter"]

# Predefined plane models: (name, weight_kg, wingspan_m, category)
PLANE_MODELS_WAR = [
    ("MQ-9 Reaper", 2200, 20),
    ("Global Hawk", 11600, 35.4),
    ("Predator", 500, 14.8),
    ("TB2 Bayraktar", 650, 12),
]

PLANE_MODELS_CIVIL = [
    ("Cessna 172", 1100, 11),
    ("Boeing 737", 79000, 35.8),
    ("DJI Agras", 25, 2.4),
    ("Small UAV", 5, 1.2),
]


@dataclass
class DroneConfig:
    drone_type: str  # UAV, Plane, Spacecraft, Quadcopter
    weight_kg: float
    size_m: float  # wingspan or characteristic size
    plane_model: str  # predefined name or "Custom"
    is_war: bool  # for Plane: True = war, False = civil

    def to_aircraft_params(self) -> dict:
        """Map to AircraftModel-like params (cruise speed, etc.)."""
        if self.drone_type == "Quadcopter":
            return {"cruise_speed_ms": 15.0, "max_turn_rate_degs": 90.0}
        if self.drone_type == "Plane":
            return {"cruise_speed_ms": 25.0, "max_turn_rate_degs": 15.0}
        if self.drone_type == "UAV":
            return {"cruise_speed_ms": 20.0, "max_turn_rate_degs": 20.0}
        # Spacecraft: not used for aircraft planner
        return {"cruise_speed_ms": 25.0, "max_turn_rate_degs": 15.0}
