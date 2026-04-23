# DES V1 — Trigger API

from core.trigger_engine import should_trigger
from storage.repository import has_active_interaction


def trigger_check(request: dict) -> dict:
    """
    Expected request:
    {
        "pricing_page_sessions_last_30d": int,
        "has_converted": bool,
        "current_page": "/pricing",
        "session_id": str,
        "cooldown_ok": bool
    }
    """

    required_fields = [
        "pricing_page_sessions_last_30d",
        "has_converted",
        "current_page",
        "session_id",
        "cooldown_ok",
    ]

    for field in required_fields:
        if field not in request:
            return {"error": "Invalid request", "code": "INVALID_INPUT"}

    active = has_active_interaction(request["session_id"])

    show = should_trigger(
        pricing_page_sessions_last_30d=request["pricing_page_sessions_last_30d"],
        has_converted=request["has_converted"],
        current_page=request["current_page"],
        has_active_interaction=active,
        cooldown_ok=request["cooldown_ok"],
    )

    return {"show": show}