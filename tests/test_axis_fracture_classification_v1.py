"""Production AXIS-fracture classification policy and runtime proof."""

from collections import Counter

import storage.repository as repository
from core.axis.bridge import CLASSIFICATION_VALUES
from core.operator_flow import (
    INTERACTION_CLOSED,
    INVALID_OPTION,
    OUT_OF_ORDER,
    answer_operator_interaction,
    start_operator_interaction,
)
from core.question_sets.axis_fracture_classification_v1 import (
    AXIS_EXECUTION_FILE,
    AXIS_FRACTURE_CLASSIFICATION_V1,
    AXIS_SOURCE_COMMIT,
    AXIS_SOURCE_FILE,
    EXPECTED_FRACTURE_IDS,
    FRACTURE_CHOICES,
    QUESTION_SET_ID,
    QUESTION_SET_VERSION,
)
from core.question_sets.registry import OPERATOR_QUESTION_SETS
from core.question_sets.sentinels import END, UNRESOLVED


EXPECTED_CHOICES = (
    ("control_loss", "Control Grip", "perceptual"),
    ("rejection_sensitivity", "Rejection Alarm", "emotional"),
    ("status_threat", "Status Threat", "narrative"),
    ("uncertainty_intolerance", "Uncertainty Pressure", "perceptual"),
    ("self_worth_dependency", "Worth Attachment", "narrative"),
    ("boundary_violation", "Boundary Drift", "behavioral"),
    ("comparison_spiral", "Comparison Loop", "narrative"),
    ("over_responsibility", "Responsibility Overreach", "behavioral"),
    ("avoidance_loop", "Avoidance Loop", "behavioral"),
    ("shame_spike", "Shame Spike", "emotional"),
)


def _activate():
    OPERATOR_QUESTION_SETS.register(AXIS_FRACTURE_CLASSIFICATION_V1)
    OPERATOR_QUESTION_SETS.activate(QUESTION_SET_ID, QUESTION_SET_VERSION)


def test_identity_and_axis_provenance_are_pinned():
    assert (QUESTION_SET_ID, QUESTION_SET_VERSION) == (
        "axis_fracture_classification", "1.0.0")
    assert AXIS_SOURCE_COMMIT == "2c3fd35d36fa0d1eea751f02f1ac38776a3d3a1f"
    assert AXIS_SOURCE_FILE == "lib/patterns/registry.ts"
    assert AXIS_EXECUTION_FILE == "app/session/page.tsx"


def test_fracture_vocabulary_labels_and_mapping_match_approved_source():
    assert FRACTURE_CHOICES == EXPECTED_CHOICES
    assert {item[0] for item in FRACTURE_CHOICES} == EXPECTED_FRACTURE_IDS
    assert {item[2] for item in FRACTURE_CHOICES} == (
        CLASSIFICATION_VALUES - {"continuity"})


def test_question_graph_has_twelve_entry_options_and_no_class_choice():
    q1, q2 = AXIS_FRACTURE_CLASSIFICATION_V1.questions
    assert (q1.id, q2.id) == ("q1", "q2")
    assert len(q1.options) == 12
    assert tuple(option.id for option in q1.options) == (
        tuple(item[0] for item in EXPECTED_CHOICES) + ("none_apply", "unsure"))
    assert not ({option.id for option in q1.options} & CLASSIFICATION_VALUES)
    assert not ({option.label.lower() for option in q1.options} & CLASSIFICATION_VALUES)
    assert all(option.next == "q2" for option in q1.options[:10])
    assert all(option.next is END for option in q1.options[10:])
    assert tuple(option.id for option in q2.options) == (
        "no_other_pattern", "another_pattern_present")


def test_every_one_of_twenty_two_paths_has_one_explicit_rule():
    question_set = AXIS_FRACTURE_CLASSIFICATION_V1
    assert len(question_set.complete_paths) == 22
    assert len(question_set.rule_index) == 22
    assert set(question_set.rule_index) == set(question_set.complete_paths)


def test_only_unambiguous_single_fractures_resolve_and_continuity_never_does():
    observed = Counter(
        getattr(outcome, "value", outcome)
        for outcome in AXIS_FRACTURE_CLASSIFICATION_V1.rule_index.values()
    )
    assert observed == Counter({
        "UNRESOLVED": 12,
        "behavioral": 3,
        "narrative": 3,
        "emotional": 2,
        "perceptual": 2,
    })
    assert "continuity" not in observed
    assert AXIS_FRACTURE_CLASSIFICATION_V1.rule_index[(
        ("q1", "none_apply"),)] is UNRESOLVED
    assert AXIS_FRACTURE_CLASSIFICATION_V1.rule_index[(
        ("q1", "unsure"),)] is UNRESOLVED


def test_all_twenty_two_paths_and_rejections_match_real_handler_behavior():
    entries = dict(OPERATOR_QUESTION_SETS._entries)
    active_key = OPERATOR_QUESTION_SETS._active_key
    try:
        _activate()
        for index, rule in enumerate(AXIS_FRACTURE_CLASSIFICATION_V1.rules):
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
            else:
                assert response["status"] == "resolved"
                assert response["classification"] == expected

        repository._INTERACTIONS.clear()
        start = start_operator_interaction("reject-user", "reject-session")
        interaction_id = start["interaction_id"]
        interaction = repository.get_interaction(interaction_id)
        assert answer_operator_interaction(interaction, "q1", "behavioral")["code"] == INVALID_OPTION
        assert answer_operator_interaction(interaction, "q1", "Control Grip")["code"] == INVALID_OPTION
        assert answer_operator_interaction(interaction, "q1", "unknown_pattern")["code"] == INVALID_OPTION
        assert answer_operator_interaction(interaction, "q2", "no_other_pattern")["code"] == OUT_OF_ORDER

        response = answer_operator_interaction(interaction, "q1", "none_apply")
        assert response["status"] == "unresolved"
        assert answer_operator_interaction(
            repository.get_interaction(interaction_id), "q1", "none_apply")["code"] == INTERACTION_CLOSED
    finally:
        repository._INTERACTIONS.clear()
        OPERATOR_QUESTION_SETS._entries = entries
        OPERATOR_QUESTION_SETS._active_key = active_key
