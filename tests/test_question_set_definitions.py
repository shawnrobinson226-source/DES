import copy
from dataclasses import FrozenInstanceError
from types import MappingProxyType

import pytest

from core.axis.bridge import CLASSIFICATION_VALUES
from core.contracts import DES_OPERATOR_CONTRACT_VERSION
from core.question_sets.definitions import END, UNRESOLVED, Option, Question, QuestionSet, Rule
from core.question_sets.errors import QuestionSetDefinitionError
from tests.operator_fixtures import (
    CLASSES,
    PATH_ADF,
    PATH_AE,
    PATH_C,
    branching_questions,
    branching_rules,
    branching_set,
    option,
    question,
    single_question_set,
)


def build(questions, rules=()):
    return QuestionSet(id="test_set", version="test-1", questions=questions, rules=rules)


def assert_definition_error(match, fn, *args, **kwargs):
    with pytest.raises(QuestionSetDefinitionError, match=match):
        fn(*args, **kwargs)


# --- contract and sentinels ---

def test_contract_version_is_1_0_0():
    assert DES_OPERATOR_CONTRACT_VERSION == "1.0.0"
    assert type(DES_OPERATOR_CONTRACT_VERSION) is str


def test_class_names_come_from_bridge_constant():
    assert len(CLASSIFICATION_VALUES) == 5
    assert set(CLASSES) == CLASSIFICATION_VALUES


def test_sentinels_are_not_class_names_or_strings():
    assert UNRESOLVED not in CLASSIFICATION_VALUES
    assert END not in CLASSIFICATION_VALUES
    assert not isinstance(UNRESOLVED, str)
    assert not isinstance(END, str)
    assert copy.deepcopy(UNRESOLVED) is UNRESOLVED
    assert copy.deepcopy(END) is END


# --- valid branching ---

def test_valid_branching_set_builds_complete_paths():
    question_set = branching_set()

    assert len(question_set.complete_paths) == 7
    assert all(1 <= len(path) <= 3 for path in question_set.complete_paths)
    assert PATH_ADF in question_set.complete_paths
    assert PATH_AE in question_set.complete_paths
    assert question_set.rule_index[PATH_C] is UNRESOLVED


def test_rules_may_cover_only_some_paths():
    question_set = single_question_set()

    assert len(question_set.complete_paths) == 2
    assert len(question_set.rule_index) == 1


def test_set_without_rules_is_valid():
    question_set = single_question_set(rules=())

    assert len(question_set.rule_index) == 0


def test_option_id_at_answer_limit_is_valid():
    long_id = "o" * 280

    question_set = build((question("q1", option(long_id)),))

    assert (("q1", long_id),) in question_set.complete_paths


# --- immutability ---

def test_definitions_are_frozen():
    question_set = branching_set()

    with pytest.raises(FrozenInstanceError):
        question_set.id = "other"
    with pytest.raises(FrozenInstanceError):
        question_set.questions[0].id = "q9"
    with pytest.raises(FrozenInstanceError):
        question_set.questions[0].options[0].next = END
    with pytest.raises(FrozenInstanceError):
        question_set.rules[0].outcome = CLASSES[1]


def test_containers_are_immutable():
    question_set = branching_set()

    assert type(question_set.questions) is tuple
    assert type(question_set.rules) is tuple
    assert type(question_set.questions[0].options) is tuple
    assert type(question_set.complete_paths) is frozenset
    assert type(question_set.rule_index) is MappingProxyType

    with pytest.raises(TypeError):
        question_set.rule_index[PATH_ADF] = CLASSES[1]


def test_lists_and_dicts_are_rejected():
    assert_definition_error("questions must be a tuple", build, list(branching_questions()))
    assert_definition_error("rules must be a tuple", build, branching_questions(), list(branching_rules()))
    assert_definition_error("options must be a tuple", Question, id="q1", text="t", options=[option("opt_x")])
    assert_definition_error("rule path must be a tuple", Rule, path=[("q1", "opt_x")], outcome=CLASSES[0])
    assert_definition_error("steps must be", Rule, path=(["q1", "opt_x"],), outcome=CLASSES[0])


# --- question count and ids ---

def test_question_count_must_be_one_to_three():
    assert_definition_error("1 to 3 questions", build, ())

    four = (
        question("q1", option("opt_a", "q2")),
        question("q2", option("opt_b", "q3")),
        question("q3", option("opt_c", "q4")),
        question("q4", option("opt_d")),
    )
    assert_definition_error("1 to 3 questions", build, four)


def test_question_ids_must_be_positional_with_q1_entry():
    assert_definition_error("positional", build, (question("q2", option("opt_a")),))
    assert_definition_error(
        "positional", build,
        (question("q1", option("opt_a", "q3")), question("q3", option("opt_b"))),
    )


def test_question_ids_must_be_unique():
    assert_definition_error(
        "unique", build,
        (question("q1", option("opt_a")), question("q1", option("opt_b"))),
    )


@pytest.mark.parametrize("bad", ["", "   ", 1, True, None])
def test_ids_and_text_must_be_non_empty_strings(bad):
    assert_definition_error("question id", Question, id=bad, text="t", options=(option("opt_x"),))
    assert_definition_error("question text", Question, id="q1", text=bad, options=(option("opt_x"),))
    assert_definition_error("option id", Option, id=bad, label="l", next=END)
    assert_definition_error("option label", Option, id="opt_x", label=bad, next=END)
    assert_definition_error(
        "question set id", QuestionSet,
        id=bad, version="v", questions=(question("q1", option("opt_x")),), rules=(),
    )
    assert_definition_error(
        "question set version", QuestionSet,
        id="s", version=bad, questions=(question("q1", option("opt_x")),), rules=(),
    )


def test_option_ids_must_be_unique_within_a_question():
    assert_definition_error("option ids in q1 must be unique", question, "q1", option("opt_a"), option("opt_a"))


def test_same_option_id_in_different_questions_is_allowed():
    question_set = build((
        question("q1", option("opt_a", "q2")),
        question("q2", option("opt_a")),
    ))

    assert (("q1", "opt_a"), ("q2", "opt_a")) in question_set.complete_paths


def test_option_id_over_answer_limit_is_rejected():
    assert_definition_error("at most 280", option, "o" * 281)


def test_question_needs_options_of_option_type():
    assert_definition_error("at least one option", Question, id="q1", text="t", options=())
    assert_definition_error("Option instances", Question, id="q1", text="t", options=("opt_x",))


def test_set_members_must_be_definition_instances():
    assert_definition_error("Question instances", build, ("q1",))
    assert_definition_error(
        "Rule instances", build,
        (question("q1", option("opt_x")),), ((("q1", "opt_x"),),),
    )


# --- routing ---

def test_every_option_must_route_explicitly():
    with pytest.raises(TypeError):
        Option(id="opt_x", label="l")

    assert_definition_error("option route", Option, id="opt_x", label="l", next=None)
    assert_definition_error("option route", Option, id="opt_x", label="l", next=2)
    assert_definition_error("option route", Option, id="opt_x", label="l", next="")


def test_dangling_route_is_rejected():
    assert_definition_error("unknown question q9", build, (question("q1", option("opt_a", "q9")),))


def test_backward_route_and_cycle_are_rejected():
    assert_definition_error(
        "route forward", build,
        (question("q1", option("opt_a", "q2")), question("q2", option("opt_b", "q1"))),
    )


def test_self_route_is_rejected():
    assert_definition_error("route forward", build, (question("q1", option("opt_a", "q1")),))


def test_unreachable_question_is_rejected():
    assert_definition_error(
        "unreachable questions: q2", build,
        (
            question("q1", option("opt_a", "q3")),
            question("q2", option("opt_b", "q3")),
            question("q3", option("opt_c")),
        ),
    )


# --- rules ---

def test_rule_on_partial_path_is_rejected():
    assert_definition_error(
        "partial", build,
        branching_questions(), (Rule(path=(("q1", "opt_a"),), outcome=CLASSES[0]),),
    )


@pytest.mark.parametrize("path", [
    (("q1", "opt_z"),),
    (("q9", "opt_a"),),
    (("q2", "opt_e"), ("q1", "opt_a")),
    (("q1", "opt_c"), ("q2", "opt_d")),
    (("q1", "opt_a"), ("q3", "opt_f")),
])
def test_rule_on_non_path_is_rejected(path):
    assert_definition_error(
        "not a path", build,
        branching_questions(), (Rule(path=path, outcome=CLASSES[0]),),
    )


def test_two_rules_on_one_path_are_rejected():
    assert_definition_error(
        "same path", build,
        branching_questions(),
        (Rule(path=PATH_AE, outcome=CLASSES[0]), Rule(path=PATH_AE, outcome=CLASSES[1])),
    )
    assert_definition_error(
        "same path", build,
        branching_questions(),
        (Rule(path=PATH_AE, outcome=CLASSES[0]), Rule(path=PATH_AE, outcome=CLASSES[0])),
    )


@pytest.mark.parametrize("outcome", [
    "unknown_class",
    CLASSES[0].upper(),
    "UNRESOLVED",
    "",
    None,
    True,
    1,
    END,
])
def test_unknown_outcome_is_rejected(outcome):
    assert_definition_error("outcome", Rule, path=PATH_AE, outcome=outcome)


def test_empty_rule_path_is_rejected():
    assert_definition_error("must not be empty", Rule, path=(), outcome=CLASSES[0])
