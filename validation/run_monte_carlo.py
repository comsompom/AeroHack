"""
Validation: Monte-Carlo runs for aircraft mission under wind uncertainty.
Run from project root with PYTHONPATH set. Produces success rate and metrics.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main():
    from src.aircraft.model import AircraftModel
    from src.aircraft.planner import plan_aircraft_mission
    from src.aircraft.simulate import monte_carlo_mission

    waypoints = [(52.0, 4.0), (52.05, 4.02), (52.1, 4.0)]
    model = AircraftModel(cruise_speed_ms=25.0, energy_budget=2e6)
    plan = plan_aircraft_mission(waypoints, model)
    result = monte_carlo_mission(plan, num_seeds=20, wind_scale=3.0, seed=123)
    print("Monte-Carlo validation (20 seeds, wind_scale=3 m/s)")
    print(f"  Success rate: {result['success_rate']:.2%}")
    print(f"  Runs: {result['runs']}")
    if result["total_times"]:
        print(f"  Total time range: {min(result['total_times']):.1f} - {max(result['total_times']):.1f} s")
    return result


if __name__ == "__main__":
    main()
