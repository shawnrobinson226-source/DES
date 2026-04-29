from urllib.error import HTTPError

from core.axis.bridge import (
    AXIS_PAYLOAD_FIELDS,
    build_axis_execute_payload,
    execute_axis_request,
)


class FakeResponse:
    status = 200

    def __init__(self, body=b'{"accepted": true}'):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self.body

    def close(self):
        return None


def des_output(friction_type):
    return {
        "friction_type": friction_type,
        "details": {},
    }


def accepting_transport(calls):
    def transport(request, timeout):
        calls.append((request, timeout))
        return FakeResponse()

    return transport


def rejecting_transport(request, timeout):
    raise HTTPError(
        request.full_url,
        400,
        "Bad Request",
        hdrs=None,
        fp=FakeResponse(b'{"error":"rejected"}'),
    )


def test_information_gap_maps_to_perceptual():
    payload = build_axis_execute_payload(des_output("information_gap"), "raw trigger")

    assert payload["classification"] == "perceptual"


def test_fit_uncertainty_maps_to_behavioral():
    payload = build_axis_execute_payload(des_output("fit_uncertainty"), "raw trigger")

    assert payload["classification"] == "behavioral"


def test_trust_deficit_maps_to_narrative():
    payload = build_axis_execute_payload(des_output("trust_deficit"), "raw trigger")

    assert payload["classification"] == "narrative"


def test_missing_operator_id_fails_without_calling_axis():
    calls = []

    result = execute_axis_request(
        des_output("information_gap"),
        "raw trigger",
        "",
        axis_base_url="https://axis.example",
        transport=accepting_transport(calls),
    )

    assert result == {
        "ok": False,
        "error": {
            "code": "MISSING_OPERATOR_ID",
            "message": "operator_id is required",
        },
    }
    assert calls == []


def test_invalid_friction_type_fails_without_calling_axis():
    calls = []

    result = execute_axis_request(
        des_output("confusion"),
        "raw trigger",
        "operator-1",
        axis_base_url="https://axis.example",
        transport=accepting_transport(calls),
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "INVALID_DES_OUTPUT"
    assert result["error"]["message"] == "unknown friction_type"
    assert calls == []


def test_axis_rejection_returns_cleanly_without_mutating_payload():
    result = execute_axis_request(
        des_output("information_gap"),
        "raw trigger",
        "operator-1",
        axis_base_url="https://axis.example",
        transport=rejecting_transport,
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "AXIS_REJECTED"
    assert result["error"]["status_code"] == 400
    assert result["payload"] == {
        "trigger": "raw trigger",
        "classification": "perceptual",
        "next_action": "Review the clarified decision information and choose one next step.",
        "reference": True,
        "stability": 6,
        "impact": 4,
    }


def test_axis_request_uses_execute_endpoint_and_operator_header():
    calls = []

    result = execute_axis_request(
        des_output("fit_uncertainty"),
        "raw trigger",
        "operator-1",
        axis_base_url="https://axis.example/root/",
        transport=accepting_transport(calls),
    )

    request, timeout = calls[0]

    assert result["ok"] is True
    assert request.full_url == "https://axis.example/root/api/v2/execute"
    assert request.headers["X-operator-id"] == "operator-1"
    assert timeout == 10


def test_payload_contains_only_axis_execute_fields():
    payload = build_axis_execute_payload(des_output("information_gap"), "raw trigger")

    assert set(payload.keys()) == AXIS_PAYLOAD_FIELDS
    assert "outcome" not in payload
    assert "distortion_class" not in payload


def run_test():
    test_information_gap_maps_to_perceptual()
    test_fit_uncertainty_maps_to_behavioral()
    test_trust_deficit_maps_to_narrative()
    test_missing_operator_id_fails_without_calling_axis()
    test_invalid_friction_type_fails_without_calling_axis()
    test_axis_rejection_returns_cleanly_without_mutating_payload()
    test_axis_request_uses_execute_endpoint_and_operator_header()
    test_payload_contains_only_axis_execute_fields()
    print("DES AXIS bridge tests passed")


if __name__ == "__main__":
    run_test()
