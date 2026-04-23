# DES V1 — Output Builder

"""
Maps friction → output

NO persuasion
NO urgency
NO manipulation
Static, controlled outputs only
"""


def build_output(friction_type: str) -> dict:

    if friction_type == "information_gap":
        return {
            "output_type": "clarify",
            "title": "Let’s clarify the differences",
            "body": "Here’s a clear breakdown of what each option does so you can decide.",
            "cta": "View comparison",
            "ui": {
                "suppress_primary_cta": False,
                "recommend_exit": False,
            },
        }

    if friction_type == "fit_uncertainty":
        return {
            "output_type": "filter",
            "title": "This may not be the right fit",
            "body": "Based on your situation, this might not match what you need right now.",
            "cta": "",
            "ui": {
                "suppress_primary_cta": True,
                "recommend_exit": True,
            },
        }

    if friction_type == "trust_deficit":
        return {
            "output_type": "proof",
            "title": "Here’s how this holds up",
            "body": "You can review real outcomes and evidence to evaluate this properly.",
            "cta": "View proof",
            "ui": {
                "suppress_primary_cta": False,
                "recommend_exit": False,
            },
        }

    # fallback (never break system)
    return {
        "output_type": "clarify",
        "title": "Let’s clarify this",
        "body": "Here’s more information to help you decide.",
        "cta": "Learn more",
        "ui": {
            "suppress_primary_cta": False,
            "recommend_exit": False,
        },
    }