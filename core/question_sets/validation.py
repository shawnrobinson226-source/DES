# DES — Question-set load-time validation

"""
Validation run when a question set is constructed.

Rules:
- 1 to 3 questions, positional ids q1..qN, q1 is the entry
- every option routes forward to an existing question or to END
- no dangling references, no cycles, no unreachable questions
- every path terminates within three answers
- rules match exact complete ordered paths only
- rule outcomes are an AXIS class name or the UNRESOLVED sentinel

NO defaults
NO partial matching
NO class list copies: names come from core.axis.bridge.CLASSIFICATION_VALUES
"""

from types import MappingProxyType

from core.axis.bridge import CLASSIFICATION_VALUES
from core.question_sets.errors import QuestionSetDefinitionError
from core.question_sets.sentinels import END, UNRESOLVED


MAX_QUESTIONS = 3

# Matches the answer length limit in api/interaction.py (validate_string(..., 280)).
MAX_OPTION_ID_LENGTH = 280


def require_text(value, what: str, max_length: int | None = None) -> None:
    if type(value) is not str or not value.strip():
        raise QuestionSetDefinitionError(f"{what} must be a non-empty string")

    if max_length is not None and len(value) > max_length:
        raise QuestionSetDefinitionError(f"{what} must be at most {max_length} characters")


def require_tuple(value, what: str) -> None:
    if type(value) is not tuple:
        raise QuestionSetDefinitionError(f"{what} must be a tuple")


def validate_route(value, what: str) -> None:
    if value is END:
        return
    require_text(value, what)


def validate_outcome(outcome) -> None:
    if outcome is UNRESOLVED:
        return

    if type(outcome) is str and outcome in CLASSIFICATION_VALUES:
        return

    raise QuestionSetDefinitionError("rule outcome must be an AXIS class name or UNRESOLVED")


def validate_rule_path(path) -> None:
    require_tuple(path, "rule path")

    if not path:
        raise QuestionSetDefinitionError("rule path must not be empty")

    for step in path:
        if type(step) is not tuple or len(step) != 2:
            raise QuestionSetDefinitionError("rule path steps must be (question id, option id) tuples")
        require_text(step[0], "rule path question id")
        require_text(step[1], "rule path option id")


def validate_questions(questions) -> frozenset:
    """Validate the question graph and return its complete paths."""
    require_tuple(questions, "questions")

    if not 1 <= len(questions) <= MAX_QUESTIONS:
        raise QuestionSetDefinitionError(f"a question set must have 1 to {MAX_QUESTIONS} questions")

    ids = [question.id for question in questions]
    if len(set(ids)) != len(ids):
        raise QuestionSetDefinitionError("question ids must be unique")

    for index, question in enumerate(questions):
        if question.id != f"q{index + 1}":
            raise QuestionSetDefinitionError("question ids must be positional, starting at q1")

    position = {question_id: index for index, question_id in enumerate(ids)}

    for index, question in enumerate(questions):
        for option in question.options:
            if option.next is END:
                continue
            if option.next not in position:
                raise QuestionSetDefinitionError(
                    f"option {question.id}/{option.id} routes to unknown question {option.next}"
                )
            if position[option.next] <= index:
                raise QuestionSetDefinitionError(
                    f"option {question.id}/{option.id} must route forward"
                )

    reachable = {"q1"}
    for question in questions:
        if question.id not in reachable:
            continue
        for option in question.options:
            if option.next is not END:
                reachable.add(option.next)

    unreachable = [question_id for question_id in ids if question_id not in reachable]
    if unreachable:
        raise QuestionSetDefinitionError(f"unreachable questions: {', '.join(unreachable)}")

    by_id = {question.id: question for question in questions}
    return frozenset(_complete_paths(by_id, "q1", (), frozenset()))


def _complete_paths(by_id: dict, question_id: str, prefix: tuple, visiting: frozenset):
    if question_id in visiting:
        raise QuestionSetDefinitionError("question routes must not form a cycle")

    if len(prefix) >= MAX_QUESTIONS:
        raise QuestionSetDefinitionError(f"every path must end within {MAX_QUESTIONS} answers")

    for option in by_id[question_id].options:
        path = prefix + ((question_id, option.id),)
        if option.next is END:
            yield path
        else:
            yield from _complete_paths(by_id, option.next, path, visiting | {question_id})


def validate_rules(rules, complete_paths: frozenset) -> MappingProxyType:
    """Validate rules against the complete paths and return a read-only index."""
    require_tuple(rules, "rules")

    partial_paths = {
        path[:length]
        for path in complete_paths
        for length in range(1, len(path))
    }

    index = {}
    for rule in rules:
        if rule.path in index:
            raise QuestionSetDefinitionError("two rules must not match the same path")

        if rule.path not in complete_paths:
            if rule.path in partial_paths:
                raise QuestionSetDefinitionError("rule path is partial; rules must match complete paths")
            raise QuestionSetDefinitionError("rule path is not a path through the question set")

        index[rule.path] = rule.outcome

    return MappingProxyType(index)
