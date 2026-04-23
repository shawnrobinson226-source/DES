# DES V1 — State Machine

"""
Controls valid DES flow.

NO hidden states
NO skipped transitions
NO runtime improvisation
"""


VALID_TRANSITIONS = {
    "idle": ["triggered"],
    "triggered": ["interaction_started", "abandoned"],
    "interaction_started": ["q1_answered", "abandoned"],
    "q1_answered": ["q2_answered", "classified", "abandoned"],
    "q2_answered": ["q3_answered", "classified", "abandoned"],
    "q3_answered": ["classified", "abandoned"],
    "classified": ["output_rendered"],
    "output_rendered": ["resolved"],
    "resolved": [],
    "abandoned": [],
}


def can_transition(current_state: str, next_state: str) -> bool:
    return next_state in VALID_TRANSITIONS.get(current_state, [])


def transition(current_state: str, next_state: str) -> str:
    if not can_transition(current_state, next_state):
        raise ValueError("Invalid state transition")

    return next_state