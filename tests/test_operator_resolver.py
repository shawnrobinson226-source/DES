from dataclasses import FrozenInstanceError

import pytest

from core.axis.bridge import AXIS_PAYLOAD_FIELDS, CLASSIFICATION_VALUES
from core.operator_resolver import (
    EXPLICIT_UNRESOLVED,
    NO_MATCHING_RULE,
    Resolved,
    Unresolved,
    resolve,
    serialize_result,
    validate_terminal_response,
)
from core.question_sets.errors import (
    QuestionSetDefinitionError,
    QuestionSetPathError,
    ResultValidationError,
)
from tests.operator_fixtures import (
    CLASS_PATHS,
    CLASSES,
    PATH_ADF,
    PATH_C,
    PATH_H,
    branching_set,
)


QUESTION_SET = branching_set()


def resolved_response(classification=CLASSES[0]):
    return serialize_result(Resolved(classification), QUESTION_SET)


def unresolved_response(reason=NO_MATCHING_RULE):
    return serialize_result(Unresolved(reason), QUESTION_SET)


# --- resolution ---

def test_all_five_classes_resolve():
    results = [resolve(QUESTION_SET, path) for path in CLASS_PATHS]

    assert all(type(result) is Resolved for result in results)
    assert {result.classification for result in results} == CLASSIFICATION_VALUES
    assert [result.classification for result in results] == list(CLASSES)


def test_explicit_unresolved_rule():
    assert resolve(QUESTION_SET, PATH_C) == Unresolved(EXPLICIT_UNRESOLVED)


def test_complete_path_without_rule_is_unresolved():
    assert resolve(QUESTION_SET, PATH_H) == Unresolved(NO_MATCHING_RULE)


def test_resolution_is_deterministic():
    assert [resolve(QUESTION_SET, PATH_ADF) for _ in range(3)] == [Resolved(CLASSES[0])] * 3


# --- invalid paths raise, never resolve ---

@pytest.mark.parametrize("path, match", [
    ((("q1", "opt_a"),), "incomplete"),
    ((("q1", "opt_a"), ("q2", "opt_d")), "incomplete"),
    ((("q1", "opt_z"),), "not a path"),
    ((("q1", "opt_c"), ("q2", "opt_d")), "not a path"),
    ((("q1", "opt_a"), ("q3", "opt_f")), "not a path"),
    ((("q2", "opt_e"), ("q1", "opt_a")), "not a path"),
    (PATH_ADF + (("q3", "opt_f"),), "not a path"),
    ((), "non-empty tuple"),
    ([("q1", "opt_c")], "non-empty tuple"),
    ((["q1", "opt_c"],), "string tuples"),
    ((("q1",),), "string tuples"),
    ((("q1", 1),), "string tuples"),
    ((("q1", True),), "string tuples"),
    (None, "non-empty tuple"),
])
def test_invalid_path_raises(path, match):
    with pytest.raises(QuestionSetPathError, match=match):
        resolve(QUESTION_SET, path)


def test_resolve_requires_a_question_set():
    with pytest.raises(QuestionSetDefinitionError):
        resolve({"id": "test_set"}, PATH_C)


# --- result types ---

def test_results_are_frozen():
    with pytest.raises(FrozenInstanceError):
        Resolved(CLASSES[0]).classification = CLASSES[1]
    with pytest.raises(FrozenInstanceError):
        Unresolved(NO_MATCHING_RULE).reason = EXPLICIT_UNRESOLVED


def test_unresolved_has_no_classification():
    assert not hasattr(Unresolved(NO_MATCHING_RULE), "classification")


@pytest.mark.parametrize("bad", ["unknown_class", CLASSES[0].upper(), "", None, True, 1])
def test_resolved_rejects_invalid_classification(bad):
    with pytest.raises(ResultValidationError):
        Resolved(bad)


@pytest.mark.parametrize("bad", ["no_matching_rule", "OTHER", "", None, True, 0])
def test_unresolved_rejects_invalid_reason(bad):
    with pytest.raises(ResultValidationError):
        Unresolved(bad)


# --- response shapes ---

def test_resolved_response_exact_shape():
    response = resolved_response(CLASSES[2])

    assert response == {
        "done": True,
        "status": "resolved",
        "classification": CLASSES[2],
        "contract_version": "1.0.0",
        "question_set": {"id": "test_set", "version": "test-1"},
    }
    assert response["done"] is True


@pytest.mark.parametrize("reason", [NO_MATCHING_RULE, EXPLICIT_UNRESOLVED])
def test_unresolved_response_exact_shape(reason):
    response = unresolved_response(reason)

    assert response == {
        "done": True,
        "status": "unresolved",
        "reason": reason,
        "contract_version": "1.0.0",
        "question_set": {"id": "test_set", "version": "test-1"},
    }
    assert response["done"] is True


def test_unresolved_response_has_no_axis_or_pricing_fields():
    response = unresolved_response()

    assert set(response) & set(AXIS_PAYLOAD_FIELDS) == set()
    assert "classification" not in response
    assert "friction_type" not in response
    assert "output" not in response
    assert "output_type" not in response


def test_resolved_response_has_no_other_axis_or_pricing_fields():
    response = resolved_response()

    assert set(response) & set(AXIS_PAYLOAD_FIELDS) == {"classification"}
    assert "friction_type" not in response
    assert "output" not in response


def test_serialization_revalidates_tampered_results():
    resolved = Resolved(CLASSES[0])
    object.__setattr__(resolved, "classification", "unknown_class")
    with pytest.raises(ResultValidationError):
        serialize_result(resolved, QUESTION_SET)

    unresolved = Unresolved(NO_MATCHING_RULE)
    object.__setattr__(unresolved, "reason", "OTHER")
    with pytest.raises(ResultValidationError):
        serialize_result(unresolved, QUESTION_SET)


def test_serialization_rejects_non_results():
    with pytest.raises(ResultValidationError):
        serialize_result({"classification": CLASSES[0]}, QUESTION_SET)
    with pytest.raises(QuestionSetDefinitionError):
        serialize_result(Resolved(CLASSES[0]), {"id": "test_set", "version": "test-1"})


# --- terminal response validation ---

def with_changes(response, **changes):
    response = dict(response)
    for key, value in changes.items():
        response[key] = value
    return response


def without_key(response, key):
    response = dict(response)
    del response[key]
    return response


def test_valid_responses_pass_validation():
    validate_terminal_response(resolved_response())
    validate_terminal_response(unresolved_response())


@pytest.mark.parametrize("extra", sorted(AXIS_PAYLOAD_FIELDS - {"classification"}) + [
    "friction_type", "output", "output_type", "extra",
])
def test_extra_fields_are_rejected(extra):
    with pytest.raises(ResultValidationError):
        validate_terminal_response(with_changes(resolved_response(), **{extra: "x"}))
    with pytest.raises(ResultValidationError):
        validate_terminal_response(with_changes(unresolved_response(), **{extra: "x"}))


def test_unresolved_with_classification_is_rejected():
    response = with_changes(unresolved_response(), classification=CLASSES[0])

    with pytest.raises(ResultValidationError, match="forbidden"):
        validate_terminal_response(response)


def test_resolved_with_reason_is_rejected():
    with pytest.raises(ResultValidationError):
        validate_terminal_response(with_changes(resolved_response(), reason=NO_MATCHING_RULE))


@pytest.mark.parametrize("key", ["done", "status", "classification", "contract_version", "question_set"])
def test_missing_resolved_field_is_rejected(key):
    with pytest.raises(ResultValidationError):
        validate_terminal_response(without_key(resolved_response(), key))


@pytest.mark.parametrize("key", ["done", "status", "reason", "contract_version", "question_set"])
def test_missing_unresolved_field_is_rejected(key):
    with pytest.raises(ResultValidationError):
        validate_terminal_response(without_key(unresolved_response(), key))


@pytest.mark.parametrize("done", [1, 1.0, "true", False, 0, None])
def test_done_must_be_exactly_true(done):
    with pytest.raises(ResultValidationError, match="done"):
        validate_terminal_response(with_changes(resolved_response(), done=done))
    with pytest.raises(ResultValidationError, match="done"):
        validate_terminal_response(with_changes(unresolved_response(), done=done))


@pytest.mark.parametrize("status", ["Resolved", "done", "", None, True, 1])
def test_unknown_status_is_rejected(status):
    with pytest.raises(ResultValidationError, match="status"):
        validate_terminal_response(with_changes(resolved_response(), status=status))


@pytest.mark.parametrize("classification", ["unknown_class", "", None, True, 1])
def test_invalid_classification_in_response_is_rejected(classification):
    with pytest.raises(ResultValidationError, match="classification"):
        validate_terminal_response(with_changes(resolved_response(), classification=classification))


@pytest.mark.parametrize("reason", ["OTHER", "", None, True, 1])
def test_invalid_reason_in_response_is_rejected(reason):
    with pytest.raises(ResultValidationError, match="reason"):
        validate_terminal_response(with_changes(unresolved_response(), reason=reason))


@pytest.mark.parametrize("version", ["1.0", "2.0.0", "", None, 1, 1.0, True])
def test_contract_version_must_match(version):
    with pytest.raises(ResultValidationError, match="contract_version"):
        validate_terminal_response(with_changes(resolved_response(), contract_version=version))


@pytest.mark.parametrize("question_set", [
    {"id": "test_set"},
    {"id": "test_set", "version": "test-1", "extra": "x"},
    {"id": "", "version": "test-1"},
    {"id": "test_set", "version": "  "},
    {"id": 1, "version": "test-1"},
    {"id": "test_set", "version": True},
    ["test_set", "test-1"],
    None,
])
def test_invalid_question_set_in_response_is_rejected(question_set):
    with pytest.raises(ResultValidationError, match="question_set"):
        validate_terminal_response(with_changes(resolved_response(), question_set=question_set))
    with pytest.raises(ResultValidationError, match="question_set"):
        validate_terminal_response(with_changes(unresolved_response(), question_set=question_set))


@pytest.mark.parametrize("response", [None, [], "resolved", (("status", "resolved"),)])
def test_non_dict_response_is_rejected(response):
    with pytest.raises(ResultValidationError, match="dict"):
        validate_terminal_response(response)
