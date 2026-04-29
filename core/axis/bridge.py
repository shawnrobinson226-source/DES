# DES V1 — AXIS execution adapter

"""
Adapter boundary for DES to AXIS execution.

Adapters translate. They do not classify, infer, persuade, or mutate DES
behavior.
"""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class AxisBridgeError(ValueError):
    """Raised when DES output cannot be converted into an AXIS request."""


AXIS_EXECUTE_PATH = "/api/v2/execute"

AXIS_PAYLOAD_FIELDS = {
    "trigger",
    "classification",
    "next_action",
    "reference",
    "stability",
    "impact",
}

CLASSIFICATION_VALUES = {
    "narrative",
    "emotional",
    "behavioral",
    "perceptual",
    "continuity",
}

FRICTION_CLASSIFICATION_MAP = {
    "information_gap": "perceptual",
    "fit_uncertainty": "behavioral",
    "trust_deficit": "narrative",
}

NEXT_ACTION_BY_FRICTION = {
    "information_gap": "Review the clarified decision information and choose one next step.",
    "fit_uncertainty": "Confirm fit or non-fit and act on the result.",
    "trust_deficit": "Review the evidence and separate verified claims from assumptions.",
}

NEXT_ACTION_BY_OUTPUT_TYPE = {
    "clarify": NEXT_ACTION_BY_FRICTION["information_gap"],
    "filter": NEXT_ACTION_BY_FRICTION["fit_uncertainty"],
    "proof": NEXT_ACTION_BY_FRICTION["trust_deficit"],
}

DEFAULT_CONTEXT = {
    "reference": True,
    "stability": 6,
    "impact": 4,
}


def build_axis_execute_payload(
    des_output: dict,
    trigger: str,
    context: dict | None = None,
) -> dict:
    if not isinstance(des_output, dict):
        raise AxisBridgeError("DES output must be a dict")

    if not _is_non_empty_string(trigger):
        raise AxisBridgeError("trigger is required")

    friction_type = des_output.get("friction_type")
    if not _is_non_empty_string(friction_type):
        raise AxisBridgeError("friction_type is required")

    if friction_type not in FRICTION_CLASSIFICATION_MAP:
        raise AxisBridgeError("unknown friction_type")

    details = des_output.get("details", {})
    if details is None:
        details = {}

    if not isinstance(details, dict):
        raise AxisBridgeError("details must be a dict")

    payload_context = _build_context(context)
    payload = {
        "trigger": trigger,
        "classification": FRICTION_CLASSIFICATION_MAP[friction_type],
        "next_action": _resolve_next_action(friction_type, details),
        "reference": payload_context["reference"],
        "stability": payload_context["stability"],
        "impact": payload_context["impact"],
    }

    validate_axis_payload(payload)
    return payload


def execute_axis_request(
    des_output: dict,
    trigger: str,
    operator_id: str,
    context: dict | None = None,
    axis_base_url: str | None = None,
    transport=urlopen,
) -> dict:
    if not _is_non_empty_string(operator_id):
        return _error("MISSING_OPERATOR_ID", "operator_id is required")

    try:
        payload = build_axis_execute_payload(des_output, trigger, context)
    except AxisBridgeError as error:
        return _error("INVALID_DES_OUTPUT", str(error))

    base_url = axis_base_url or os.environ.get("AXIS_BASE_URL")
    if not _is_non_empty_string(base_url):
        return _error("MISSING_AXIS_BASE_URL", "AXIS_BASE_URL is required", payload)

    request = Request(
        _execute_url(base_url),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-operator-id": operator_id,
        },
        method="POST",
    )

    try:
        with transport(request, timeout=10) as response:
            body = response.read().decode("utf-8")
            return {
                "ok": True,
                "status_code": getattr(response, "status", None),
                "payload": payload,
                "response": _decode_json(body),
            }
    except HTTPError as error:
        return {
            "ok": False,
            "error": {
                "code": "AXIS_REJECTED",
                "message": "AXIS rejected the request",
                "status_code": error.code,
                "body": _safe_error_body(error),
            },
            "payload": payload,
        }
    except URLError as error:
        return _error("AXIS_REQUEST_FAILED", str(error.reason), payload)


def validate_axis_payload(payload: dict) -> None:
    if not isinstance(payload, dict):
        raise AxisBridgeError("payload must be a dict")

    if set(payload.keys()) != AXIS_PAYLOAD_FIELDS:
        raise AxisBridgeError("payload fields are invalid")

    if not _is_non_empty_string(payload["trigger"]):
        raise AxisBridgeError("payload trigger is required")

    if payload["classification"] not in CLASSIFICATION_VALUES:
        raise AxisBridgeError("payload classification is invalid")

    if not _is_non_empty_string(payload["next_action"]):
        raise AxisBridgeError("payload next_action is required")

    if not isinstance(payload["reference"], bool):
        raise AxisBridgeError("payload reference must be a boolean")

    if not _is_number(payload["stability"]):
        raise AxisBridgeError("payload stability must be a number")

    if not _is_number(payload["impact"]):
        raise AxisBridgeError("payload impact must be a number")


def _resolve_next_action(friction_type: str, details: dict) -> str:
    next_action = details.get("next_action")
    if _is_non_empty_string(next_action):
        return next_action

    output_type = details.get("output_type")
    if _is_non_empty_string(output_type):
        if output_type not in NEXT_ACTION_BY_OUTPUT_TYPE:
            raise AxisBridgeError("unknown output_type")
        return NEXT_ACTION_BY_OUTPUT_TYPE[output_type]

    return NEXT_ACTION_BY_FRICTION[friction_type]


def _build_context(context: dict | None) -> dict:
    if context is None:
        return dict(DEFAULT_CONTEXT)

    if not isinstance(context, dict):
        raise AxisBridgeError("context must be a dict")

    allowed_context = set(DEFAULT_CONTEXT.keys())
    if any(key not in allowed_context for key in context.keys()):
        raise AxisBridgeError("context contains unknown fields")

    payload_context = dict(DEFAULT_CONTEXT)
    payload_context.update(context)

    if not isinstance(payload_context["reference"], bool):
        raise AxisBridgeError("reference must be a boolean")

    if not _is_number(payload_context["stability"]):
        raise AxisBridgeError("stability must be a number")

    if not _is_number(payload_context["impact"]):
        raise AxisBridgeError("impact must be a number")

    return payload_context


def _execute_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}{AXIS_EXECUTE_PATH}"


def _decode_json(body: str):
    if not body:
        return None

    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return body


def _safe_error_body(error: HTTPError):
    try:
        return _decode_json(error.read().decode("utf-8"))
    except Exception:
        return None


def _error(code: str, message: str, payload: dict | None = None) -> dict:
    result = {
        "ok": False,
        "error": {
            "code": code,
            "message": message,
        },
    }

    if payload is not None:
        result["payload"] = payload

    return result


def _is_non_empty_string(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)
