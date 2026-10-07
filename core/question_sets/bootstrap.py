# DES — Explicit production question-set bootstrap

"""Register and activate operator content only after an exact startup choice.

The default is deliberately inert: an absent or empty environment value leaves
the production registry empty, so operator starts fail closed with
QUESTION_SET_UNAVAILABLE. A non-empty value must identify one allowlisted set
exactly as ``<id>@<version>``; malformed or unknown values stop application
startup instead of selecting a fallback.
"""

import os

from core.question_sets.operator_v1 import OPERATOR_QUESTION_SET_V1
from core.question_sets.registry import OPERATOR_QUESTION_SETS, QuestionSetRegistry


ACTIVATION_ENV = "DES_OPERATOR_QUESTION_SET"

AVAILABLE_QUESTION_SETS = {
    f"{OPERATOR_QUESTION_SET_V1.id}@{OPERATOR_QUESTION_SET_V1.version}":
        OPERATOR_QUESTION_SET_V1,
}


class OperatorBootstrapError(RuntimeError):
    pass


def bootstrap_operator_question_sets(
    selection: str | None = None,
    *,
    registry: QuestionSetRegistry = OPERATOR_QUESTION_SETS,
    environ=None,
) -> tuple | None:
    """Apply one exact activation choice, or leave the registry untouched.

    ``selection=None`` reads :data:`ACTIVATION_ENV` from ``environ`` (or
    ``os.environ``). Passing an explicit string is useful to launchers and
    tests. The return value is the activated ``(id, version)`` pair, or None
    when activation is disabled.
    """
    if not isinstance(registry, QuestionSetRegistry):
        raise OperatorBootstrapError("operator registry must be a QuestionSetRegistry")

    source = os.environ if environ is None else environ
    value = source.get(ACTIVATION_ENV) if selection is None else selection

    if value is None or value == "":
        return None
    if type(value) is not str or value.strip() != value:
        raise OperatorBootstrapError(
            f"{ACTIVATION_ENV} must be an exact <id>@<version> value")

    question_set = AVAILABLE_QUESTION_SETS.get(value)
    if question_set is None:
        raise OperatorBootstrapError(
            f"{ACTIVATION_ENV} does not name an available question set")

    existing = registry.get(question_set.id, question_set.version)
    if existing is None:
        registry.register(question_set)
    elif existing is not question_set:
        raise OperatorBootstrapError(
            "a different question set already uses the selected id and version")

    registry.activate(question_set.id, question_set.version)
    return (question_set.id, question_set.version)


__all__ = [
    "ACTIVATION_ENV",
    "AVAILABLE_QUESTION_SETS",
    "OperatorBootstrapError",
    "bootstrap_operator_question_sets",
]
