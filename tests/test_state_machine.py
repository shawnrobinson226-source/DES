from core.state_machine import VALID_TRANSITIONS, can_transition, transition


def test_reserved_state_machine_allows_documented_happy_path():
    path = [
        "idle",
        "triggered",
        "interaction_started",
        "q1_answered",
        "q2_answered",
        "q3_answered",
        "classified",
        "output_rendered",
        "resolved",
    ]

    current = path[0]
    for next_state in path[1:]:
        assert can_transition(current, next_state) is True
        assert transition(current, next_state) == next_state
        current = next_state


def test_reserved_state_machine_allows_classification_without_q3():
    assert can_transition("q1_answered", "classified") is True
    assert can_transition("q2_answered", "classified") is True


def test_reserved_state_machine_allows_abandonment_before_terminal_states():
    assert can_transition("triggered", "abandoned") is True
    assert can_transition("interaction_started", "abandoned") is True
    assert can_transition("q1_answered", "abandoned") is True
    assert can_transition("q2_answered", "abandoned") is True
    assert can_transition("q3_answered", "abandoned") is True


def test_reserved_state_machine_rejects_invalid_transitions():
    assert can_transition("idle", "resolved") is False
    assert can_transition("resolved", "output_rendered") is False
    assert can_transition("abandoned", "resolved") is False
    assert can_transition("unknown", "triggered") is False


def test_transition_raises_for_invalid_transition():
    try:
        transition("idle", "resolved")
    except ValueError as error:
        assert str(error) == "Invalid state transition"
    else:
        raise AssertionError("Expected invalid transition to raise ValueError")


def test_terminal_states_have_no_outbound_transitions():
    assert VALID_TRANSITIONS["resolved"] == []
    assert VALID_TRANSITIONS["abandoned"] == []


def run_test():
    test_reserved_state_machine_allows_documented_happy_path()
    test_reserved_state_machine_allows_classification_without_q3()
    test_reserved_state_machine_allows_abandonment_before_terminal_states()
    test_reserved_state_machine_rejects_invalid_transitions()
    test_transition_raises_for_invalid_transition()
    test_terminal_states_have_no_outbound_transitions()
    print("State machine tests passed")


if __name__ == "__main__":
    run_test()
