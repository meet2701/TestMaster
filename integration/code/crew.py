"""Crew Management module.

Responsibilities:
- Manage roles and skill levels
- Validate role availability for missions
- Validate drivers for races

Will depend on: models.py (and also registration.py only for the registration rule).
"""

from __future__ import annotations

from models import CrewMember, NotFoundError, SystemState, ValidationError

import registration


VALID_ROLES = {"driver", "mechanic", "strategist", "spotter", "doctor"}


def get_all_members(state: SystemState) -> list[CrewMember]:
    return registration.get_all_members(state)


def get_members_by_role(state: SystemState, role: str) -> list[CrewMember]:
    role = role.strip().lower()
    if role not in VALID_ROLES:
        raise ValidationError(f"Invalid role: {role}")
    return [m for m in get_all_members(state) if (m.role or "").strip().lower() == role]


def get_member_details(state: SystemState, name: str) -> CrewMember:
    return get_member(state, name)


def get_member(state: SystemState, name: str) -> CrewMember:
    try:
        return state.crew[name]
    except KeyError as exc:
        raise NotFoundError(f"Crew member not found: {name}") from exc


def is_registered(state: SystemState, name: str) -> bool:
    return name in state.crew


def set_role(state: SystemState, name: str, role: str) -> CrewMember:
    registration.ensure_registered(state, name)

    role = role.strip().lower()
    if role not in VALID_ROLES:
        raise ValidationError(f"Invalid role: {role}")

    member = get_member(state, name)
    member.role = role
    return member


def set_skill_level(state: SystemState, name: str, skill_level: int) -> CrewMember:
    registration.ensure_registered(state, name)

    if skill_level < 1 or skill_level > 10:
        raise ValidationError("Skill level must be between 1 and 10")

    member = get_member(state, name)
    member.skill_level = skill_level
    return member


def deactivate_member(state: SystemState, name: str) -> CrewMember:
    member = get_member(state, name)
    member.active = False
    return member


def validate_driver(state: SystemState, name: str, *, min_skill: int = 1) -> CrewMember:
    member = get_member(state, name)
    if not member.active:
        raise ValidationError(f"Crew member is not active: {name}")
    if member.role != "driver":
        raise ValidationError(f"Only drivers can be added to races: {name}")
    if member.skill_level < min_skill:
        raise ValidationError(f"Driver skill too low: {name}")
    return member


def require_roles_available(
    state: SystemState,
    required_roles: list[str],
) -> list[str]:
    """Return a list of assigned crew member names for each required role.

    Simple strategy: pick the first active member for each role.
    Roles can repeat; each assignment must be distinct.
    """

    assigned: list[str] = []
    used: set[str] = set()

    for role in required_roles:
        role = role.strip().lower()
        if role not in VALID_ROLES:
            raise ValidationError(f"Invalid required role: {role}")

        found_name: str | None = None
        for name, member in state.crew.items():
            if name in used:
                continue
            if member.active and member.role == role:
                found_name = name
                break

        if not found_name:
            raise ValidationError(f"Required role unavailable: {role}")

        assigned.append(found_name)
        used.add(found_name)

    return assigned
