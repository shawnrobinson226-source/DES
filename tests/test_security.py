# DES V1 — Security Test

from api.trigger import trigger_check
from api.interaction import start_interaction


def run_security_tests():
    print("Test 1 — Unknown field (trigger)")

    res1 = trigger_check({
        "pricing_page_sessions_last_30d": 2,
        "has_converted": False,
        "current_page": "/pricing",
        "session_id": "s1",
        "cooldown_ok": True,
        "extra_field": "should_fail"
    })

    print(res1)

    print("\nTest 2 — Missing field (start)")

    res2 = start_interaction({
        "user_id": "u1",
        # missing session_id
        "trigger_type": "repeat_pricing_visit"
    })

    print(res2)


if __name__ == "__main__":
    run_security_tests()