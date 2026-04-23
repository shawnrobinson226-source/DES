# DES V1 — Trigger API

from core.trigger_engine import should_trigger
from storage.repository import has_active_interaction
from security.validation import validate_required, reject_unknown_fields


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