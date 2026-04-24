# DES V1 — Trigger API

from core.trigger_engine import should_trigger
from storage.repository import has_active_interaction
from security.validation import (
    validate_required,
    reject_unknown_fields,
    validate_int,
    validate_bool,
    validate_string,
)
from security.rate_limit import allow_request


def trigger_check(request: dict) -> dict:
    allowed_fields = [
        "pricing_page_sessions_last_30d",
        "has_converted",
        "current_page",
        "session_id",
        "cooldown_ok",
    ]

    if not validate_required(request, allowed_fields):
        return {"error": "Invalid request", "code": "INVALID_INPUT"}

    if not reject_unknown_fields(request, allowed_fields):
        return {"error": "Unknown field", "code": "UNKNOWN_FIELD"}

    if not validate_int(request["pricing_page_sessions_last_30d"]):
        return {"error": "Invalid type", "code": "INVALID_INPUT"}

    if not validate_bool(request["has_converted"]):
        return {"error": "Invalid type", "code": "INVALID_INPUT"}

    if not validate_string(request["current_page"], 128):
        return {"error": "Invalid current_page", "code": "INVALID_INPUT"}

    if not validate_string(request["session_id"], 128):
        return {"error": "Invalid session_id", "code": "INVALID_INPUT"}

    if not validate_bool(request["cooldown_ok"]):
        return {"error": "Invalid type", "code": "INVALID_INPUT"}

    key = f"trigger:{request.get('session_id', 'unknown')}"
    if not allow_request(key, limit=60, window_seconds=60):
        return {"error": "Rate limited", "code": "RATE_LIMITED"}

    if request["current_page"] != "/pricing":
        return {"show": False}

    active = has_active_interaction(request["session_id"])

    show = should_trigger(
        pricing_page_sessions_last_30d=request["pricing_page_sessions_last_30d"],
        has_converted=request["has_converted"],
        current_page=request["current_page"],
        has_active_interaction=active,
        cooldown_ok=request["cooldown_ok"],
    )

    return {"show": show}
