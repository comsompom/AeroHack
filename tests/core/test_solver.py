"""Tests for core solver (greedy + constraint check)."""
import pytest

from src.core import Constraint, DecisionVariables, Objective, solve


class ListVars(DecisionVariables):
    """Plan = list of ints; complete when len >= 2. Candidates = [1, 2, 3] until then."""

    def initial_plan(self):
        return []

    def candidates(self, plan):
        if len(plan) >= 2:
            return []
        return [1, 2, 3]

    def add(self, plan, choice):
        return list(plan) + [choice]

    def is_complete(self, plan):
        return len(plan) >= 2


class MaxSum(Objective):
    def evaluate(self, plan):
        return sum(plan) if plan else 0.0


class NoFour(Constraint):
    def check(self, plan):
        if 4 in (plan or []):
            return False, 1.0
        return True, 0.0


def test_solver_returns_plan():
    plan = solve(ListVars(), [], MaxSum())
    assert isinstance(plan, list)
    assert len(plan) == 2  # complete
    assert sum(plan) >= 2  # at least 1+1


def test_solver_respects_constraint():
    # If we only allow small numbers via a constraint that rejects 3 when plan already has 3
    class RejectSecondThree(Constraint):
        def check(self, plan):
            if plan and plan.count(3) > 1:
                return False, 1.0
            return True, 0.0

    plan = solve(ListVars(), [RejectSecondThree()], MaxSum())
    assert plan is not None
    ok, _ = RejectSecondThree().check(plan)
    assert ok


def test_solver_empty_candidates_stops():
    class OneStepVars(DecisionVariables):
        def initial_plan(self):
            return []

        def candidates(self, plan):
            return []  # no candidates ever

        def add(self, plan, choice):
            return list(plan) + [choice]

        def is_complete(self, plan):
            return len(plan) >= 1

    plan = solve(OneStepVars(), [], MaxSum())
    assert plan == []


def test_solver_single_step_plan():
    class SingleStepVars(DecisionVariables):
        def initial_plan(self):
            return []

        def candidates(self, plan):
            if len(plan) >= 1:
                return []
            return [42]

        def add(self, plan, choice):
            return list(plan) + [choice]

        def is_complete(self, plan):
            return len(plan) >= 1

    plan = solve(SingleStepVars(), [], MaxSum())
    assert plan == [42]
