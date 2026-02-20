"""
Unified planning method: one solver used for both aircraft and spacecraft.
Greedy construction with constraint checking.
"""
from typing import Any, Callable, List, Optional

from .constraints import Constraint
from .objective import Objective
from .variables import DecisionVariables


def solve(
    variables: DecisionVariables,
    constraints: List[Constraint],
    objective: Objective,
    max_steps: Optional[int] = 1000,
) -> Any:
    """
    Build a feasible plan using greedy construction and constraint checks.
    Used by both aircraft and spacecraft planners.

    Args:
        variables: Decision variable abstraction (candidates, add, is_complete).
        constraints: List of constraints; all must be satisfied.
        objective: Objective to maximize (higher is better).
        max_steps: Maximum plan steps to avoid infinite loops.

    Returns:
        A feasible plan (or best effort if no feasible plan found).
    """
    plan = variables.initial_plan()
    step = 0

    while not variables.is_complete(plan) and step < max_steps:
        candidates = variables.candidates(plan)
        if not candidates:
            break

        best_plan = None
        best_score = float("-inf")

        for choice in candidates:
            new_plan = variables.add(plan, choice)
            feasible = True
            for c in constraints:
                ok, violation = c.check(new_plan)
                if not ok or violation > 0:
                    feasible = False
                    break
            if not feasible:
                continue
            score = objective.evaluate(new_plan)
            if score > best_score:
                best_score = score
                best_plan = new_plan

        if best_plan is None:
            break
        plan = best_plan
        step += 1

    return plan
