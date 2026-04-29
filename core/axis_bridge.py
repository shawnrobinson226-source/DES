# DES V1 — AXIS Bridge Payload Mapper

"""
Compatibility wrapper for the canonical adapter in core.axis.bridge.

The DES to AXIS classification mapping lives only in core.axis.bridge.
"""

from core.axis.bridge import (
    AXIS_PAYLOAD_FIELDS as ALLOWED_FIELDS,
    FRICTION_CLASSIFICATION_MAP as FRICTION_TO_CLASSIFICATION,
    NEXT_ACTION_BY_OUTPUT_TYPE as OUTPUT_TO_NEXT_ACTION,
    AxisBridgeError as BridgeError,
    build_axis_execute_payload,
)


def build_axis_payload(des_result: dict) -> dict:
    if not isinstance(des_result, dict):
        raise BridgeError("DES result must be a dict")

    output = des_result.get("output")
    if output is None:
        raise BridgeError("Missing output")

    if not isinstance(output, dict):
        raise BridgeError("Output must be a dict")

    output_type = output.get("output_type")
    if not output_type:
        raise BridgeError("Missing output_type")

    des_output = {
        "friction_type": des_result.get("friction_type"),
        "details": {
            "output_type": output_type,
        },
    }

    try:
        return build_axis_execute_payload(
            des_output=des_output,
            trigger=des_result.get("trigger"),
        )
    except BridgeError as error:
        message = str(error)
        if message == "friction_type is required":
            raise BridgeError("Missing friction_type")
        if message == "unknown friction_type":
            raise BridgeError("Unknown friction_type")
        if message == "trigger is required":
            raise BridgeError("Trigger must be a non-empty string")
        if message == "unknown output_type":
            raise BridgeError("Unknown output_type")
        raise
