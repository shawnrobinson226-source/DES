# DES V1 — Interaction API

from models.interaction import Interaction
from storage.repository import save_interaction, get_interaction, update_interaction
from core.question_flow import get_q1, get_q2, get_q3, should_ask_q3
from core.classifier import classify
from core.output_builder import build_output
from security.validation import validate_required, reject_unknown_fields, validate_string
from security.rate_limit import allow_request


def start_interaction(request: dict) -> dict:

    key = f"start:{request.get('user_id', 'unknown')}"
    if not allow_request(key, limit=10, window_seconds=60):
        return {"error": "Rate limited", "code": "RATE_LIMITED"}
    allowed_fields = ["user_id", "session_id", "trigger_type"]

    if not validate_required(request, allowed_fields):
        return {"error": "Invalid request", "code": "INVALID_INPUT"}

    if not reject_unknown_fields(request, allowed_fields):
        return {"error": "Unknown field", "code": "UNKNOWN_FIELD"}

    if not validate_string(request["user_id"], 128):
        return {"error": "Invalid user_id", "code": "INVALID_INPUT"}

    if not validate_string(request["session_id"], 128):
        return {"error": "Invalid session_id", "code": "INVALID_INPUT"}

    if request["trigger_type"] != "repeat_pricing_visit":
        return {"error": "Invalid trigger_type", "code": "INVALID_INPUT"}

    interaction = Interaction(
        user_id=request["user_id"],
        session_id=request["session_id"],
        trigger_type=request["trigger_type"],
    )

    save_interaction(interaction)

    return {
        "interaction_id": interaction.interaction_id,
        "done": False,
        "question": get_q1(),
    }


def answer_interaction(request: dict) -> dict:

    key = f"answer:{request.get('interaction_id', 'unknown')}"
    if not allow_request(key, limit=30, window_seconds=60):
        return {"error": "Rate limited", "code": "RATE_LIMITED"}
    allowed_fields = ["interaction_id", "question_id", "answer"]

    if not validate_required(request, allowed_fields):
        return {"error": "Invalid request", "code": "INVALID_INPUT"}

    if not reject_unknown_fields(request, allowed_fields):
        return {"error": "Unknown field", "code": "UNKNOWN_FIELD"}

    if request["question_id"] not in ["q1", "q2", "q3"]:
        return {"error": "Invalid question_id", "code": "INVALID_INPUT"}

    if not validate_string(request["answer"], 280):
        return {"error": "Invalid answer", "code": "INVALID_INPUT"}

    interaction = get_interaction(request["interaction_id"])

    if not interaction:
        return {"error": "Interaction not found", "code": "INTERACTION_NOT_FOUND"}

    question_id = request["question_id"]
    answer = request["answer"]

    if question_id == "q1":
        interaction.q1 = answer
        interaction.state = "q1_answered"
        update_interaction(interaction)
        return {"done": False, "question": get_q2(answer)}

    if question_id == "q2":
        interaction.q2 = answer

        if should_ask_q3(interaction.q1, interaction.q2):
            interaction.state = "q2_answered"
            update_interaction(interaction)
            return {"done": False, "question": get_q3()}

        friction = classify(interaction.q1, interaction.q2)
        output = build_output(friction)

        interaction.friction_type = friction
        interaction.output_type = output["output_type"]
        interaction.state = "output_rendered"
        interaction.resolved = True
        update_interaction(interaction)

        return {
            "done": True,
            "friction_type": friction,
            "output": output,
        }

    if question_id == "q3":
        interaction.q3 = answer
        friction = classify(interaction.q1, interaction.q2, interaction.q3)
        output = build_output(friction)

        interaction.friction_type = friction
        interaction.output_type = output["output_type"]
        interaction.state = "output_rendered"
        interaction.resolved = True
        update_interaction(interaction)

        return {
            "done": True,
            "friction_type": friction,
            "output": output,
        }

    return {"error": "Invalid request", "code": "INVALID_INPUT"}
