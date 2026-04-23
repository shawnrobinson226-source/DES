# DES V1 — Interaction Model

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import uuid4


@dataclass
class Interaction:
    user_id: str
    session_id: str
    trigger_type: str
    interaction_id: str = field(default_factory=lambda: str(uuid4()))
    state: str = "interaction_started"
    q1: Optional[str] = None
    q2: Optional[str] = None
    q3: Optional[str] = None
    friction_type: Optional[str] = None
    output_type: Optional[str] = None
    resolved: bool = False
    abandoned: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)