"""Unit tests for core.operator_flow, calling the handlers directly (no routes).

Every question set used here is a test fixture. The production registry is
empty before and after every test.
"""

import ast
from dataclasses import asdict
from pathlib import Path

import pytest

import core.operator_flow as operator_flow
import security.rate_limit as rate_limit
import storage.repository as repository
from api.interaction import answer_interaction, start_interaction
from core.axis.bridge import CLASSIFICATION_VALUES
from core.contracts import DES_OPERATOR_CONTRACT_VERSION
from core.operator_flow import (
    INTERACTION_CLOSED,
    INVALID_OPTION,
    OUT_OF_ORDER,
    QUESTION_SET_UNAVAILABLE,
    RESULT_VALIDATION_FAILED,
    answer_operator_interaction,
    build_question_response,
    start_operator_interaction,
    validate_question_response,
)
from core.operator_resolver import EXPLICIT_UNRESOLVED, NO_MATCHING_RULE
from core.question_sets.errors import QuestionSetPathError, ResultValidationError
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

ERROR_MESSAGES = {
    QUESTION_SET_UNAVAILABLE: "Question set unavailable",
    INTERACTION_CLOSED: "Interaction closed",
    OUT_OF_ORDER: "Question out of order",
    INVALID_OPTION: "Invalid option",
    RESULT_VALIDATION_FAILED: "Result validation failed",
}

NEW_FIELDS = (
    "question_set_id",
    "question_set_version",
    "resolution_status",
    "axis_classification",
    "unresolved_reason",
)


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


def unregister(question_set):
    del OPERATOR_QUESTION_SETS._entries[(question_set.id, question_set.version)]


def error(code):
    return {"error": ERROR_MESSAGES[code], "code": code}


def snapshot():
    return {key: asdict(value) for key, value in repository._INTERACTIONS.items()}


def stored(interaction_id):
    return repository._INTERACTIONS[interaction_id]


def start():
    response = start_operator_interaction("u1", "s1")
    assert response["done"] is False
    return response["interaction_id"]


def answer(interaction_id, question_id, option_id):
    return answer_operator_interaction(stored(interaction_id), question_id, option_id)


def walk(interaction_id, path):
    response = None
    for question_id, option_id in path:
        response = answer(interaction_id, question_id, option_id)
    return response


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


def assert_rejected_unchanged(call, code):
    before = snapshot()
    objects = dict(repository._INTERACTIONS)

    assert call() == error(code)

    assert snapshot() == before
    assert all(repository._INTERACTIONS[key] is value for key, value in objects.items())
    assert repository._INTERACTIONS.keys() == objects.keys()


@pytest.fixture
def no_writes(monkeypatch):
    """Record every repository write the handler makes, passing it through."""
    calls = []

    def spy(name, real):
        def write(interaction):
            calls.append((name, interaction.interaction_id))
            real(interaction)
        return write

    monkeypatch.setattr(operator_flow, "save_interaction", spy("save", repository.save_interaction))
    monkeypatch.setattr(operator_flow, "update_interaction", spy("update", repository.update_interaction))
    return calls


# --- error shape ---

@pytest.mark.parametrize("code", sorted(ERROR_MESSAGES))
def test_error_shape_has_no_version_fields(code):
    response = operator_flow.operator_error(code)

    assert response == error(code)
    assert set(response) == {"error", "code"}
    assert response["code"] == code


def test_error_code_constants():
    assert (QUESTION_SET_UNAVAILABLE, INTERACTION_CLOSED, OUT_OF_ORDER, INVALID_OPTION,
            RESULT_VALIDATION_FAILED) == (
        "QUESTION_SET_UNAVAILABLE", "INTERACTION_CLOSED", "OUT_OF_ORDER", "INVALID_OPTION",
        "RESULT_VALIDATION_FAILED",
    )


# --- start ---

def test_start_with_empty_production_registry_is_unavailable(no_writes):
    assert start_operator_interaction("u1", "s1") == error(QUESTION_SET_UNAVAILABLE)
    assert repository._INTERACTIONS == {}
    assert no_writes == []


def test_start_with_registered_but_inactive_set_is_unavailable():
    OPERATOR_QUESTION_SETS.register(branching_set())

    assert start_operator_interaction("u1", "s1") == error(QUESTION_SET_UNAVAILABLE)
    assert repository._INTERACTIONS == {}


def test_start_response_exact_shape():
    question_set = activate(branching_set())

    response = start_operator_interaction("u1", "s1")

    interaction_id = response["interaction_id"]
    assert response == expected_question(interaction_id, question_set, "q1")
    assert list(response) == ["interaction_id", "done", "contract_version", "question_set", "question"]
    assert response["question"]["options"] == [
        {"id": "opt_a", "label": "Test label opt_a"},
        {"id": "opt_b", "label": "Test label opt_b"},
        {"id": "opt_c", "label": "Test label opt_c"},
        {"id": "opt_h", "label": "Test label opt_h"},
    ]
    assert response["done"] is False
    assert type(interaction_id) is str and interaction_id


def test_start_stores_interaction_pinned_to_active_set():
    activate(branching_set())

    interaction_id = start()

    interaction = stored(interaction_id)
    assert list(repository._INTERACTIONS) == [interaction_id]
    assert interaction.user_id == "u1"
    assert interaction.session_id == "s1"
    assert interaction.trigger_type == "operator_initiated"
    assert interaction.question_set_id == "test_set"
    assert interaction.question_set_version == "test-1"
    assert interaction.state == "interaction_started"
    assert interaction.resolved is False
    assert interaction.abandoned is False
    assert (interaction.q1, interaction.q2, interaction.q3) == (None, None, None)
    assert (interaction.friction_type, interaction.output_type) == (None, None)
    assert (interaction.resolution_status, interaction.axis_classification,
            interaction.unresolved_reason) == (None, None, None)


def test_start_response_validation_failure_stores_nothing(monkeypatch):
    activate(branching_set())
    real = operator_flow.build_question_response

    def with_extra_field(*args):
        return {**real(*args), "friction_type": "information_gap"}

    monkeypatch.setattr(operator_flow, "build_question_response", with_extra_field)

    assert start_operator_interaction("u1", "s1") == error(RESULT_VALIDATION_FAILED)
    assert repository._INTERACTIONS == {}


def test_start_validator_raising_stores_nothing(monkeypatch, no_writes):
    activate(branching_set())

    def fail(*args):
        raise ResultValidationError("forced")

    monkeypatch.setattr(operator_flow, "validate_question_response", fail)

    assert start_operator_interaction("u1", "s1") == error(RESULT_VALIDATION_FAILED)
    assert no_writes == []


def test_start_uses_newly_activated_version():
    activate(branching_set(version="test-1"))
    first = start()
    newer = activate(single_question_set(set_id="test_set", version="test-2"))

    response = start_operator_interaction("u2", "s2")

    assert response == expected_question(response["interaction_id"], newer, "q1")
    assert stored(first).question_set_version == "test-1"
    assert stored(response["interaction_id"]).question_set_version == "test-2"


# --- answer: routing onward ---

def test_answer_routes_to_next_question_in_start_shape():
    question_set = activate(branching_set())
    interaction_id = start()

    response = answer(interaction_id, "q1", "opt_a")

    assert response == expected_question(interaction_id, question_set, "q2")
    assert list(response) == ["interaction_id", "done", "contract_version", "question_set", "question"]


def test_answer_can_skip_a_question():
    question_set = activate(branching_set())
    interaction_id = start()

    response = answer(interaction_id, "q1", "opt_b")

    assert response == expected_question(interaction_id, question_set, "q3")
    assert answer(interaction_id, "q2", "opt_d") == error(OUT_OF_ORDER)


def test_onward_answer_stores_on_a_copy():
    activate(branching_set())
    interaction_id = start()
    original = stored(interaction_id)
    before = asdict(original)

    answer(interaction_id, "q1", "opt_a")

    assert asdict(original) == before
    updated = stored(interaction_id)
    assert updated is not original
    assert updated.q1 == "opt_a"
    assert (updated.q2, updated.q3) == (None, None)
    assert updated.state == "interaction_started"
    assert updated.resolved is False
    assert updated.resolution_status is None
    assert updated.created_at == original.created_at


# --- answer: terminal ---

@pytest.mark.parametrize("path, classification", list(zip(CLASS_PATHS, CLASSES)))
def test_every_class_resolves_and_is_stored(path, classification):
    activate(branching_set())
    interaction_id = start()
    original = stored(interaction_id)

    response = walk(interaction_id, path)

    assert response == {
        "done": True,
        "status": "resolved",
        "classification": classification,
        "contract_version": DES_OPERATOR_CONTRACT_VERSION,
        "question_set": {"id": "test_set", "version": "test-1"},
    }
    interaction = stored(interaction_id)
    assert interaction.resolved is True
    assert interaction.resolution_status == "resolved"
    assert interaction.axis_classification == classification
    assert interaction.unresolved_reason is None
    assert interaction.state == "interaction_started"
    assert (interaction.friction_type, interaction.output_type) == (None, None)
    answers = dict(path)
    assert (interaction.q1, interaction.q2, interaction.q3) == tuple(
        answers.get(q) for q in ("q1", "q2", "q3")
    )
    assert original.resolved is False


def test_all_five_classes_are_covered():
    assert set(CLASSES) == CLASSIFICATION_VALUES and len(CLASS_PATHS) == 5


@pytest.mark.parametrize("path, reason", [(PATH_C, EXPLICIT_UNRESOLVED), (PATH_H, NO_MATCHING_RULE)])
def test_unresolved_reasons_are_returned_and_stored(path, reason):
    activate(branching_set())
    interaction_id = start()

    response = walk(interaction_id, path)

    assert response == {
        "done": True,
        "status": "unresolved",
        "reason": reason,
        "contract_version": DES_OPERATOR_CONTRACT_VERSION,
        "question_set": {"id": "test_set", "version": "test-1"},
    }
    interaction = stored(interaction_id)
    assert interaction.resolved is True
    assert interaction.resolution_status == "unresolved"
    assert interaction.unresolved_reason == reason
    assert interaction.axis_classification is None
    assert interaction.state == "interaction_started"
    assert interaction.q1 == path[0][1]
    assert (interaction.q2, interaction.q3) == (None, None)


# --- answer: rejections, in order ---

def test_missing_pinned_set_is_unavailable_and_unchanged(no_writes):
    question_set = activate(branching_set())
    interaction_id = start()
    unregister(question_set)
    no_writes.clear()

    assert_rejected_unchanged(lambda: answer(interaction_id, "q1", "opt_a"), QUESTION_SET_UNAVAILABLE)
    assert no_writes == []


def test_missing_pinned_set_wins_over_closed():
    question_set = activate(branching_set())
    interaction_id = start()
    walk(interaction_id, PATH_AE)
    unregister(question_set)

    assert_rejected_unchanged(lambda: answer(interaction_id, "q1", "opt_a"), QUESTION_SET_UNAVAILABLE)


@pytest.mark.parametrize("set_id, version", [(None, "test-1"), ("test_set", None), (1, "test-1")])
def test_unusable_pin_is_unavailable(set_id, version):
    activate(branching_set())
    interaction_id = start()
    stored(interaction_id).question_set_id = set_id
    stored(interaction_id).question_set_version = version

    assert_rejected_unchanged(lambda: answer(interaction_id, "q1", "opt_a"), QUESTION_SET_UNAVAILABLE)


def test_answer_follows_pinned_version_after_newer_activation():
    activate(branching_set(version="test-1"))
    interaction_id = start()
    activate(single_question_set(set_id="test_set", version="test-2"))

    response = walk(interaction_id, PATH_ADF)

    assert response["question_set"] == {"id": "test_set", "version": "test-1"}
    assert response["classification"] == CLASSES[0]
    assert stored(interaction_id).question_set_version == "test-1"


@pytest.mark.parametrize("question_id, option_id", [("q1", "opt_a"), ("q2", "opt_e"), ("q3", "nonsense")])
def test_closed_interaction_rejects_any_answer(question_id, option_id, no_writes):
    activate(branching_set())
    interaction_id = start()
    walk(interaction_id, PATH_AE)
    no_writes.clear()

    assert_rejected_unchanged(lambda: answer(interaction_id, question_id, option_id), INTERACTION_CLOSED)
    assert no_writes == []


@pytest.mark.parametrize("answered, question_id", [
    ((), "q2"),
    ((), "q3"),
    ((), "q4"),
    ((), ""),
    ((), None),
    ((("q1", "opt_a"),), "q1"),
    ((("q1", "opt_a"),), "q3"),
    ((("q1", "opt_b"),), "q2"),
    ((("q1", "opt_a"), ("q2", "opt_d")), "q2"),
])
def test_out_of_order_question_is_rejected_unchanged(answered, question_id, no_writes):
    activate(branching_set())
    interaction_id = start()
    walk(interaction_id, answered)
    no_writes.clear()

    assert_rejected_unchanged(lambda: answer(interaction_id, question_id, "opt_d"), OUT_OF_ORDER)
    assert no_writes == []


def test_out_of_order_wins_over_invalid_option():
    activate(branching_set())
    interaction_id = start()

    assert_rejected_unchanged(lambda: answer(interaction_id, "q2", "not an option"), OUT_OF_ORDER)


@pytest.mark.parametrize("value", [
    "",
    "Test label opt_a",
    "I am not sure what to pick",
    "OPT_A",
    " opt_a",
    "opt_a ",
    "opt_",
    "opt_d",
    None,
    1,
])
def test_invalid_option_is_rejected_unchanged(value, no_writes):
    activate(branching_set())
    interaction_id = start()
    no_writes.clear()

    assert_rejected_unchanged(lambda: answer(interaction_id, "q1", value), INVALID_OPTION)
    assert no_writes == []


def test_invalid_option_on_later_question_is_rejected_unchanged():
    activate(branching_set())
    interaction_id = start()
    answer(interaction_id, "q1", "opt_a")

    assert_rejected_unchanged(lambda: answer(interaction_id, "q2", "Test label opt_d"), INVALID_OPTION)
    assert_rejected_unchanged(lambda: answer(interaction_id, "q2", "opt_a"), INVALID_OPTION)
    assert stored(interaction_id).q1 == "opt_a"


@pytest.mark.parametrize("tamper", [
    {"q1": "bogus"},
    {"q2": "opt_d"},
    {"q1": "opt_b", "q2": "opt_d"},
    {"q1": "opt_c"},
])
def test_inconsistent_stored_answers_fail_validation_unchanged(tamper):
    activate(branching_set())
    interaction_id = start()
    for field_name, value in tamper.items():
        setattr(stored(interaction_id), field_name, value)

    assert_rejected_unchanged(lambda: answer(interaction_id, "q3", "opt_f"), RESULT_VALIDATION_FAILED)


# --- forced validation failures ---

def test_forced_terminal_validation_failure_leaves_interaction_unchanged(monkeypatch, no_writes):
    activate(branching_set())
    interaction_id = start()
    answer(interaction_id, "q1", "opt_a")
    no_writes.clear()

    def fail(response):
        raise ResultValidationError("forced")

    monkeypatch.setattr(operator_flow, "validate_terminal_response", fail)

    assert_rejected_unchanged(lambda: answer(interaction_id, "q2", "opt_e"), RESULT_VALIDATION_FAILED)
    assert no_writes == []
    assert stored(interaction_id).q2 is None
    assert stored(interaction_id).resolved is False


@pytest.mark.parametrize("corrupt", [
    lambda r: {**r, "friction_type": "information_gap"},
    lambda r: {**r, "next_action": "clarify"},
    lambda r: {**r, "question_set": {"id": "test_set", "version": "test-2"}},
    lambda r: {**r, "question_set": {"id": "other", "version": "test-1"}},
    lambda r: {**r, "contract_version": "0.0.0"},
    lambda r: {**r, "done": 1},
    lambda r: {k: v for k, v in r.items() if k != "contract_version"},
])
def test_corrupted_terminal_response_fails_validation_unchanged(monkeypatch, corrupt):
    activate(branching_set())
    interaction_id = start()
    answer(interaction_id, "q1", "opt_a")
    real = operator_flow.serialize_result
    monkeypatch.setattr(operator_flow, "serialize_result", lambda *a: corrupt(real(*a)))

    assert_rejected_unchanged(lambda: answer(interaction_id, "q2", "opt_e"), RESULT_VALIDATION_FAILED)


@pytest.mark.parametrize("error_type", [QuestionSetPathError, ResultValidationError])
def test_resolver_errors_fail_validation_unchanged(monkeypatch, error_type):
    activate(branching_set())
    interaction_id = start()

    def fail(*args):
        raise error_type("forced")

    monkeypatch.setattr(operator_flow, "resolve", fail)

    assert_rejected_unchanged(lambda: answer(interaction_id, "q1", "opt_c"), RESULT_VALIDATION_FAILED)


def test_forced_next_question_validation_failure_leaves_interaction_unchanged(monkeypatch, no_writes):
    activate(branching_set())
    interaction_id = start()
    no_writes.clear()
    real = operator_flow.build_question_response

    def with_wrong_version(*args):
        response = real(*args)
        return {**response, "question_set": {"id": "test_set", "version": "test-2"}}

    monkeypatch.setattr(operator_flow, "build_question_response", with_wrong_version)

    assert_rejected_unchanged(lambda: answer(interaction_id, "q1", "opt_a"), RESULT_VALIDATION_FAILED)
    assert no_writes == []
    assert stored(interaction_id).q1 is None


# --- question response validation ---

def valid_question_response():
    question_set = branching_set()
    return build_question_response("iid", question_set, "q2"), question_set


def test_valid_question_response_passes():
    response, question_set = valid_question_response()

    validate_question_response(response, question_set)


@pytest.mark.parametrize("corrupt", [
    lambda r: [r],
    lambda r: {**r, "extra": 1},
    lambda r: {k: v for k, v in r.items() if k != "done"},
    lambda r: {**r, "interaction_id": ""},
    lambda r: {**r, "interaction_id": 1},
    lambda r: {**r, "done": True},
    lambda r: {**r, "done": 0},
    lambda r: {**r, "done": None},
    lambda r: {**r, "contract_version": "2.0.0"},
    lambda r: {**r, "contract_version": None},
    lambda r: {**r, "question_set": {"id": "test_set"}},
    lambda r: {**r, "question_set": {"id": "test_set", "version": "test-2"}},
    lambda r: {**r, "question_set": {"id": "test_set", "version": "test-1", "extra": 1}},
    lambda r: {**r, "question_set": ("test_set", "test-1")},
    lambda r: {**r, "question": None},
    lambda r: {**r, "question": {**r["question"], "extra": 1}},
    lambda r: {**r, "question": {**r["question"], "id": "q9"}},
    lambda r: {**r, "question": {**r["question"], "id": 2}},
    lambda r: {**r, "question": {**r["question"], "text": "Other text"}},
    lambda r: {**r, "question": {**r["question"], "options": tuple(r["question"]["options"])}},
    lambda r: {**r, "question": {**r["question"], "options": r["question"]["options"][:1]}},
    lambda r: {**r, "question": {**r["question"], "options": r["question"]["options"][::-1]}},
    lambda r: {**r, "question": {**r["question"], "options": [
        {**r["question"]["options"][0], "next": "q3"}, r["question"]["options"][1]]}},
    lambda r: {**r, "question": {**r["question"], "options": [
        {"id": "opt_d"}, r["question"]["options"][1]]}},
    lambda r: {**r, "question": {**r["question"], "options": [
        {"id": "opt_d", "label": "Wrong"}, r["question"]["options"][1]]}},
    lambda r: {**r, "question": {**r["question"], "options": [
        {"id": "opt_x", "label": "Test label opt_d"}, r["question"]["options"][1]]}},
    lambda r: {**r, "question": {**r["question"], "options": [
        ["opt_d", "Test label opt_d"], r["question"]["options"][1]]}},
])
def test_invalid_question_responses_are_rejected(corrupt):
    response, question_set = valid_question_response()

    with pytest.raises(ResultValidationError):
        validate_question_response(corrupt(response), question_set)


# --- pricing never sets the new fields ---

def test_pricing_interactions_never_set_new_fields():
    started = start_interaction(pricing_cases.start()[1])
    interaction_id = started["interaction_id"]
    answer_interaction(pricing_cases.answer("q1", "too_expensive", interaction_id)[1])
    answer_interaction(pricing_cases.answer("q2", "value", interaction_id)[1])

    interaction = stored(interaction_id)
    assert interaction.resolved is True
    assert [getattr(interaction, name) for name in NEW_FIELDS] == [None] * len(NEW_FIELDS)


def test_new_model_fields_default_to_none():
    from models.interaction import Interaction

    interaction = Interaction(user_id="u", session_id="s", trigger_type="repeat_pricing_visit")

    assert [getattr(interaction, name) for name in NEW_FIELDS] == [None] * len(NEW_FIELDS)


# --- static: no AXIS execution, no network imports ---

def test_operator_flow_does_not_reference_execute_axis_request_or_network():
    source = (ROOT / "core" / "operator_flow.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    names |= {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    names |= {alias.name for node in ast.walk(tree)
              if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names}
    modules = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    modules |= {alias.name for node in ast.walk(tree)
                if isinstance(node, ast.Import) for alias in node.names}

    assert "execute_axis_request" not in names
    assert "execute_axis_request" not in source
    assert not {m for m in modules if m.split(".")[0] in {"urllib", "socket", "requests", "httpx", "http"}}
    assert "core.axis.bridge" not in modules
    assert "core.axis_bridge" not in modules
    assert not {"classify", "build_output"} & names
