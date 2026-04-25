from core.output_builder import build_output


def test_information_gap_builds_clarify_output():
    output = build_output("information_gap")

    assert output["output_type"] == "clarify"
    assert output["title"] == "Let’s clarify the differences"
    assert output["cta"] == "View comparison"
    assert output["ui"] == {
        "suppress_primary_cta": False,
        "recommend_exit": False,
    }


def test_fit_uncertainty_builds_filter_output():
    output = build_output("fit_uncertainty")

    assert output["output_type"] == "filter"
    assert output["title"] == "This may not be the right fit"
    assert output["cta"] == ""
    assert output["ui"] == {
        "suppress_primary_cta": True,
        "recommend_exit": True,
    }


def test_trust_deficit_builds_proof_output():
    output = build_output("trust_deficit")

    assert output["output_type"] == "proof"
    assert output["title"] == "Here’s how this holds up"
    assert output["cta"] == "View proof"
    assert output["ui"] == {
        "suppress_primary_cta": False,
        "recommend_exit": False,
    }


def test_unknown_friction_type_falls_back_to_clarify_output():
    output = build_output("unknown")

    assert output == {
        "output_type": "clarify",
        "title": "Let’s clarify this",
        "body": "Here’s more information to help you decide.",
        "cta": "Learn more",
        "ui": {
            "suppress_primary_cta": False,
            "recommend_exit": False,
        },
    }


def run_test():
    test_information_gap_builds_clarify_output()
    test_fit_uncertainty_builds_filter_output()
    test_trust_deficit_builds_proof_output()
    test_unknown_friction_type_falls_back_to_clarify_output()
    print("Output tests passed")


if __name__ == "__main__":
    run_test()
