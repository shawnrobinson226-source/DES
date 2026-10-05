"""Error precedence in the pricing API, as the source at b3117c0 behaves.

Each request carries two problems; the test pins which one is reported.
Time is fixed and both in-memory stores are cleared around every test.
"""

import pytest

import security.rate_limit as rate_limit
import storage.repository as repository
from api.interaction import answer_interaction, start_interaction
from tests.golden import pricing_cases


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    pricing_cases.reset_state()
    monkeypatch.setattr(rate_limit, "time", pricing_cases.fixed_time)
    yield
    pricing_cases.reset_state()


def test_invalid_question_id_wins_over_missing_interaction():
    # api/interaction.py:62 checks question_id before the lookup at :68-71.
    response = answer_interaction({
        "interaction_id": pricing_cases.MISSING_INTERACTION_ID,
        "question_id": "q9",
        "answer": "too_expensive",
    })

    assert response == {"error": "Invalid question_id", "code": "INVALID_INPUT"}
    assert repository._INTERACTIONS == {}


def test_rate_limit_wins_over_invalid_start_input():
    # api/interaction.py:14-16 rate-limits by user_id before any validation.
    for _ in range(10):
        assert "interaction_id" in start_interaction(pricing_cases.start(user_id="u_rate")[1])

    response = start_interaction(
        pricing_cases.start(user_id="u_rate", trigger_type="unknown_trigger")[1]
    )

    assert response == {"error": "Rate limited", "code": "RATE_LIMITED"}
    assert len(repository._INTERACTIONS) == 10


def test_invalid_start_requests_count_toward_rate_limit():
    for _ in range(10):
        response = start_interaction(
            pricing_cases.start(user_id="u_rate", trigger_type="unknown_trigger")[1]
        )
        assert response == {"error": "Invalid trigger_type", "code": "INVALID_INPUT"}

    response = start_interaction(pricing_cases.start(user_id="u_rate")[1])

    assert response == {"error": "Rate limited", "code": "RATE_LIMITED"}
    assert repository._INTERACTIONS == {}


def test_over_length_user_id_wins_over_wrong_trigger_type():
    # api/interaction.py:25-26 validates user_id before trigger_type at :31-32.
    response = start_interaction(
        pricing_cases.start(user_id="u" * 129, trigger_type="unknown_trigger")[1]
    )

    assert response == {"error": "Invalid user_id", "code": "INVALID_INPUT"}
    assert repository._INTERACTIONS == {}
