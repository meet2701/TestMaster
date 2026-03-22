"""Registration module.

Responsibilities:
- Register crew members (name)
- Optionally set an initial role at registration time

Role and skill management will be primarily handled by crew.py.
"""

from __future__ import annotations

from models import CrewMember, SystemState, ValidationError


def register_member(
    state: SystemState,
    name: str,
    role: str | None = None,
    *,
    age: int | None = None,
    experience: int | None = None,
    skills: int | None = None,
) -> CrewMember:
    name = name.strip()
    if not name:
        raise ValidationError("Name cannot be empty")
    if name in state.crew:
        raise ValidationError(f"Crew member already registered: {name}")

    if age is not None:
        if age <= 0:
            raise ValidationError("Age must be > 0")
    if experience is not None:
        if experience < 0 or experience > 100:
            raise ValidationError("Experience must be between 0 and 100")
    if skills is not None:
        if skills < 0 or skills > 100:
            raise ValidationError("Skills must be between 0 and 100")
    if experience is not None:
        if age is None:
            raise ValidationError("Age must be provided if experience is given")
        if experience >= age:
            raise ValidationError(...)

    member = CrewMember(
        name=name,
        role=role,
        age=age or 0,
        experience=experience or 0,
        skills=skills or 0,
    )
    state.crew[name] = member
    return member


def get_all_members(state: SystemState) -> list[CrewMember]:
    return [state.crew[name] for name in sorted(state.crew.keys())]


def ensure_registered(state: SystemState, name: str) -> None:
    if name not in state.crew:
        raise ValidationError(f"Crew member must be registered first: {name}")
