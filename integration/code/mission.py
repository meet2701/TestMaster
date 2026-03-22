"""Missions module (fixed mission board).

Responsibilities:
- Provide a fixed set of 10 missions (mission board)
- Validate required roles via crew.py
- Assign, complete, abort missions

Integration points:
- Uses crew.require_roles_available to pick available members
- Uses finance.record_income to award bounties (skip if bounty == 0 / "Free")

Status model:
- "assigned": mission in progress (members are busy)
- "completed": last run completed successfully
- "aborted": last run aborted / not currently active
"""

from __future__ import annotations

from models import Mission, NotFoundError, SystemState, ValidationError

import crew
import finance


def _ensure_mission_board(state: SystemState) -> None:
    """Create the fixed mission board once per state."""

    if state.missions:
        return

    board: list[Mission] = [
        Mission(
            mission_id="mis-0001",
            name="Street Sprint",
            required_roles=["driver"],
            description=(
                "A pure, solo dash from A to B. No backup, no excuses—just you and the redline."
            ),
            bounty=500,
            status="aborted",
        ),
        Mission(
            mission_id="mis-0002",
            name="Blind Alley",
            required_roles=["driver", "spotter"],
            description=(
                "Racing through narrow construction zones. You’re driving, but the Spotter is the only reason you won't hit a concrete barrier at 100mph."
            ),
            bounty=0,
            status="aborted",
        ),
        Mission(
            mission_id="mis-0003",
            name="Junk Run",
            required_roles=["driver", "mechanic"],
            description=(
                "Nursing a beat-up car across town. The Driver keeps it moving while the Mechanic keeps the engine from exploding in the passenger seat."
            ),
            bounty=1200,
            status="aborted",
        ),
        Mission(
            mission_id="mis-0004",
            name="Grid Bypass",
            required_roles=["driver", "strategist"],
            description=(
                "A high-speed delivery through a smart-city zone. The Strategist hacks the lights so you never have to hit the brakes."
            ),
            bounty=2500,
            status="aborted",
        ),
        Mission(
            mission_id="mis-0005",
            name="Med-Dash",
            required_roles=["driver", "doctor"],
            description=(
                "Getting a teammate to a safe house after a job gone wrong. The Doctor keeps them alive while you take the corners as smoothly as possible."
            ),
            bounty=0,
            status="aborted",
        ),
        Mission(
            mission_id="mis-0006",
            name="The Extraction",
            required_roles=["driver", "spotter", "strategist"],
            description=(
                "Plucking a high-value target from a hot zone. You need the Strategist for the route and the Spotter to watch for the heat."
            ),
            bounty=5000,
            status="aborted",
        ),
        Mission(
            mission_id="mis-0007",
            name="Heavy Haul",
            required_roles=["driver", "mechanic", "spotter"],
            description=(
                "Moving an armored truck that handles like a brick. The Spotter clears the path, and the Mechanic keeps the heavy-duty suspension from snapping."
            ),
            bounty=3500,
            status="aborted",
        ),
        Mission(
            mission_id="mis-0008",
            name="The Marathon",
            required_roles=["driver", "mechanic", "doctor"],
            description=(
                "A brutal cross-state endurance race. You’re going to need a wrench for the car and a needle for the Driver’s fatigue."
            ),
            bounty=8000,
            status="aborted",
        ),
        Mission(
            mission_id="mis-0009",
            name="Eye in the Sky",
            required_roles=["spotter", "strategist"],
            description=(
                "No driving allowed. You’re sitting on a rooftop mapping out police routes and timing traffic patterns for the next big job."
            ),
            bounty=1000,
            status="aborted",
        ),
        Mission(
            mission_id="mis-0010",
            name="The Grand Heist",
            required_roles=["driver", "mechanic", "strategist", "doctor", "spotter"],
            description=(
                "The big one. Every role is active and every soul is on the line. If one person slips up, the whole crew goes down."
            ),
            bounty=25000,
            status="aborted",
        ),
    ]

    state.missions = {m.mission_id: m for m in board}


def get_all_missions(state: SystemState) -> list[Mission]:
    _ensure_mission_board(state)
    missions = list(state.missions.values())
    missions.sort(key=lambda m: m.mission_id)
    return missions


def get_mission(state: SystemState, mission_id: str) -> Mission:
    _ensure_mission_board(state)
    try:
        return state.missions[mission_id]
    except KeyError as exc:
        raise NotFoundError(f"Mission not found: {mission_id}") from exc


def assign_mission(state: SystemState, mission_id: str) -> Mission:
    mission_obj = get_mission(state, mission_id)

    if mission_obj.status == "assigned":
        raise ValidationError(f"Mission already assigned: {mission_id}")

    assigned = crew.require_roles_available(state, mission_obj.required_roles)

    # Mark the chosen crew members busy.
    for name in assigned:
        crew.set_memberstatus(state, name, "In Mission")

    mission_obj.assigned_members = assigned
    mission_obj.status = "assigned"
    return mission_obj


def complete_mission(state: SystemState, mission_id: str) -> Mission:
    mission_obj = get_mission(state, mission_id)

    if mission_obj.status != "assigned":
        raise ValidationError(f"Mission cannot be completed from status: {mission_obj.status}")

    # Release crew members.
    for name in mission_obj.assigned_members:
        if name in state.crew:
            crew.mark_available(state, name)

    mission_obj.status = "completed"

    if mission_obj.bounty > 0:
        finance.record_income(state, mission_obj.bounty, reason=f"Mission bounty: {mission_obj.name}")

    return mission_obj


def abort_mission(state: SystemState, mission_id: str) -> Mission:
    mission_obj = get_mission(state, mission_id)

    if mission_obj.status != "assigned":
        raise ValidationError(f"Mission cannot be aborted from status: {mission_obj.status}")

    for name in mission_obj.assigned_members:
        if name in state.crew:
            crew.mark_available(state, name)

    mission_obj.status = "aborted"
    return mission_obj
