"""Golden case definitions for the DES V1 pricing flow.

Recorded once at SOURCE_COMMIT by capture_pricing_v1.py into pricing_v1.json.
test_pricing_golden.py replays every case here and compares the result with
the recording. Nothing in this module writes files.

Determinism:
- interaction and rate-limit stores are cleared before and after every case
- security.rate_limit.time is replaced by a fixed clock for every case
- generated interaction_id values are replaced by a fixed placeholder
"""

from copy import deepcopy

import security.rate_limit as rate_limit
import storage.repository as repository
from api.interaction import answer_interaction, start_interaction
from api.trigger import trigger_check


SOURCE_COMMIT = "b3117c036d5c04c2102fe884ba48e806155475ac"
INTERACTION_ID_PLACEHOLDER = "<interaction_id>"
MISSING_INTERACTION_ID = "00000000-0000-0000-0000-000000000000"
FIXED_NOW = 1_000_000.0

HANDLERS = {
    "trigger": trigger_check,
    "start": start_interaction,
    "answer": answer_interaction,
}


def fixed_time():
    return FIXED_NOW


def reset_state():
    repository._INTERACTIONS.clear()
    rate_limit._REQUESTS.clear()


# --- request builders ---

def trigger(**overrides):
    request = {
        "pricing_page_sessions_last_30d": 2,
        "has_converted": False,
        "current_page": "/pricing",
        "session_id": "s1",
        "cooldown_ok": True,
    }
    request.update(overrides)
    return ("trigger", request)


def start(**overrides):
    request = {
        "user_id": "u1",
        "session_id": "s1",
        "trigger_type": "repeat_pricing_visit",
    }
    request.update(overrides)
    return ("start", request)


def answer(question_id, value, interaction_id=INTERACTION_ID_PLACEHOLDER):
    return ("answer", {
        "interaction_id": interaction_id,
        "question_id": question_id,
        "answer": value,
    })


def without(step, field):
    endpoint, request = step
    request = dict(request)
    del request[field]
    return (endpoint, request)


def with_extra(step, field, value):
    endpoint, request = step
    request = dict(request)
    request[field] = value
    return (endpoint, request)


# --- runners ---

class _IdTracker:
    def __init__(self):
        self.current = None
        self.seen = set()

    def record(self, response):
        if isinstance(response, dict) and isinstance(response.get("interaction_id"), str):
            self.current = response["interaction_id"]
            self.seen.add(self.current)

    def substitute(self, request):
        request = deepcopy(request)
        if request.get("interaction_id") == INTERACTION_ID_PLACEHOLDER:
            request["interaction_id"] = self.current
        return request

    def normalize(self, value):
        if isinstance(value, dict):
            return {key: self.normalize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.normalize(item) for item in value]
        if isinstance(value, str) and value in self.seen:
            return INTERACTION_ID_PLACEHOLDER
        return value


def run_steps(steps):
    ids = _IdTracker()
    results = []
    for endpoint, request in steps:
        response = HANDLERS[endpoint](ids.substitute(request))
        ids.record(response)
        results.append({
            "endpoint": endpoint,
            "request": request,
            "response": ids.normalize(response),
        })
    return results


def run_repeated(step, count):
    """Send the same request count times; record responses run-length encoded."""
    endpoint, request = step
    ids = _IdTracker()
    runs = []
    for _ in range(count):
        response = HANDLERS[endpoint](ids.substitute(request))
        ids.record(response)
        response = ids.normalize(response)
        if runs and runs[-1]["response"] == response:
            runs[-1]["count"] += 1
        else:
            runs.append({"count": 1, "response": response})
    return {"endpoint": endpoint, "request": request, "calls": count, "runs": runs}


def _http_client():
    from fastapi.testclient import TestClient
    from api.app import app

    return TestClient(app, raise_server_exceptions=False)


def run_http(calls, record_body=True):
    client = _http_client()
    ids = _IdTracker()
    results = []
    for path, body in calls:
        response = client.post(path, json=ids.substitute(body) if isinstance(body, dict) else body)
        entry = {"path": path, "request": body, "status": response.status_code}
        if record_body:
            payload = response.json()
            ids.record(payload)
            entry["body"] = ids.normalize(payload)
        results.append(entry)
    return results


# --- cases ---

CASES = {}


def case(group, name, fn):
    if name in CASES:
        raise ValueError(f"duplicate case {name}")
    CASES[name] = (group, fn)


def flow(group, name, *steps):
    case(group, name, lambda: run_steps([start(), *steps]))


SHORT_TEXT = "soon"
LONG_TEXT = "after budget approval"

# Q1 x Q2 options
for q2 in ["plan_a_vs_b", "plan_b_vs_c", "all_plans"]:
    flow("q1_q2", f"dont_understand_difference__{q2}",
         answer("q1", "dont_understand_difference"), answer("q2", q2))

for q2 in ["total_cost", "value", "risk"]:
    flow("q1_q2", f"too_expensive__{q2}",
         answer("q1", "too_expensive"), answer("q2", q2))

# Q1 x Q2 text. Short and empty text asks Q3, answered with "clarity".
for q1 in ["not_sure_fit", "not_ready"]:
    flow("q1_q2", f"{q1}__long_text",
         answer("q1", q1), answer("q2", LONG_TEXT))
    flow("q1_q2", f"{q1}__short_text",
         answer("q1", q1), answer("q2", SHORT_TEXT), answer("q3", "clarity"))
    flow("q1_q2", f"{q1}__empty_text",
         answer("q1", q1), answer("q2", ""), answer("q3", "clarity"))

# other -> fallback Q2 -> each Q3 option
for q3 in ["clarity", "fit", "trust", "cost"]:
    flow("other_q3", f"other__fallback_q2__{q3}",
         answer("q1", "other"), answer("q2", "not sure"), answer("q3", q3))

# unknown Q1 and fallback edges
flow("unknown_and_fallback", "unknown_q1",
     answer("q1", "banana"), answer("q2", "something specific"))
flow("unknown_and_fallback", "empty_q1",
     answer("q1", ""), answer("q2", "something specific"))
flow("unknown_and_fallback", "too_expensive__unmapped_q2",
     answer("q1", "too_expensive"), answer("q2", "unmapped"))
flow("unknown_and_fallback", "too_expensive__empty_q2__q3_trust",
     answer("q1", "too_expensive"), answer("q2", ""), answer("q3", "trust"))

# out of order and after the result
flow("order", "q2_before_q1", answer("q2", "value"))
flow("order", "q3_before_q1", answer("q3", "trust"))
flow("order", "answers_after_result",
     answer("q1", "too_expensive"), answer("q2", "value"),
     answer("q1", "not_sure_fit"), answer("q2", LONG_TEXT))

# trigger outcomes
case("trigger", "trigger_shows",
     lambda: run_steps([trigger()]))
case("trigger", "trigger_not_pricing_page",
     lambda: run_steps([trigger(current_page="/dashboard")]))
case("trigger", "trigger_suppressed_by_active_interaction",
     lambda: run_steps([start(), trigger()]))

# trigger errors
case("errors_trigger", "trigger_missing_field",
     lambda: run_steps([without(trigger(), "cooldown_ok")]))
case("errors_trigger", "trigger_unknown_field",
     lambda: run_steps([with_extra(trigger(), "extra_field", "x")]))
case("errors_trigger", "trigger_sessions_not_int",
     lambda: run_steps([trigger(pricing_page_sessions_last_30d="2")]))
case("errors_trigger", "trigger_has_converted_not_bool",
     lambda: run_steps([trigger(has_converted="false")]))
case("errors_trigger", "trigger_current_page_not_string",
     lambda: run_steps([trigger(current_page=1)]))
case("errors_trigger", "trigger_current_page_too_long",
     lambda: run_steps([trigger(current_page="/" + "p" * 128)]))
case("errors_trigger", "trigger_session_id_not_string",
     lambda: run_steps([trigger(session_id=1)]))
case("errors_trigger", "trigger_cooldown_not_bool",
     lambda: run_steps([trigger(cooldown_ok=1)]))

# start errors
case("errors_start", "start_missing_field",
     lambda: run_steps([without(start(), "session_id")]))
case("errors_start", "start_unknown_field",
     lambda: run_steps([with_extra(start(), "extra_field", "x")]))
case("errors_start", "start_wrong_trigger_type",
     lambda: run_steps([start(trigger_type="operator_initiated")]))
case("errors_start", "start_user_id_not_string",
     lambda: run_steps([start(user_id=1)]))
case("errors_start", "start_user_id_too_long",
     lambda: run_steps([start(user_id="u" * 129)]))
case("errors_start", "start_session_id_not_string",
     lambda: run_steps([start(session_id=1)]))
case("errors_start", "start_session_id_too_long",
     lambda: run_steps([start(session_id="s" * 129)]))

# answer errors
case("errors_answer", "answer_missing_field",
     lambda: run_steps([start(), without(answer("q1", "too_expensive"), "answer")]))
case("errors_answer", "answer_unknown_field",
     lambda: run_steps([start(), with_extra(answer("q1", "too_expensive"), "extra_field", "x")]))
case("errors_answer", "answer_bad_question_id",
     lambda: run_steps([start(), answer("q4", "too_expensive")]))
case("errors_answer", "answer_too_long",
     lambda: run_steps([start(), answer("q1", "a" * 281)]))
case("errors_answer", "answer_not_string",
     lambda: run_steps([start(), answer("q1", 5)]))
case("errors_answer", "answer_interaction_not_found",
     lambda: run_steps([answer("q1", "too_expensive", MISSING_INTERACTION_ID)]))

# rate limits (fixed clock: every call falls inside the same window)
case("rate_limits", "rate_limit_trigger",
     lambda: run_repeated(trigger(session_id="rate_test"), 61))
case("rate_limits", "rate_limit_start",
     lambda: run_repeated(start(user_id="rate_user"), 11))
case("rate_limits", "rate_limit_answer",
     lambda: run_repeated(answer("q1", "too_expensive", MISSING_INTERACTION_ID), 31))

# HTTP-level checks through api/app.py
case("http", "http_start_and_answer_200", lambda: run_http([
    ("/interaction/start", start()[1]),
    ("/interaction/answer", answer("q1", "too_expensive")[1]),
    ("/interaction/answer", answer("q2", "value")[1]),
]))
case("http", "http_handler_error_200", lambda: run_http([
    ("/interaction/start", start(trigger_type="operator_initiated")[1]),
]))
# Status only: FastAPI's 422 detail body varies between versions.
case("http", "http_non_object_body_422", lambda: run_http([
    ("/interaction/start", []),
], record_body=False))
# Retained behaviour: an unhashable interaction_id raises TypeError in
# storage.repository.get_interaction and surfaces as HTTP 500.
case("http", "http_unhashable_interaction_id_500", lambda: run_http([
    ("/interaction/answer", answer("q1", "too_expensive", ["a"])[1]),
], record_body=False))


def run_case(name):
    _, fn = CASES[name]
    original_time = rate_limit.time
    reset_state()
    rate_limit.time = fixed_time
    try:
        return fn()
    finally:
        rate_limit.time = original_time
        reset_state()
