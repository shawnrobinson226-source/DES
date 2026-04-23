# DES V1 — Question Flow

"""
Rules:
- Max 3 questions
- Q1 always asked first
- Q2 depends on Q1
- Q3 only if ambiguity

NO extra questions
NO dynamic expansion
"""


# --- Q1 ---

def get_q1():
    return {
        "id": "q1",
        "text": "What’s the main thing holding you back right now?",
        "options": [
            "dont_understand_difference",
            "not_sure_fit",
            "too_expensive",
            "not_ready",
            "other",
        ],
    }


# --- Q2 ---

def get_q2(q1_answer: str):
    if q1_answer == "dont_understand_difference":
        return {
            "id": "q2",
            "text": "Which plans are you comparing?",
            "options": [
                "plan_a_vs_b",
                "plan_b_vs_c",
                "all_plans",
            ],
        }

    if q1_answer == "not_sure_fit":
        return {
            "id": "q2",
            "text": "What are you trying to use this for?",
            "input": "text",
        }

    if q1_answer == "too_expensive":
        return {
            "id": "q2",
            "text": "What makes it feel expensive?",
            "options": [
                "total_cost",
                "value",
                "risk",
            ],
        }

    if q1_answer == "not_ready":
        return {
            "id": "q2",
            "text": "What needs to happen before you’re ready?",
            "input": "text",
        }

    # fallback
    return {
        "id": "q2",
        "text": "Can you clarify a bit more?",
        "input": "text",
    }


# --- Q3 DECISION ---

def should_ask_q3(q1_answer: str, q2_answer: str) -> bool:
    if q1_answer == "other":
        return True

    if not q2_answer:
        return True

    if isinstance(q2_answer, str) and len(q2_answer.strip()) < 10:
        return True

    return False


# --- Q3 ---

def get_q3():
    return {
        "id": "q3",
        "text": "Which of these best describes your situation?",
        "options": [
            "clarity",
            "fit",
            "trust",
            "cost",
        ],
    }