"""
Unified objective interface for mission planning.
Minimize time/energy (aircraft) or maximize science value (spacecraft) via a single interface.
"""
from abc import ABC, abstractmethod
from typing import Any


class Objective(ABC):
    """
    Single objective interface: evaluate(plan) -> float.
    Solver will maximize this value (so for minimize-time, return negative time).
    """

    @abstractmethod
    def evaluate(self, plan: Any) -> float:
        """
        Score the plan. Higher is better.
        For minimize-time: return -total_time.
        For maximize science value: return total science value.
        """
        pass

    @property
    def name(self) -> str:
        """Human-readable name for logging."""
        return self.__class__.__name__
