"""Registration module.

Responsibilities:
- Register crew members (name)
- Optionally set an initial role at registration time

Role and skill management will be primarily handled by crew.py.
"""

from __future__ import annotations

from models import CrewMember, SystemState, ValidationError


def register_member(state: SystemState, name: str, role: str | None = None) -> CrewMember:
    name = name.strip()
    if not name:
        raise ValidationError("Name cannot be empty")
    if name in state.crew:
        raise ValidationError(f"Crew member already registered: {name}")

    member = CrewMember(name=name, role=role)
    state.crew[name] = member
    return member


def ensure_registered(state: SystemState, name: str) -> None:
    if name not in state.crew:
        raise ValidationError(f"Crew member must be registered first: {name}")
