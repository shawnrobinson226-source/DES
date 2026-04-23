# DES V1 — Classifier

"""
Deterministic classification.

NO probabilities
NO inference
NO hidden logic
"""


def classify(q1_answer: str, q2_answer: str = None, q3_answer: str = None) -> str:

    # --- Direct mappings ---

    if q1_answer == "dont_understand_difference":
        return "information_gap"

    if q1_answer == "not_sure_fit":
        return "fit_uncertainty"

    if q1_answer == "not_ready":
        return "information_gap"

    # --- Cost handling ---

    if q1_answer == "too_expensive":
        if q2_answer == "total_cost":
            return "fit_uncertainty"
        if q2_answer in ["value", "risk"]:
            return "trust_deficit"

    # --- Q3 tiebreaker ---

    if q3_answer == "clarity":
        return "information_gap"

    if q3_answer == "fit":
        return "fit_uncertainty"

    if q3_answer == "trust":
        return "trust_deficit"

    if q3_answer == "cost":
        return "fit_uncertainty"

    # --- Default fallback ---

    return "information_gap"