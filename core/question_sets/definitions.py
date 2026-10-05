# DES — Question-set definitions

"""
Immutable question-set definitions for the operator flow.

Every instance is validated on construction. Containers are tuples, the rule
index is a read-only mapping, and all dataclasses are frozen.

NO production content lives here.
"""

from dataclasses import dataclass, field
from types import MappingProxyType

from core.question_sets.errors import QuestionSetDefinitionError
from core.question_sets.sentinels import END, UNRESOLVED, Outcome, Route
from core.question_sets.validation import (
    MAX_OPTION_ID_LENGTH,
    require_text,
    require_tuple,
    validate_outcome,
    validate_questions,
    validate_route,
    validate_rule_path,
    validate_rules,
)


@dataclass(frozen=True)
class Option:
    id: str
    label: str
    next: str | Route

    def __post_init__(self):
        require_text(self.id, "option id", MAX_OPTION_ID_LENGTH)
        require_text(self.label, "option label")
        validate_route(self.next, "option route")


@dataclass(frozen=True)
class Question:
    id: str
    text: str
    options: tuple

    def __post_init__(self):
        require_text(self.id, "question id")
        require_text(self.text, "question text")
        require_tuple(self.options, "question options")

        if not self.options:
            raise QuestionSetDefinitionError("a question must have at least one option")

        for option in self.options:
            if not isinstance(option, Option):
                raise QuestionSetDefinitionError("question options must be Option instances")

        option_ids = [option.id for option in self.options]
        if len(set(option_ids)) != len(option_ids):
            raise QuestionSetDefinitionError(f"option ids in {self.id} must be unique")


@dataclass(frozen=True)
class Rule:
    path: tuple
    outcome: str | Outcome

    def __post_init__(self):
        validate_rule_path(self.path)
        validate_outcome(self.outcome)


@dataclass(frozen=True)
class QuestionSet:
    id: str
    version: str
    questions: tuple
    rules: tuple
    complete_paths: frozenset = field(init=False, repr=False, compare=False)
    rule_index: MappingProxyType = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        require_text(self.id, "question set id")
        require_text(self.version, "question set version")
        require_tuple(self.questions, "questions")
        require_tuple(self.rules, "rules")

        for question in self.questions:
            if not isinstance(question, Question):
                raise QuestionSetDefinitionError("questions must be Question instances")

        for rule in self.rules:
            if not isinstance(rule, Rule):
                raise QuestionSetDefinitionError("rules must be Rule instances")

        complete_paths = validate_questions(self.questions)
        rule_index = validate_rules(self.rules, complete_paths)

        object.__setattr__(self, "complete_paths", complete_paths)
        object.__setattr__(self, "rule_index", rule_index)

    def question(self, question_id: str) -> Question:
        for question in self.questions:
            if question.id == question_id:
                return question
        raise KeyError(question_id)


__all__ = ["END", "UNRESOLVED", "Option", "Question", "QuestionSet", "Rule"]
