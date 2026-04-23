# DES V1 — Trigger Engine

"""
Trigger condition (MVP — locked):

Fire ONLY if:
- pricing_page_sessions_last_30d >= 2
- has_converted == False
- current_page == "/pricing"
- no DES interaction in current session
- cooldown satisfied

Return:
True  → show DES
False → do not show DES

NO side effects.
NO DB writes.
Pure function only.
"""


def should_trigger(
    pricing_page_sessions_last_30d: int,
    has_converted: bool,
    current_page: str,
    has_active_interaction: bool,
    cooldown_ok: bool,
) -> bool:

    if pricing_page_sessions_last_30d < 2:
        return False

    if has_converted:
        return False

    if current_page != "/pricing":
        return False

    if has_active_interaction:
        return False

    if not cooldown_ok:
        return False

    return True