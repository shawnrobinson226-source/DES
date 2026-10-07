# DES V1 — FastAPI Wrapper

from fastapi import FastAPI
from api.trigger import trigger_check
from api.interaction import start_interaction, answer_interaction
from core.question_sets.bootstrap import bootstrap_operator_question_sets


bootstrap_operator_question_sets()

app = FastAPI(title="DES V1")


@app.post("/trigger/check")
def trigger_check_route(payload: dict):
    return trigger_check(payload)


@app.post("/interaction/start")
def interaction_start_route(payload: dict):
    return start_interaction(payload)


@app.post("/interaction/answer")
def interaction_answer_route(payload: dict):
    return answer_interaction(payload)


@app.get("/health")
def health():
    # Deliberately minimal: this unauthenticated local readiness route does not
    # disclose a version, filesystem path, configuration, or registry state.
    return {"ok": True, "service": "DES"}
