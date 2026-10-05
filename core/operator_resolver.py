# DES — Operator Resolver

"""
Resolves a complete answer path through a question set.

Returns Resolved(classification) or Unresolved(reason).

NO class default
NO inference
NO wildcard or partial matching
An invalid or incomplete path raises QuestionSetPathError.

Also serializes terminal responses with runtime validation. An unresolved
response never carries a classification or any AXIS payload field.
"""

from dataclasses import dataclass

from core.axis.bridge import AXIS_PAYLOAD_FIELDS, CLASSIFICATION_VALUES
from core.contracts import DES_OPERATOR_CONTRACT_VERSION
from core.question_sets.definitions import QuestionSet
from core.question_sets.errors import (
    QuestionSetDefinitionError,
    QuestionSetPathError,
    ResultValidationError,
)
from core.question_sets.sentinels import UNRESOLVED


NO_MATCHING_RULE = "NO_MATCHING_RULE"
EXPLICIT_UNRESOLVED = "EXPLICIT_UNRESOLVED"
UNRESOLVED_REASONS = frozenset({NO_MATCHING_RULE, EXPLICIT_UNRESOLVED})

RESOLVED_KEYS = frozenset({"done", "status", "classification", "contract_version", "question_set"})
UNRESOLVED_KEYS = frozenset({"done", "status", "reason", "contract_version", "question_set"})
QUESTION_SET_KEYS = frozenset({"id", "version"})

PRICING_KEYS = frozenset({"friction_type", "output", "output_type"})
FORBIDDEN_UNRESOLVED_KEYS = frozenset(AXIS_PAYLOAD_FIELDS) | PRICING_KEYS
FORBIDDEN_RESOLVED_KEYS = (frozenset(AXIS_PAYLOAD_FIELDS) - {"classification"}) | PRICING_KEYS


@dataclass(frozen=True)
class Resolved:
    classification: str

    def __post_init__(self):
        _check_classification(self.classification)


@dataclass(frozen=True)
class Unresolved:
    reason: str

    def __post_init__(self):
        _check_reason(self.reason)


def resolve(question_set: QuestionSet, path: tuple) -> Resolved | Unresolved:
    if not isinstance(question_set, QuestionSet):
        raise QuestionSetDefinitionError("question_set must be a QuestionSet")

    _check_path(question_set, path)

    if path not in question_set.rule_index:
        return Unresolved(NO_MATCHING_RULE)

    outcome = question_set.rule_index[path]
    if outcome is UNRESOLVED:
        return Unresolved(EXPLICIT_UNRESOLVED)

    return Resolved(outcome)


def serialize_result(result, question_set: QuestionSet) -> dict:
    if not isinstance(question_set, QuestionSet):
        raise QuestionSetDefinitionError("question_set must be a QuestionSet")

    common = {
        "done": True,
        "contract_version": DES_OPERATOR_CONTRACT_VERSION,
        "question_set": {"id": question_set.id, "version": question_set.version},
    }

    if type(result) is Resolved:
        _check_classification(result.classification)
        response = {"status": "resolved", "classification": result.classification, **common}
    elif type(result) is Unresolved:
        _check_reason(result.reason)
        response = {"status": "unresolved", "reason": result.reason, **common}
    else:
        raise ResultValidationError("result must be Resolved or Unresolved")

    validate_terminal_response(response)
    return response


def validate_terminal_response(response) -> None:
    if type(response) is not dict:
        raise ResultValidationError("response must be a dict")

    status = response.get("status")

    if status == "resolved" and type(status) is str:
        _check_keys(response, RESOLVED_KEYS, FORBIDDEN_RESOLVED_KEYS)
        _check_classification(response["classification"])
    elif status == "unresolved" and type(status) is str:
        _check_keys(response, UNRESOLVED_KEYS, FORBIDDEN_UNRESOLVED_KEYS)
        _check_reason(response["reason"])
    else:
        raise ResultValidationError("response status must be resolved or unresolved")

    if response["done"] is not True:
        raise ResultValidationError("done must be exactly True")

    if type(response["contract_version"]) is not str or (
        response["contract_version"] != DES_OPERATOR_CONTRACT_VERSION
    ):
        raise ResultValidationError("contract_version is invalid")

    question_set = response["question_set"]
    if type(question_set) is not dict or set(question_set) != QUESTION_SET_KEYS:
        raise ResultValidationError("question_set must have exactly id and version")

    for key in sorted(QUESTION_SET_KEYS):
        if not _is_non_empty_string(question_set[key]):
            raise ResultValidationError(f"question_set {key} must be a non-empty string")


def _check_keys(response: dict, expected: frozenset, forbidden: frozenset) -> None:
    present = set(response)

    leaked = present & forbidden
    if leaked:
        raise ResultValidationError(f"response contains forbidden fields: {', '.join(sorted(leaked))}")

    if present != expected:
        raise ResultValidationError("response fields are invalid")


def _check_path(question_set: QuestionSet, path) -> None:
    if type(path) is not tuple or not path:
        raise QuestionSetPathError("path must be a non-empty tuple")

    for step in path:
        if type(step) is not tuple or len(step) != 2 or not all(type(part) is str for part in step):
            raise QuestionSetPathError("path steps must be (question id, option id) string tuples")

    if path in question_set.complete_paths:
        return

    for complete in question_set.complete_paths:
        if len(path) < len(complete) and complete[:len(path)] == path:
            raise QuestionSetPathError("path is incomplete")

    raise QuestionSetPathError("path is not a path through the question set")


def _check_classification(classification) -> None:
    if type(classification) is not str or classification not in CLASSIFICATION_VALUES:
        raise ResultValidationError("classification must be an AXIS class name")


def _check_reason(reason) -> None:
    if type(reason) is not str or reason not in UNRESOLVED_REASONS:
        raise ResultValidationError("reason must be NO_MATCHING_RULE or EXPLICIT_UNRESOLVED")


def _is_non_empty_string(value) -> bool:
    return type(value) is str and bool(value.strip())
