# DES V1 — Basic Flow Test

from api.trigger import trigger_check
from api.interaction import start_interaction, answer_interaction


def run_test():
    # --- trigger ---
    trigger = trigger_check({
        "pricing_page_sessions_last_30d": 2,
        "has_converted": False,
        "current_page": "/pricing",
        "session_id": "s1",
        "cooldown_ok": True,
    })

    print("Trigger:", trigger)

    if not trigger["show"]:
        print("FAILED: trigger did not fire")
        return

    # --- start ---
    start = start_interaction({
        "user_id": "u1",
        "session_id": "s1",
        "trigger_type": "repeat_pricing_visit",
    })

    print("Start:", start)

    interaction_id = start["interaction_id"]

    # --- q1 ---
    q2 = answer_interaction({
        "interaction_id": interaction_id,
        "question_id": "q1",
        "answer": "too_expensive",
    })

    print("Q2:", q2)

    # --- q2 ---
    result = answer_interaction({
        "interaction_id": interaction_id,
        "question_id": "q2",
        "answer": "value",
    })

    print("Result:", result)


if __name__ == "__main__":
    run_test()