"""Golden regression tests for the DES V1 pricing flow.

Compares live behaviour with tests/golden/pricing_v1.json, recorded at
b3117c0. This file only reads the recording; it never writes it.
"""

import json
from pathlib import Path

import pytest

import security.rate_limit as rate_limit
from tests.golden import pricing_cases


RECORDING = json.loads(
    (Path(__file__).parent / "golden" / "pricing_v1.json").read_text(encoding="utf-8")
)


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    pricing_cases.reset_state()
    monkeypatch.setattr(rate_limit, "time", pricing_cases.fixed_time)
    yield
    pricing_cases.reset_state()


def test_recording_is_from_pinned_commit():
    assert RECORDING["source_commit"] == pricing_cases.SOURCE_COMMIT


def test_case_set_matches_recording():
    assert sorted(pricing_cases.CASES) == sorted(RECORDING["cases"])


@pytest.mark.parametrize("name", sorted(pricing_cases.CASES))
def test_pricing_case_matches_golden(name):
    group, _ = pricing_cases.CASES[name]
    recorded = RECORDING["cases"][name]

    assert recorded["group"] == group
    assert pricing_cases.run_case(name) == recorded["result"]
