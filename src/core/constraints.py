"""
Unified constraint interface for mission planning.
Both aircraft and spacecraft use this; each domain implements its own constraints.
"""
from abc import ABC, abstractmethod
from typing import Any, Tuple


class Constraint(ABC):
    """
    Common constraint interface: check(state, plan) -> (feasible, violation).
    """

    @abstractmethod
    def check(self, plan: Any) -> Tuple[bool, float]:
        """
        Check constraint for the given plan.
        Returns:
            feasible: True if constraint is satisfied
            violation: non-negative value (0 if feasible); magnitude of violation if infeasible
        """
        pass

    @property
    def name(self) -> str:
        """Human-readable name for logging."""
        return self.__class__.__name__
