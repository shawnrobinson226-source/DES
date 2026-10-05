"""Strict replay of the pricing golden recording.

Python == treats True == 1 and 1 == 1.0, so the plain golden comparison can
miss a bool/int/float change. This replay compares JSON value types as well
as values. Dictionary key order is ignored; list order is preserved.
"""

import json
from pathlib import Path

import pytest

import security.rate_limit as rate_limit
from tests.golden import pricing_cases


RECORDING = json.loads(
    (Path(__file__).parent / "golden" / "pricing_v1.json").read_text(encoding="utf-8")
)


def strict_diff(expected, actual, path="$"):
    """Return a list of differences; an empty list means strictly equal."""
    if type(expected) is not type(actual):
        return [f"{path}: type {type(expected).__name__} != {type(actual).__name__}"]

    if isinstance(expected, dict):
        diffs = []
        for key in sorted(expected.keys() - actual.keys(), key=repr):
            diffs.append(f"{path}.{key}: missing")
        for key in sorted(actual.keys() - expected.keys(), key=repr):
            diffs.append(f"{path}.{key}: unexpected")
        for key in sorted(expected.keys() & actual.keys(), key=repr):
            diffs.extend(strict_diff(expected[key], actual[key], f"{path}.{key}"))
        return diffs

    if isinstance(expected, list):
        if len(expected) != len(actual):
            return [f"{path}: length {len(expected)} != {len(actual)}"]
        diffs = []
        for index, (left, right) in enumerate(zip(expected, actual)):
            diffs.extend(strict_diff(left, right, f"{path}[{index}]"))
        return diffs

    if expected != actual:
        return [f"{path}: {expected!r} != {actual!r}"]

    return []


# --- comparator unit tests ---

def test_bool_differs_from_int():
    assert strict_diff(True, 1) != []
    assert strict_diff(False, 0) != []
    assert strict_diff({"done": False}, {"done": 0}) != []


def test_int_differs_from_float():
    assert strict_diff(1, 1.0) != []
    assert strict_diff({"count": 10}, {"count": 10.0}) != []


def test_none_differs_from_false():
    assert strict_diff(None, False) != []


def test_dict_key_order_is_ignored():
    assert strict_diff({"a": 1, "b": 2}, {"b": 2, "a": 1}) == []


def test_extra_and_missing_keys_differ():
    assert strict_diff({"a": 1}, {"a": 1, "b": 2}) == ["$.b: unexpected"]
    assert strict_diff({"a": 1, "b": 2}, {"a": 1}) == ["$.b: missing"]


def test_list_order_is_preserved():
    assert strict_diff([1, 2], [2, 1]) != []
    assert strict_diff([1, 2], [1, 2, 3]) != []


def test_list_differs_from_tuple():
    assert strict_diff([1, 2], (1, 2)) != []


def test_nested_difference_reports_path():
    expected = {"output": {"ui": {"recommend_exit": True}}}
    actual = {"output": {"ui": {"recommend_exit": 1}}}
    assert strict_diff(expected, actual) == ["$.output.ui.recommend_exit: type bool != int"]


def test_identical_nested_values_are_equal():
    value = {"a": [1, 2.5, "x", None, True, {"b": False}]}
    assert strict_diff(value, json.loads(json.dumps(value))) == []


# --- strict replay ---

@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    pricing_cases.reset_state()
    monkeypatch.setattr(rate_limit, "time", pricing_cases.fixed_time)
    yield
    pricing_cases.reset_state()


@pytest.mark.parametrize("name", sorted(pricing_cases.CASES))
def test_pricing_case_matches_golden_strictly(name):
    recorded = RECORDING["cases"][name]["result"]

    assert strict_diff(recorded, pricing_cases.run_case(name)) == []
