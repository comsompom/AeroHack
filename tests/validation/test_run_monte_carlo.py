"""Tests for validation.run_monte_carlo."""
import os
import sys
import importlib.util
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _load_run_monte_carlo_main():
    """Load main() from validation/run_monte_carlo.py without package shadowing."""
    path = os.path.join(ROOT, "validation", "run_monte_carlo.py")
    spec = importlib.util.spec_from_file_location("run_monte_carlo", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.main


def test_main_returns_dict_with_expected_keys():
    main = _load_run_monte_carlo_main()
    result = main()
    assert isinstance(result, dict)
    assert "success_rate" in result
    assert "runs" in result
    assert result["runs"] == 20
    assert 0 <= result["success_rate"] <= 1
