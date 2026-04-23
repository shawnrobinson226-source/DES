# DES V1 — Validation

"""
Strict input validation.

Reject:
- missing fields
- unknown fields
- invalid types
"""


def validate_required(data: dict, required_fields: list):
    for field in required_fields:
        if field not in data:
            return False
    return True


def reject_unknown_fields(data: dict, allowed_fields: list):
    for key in data.keys():
        if key not in allowed_fields:
            return False
    return True


def validate_string(value, max_length=280):
    if not isinstance(value, str):
        return False
    if len(value) > max_length:
        return False
    return True


def validate_enum(value, allowed_values: list):
    return value in allowed_values