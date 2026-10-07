"""Candidate-content checks without persistent registration side effects."""

from collections import Counter

import storage.repository as repository
from core.axis.bridge import CLASSIFICATION_VALUES
from core.operator_flow import answer_operator_interaction, start_operator_interaction
from core.question_sets.operator_v1 import (
    CLASS_CHOICES,
    OPERATOR_QUESTION_SET_V1,
    QUESTION_SET_ID,
    QUESTION_SET_VERSION,
)
from core.question_sets.registry import OPERATOR_QUESTION_SETS
from core.question_sets.sentinels import UNRESOLVED


def outcome(path):
    return OPERATOR_QUESTION_SET_V1.rule_index[path]


def test_content_identity_and_import_do_not_activate_production_registry():
    assert (QUESTION_SET_ID, QUESTION_SET_VERSION) == (
        "tri_operator_classification", "1.0.0")
    assert OPERATOR_QUESTION_SET_V1.id == QUESTION_SET_ID
    assert OPERATOR_QUESTION_SET_V1.version == QUESTION_SET_VERSION
    assert OPERATOR_QUESTION_SETS.keys() == ()
    assert OPERATOR_QUESTION_SETS.get_active() is None


def test_content_has_exactly_three_ordered_questions_and_explanatory_labels():
    questions = OPERATOR_QUESTION_SET_V1.questions
    assert tuple(question.id for question in questions) == ("q1", "q2", "q3")
    assert all(question.text.strip() for question in questions)
    assert all(option.label.strip() for question in questions for option in question.options)
    assert {name for name, _ in CLASS_CHOICES} == CLASSIFICATION_VALUES


def test_every_complete_path_has_one_explicit_rule_and_no_default_gap():
    question_set = OPERATOR_QUESTION_SET_V1
    assert len(question_set.complete_paths) == 46
    assert len(question_set.rule_index) == 46
    assert set(question_set.rule_index) == set(question_set.complete_paths)


def test_confirm_uses_the_initial_operator_selected_class():
    for classification in CLASSIFICATION_VALUES:
        path = (("q1", classification), ("q2", "confirm"))
        assert outcome(path) == classification


def test_review_all_uses_only_the_final_operator_selected_class():
    for initial in CLASSIFICATION_VALUES:
        for final in CLASSIFICATION_VALUES:
            path = (("q1", initial), ("q2", "review_all"),
                    ("q3", f"choose_{final}"))
            assert outcome(path) == final


def test_uncertain_initial_choice_uses_only_the_final_operator_selected_class():
    for final in CLASSIFICATION_VALUES:
        path = (("q1", "uncertain"), ("q3", f"choose_{final}"))
        assert outcome(path) == final


def test_every_unresolved_exit_is_explicit():
    paths = [
        (("q1", classification), ("q2", "unresolved"))
        for classification in CLASSIFICATION_VALUES
    ]
    paths += [
        (("q1", classification), ("q2", "review_all"),
         ("q3", "choose_unresolved"))
        for classification in CLASSIFICATION_VALUES
    ]
    paths.append((("q1", "uncertain"), ("q3", "choose_unresolved")))
    assert len(paths) == 11
    assert all(outcome(path) is UNRESOLVED for path in paths)


def test_content_contains_no_legacy_pricing_vocabulary():
    rendered = repr(OPERATOR_QUESTION_SET_V1).lower()
    for term in ("friction_type", "output_type", "repeat_pricing_visit", "pricing"):
        assert term not in rendered


def test_all_46_authored_paths_match_real_handler_behavior():
    entries = dict(OPERATOR_QUESTION_SETS._entries)
    active_key = OPERATOR_QUESTION_SETS._active_key
    observed = Counter()
    try:
        OPERATOR_QUESTION_SETS.register(OPERATOR_QUESTION_SET_V1)
        OPERATOR_QUESTION_SETS.activate(QUESTION_SET_ID, QUESTION_SET_VERSION)

        for index, rule in enumerate(OPERATOR_QUESTION_SET_V1.rules):
            repository._INTERACTIONS.clear()
            start = start_operator_interaction(f"user-{index}", f"session-{index}")
            interaction_id = start["interaction_id"]
            response = None
            for question_id, option_id in rule.path:
                response = answer_operator_interaction(
                    repository.get_interaction(interaction_id), question_id, option_id)

            expected = getattr(rule.outcome, "value", rule.outcome)
            if expected == "UNRESOLVED":
                assert response["status"] == "unresolved"
                assert response["reason"] == "EXPLICIT_UNRESOLVED"
                observed["UNRESOLVED"] += 1
            else:
                assert response["status"] == "resolved"
                assert response["classification"] == expected
                observed[expected] += 1

        assert observed == Counter({
            "perceptual": 7,
            "narrative": 7,
            "emotional": 7,
            "behavioral": 7,
            "continuity": 7,
            "UNRESOLVED": 11,
        })
    finally:
        repository._INTERACTIONS.clear()
        OPERATOR_QUESTION_SETS._entries = entries
        OPERATOR_QUESTION_SETS._active_key = active_key
