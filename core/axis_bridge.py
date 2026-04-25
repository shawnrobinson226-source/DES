# DES V1 — AXIS Bridge Payload Mapper

"""
Pure DES-to-AXIS payload mapping.

NO live AXIS calls.
NO network clients.
NO persistence.
NO API route wiring.
"""


class BridgeError(ValueError):
    """Raised when a DES result cannot be safely mapped for AXIS."""


ALLOWED_FIELDS = {
    "trigger",
    "classification",
    "next_action",
    "reference",
    "stability",
    "impact",
}

FRICTION_TO_CLASSIFICATION = {
    "information_gap": "perceptual",
    "fit_uncertainty": "behavioral",
    "trust_deficit": "narrative",
    "unknown": "continuity",
}

OUTPUT_TO_NEXT_ACTION = {
    "clarify": "Review the clarified decision information and choose one next step.",
    "filter": "Confirm fit or non-fit and act on the result.",
    "proof": "Review the evidence and separate verified claims from assumptions.",
}

DEFAULT_REFERENCE = True
DEFAULT_STABILITY = 6
DEFAULT_IMPACT = 4


def build_axis_payload(des_result: dict) -> dict:
    if not isinstance(des_result, dict):
        raise BridgeError("DES result must be a dict")

    friction_type = des_result.get("friction_type")
    if not friction_type:
        raise BridgeError("Missing friction_type")

    if friction_type not in FRICTION_TO_CLASSIFICATION:
        raise BridgeError("Unknown friction_type")

    output = des_result.get("output")
    if output is None:
        raise BridgeError("Missing output")

    if not isinstance(output, dict):
        raise BridgeError("Output must be a dict")

    output_type = output.get("output_type")
    if not output_type:
        raise BridgeError("Missing output_type")

    if output_type not in OUTPUT_TO_NEXT_ACTION:
        raise BridgeError("Unknown output_type")

    trigger = _extract_trigger(des_result, output)

    payload = {
        "trigger": trigger,
        "classification": FRICTION_TO_CLASSIFICATION[friction_type],
        "next_action": OUTPUT_TO_NEXT_ACTION[output_type],
        "reference": DEFAULT_REFERENCE,
        "stability": DEFAULT_STABILITY,
        "impact": DEFAULT_IMPACT,
    }

    if set(payload.keys()) != ALLOWED_FIELDS:
        raise BridgeError("Invalid AXIS payload fields")

    return payload


def _extract_trigger(des_result: dict, output: dict) -> str:
    if "trigger" in des_result:
        trigger = des_result.get("trigger")
        if not _is_non_empty_string(trigger):
            raise BridgeError("Trigger must be a non-empty string")
        return trigger.strip()

    # Fallback is explicit and documented: completed DES results produced before
    # bridge preparation may not include trigger, so output.title can label the
    # AXIS event without adding hidden inference.
    fallback = output.get("title")
    if not _is_non_empty_string(fallback):
        raise BridgeError("Missing trigger")

    return fallback.strip()


def _is_non_empty_string(value) -> bool:
    return isinstance(value, str) and bool(value.strip())
