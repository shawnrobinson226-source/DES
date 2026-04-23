# DES V1 — Repository (in-memory for MVP)

"""
Simple storage layer.

NO database yet
NO persistence across restarts
Replace later with real storage
"""


from typing import Dict
from models.interaction import Interaction


# in-memory store
_INTERACTIONS: Dict[str, Interaction] = {}


def save_interaction(interaction: Interaction) -> None:
    _INTERACTIONS[interaction.interaction_id] = interaction


def get_interaction(interaction_id: str) -> Interaction:
    return _INTERACTIONS.get(interaction_id)


def update_interaction(interaction: Interaction) -> None:
    _INTERACTIONS[interaction.interaction_id] = interaction


def has_active_interaction(session_id: str) -> bool:
    for interaction in _INTERACTIONS.values():
        if interaction.session_id == session_id and not interaction.resolved and not interaction.abandoned:
            return True
    return False