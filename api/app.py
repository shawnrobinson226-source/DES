# DES V1 — FastAPI Wrapper (clean)

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from api.trigger import trigger_check
from api.interaction import start_interaction, answer_interaction

app = FastAPI()


@app.post("/trigger/check")
def trigger_endpoint(request: dict):
    result = trigger_check(request)
    return JSONResponse(content=result)


@app.post("/interaction/start")
def start_endpoint(request: dict):
    result = start_interaction(request)
    return JSONResponse(content=result)


@app.post("/interaction/answer")
def answer_endpoint(request: dict):
    result = answer_interaction(request)
    return JSONResponse(content=result)