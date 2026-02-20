"""
Unified decision variable abstraction for mission planning.
Both aircraft and spacecraft planners use this interface.
"""
from abc import ABC, abstractmethod
from typing import Any, List


class DecisionVariables(ABC):
    """
    Abstract interface for decision variables.
    Domain-specific implementations: flight segments (aircraft), observation/downlink windows (spacecraft).
    """

    @abstractmethod
    def initial_plan(self) -> Any:
        """Return an empty or initial plan structure."""
        pass

    @abstractmethod
    def candidates(self, plan: Any) -> List[Any]:
        """Return list of possible next choices (steps) given current plan."""
        pass

    @abstractmethod
    def add(self, plan: Any, choice: Any) -> Any:
        """Return a new plan with the given choice appended. Do not mutate plan."""
        pass

    @abstractmethod
    def is_complete(self, plan: Any) -> bool:
        """Return True if the plan is complete (mission fulfilled)."""
        pass
