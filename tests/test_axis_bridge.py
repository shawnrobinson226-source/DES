from core.axis_bridge import (
    ALLOWED_FIELDS,
    BridgeError,
    build_axis_payload,
)


def completed_result(
    friction_type="information_gap",
    output_type="clarify",
    trigger="repeat_pricing_visit",
    title="Fallback trigger title",
):
    return {
        "trigger": trigger,
        "friction_type": friction_type,
        "output": {
            "output_type": output_type,
            "title": title,
            "body": "Controlled DES output body.",
            "cta": "View comparison",
            "ui": {
                "suppress_primary_cta": False,
                "recommend_exit": False,
            },
        },
    }


def assert_bridge_error(des_result, expected_message):
    try:
        build_axis_payload(des_result)
    except BridgeError as error:
        assert str(error) == expected_message
    else:
        raise AssertionError("Expected BridgeError")


def test_valid_payload_builds_correctly():
    payload = build_axis_payload(completed_result())

    assert payload == {
        "trigger": "repeat_pricing_visit",
        "classification": "perceptual",
        "next_action": "Review the clarified decision information and choose one next step.",
        "reference": True,
        "stability": 6,
        "impact": 4,
    }


def test_all_friction_type_mappings():
    cases = {
        "information_gap": "perceptual",
        "fit_uncertainty": "behavioral",
        "trust_deficit": "narrative",
    }

    for friction_type, classification in cases.items():
        payload = build_axis_payload(completed_result(friction_type=friction_type))
        assert payload["classification"] == classification


def test_all_output_type_mappings():
    cases = {
        "clarify": "Review the clarified decision information and choose one next step.",
        "filter": "Confirm fit or non-fit and act on the result.",
        "proof": "Review the evidence and separate verified claims from assumptions.",
    }

    for output_type, next_action in cases.items():
        payload = build_axis_payload(completed_result(output_type=output_type))
        assert payload["next_action"] == next_action


def test_uses_des_result_trigger_when_present():
    payload = build_axis_payload(
        completed_result(trigger="completed_des_interaction")
    )

    assert payload["trigger"] == "completed_des_interaction"


def test_missing_trigger_fails():
    des_result = completed_result(title="Lets clarify the differences")
    del des_result["trigger"]

    assert_bridge_error(des_result, "Trigger must be a non-empty string")


def test_empty_trigger_fails():
    assert_bridge_error(completed_result(trigger="  "), "Trigger must be a non-empty string")


def test_unknown_friction_type_fails():
    assert_bridge_error(completed_result(friction_type="unknown"), "Unknown friction_type")


def test_unknown_output_type_fails():
    assert_bridge_error(completed_result(output_type="redirect"), "Unknown output_type")


def test_missing_output_fails():
    des_result = completed_result()
    del des_result["output"]

    assert_bridge_error(des_result, "Missing output")


def test_non_dict_output_fails():
    des_result = completed_result()
    des_result["output"] = "clarify"

    assert_bridge_error(des_result, "Output must be a dict")


def test_payload_contains_only_allowed_axis_fields():
    payload = build_axis_payload(completed_result())

    assert set(payload.keys()) == ALLOWED_FIELDS


def test_payload_uses_classification_not_distortion_class():
    payload = build_axis_payload(completed_result())

    assert "classification" in payload
    assert "distortion_class" not in payload


def test_no_live_axis_call_occurs():
    payload = build_axis_payload(completed_result())

    assert payload["trigger"] == "repeat_pricing_visit"
    assert "url" not in payload
    assert "endpoint" not in payload


def test_missing_friction_type_fails():
    des_result = completed_result()
    del des_result["friction_type"]

    assert_bridge_error(des_result, "Missing friction_type")


def test_missing_output_type_fails():
    des_result = completed_result()
    del des_result["output"]["output_type"]

    assert_bridge_error(des_result, "Missing output_type")


def run_test():
    test_valid_payload_builds_correctly()
    test_all_friction_type_mappings()
    test_all_output_type_mappings()
    test_uses_des_result_trigger_when_present()
    test_missing_trigger_fails()
    test_empty_trigger_fails()
    test_unknown_friction_type_fails()
    test_unknown_output_type_fails()
    test_missing_output_fails()
    test_non_dict_output_fails()
    test_payload_contains_only_allowed_axis_fields()
    test_payload_uses_classification_not_distortion_class()
    test_no_live_axis_call_occurs()
    test_missing_friction_type_fails()
    test_missing_output_type_fails()
    print("AXIS bridge tests passed")


if __name__ == "__main__":
    run_test()
