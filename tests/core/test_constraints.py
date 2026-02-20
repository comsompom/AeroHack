"""Tests for core Constraint interface."""
import pytest

from src.core import Constraint


class AlwaysFeasible(Constraint):
    def check(self, plan):
        return True, 0.0


class AlwaysInfeasible(Constraint):
    def check(self, plan):
        return False, 1.5


class LengthLimit(Constraint):
    def __init__(self, max_len):
        self.max_len = max_len

    def check(self, plan):
        n = len(plan) if hasattr(plan, "__len__") else 0
        if n <= self.max_len:
            return True, 0.0
        return False, float(n - self.max_len)


def test_constraint_feasible():
    c = AlwaysFeasible()
    ok, v = c.check([1, 2, 3])
    assert ok is True
    assert v == 0.0


def test_constraint_infeasible():
    c = AlwaysInfeasible()
    ok, v = c.check(None)
    assert ok is False
    assert v == 1.5


def test_constraint_name():
    assert AlwaysFeasible().name == "AlwaysFeasible"


def test_length_limit():
    c = LengthLimit(2)
    assert c.check([1]) == (True, 0.0)
    assert c.check([1, 2]) == (True, 0.0)
    ok, v = c.check([1, 2, 3])
    assert ok is False
    assert v == 1.0
