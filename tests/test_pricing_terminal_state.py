"""Stored terminal state of completed pricing interactions.

Asserts only named fields of the stored interaction, as the source at b3117c0
behaves. Ids and timestamps are never asserted, and the whole object is never
compared, so later optional model fields do not break these tests.
"""

import pytest

import security.rate_limit as rate_limit
import storage.repository as repository
from api.interaction import answer_interaction, start_interaction
from api.trigger import trigger_check
from tests.golden import pricing_cases


TERMINAL_FIELDS = [
    "resolved",
    "abandoned",
    "state",
    "q1",
    "q2",
    "q3",
    "friction_type",
    "output_type",
]

COMPLETED_PATHS = [
    (
        "dont_understand_difference__plan_a_vs_b",
        [("q1", "dont_understand_difference"), ("q2", "plan_a_vs_b")],
        {"q1": "dont_understand_difference", "q2": "plan_a_vs_b", "q3": None,
         "friction_type": "information_gap", "output_type": "clarify"},
    ),
    (
        "too_expensive__value",
        [("q1", "too_expensive"), ("q2", "value")],
        {"q1": "too_expensive", "q2": "value", "q3": None,
         "friction_type": "trust_deficit", "output_type": "proof"},
    ),
    (
        "not_sure_fit__long_text",
        [("q1", "not_sure_fit"), ("q2", "after budget approval")],
        {"q1": "not_sure_fit", "q2": "after budget approval", "q3": None,
         "friction_type": "fit_uncertainty", "output_type": "filter"},
    ),
    (
        "not_ready__short_text__q3_clarity",
        [("q1", "not_ready"), ("q2", "soon"), ("q3", "clarity")],
        {"q1": "not_ready", "q2": "soon", "q3": "clarity",
         "friction_type": "information_gap", "output_type": "clarify"},
    ),
    (
        "other__fallback_q2__q3_trust",
        [("q1", "other"), ("q2", "not sure"), ("q3", "trust")],
        {"q1": "other", "q2": "not sure", "q3": "trust",
         "friction_type": "trust_deficit", "output_type": "proof"},
    ),
    (
        "unknown_q1__fallback",
        [("q1", "banana"), ("q2", "something specific")],
        {"q1": "banana", "q2": "something specific", "q3": None,
         "friction_type": "information_gap", "output_type": "clarify"},
    ),
]


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    pricing_cases.reset_state()
    monkeypatch.setattr(rate_limit, "time", pricing_cases.fixed_time)
    yield
    pricing_cases.reset_state()


def complete_path(answers):
    started = start_interaction(pricing_cases.start()[1])
    interaction_id = started["interaction_id"]

    response = None
    for question_id, value in answers:
        response = answer_interaction({
            "interaction_id": interaction_id,
            "question_id": question_id,
            "answer": value,
        })

    assert response["done"] is True
    return repository.get_interaction(interaction_id)


@pytest.mark.parametrize(
    "answers, expected",
    [(answers, expected) for _, answers, expected in COMPLETED_PATHS],
    ids=[name for name, _, _ in COMPLETED_PATHS],
)
def test_completed_interaction_terminal_fields(answers, expected):
    stored = complete_path(answers)

    expected_fields = {
        "resolved": True,
        "abandoned": False,
        "state": "output_rendered",
        **expected,
    }
    actual_fields = {field: getattr(stored, field) for field in TERMINAL_FIELDS}

    assert actual_fields == expected_fields
    assert stored.resolved is True
    assert stored.abandoned is False


@pytest.mark.parametrize(
    "answers",
    [answers for _, answers, _ in COMPLETED_PATHS],
    ids=[name for name, _, _ in COMPLETED_PATHS],
)
def test_pricing_trigger_shows_again_after_completion(answers):
    complete_path(answers)

    result = trigger_check(pricing_cases.trigger(session_id="s1")[1])

    assert result == {"show": True}
    assert result["show"] is True
