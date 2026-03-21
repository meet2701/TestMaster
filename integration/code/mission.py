"""Mission Planning module.

Responsibilities:
- Create missions
- Validate required roles via crew.py
- Assign available crew

This module calls:
- crew.require_roles_available
"""

from __future__ import annotations

from models import Mission, NotFoundError, SystemState, ValidationError

import crew


def create_mission(state: SystemState, name: str, required_roles: list[str]) -> Mission:
    name = name.strip()
    if not name:
        raise ValidationError("Mission name cannot be empty")
    if not required_roles:
        raise ValidationError("Mission must require at least one role")

    mission_id = state.new_id("mis")
    mission_obj = Mission(mission_id=mission_id, name=name, required_roles=list(required_roles))
    state.missions[mission_id] = mission_obj
    return mission_obj


def get_mission(state: SystemState, mission_id: str) -> Mission:
    try:
        return state.missions[mission_id]
    except KeyError as exc:
        raise NotFoundError(f"Mission not found: {mission_id}") from exc


def validate_and_assign(state: SystemState, mission_id: str) -> Mission:
    mission_obj = get_mission(state, mission_id)
    if mission_obj.status not in {"planned", "failed"}:
        raise ValidationError(f"Mission cannot be (re)assigned from status: {mission_obj.status}")

    # Business rule: missions fail if roles are unavailable.
    try:
        assigned = crew.require_roles_available(state, mission_obj.required_roles)
    except ValidationError:
        mission_obj.status = "failed"
        mission_obj.assigned_members = []
        raise

    mission_obj.assigned_members = assigned
    mission_obj.status = "active"
    return mission_obj


def complete_mission(state: SystemState, mission_id: str) -> Mission:
    mission_obj = get_mission(state, mission_id)
    if mission_obj.status != "active":
        raise ValidationError(f"Mission cannot be completed from status: {mission_obj.status}")
    mission_obj.status = "completed"
    return mission_obj
