"""Tests for core Objective interface."""
import pytest

from src.core import Objective


class SumObjective(Objective):
    """Maximize sum of plan elements (for lists of numbers)."""

    def evaluate(self, plan):
        return sum(plan) if plan else 0.0


class NegLengthObjective(Objective):
    """Minimize length = maximize -len(plan)."""

    def evaluate(self, plan):
        return -len(plan) if plan else 0.0


def test_objective_evaluate():
    o = SumObjective()
    assert o.evaluate([]) == 0.0
    assert o.evaluate([1, 2, 3]) == 6.0


def test_objective_name():
    assert SumObjective().name == "SumObjective"


def test_neg_length():
    o = NegLengthObjective()
    assert o.evaluate([1, 2]) > o.evaluate([1, 2, 3])
