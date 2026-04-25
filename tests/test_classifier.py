from core.classifier import classify


def test_direct_q1_mappings():
    assert classify("dont_understand_difference") == "information_gap"
    assert classify("not_sure_fit") == "fit_uncertainty"
    assert classify("not_ready") == "information_gap"


def test_cost_mappings_use_q2_answer():
    assert classify("too_expensive", "total_cost") == "fit_uncertainty"
    assert classify("too_expensive", "value") == "trust_deficit"
    assert classify("too_expensive", "risk") == "trust_deficit"


def test_q3_tiebreaker_mappings():
    assert classify("other", "short", "clarity") == "information_gap"
    assert classify("other", "short", "fit") == "fit_uncertainty"
    assert classify("other", "short", "trust") == "trust_deficit"
    assert classify("other", "short", "cost") == "fit_uncertainty"


def test_unknown_inputs_fall_back_to_information_gap():
    assert classify("other", "unmapped", "unmapped") == "information_gap"
    assert classify("too_expensive", "unmapped") == "information_gap"


def run_test():
    test_direct_q1_mappings()
    test_cost_mappings_use_q2_answer()
    test_q3_tiebreaker_mappings()
    test_unknown_inputs_fall_back_to_information_gap()
    print("Classifier tests passed")


if __name__ == "__main__":
    run_test()
