"""Tests for core DecisionVariables interface."""
import pytest

from src.core import DecisionVariables


class DummyVariables(DecisionVariables):
    """Minimal implementation: plan is list of ints; complete when length >= 2."""

    def initial_plan(self):
        return []

    def candidates(self, plan):
        if len(plan) >= 2:
            return []
        return [1, 2, 3]  # arbitrary choices

    def add(self, plan, choice):
        return list(plan) + [choice]

    def is_complete(self, plan):
        return len(plan) >= 2


def test_initial_plan():
    v = DummyVariables()
    p = v.initial_plan()
    assert p == []


def test_add_and_candidates():
    v = DummyVariables()
    p = v.initial_plan()
    assert v.candidates(p) == [1, 2, 3]
    p1 = v.add(p, 1)
    assert p1 == [1]
    assert v.add(p1, 2) == [1, 2]


def test_is_complete():
    v = DummyVariables()
    assert v.is_complete([]) is False
    assert v.is_complete([1]) is False
    assert v.is_complete([1, 2]) is True
