# DES V1 — Simple Rate Limit

from time import time

_REQUESTS = {}


def allow_request(key: str, limit: int, window_seconds: int) -> bool:
    now = time()

    if key not in _REQUESTS:
        _REQUESTS[key] = []

    # remove old timestamps
    _REQUESTS[key] = [
        t for t in _REQUESTS[key] if now - t < window_seconds
    ]

    if len(_REQUESTS[key]) >= limit:
        return False

    _REQUESTS[key].append(now)
    return True