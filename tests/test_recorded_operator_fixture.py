"""Real-loopback fixture recording, normalization, and drift coverage."""

import hashlib
import json
import uuid
from pathlib import Path

import pytest

from tools.record_operator_contract_v1 import (
    FORBIDDEN_AXIS_ENV,
    NORMALIZED_IDS,
    RUNTIME_COMMIT,
    render_fixture,
)


ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "operator_contract_v1_recorded.json"


def test_recorder_refuses_even_empty_axis_settings():
    for name in FORBIDDEN_AXIS_ENV:
        with pytest.raises(RuntimeError, match=name):
            render_fixture(environ={name: ""})


def test_recorder_is_byte_stable_across_two_real_loopback_runs():
    first = render_fixture(environ={})
    second = render_fixture(environ={})
    assert first == second

    regenerated = json.loads(first)
    committed = json.loads(FIXTURE.read_text(encoding="utf-8"))

    # Runtime metadata records the environment used for the checked-in capture;
    # semantic drift is checked independently so another interpreter can run
    # the suite without rewriting provenance.
    assert regenerated["recorded_wire"] == committed["recorded_wire"]
    assert regenerated["contract_derived"] == committed["contract_derived"]
    assert regenerated["normalizations"] == committed["normalizations"]


def test_recorded_fixture_provenance_and_scenarios_are_complete():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert fixture["contract_version"] == "1.0.0"
    assert fixture["question_set"] == {
        "id": "tri_operator_classification", "version": "1.0.0"}
    assert fixture["des_runtime_commit"] == RUNTIME_COMMIT
    assert fixture["server_tree_clean_against_runtime_commit"] is True
    assert set(fixture["runtime"]) == {"python", "fastapi", "uvicorn"}
    assert fixture["recorder"] == "DES tools/record_operator_contract_v1.py"
    assert fixture["normalization_version"] == "1"
    assert fixture["canonicalization"] == (
        "UTF-8 JSON, sorted keys, no insignificant whitespace")
    assert fixture["hash_scope"] == (
        "normalized request bodies, HTTP status codes, and response bodies; "
        "provenance fields are excluded")

    wire = fixture["recorded_wire"]
    assert set(wire) == {
        "full_length_resolved",
        "short_resolved",
        "explicit_unresolved",
        "invalid_option",
        "out_of_order",
        "interaction_closed",
        "interaction_not_found",
        "default_empty",
    }
    assert all(
        step["status"] == 200
        for scenario in wire.values()
        for step in scenario
    )
    assert wire["full_length_resolved"][-1]["response"]["classification"] == "perceptual"
    assert wire["short_resolved"][1]["response"]["question"]["id"] == "q3"
    assert wire["short_resolved"][-1]["response"]["classification"] == "continuity"
    assert wire["explicit_unresolved"][-1]["response"]["reason"] == "EXPLICIT_UNRESOLVED"
    assert wire["invalid_option"][-1]["response"]["code"] == "INVALID_OPTION"
    assert wire["out_of_order"][-1]["response"]["code"] == "OUT_OF_ORDER"
    assert wire["interaction_closed"][-1]["response"]["code"] == "INTERACTION_CLOSED"
    assert wire["interaction_not_found"][-1]["response"]["code"] == "INTERACTION_NOT_FOUND"
    assert wire["default_empty"][-1]["response"]["code"] == "QUESTION_SET_UNAVAILABLE"

    for value in NORMALIZED_IDS.values():
        parsed = uuid.UUID(value)
        assert parsed.version == 4
        assert parsed.variant == uuid.RFC_4122

    canonical = json.dumps(
        wire, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    assert fixture["normalized_wire_sha256"] == hashlib.sha256(canonical).hexdigest()


def test_non_wire_cases_are_explicitly_contract_derived():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    derived = fixture["contract_derived"]
    assert derived["result_validation_failed"] == {
        "error": "Result validation failed",
        "code": "RESULT_VALIDATION_FAILED",
    }
    assert derived["no_matching_rule"] == {
        "status": "unresolved",
        "reason": "NO_MATCHING_RULE",
        "done": True,
        "contract_version": "1.0.0",
        "question_set": {"id": "tri_operator_classification", "version": "1.0.0"},
    }
