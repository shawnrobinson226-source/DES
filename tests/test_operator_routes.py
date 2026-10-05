"""Integration tests for operator_initiated routing through api/interaction.py.

Requests go through the public handlers and through api/app.py with
TestClient. Every question set used here is a test fixture; the production
registry is empty before and after every test.
"""

import ast
import socket
import urllib.request
from dataclasses import asdict
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api.interaction as api_interaction
import core.axis.bridge as axis_bridge
import core.classifier as classifier
import core.operator_flow as operator_flow
import core.output_builder as output_builder
import security.rate_limit as rate_limit
import storage.repository as repository
from api.app import app
from api.interaction import answer_interaction, start_interaction
from api.trigger import trigger_check
from core.axis_bridge import BridgeError, build_axis_payload
from core.contracts import DES_OPERATOR_CONTRACT_VERSION
from core.operator_resolver import EXPLICIT_UNRESOLVED, NO_MATCHING_RULE
from core.question_sets.errors import ResultValidationError
from core.question_sets.registry import OPERATOR_QUESTION_SETS
from tests.golden import pricing_cases
from tests.operator_fixtures import (
    CLASS_PATHS,
    CLASSES,
    PATH_ADF,
    PATH_AE,
    PATH_C,
    PATH_H,
    branching_set,
    single_question_set,
)


ROOT = Path(__file__).resolve().parent.parent

FORBIDDEN_NETWORK_ROOTS = {"urllib", "socket", "requests", "httpx", "http"}

UNAVAILABLE = {"error": "Question set unavailable", "code": "QUESTION_SET_UNAVAILABLE"}
CLOSED = {"error": "Interaction closed", "code": "INTERACTION_CLOSED"}
OUT_OF_ORDER = {"error": "Question out of order", "code": "OUT_OF_ORDER"}
INVALID_OPTION = {"error": "Invalid option", "code": "INVALID_OPTION"}
VALIDATION_FAILED = {"error": "Result validation failed", "code": "RESULT_VALIDATION_FAILED"}

client = TestClient(app)


def production_is_empty():
    return OPERATOR_QUESTION_SETS.keys() == () and OPERATOR_QUESTION_SETS.get_active() is None


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    assert production_is_empty()
    pricing_cases.reset_state()
    monkeypatch.setattr(rate_limit, "time", pricing_cases.fixed_time)
    entries = dict(OPERATOR_QUESTION_SETS._entries)
    active_key = OPERATOR_QUESTION_SETS._active_key
    yield
    OPERATOR_QUESTION_SETS._entries = entries
    OPERATOR_QUESTION_SETS._active_key = active_key
    pricing_cases.reset_state()
    assert production_is_empty()


def activate(question_set):
    OPERATOR_QUESTION_SETS.register(question_set)
    OPERATOR_QUESTION_SETS.activate(question_set.id, question_set.version)
    return question_set


def start_request(user_id="u1", session_id="s1"):
    return {"user_id": user_id, "session_id": session_id, "trigger_type": "operator_initiated"}


def answer_request(interaction_id, question_id, value):
    return {"interaction_id": interaction_id, "question_id": question_id, "answer": value}


def post(path, payload):
    response = client.post(path, json=payload)
    assert response.status_code == 200
    return response.json()


def http_start(**kwargs):
    return post("/interaction/start", start_request(**kwargs))


def http_answer(interaction_id, question_id, value):
    return post("/interaction/answer", answer_request(interaction_id, question_id, value))


def http_walk(interaction_id, path):
    response = None
    for question_id, option_id in path:
        response = http_answer(interaction_id, question_id, option_id)
    return response


def snapshot():
    return {key: asdict(value) for key, value in repository._INTERACTIONS.items()}


def stored(interaction_id):
    return repository._INTERACTIONS[interaction_id]


def expected_question(interaction_id, question_set, question_id):
    question = question_set.question(question_id)
    return {
        "interaction_id": interaction_id,
        "done": False,
        "contract_version": DES_OPERATOR_CONTRACT_VERSION,
        "question_set": {"id": question_set.id, "version": question_set.version},
        "question": {
            "id": question.id,
            "text": question.text,
            "options": [{"id": o.id, "label": o.label} for o in question.options],
        },
    }


def terminal(status, key, value, version="test-1"):
    return {
        "done": True,
        "status": status,
        key: value,
        "contract_version": DES_OPERATOR_CONTRACT_VERSION,
        "question_set": {"id": "test_set", "version": version},
    }


def assert_rejected_unchanged(call, expected):
    before = snapshot()
    objects = dict(repository._INTERACTIONS)

    assert call() == expected

    assert snapshot() == before
    assert repository._INTERACTIONS.keys() == objects.keys()
    assert all(repository._INTERACTIONS[key] is value for key, value in objects.items())


# --- start routing ---

def test_empty_production_registry_returns_unavailable_and_stores_nothing():
    assert start_interaction(start_request()) == UNAVAILABLE
    assert http_start() == UNAVAILABLE
    assert repository._INTERACTIONS == {}


def test_start_exact_shape_through_http():
    question_set = activate(branching_set())

    response = http_start()

    assert response == expected_question(response["interaction_id"], question_set, "q1")
    assert list(response) == ["interaction_id", "done", "contract_version", "question_set", "question"]
    interaction = stored(response["interaction_id"])
    assert interaction.trigger_type == "operator_initiated"
    assert (interaction.question_set_id, interaction.question_set_version) == ("test_set", "test-1")


def test_other_trigger_types_keep_the_byte_identical_error():
    activate(branching_set())

    for value in ["unknown_trigger", "Operator_Initiated", "operator_initiated ", "", None, 1, ["operator_initiated"]]:
        request = {**start_request(), "trigger_type": value}
        assert start_interaction(request) == {"error": "Invalid trigger_type", "code": "INVALID_INPUT"}

    raw = client.post("/interaction/start", json={**start_request(), "trigger_type": "unknown_trigger"})
    assert raw.status_code == 200
    assert raw.content == b'{"error":"Invalid trigger_type","code":"INVALID_INPUT"}'
    assert repository._INTERACTIONS == {}


@pytest.mark.parametrize("request_body, expected", [
    ({"user_id": "u1", "session_id": "s1"}, {"error": "Invalid request", "code": "INVALID_INPUT"}),
    ({**start_request(), "extra": "x"}, {"error": "Unknown field", "code": "UNKNOWN_FIELD"}),
    ({**start_request(), "user_id": "u" * 129}, {"error": "Invalid user_id", "code": "INVALID_INPUT"}),
    ({**start_request(), "session_id": 5}, {"error": "Invalid session_id", "code": "INVALID_INPUT"}),
])
def test_shared_start_checks_run_before_operator_start(request_body, expected):
    activate(branching_set())

    assert start_interaction(request_body) == expected
    assert repository._INTERACTIONS == {}


def test_start_rate_limit_runs_before_operator_start():
    for _ in range(10):
        assert start_interaction(start_request()) == UNAVAILABLE

    activate(branching_set())

    assert start_interaction(start_request()) == {"error": "Rate limited", "code": "RATE_LIMITED"}
    assert repository._INTERACTIONS == {}


def test_forced_start_validation_failure_creates_nothing(monkeypatch):
    activate(branching_set())

    def fail(*args):
        raise ResultValidationError("forced")

    monkeypatch.setattr(operator_flow, "validate_question_response", fail)

    assert http_start() == VALIDATION_FAILED
    assert repository._INTERACTIONS == {}


# --- answer routing ---

def test_answer_exact_shape_through_http():
    question_set = activate(branching_set())
    interaction_id = http_start()["interaction_id"]

    response = http_answer(interaction_id, "q1", "opt_a")

    assert response == expected_question(interaction_id, question_set, "q2")
    assert list(response) == ["interaction_id", "done", "contract_version", "question_set", "question"]


@pytest.mark.parametrize("path, classification", list(zip(CLASS_PATHS, CLASSES)))
def test_every_class_end_to_end(path, classification):
    activate(branching_set())
    interaction_id = http_start()["interaction_id"]

    response = http_walk(interaction_id, path)

    assert response == terminal("resolved", "classification", classification)
    interaction = stored(interaction_id)
    assert interaction.resolved is True
    assert interaction.resolution_status == "resolved"
    assert interaction.axis_classification == classification
    assert interaction.unresolved_reason is None
    assert interaction.state == "interaction_started"
    assert (interaction.friction_type, interaction.output_type) == (None, None)


@pytest.mark.parametrize("path, reason", [(PATH_C, EXPLICIT_UNRESOLVED), (PATH_H, NO_MATCHING_RULE)])
def test_both_unresolved_reasons_end_to_end(path, reason):
    activate(branching_set())
    interaction_id = http_start()["interaction_id"]

    response = http_walk(interaction_id, path)

    assert response == terminal("unresolved", "reason", reason)
    interaction = stored(interaction_id)
    assert interaction.resolution_status == "unresolved"
    assert interaction.unresolved_reason == reason
    assert interaction.axis_classification is None


def test_out_of_order_through_routes():
    activate(branching_set())
    interaction_id = http_start()["interaction_id"]

    assert_rejected_unchanged(lambda: http_answer(interaction_id, "q2", "opt_d"), OUT_OF_ORDER)
    http_answer(interaction_id, "q1", "opt_b")
    assert_rejected_unchanged(lambda: http_answer(interaction_id, "q2", "opt_d"), OUT_OF_ORDER)
    assert_rejected_unchanged(lambda: http_answer(interaction_id, "q1", "opt_a"), OUT_OF_ORDER)


def test_interaction_closed_through_routes():
    activate(branching_set())
    interaction_id = http_start()["interaction_id"]
    http_walk(interaction_id, PATH_AE)

    assert_rejected_unchanged(lambda: http_answer(interaction_id, "q1", "opt_a"), CLOSED)
    assert_rejected_unchanged(lambda: http_answer(interaction_id, "q3", "opt_f"), CLOSED)


@pytest.mark.parametrize("value", ["", "Test label opt_a", "some free text", "OPT_A", " opt_a"])
def test_invalid_option_through_routes(value):
    activate(branching_set())
    interaction_id = http_start()["interaction_id"]

    assert_rejected_unchanged(lambda: http_answer(interaction_id, "q1", value), INVALID_OPTION)


@pytest.mark.parametrize("request_body, expected", [
    ({"interaction_id": "x", "question_id": "q1"}, {"error": "Invalid request", "code": "INVALID_INPUT"}),
    ({"interaction_id": "x", "question_id": "q1", "answer": "opt_a", "extra": 1},
     {"error": "Unknown field", "code": "UNKNOWN_FIELD"}),
    ({"interaction_id": "<id>", "question_id": "q4", "answer": "opt_a"},
     {"error": "Invalid question_id", "code": "INVALID_INPUT"}),
    ({"interaction_id": "<id>", "question_id": "q1", "answer": "a" * 281},
     {"error": "Invalid answer", "code": "INVALID_INPUT"}),
    ({"interaction_id": "<id>", "question_id": "q1", "answer": 7},
     {"error": "Invalid answer", "code": "INVALID_INPUT"}),
    ({"interaction_id": "missing", "question_id": "q1", "answer": "opt_a"},
     {"error": "Interaction not found", "code": "INTERACTION_NOT_FOUND"}),
])
def test_shared_answer_checks_run_before_operator_answer(request_body, expected):
    activate(branching_set())
    interaction_id = http_start()["interaction_id"]
    if request_body.get("interaction_id") == "<id>":
        request_body = {**request_body, "interaction_id": interaction_id}

    assert_rejected_unchanged(lambda: answer_interaction(request_body), expected)


def test_forced_result_validation_failure_leaves_stored_fields_identical(monkeypatch):
    activate(branching_set())
    interaction_id = http_start()["interaction_id"]
    http_answer(interaction_id, "q1", "opt_a")
    before = asdict(stored(interaction_id))

    def fail(response):
        raise ResultValidationError("forced")

    monkeypatch.setattr(operator_flow, "validate_terminal_response", fail)

    assert_rejected_unchanged(lambda: http_answer(interaction_id, "q2", "opt_e"), VALIDATION_FAILED)
    assert asdict(stored(interaction_id)) == before


def test_forced_next_question_validation_failure_changes_nothing(monkeypatch):
    activate(branching_set())
    interaction_id = http_start()["interaction_id"]
    real = operator_flow.build_question_response
    monkeypatch.setattr(operator_flow, "build_question_response",
                        lambda *args: {**real(*args), "done": True})

    assert_rejected_unchanged(lambda: http_answer(interaction_id, "q1", "opt_a"), VALIDATION_FAILED)
    assert stored(interaction_id).q1 is None


def test_version_pinning_when_newer_version_is_activated_mid_flow():
    activate(branching_set(version="test-1"))
    interaction_id = http_start()["interaction_id"]
    http_answer(interaction_id, "q1", "opt_a")
    newer = activate(single_question_set(set_id="test_set", version="test-2"))

    response = http_walk(interaction_id, PATH_ADF[1:])

    assert response == terminal("resolved", "classification", CLASSES[0], version="test-1")
    second = http_start(user_id="u2", session_id="s2")
    assert second == expected_question(second["interaction_id"], newer, "q1")


def test_missing_pinned_set_on_answer():
    question_set = activate(branching_set())
    interaction_id = http_start()["interaction_id"]
    del OPERATOR_QUESTION_SETS._entries[(question_set.id, question_set.version)]

    assert_rejected_unchanged(lambda: http_answer(interaction_id, "q1", "opt_a"), UNAVAILABLE)


# --- isolation from pricing logic, AXIS execution and the network ---

def test_operator_runs_never_call_classify_or_build_output(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("pricing logic called during an operator run")

    for module, name in [(api_interaction, "classify"), (api_interaction, "build_output"),
                         (classifier, "classify"), (output_builder, "build_output")]:
        monkeypatch.setattr(module, name, boom)

    activate(branching_set())
    for path in CLASS_PATHS + (PATH_C, PATH_H):
        interaction_id = http_start(user_id=f"u_{len(path)}_{path[-1][1]}")["interaction_id"]
        assert http_walk(interaction_id, path)["done"] is True


def operator_responses():
    activate(branching_set())
    responses = []
    started = http_start()
    responses.append(started)
    responses.append(http_answer(started["interaction_id"], "q1", "opt_a"))
    responses.append(http_answer(started["interaction_id"], "q2", "opt_e"))
    unresolved = http_start(user_id="u2")
    responses.append(http_answer(unresolved["interaction_id"], "q1", "opt_c"))
    responses.append(http_answer(unresolved["interaction_id"], "q1", "opt_c"))
    return responses


def test_operator_responses_are_rejected_by_build_axis_payload():
    responses = operator_responses()
    assert [r.get("status", r.get("code", "question")) for r in responses] == [
        "question", "question", "resolved", "unresolved", "INTERACTION_CLOSED",
    ]

    # Raw operator responses carry no pricing output, so the bridge stops first at output.
    for response in responses:
        with pytest.raises(BridgeError, match="^Missing output$"):
            build_axis_payload(response)

    # Even given a valid output and trigger, the classification never stands in
    # for friction_type: the bridge raises Missing friction_type.
    for response in responses:
        with_envelope = {**response, "output": {"output_type": "clarify"}, "trigger": "operator_initiated"}
        with pytest.raises(BridgeError) as raised:
            build_axis_payload(with_envelope)
        assert str(raised.value) == "Missing friction_type"


def test_operator_flow_runs_with_socket_and_urlopen_raising(monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "socket", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)
    monkeypatch.setattr(urllib.request, "urlopen", no_network)
    monkeypatch.setattr(axis_bridge, "urlopen", no_network)

    activate(branching_set())
    for path, expected in [(PATH_ADF, terminal("resolved", "classification", CLASSES[0])),
                           (PATH_C, terminal("unresolved", "reason", EXPLICIT_UNRESOLVED))]:
        interaction_id = start_interaction(start_request(user_id=f"u_{path[-1][1]}"))["interaction_id"]
        response = None
        for question_id, option_id in path:
            response = answer_interaction(answer_request(interaction_id, question_id, option_id))
        assert response == expected


def python_files():
    return sorted((ROOT / "api").glob("*.py")) + [ROOT / "core" / "operator_flow.py"]


@pytest.mark.parametrize("path", python_files(), ids=lambda p: p.relative_to(ROOT).as_posix())
def test_no_execute_axis_request_or_direct_network_imports(path):
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    modules = [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
    modules += [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module]

    assert "execute_axis_request" not in source
    assert [m for m in modules if m.split(".")[0] in FORBIDDEN_NETWORK_ROOTS] == []


def test_static_check_covers_every_api_module():
    names = {p.relative_to(ROOT).as_posix() for p in python_files()}

    assert names == {"api/__init__.py", "api/app.py", "api/interaction.py", "api/trigger.py",
                     "core/operator_flow.py"}


# --- pricing is unaffected by the operator registry ---

def test_pricing_flow_unchanged_with_an_active_operator_set():
    activate(branching_set())

    started = start_interaction(pricing_cases.start()[1])
    interaction_id = started["interaction_id"]
    answer_interaction(pricing_cases.answer("q1", "too_expensive", interaction_id)[1])
    response = answer_interaction(pricing_cases.answer("q2", "value", interaction_id)[1])

    assert set(started) == {"interaction_id", "done", "question"}
    assert response["friction_type"] == "trust_deficit"
    assert response["output"]["output_type"] == "proof"
    assert stored(interaction_id).question_set_id is None


# --- accepted limitation ---

def pricing_trigger(session_id):
    return trigger_check(pricing_cases.trigger(session_id=session_id)[1])


def test_unfinished_operator_interaction_suppresses_pricing_trigger_but_not_operator_start():
    """Accepted limitation.

    has_active_interaction does not look at trigger_type, so an unfinished
    operator interaction suppresses the pricing trigger in its session. It does
    not block another operator start in the same session.
    """
    activate(branching_set())
    assert pricing_trigger("s1") == {"show": True}

    first = http_start(session_id="s1")["interaction_id"]

    assert pricing_trigger("s1") == {"show": False}
    assert pricing_trigger("s2") == {"show": True}

    second = http_start(session_id="s1")
    assert "interaction_id" in second
    assert second["interaction_id"] != first

    http_walk(first, PATH_AE)
    http_walk(second["interaction_id"], PATH_AE)
    assert pricing_trigger("s1") == {"show": True}
