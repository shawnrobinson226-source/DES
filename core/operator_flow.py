# DES — Operator Flow Handler

"""
Start and answer handling for operator_initiated interactions.

Callers run the shared request checks first (rate limit, required and unknown
fields, lengths, interaction lookup). These handlers then:

- pin each new interaction to the active question set (id, version)
- accept only the expected next question and an exact option id
- compute the new state on a copy and store it only after every check passes
- validate every response before anything is stored

A rejection never creates or changes a stored interaction.

The stored state field is never changed. Terminal results are stored in
resolved, resolution_status, axis_classification and unresolved_reason.

NO network access
NO pricing classifier or output builder
NO AXIS execution
"""

from copy import copy

from core.contracts import DES_OPERATOR_CONTRACT_VERSION
from core.operator_resolver import (
    QUESTION_SET_KEYS,
    Resolved,
    Unresolved,
    resolve,
    serialize_result,
    validate_terminal_response,
)
from core.question_sets.errors import QuestionSetPathError, ResultValidationError
from core.question_sets.registry import OPERATOR_QUESTION_SETS
from core.question_sets.sentinels import END
from models.interaction import Interaction
from storage.repository import save_interaction, update_interaction


OPERATOR_INITIATED = "operator_initiated"

QUESTION_SET_UNAVAILABLE = "QUESTION_SET_UNAVAILABLE"
INTERACTION_CLOSED = "INTERACTION_CLOSED"
OUT_OF_ORDER = "OUT_OF_ORDER"
INVALID_OPTION = "INVALID_OPTION"
RESULT_VALIDATION_FAILED = "RESULT_VALIDATION_FAILED"

ERROR_MESSAGES = {
    QUESTION_SET_UNAVAILABLE: "Question set unavailable",
    INTERACTION_CLOSED: "Interaction closed",
    OUT_OF_ORDER: "Question out of order",
    INVALID_OPTION: "Invalid option",
    RESULT_VALIDATION_FAILED: "Result validation failed",
}

ANSWER_FIELDS = ("q1", "q2", "q3")

QUESTION_RESPONSE_KEYS = frozenset({"interaction_id", "done", "contract_version", "question_set", "question"})
QUESTION_KEYS = frozenset({"id", "text", "options"})
OPTION_KEYS = frozenset({"id", "label"})


def start_operator_interaction(user_id: str, session_id: str) -> dict:
    question_set = OPERATOR_QUESTION_SETS.get_active()
    if question_set is None:
        return operator_error(QUESTION_SET_UNAVAILABLE)

    interaction = Interaction(
        user_id=user_id,
        session_id=session_id,
        trigger_type=OPERATOR_INITIATED,
        question_set_id=question_set.id,
        question_set_version=question_set.version,
    )

    try:
        response = build_question_response(interaction.interaction_id, question_set, "q1")
        validate_question_response(response, question_set)
    except ResultValidationError:
        return operator_error(RESULT_VALIDATION_FAILED)

    save_interaction(interaction)
    return response


def answer_operator_interaction(interaction: Interaction, question_id: str, answer: str) -> dict:
    question_set = _pinned_question_set(interaction)
    if question_set is None:
        return operator_error(QUESTION_SET_UNAVAILABLE)

    if interaction.resolved:
        return operator_error(INTERACTION_CLOSED)

    try:
        path, expected_id = _progress(interaction, question_set)
    except QuestionSetPathError:
        return operator_error(RESULT_VALIDATION_FAILED)

    if type(question_id) is not str or question_id != expected_id:
        return operator_error(OUT_OF_ORDER)

    option = _matching_option(question_set.question(expected_id), answer)
    if option is None:
        return operator_error(INVALID_OPTION)

    updated = copy(interaction)
    setattr(updated, question_id, option.id)

    if option.next is not END:
        try:
            response = build_question_response(updated.interaction_id, question_set, option.next)
            validate_question_response(response, question_set)
        except ResultValidationError:
            return operator_error(RESULT_VALIDATION_FAILED)

        update_interaction(updated)
        return response

    try:
        result = resolve(question_set, path + ((question_id, option.id),))
        response = serialize_result(result, question_set)
        validate_terminal_response(response)
        _check_pinned(response["question_set"], question_set)
    except (QuestionSetPathError, ResultValidationError):
        return operator_error(RESULT_VALIDATION_FAILED)

    updated.resolved = True
    if type(result) is Resolved:
        updated.resolution_status = "resolved"
        updated.axis_classification = result.classification
    elif type(result) is Unresolved:
        updated.resolution_status = "unresolved"
        updated.unresolved_reason = result.reason
    else:
        return operator_error(RESULT_VALIDATION_FAILED)

    update_interaction(updated)
    return response


def build_question_response(interaction_id: str, question_set, question_id: str) -> dict:
    question = question_set.question(question_id)
    return {
        "interaction_id": interaction_id,
        "done": False,
        "contract_version": DES_OPERATOR_CONTRACT_VERSION,
        "question_set": {"id": question_set.id, "version": question_set.version},
        "question": {
            "id": question.id,
            "text": question.text,
            "options": [{"id": option.id, "label": option.label} for option in question.options],
        },
    }


def validate_question_response(response, question_set) -> None:
    if type(response) is not dict or set(response) != QUESTION_RESPONSE_KEYS:
        raise ResultValidationError("question response fields are invalid")

    if not _is_non_empty_string(response["interaction_id"]):
        raise ResultValidationError("interaction_id must be a non-empty string")

    if response["done"] is not False:
        raise ResultValidationError("done must be exactly False")

    if type(response["contract_version"]) is not str or (
        response["contract_version"] != DES_OPERATOR_CONTRACT_VERSION
    ):
        raise ResultValidationError("contract_version is invalid")

    _check_pinned(response["question_set"], question_set)

    question = response["question"]
    if type(question) is not dict or set(question) != QUESTION_KEYS:
        raise ResultValidationError("question fields are invalid")

    if type(question["id"]) is not str:
        raise ResultValidationError("question id must be a string")

    try:
        definition = question_set.question(question["id"])
    except KeyError:
        raise ResultValidationError("question id is not in the pinned question set")

    if type(question["text"]) is not str or question["text"] != definition.text:
        raise ResultValidationError("question text does not match the pinned question set")

    options = question["options"]
    if type(options) is not list or len(options) != len(definition.options):
        raise ResultValidationError("question options do not match the pinned question set")

    for item, option in zip(options, definition.options):
        if type(item) is not dict or set(item) != OPTION_KEYS:
            raise ResultValidationError("option fields are invalid")
        if type(item["id"]) is not str or item["id"] != option.id:
            raise ResultValidationError("option id does not match the pinned question set")
        if type(item["label"]) is not str or item["label"] != option.label:
            raise ResultValidationError("option label does not match the pinned question set")


def operator_error(code: str) -> dict:
    return {"error": ERROR_MESSAGES[code], "code": code}


def _pinned_question_set(interaction: Interaction):
    set_id = interaction.question_set_id
    version = interaction.question_set_version
    if type(set_id) is not str or type(version) is not str:
        return None
    return OPERATOR_QUESTION_SETS.get(set_id, version)


def _progress(interaction: Interaction, question_set) -> tuple:
    """Return the stored answer path and the id of the expected next question."""
    path = ()
    current = "q1"

    while True:
        stored = getattr(interaction, current)
        if stored is None:
            break

        option = _matching_option(question_set.question(current), stored)
        if option is None:
            raise QuestionSetPathError("stored answer is not an option of its question")

        path += ((current, option.id),)
        if option.next is END:
            raise QuestionSetPathError("stored answers already complete the path")
        current = option.next

    on_path = {step[0] for step in path}
    for field_name in ANSWER_FIELDS:
        if field_name not in on_path and getattr(interaction, field_name) is not None:
            raise QuestionSetPathError("stored answers do not follow the question routing")

    return path, current


def _matching_option(question, answer):
    if type(answer) is not str:
        return None
    for option in question.options:
        if option.id == answer:
            return option
    return None


def _check_pinned(pinned, question_set) -> None:
    if type(pinned) is not dict or set(pinned) != QUESTION_SET_KEYS:
        raise ResultValidationError("question_set must have exactly id and version")

    if type(pinned["id"]) is not str or type(pinned["version"]) is not str:
        raise ResultValidationError("question_set id and version must be strings")

    if (pinned["id"], pinned["version"]) != (question_set.id, question_set.version):
        raise ResultValidationError("question_set does not match the pinned question set")


def _is_non_empty_string(value) -> bool:
    return type(value) is str and bool(value.strip())
