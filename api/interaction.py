# DES V1 — Interaction API

from models.interaction import Interaction
from storage.repository import save_interaction, get_interaction, update_interaction
from core.question_flow import get_q1, get_q2, get_q3, should_ask_q3
from core.classifier import classify
from core.output_builder import build_output


def start_interaction(request: dict) -> dict:
    required = ["user_id", "session_id", "trigger_type"]

    for field in required:
        if field not in request:
            return {"error": "Invalid request", "code": "INVALID_INPUT"}

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
    required = ["interaction_id", "question_id", "answer"]

    for field in required:
        if field not in request:
            return {"error": "Invalid request", "code": "INVALID_INPUT"}

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