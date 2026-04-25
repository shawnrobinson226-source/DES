from core.trigger_engine import should_trigger


def test_trigger_fires_only_when_all_conditions_pass():
    assert should_trigger(
        pricing_page_sessions_last_30d=2,
        has_converted=False,
        current_page="/pricing",
        has_active_interaction=False,
        cooldown_ok=True,
    ) is True


def test_trigger_requires_at_least_two_pricing_sessions():
    assert should_trigger(1, False, "/pricing", False, True) is False


def test_trigger_does_not_fire_for_converted_users():
    assert should_trigger(2, True, "/pricing", False, True) is False


def test_trigger_requires_pricing_page():
    assert should_trigger(2, False, "/dashboard", False, True) is False


def test_trigger_does_not_fire_with_active_interaction():
    assert should_trigger(2, False, "/pricing", True, True) is False


def test_trigger_requires_cooldown_to_be_satisfied():
    assert should_trigger(2, False, "/pricing", False, False) is False


def run_test():
    test_trigger_fires_only_when_all_conditions_pass()
    test_trigger_requires_at_least_two_pricing_sessions()
    test_trigger_does_not_fire_for_converted_users()
    test_trigger_requires_pricing_page()
    test_trigger_does_not_fire_with_active_interaction()
    test_trigger_requires_cooldown_to_be_satisfied()
    print("Trigger tests passed")


if __name__ == "__main__":
    run_test()
