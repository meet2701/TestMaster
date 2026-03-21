"""Simple command-line UI for StreetRace Manager.

This provides a minimal interactive loop to satisfy the "command-line system"
expectation while keeping the core logic inside modules for integration testing.

Integration tests should NOT test this UI; they should import module functions
and operate on SystemState directly.
"""

from __future__ import annotations

from typing import Callable

from models import SystemState, StreetRaceError, ValidationError

import crew
import finance
import inventory
import mission
import race
import registration
import results


def run_cli() -> None:
    state = SystemState()

    print("StreetRace Manager (CLI)")
    print("Tip: Seed some cash before entering races.")

    actions: dict[str, tuple[str, Callable[[], None]]] = {
        "1": ("Seed cash (income)", lambda: _seed_cash(state)),
        "2": ("Register crew member", lambda: _register_member(state)),
        "3": ("Set role", lambda: _set_role(state)),
        "4": ("Set skill level", lambda: _set_skill(state)),
        "5": ("Add car", lambda: _add_car(state)),
        "6": ("Create race", lambda: _create_race(state)),
        "7": ("Enroll driver + car", lambda: _enroll_race(state)),
        "8": ("Start race", lambda: _start_race(state)),
        "9": ("Record race outcome", lambda: _record_outcome(state)),
        "10": ("Create mission", lambda: _create_mission(state)),
        "11": ("Assign mission (validate roles)", lambda: _assign_mission(state)),
        "12": ("Show summary", lambda: _show_summary(state)),
        "0": ("Exit", lambda: None),
    }

    while True:
        print("\n--- Menu ---")
        for key in sorted(actions.keys(), key=lambda x: int(x) if x.isdigit() else 999):
            print(f"{key}. {actions[key][0]}")

        choice = input("Choose an option: ").strip()
        if choice == "0":
            print("Exiting.")
            return

        action = actions.get(choice)
        if not action:
            print("Invalid option.")
            continue

        try:
            action[1]()
        except ValidationError as exc:
            print(f"Validation error: {exc}")
        except StreetRaceError as exc:
            print(f"Error: {exc}")
        except Exception as exc:  # keep CLI alive; integration tests should be strict
            print(f"Unexpected error: {exc}")


# ---- Input helpers ----


def _read_int(prompt: str, *, min_value: int | None = None) -> int:
    raw = input(prompt).strip()
    value = int(raw)
    if min_value is not None and value < min_value:
        raise ValidationError(f"Value must be >= {min_value}")
    return value


def _read_nonempty(prompt: str) -> str:
    value = input(prompt).strip()
    if not value:
        raise ValidationError("Input cannot be empty")
    return value


def _read_roles_csv(prompt: str) -> list[str]:
    raw = _read_nonempty(prompt)
    roles = [r.strip().lower() for r in raw.split(",") if r.strip()]
    if not roles:
        raise ValidationError("At least one role required")
    return roles


# ---- Action handlers (thin; real logic is in modules) ----


def _seed_cash(state: SystemState) -> None:
    amount = _read_int("Amount to add as income: ", min_value=1)
    reason = input("Reason (optional): ").strip() or "seed cash"
    entry = finance.record_income(state, amount, reason=reason)
    print(f"Recorded income {entry.amount}. Cash is now {state.inventory.cash}.")


def _register_member(state: SystemState) -> None:
    name = _read_nonempty("Crew member name: ")
    role = input("Role (optional at registration): ").strip() or None
    member = registration.register_member(state, name, role=role)
    print(f"Registered: {member.name} (role={member.role})")


def _set_role(state: SystemState) -> None:
    name = _read_nonempty("Member name: ")
    role = _read_nonempty("Role (driver/mechanic/strategist): ")
    member = crew.set_role(state, name, role)
    print(f"Updated: {member.name} role={member.role}")


def _set_skill(state: SystemState) -> None:
    name = _read_nonempty("Member name: ")
    level = _read_int("Skill level (1-10): ", min_value=1)
    member = crew.set_skill_level(state, name, level)
    print(f"Updated: {member.name} skill={member.skill_level}")


def _add_car(state: SystemState) -> None:
    model = _read_nonempty("Car model: ")
    condition_raw = input("Condition (0-100, default 100): ").strip()
    condition = int(condition_raw) if condition_raw else 100
    car = inventory.add_car(state, model, condition=condition)
    print(f"Added car: {car.car_id} ({car.model}) condition={car.condition}")


def _create_race(state: SystemState) -> None:
    name = _read_nonempty("Race name: ")
    entry_fee = _read_int("Entry fee (>=0): ", min_value=0)
    prize = _read_int("Prize (>=0): ", min_value=0)
    race_obj = race.create_race(state, name, entry_fee=entry_fee, prize=prize)
    print(f"Created race: {race_obj.race_id} ({race_obj.name})")


def _enroll_race(state: SystemState) -> None:
    race_id = _read_nonempty("Race id: ")
    driver_name = _read_nonempty("Driver name: ")
    car_id = _read_nonempty("Car id: ")
    race_obj = race.enroll_driver_and_car(state, race_id, driver_name=driver_name, car_id=car_id)
    print(f"Enrolled {race_obj.driver_name} with car {race_obj.car_id} (status={race_obj.status})")


def _start_race(state: SystemState) -> None:
    race_id = _read_nonempty("Race id: ")
    race_obj = race.start_race(state, race_id)
    print(f"Race started: {race_obj.race_id} (status={race_obj.status})")


def _record_outcome(state: SystemState) -> None:
    race_id = _read_nonempty("Race id: ")
    position = _read_int("Position (1=win): ", min_value=1)
    damage = _read_int("Damage percent (0-100): ", min_value=0)
    notes = input("Notes (optional): ").strip()
    outcome = results.record_race_outcome(
        state,
        race_id,
        position=position,
        damage_percent=damage,
        notes=notes,
    )
    print(
        f"Outcome recorded: {outcome.outcome_id} position={outcome.position} prize={outcome.prize_won} damage={outcome.damage_percent}%"
    )


def _create_mission(state: SystemState) -> None:
    name = _read_nonempty("Mission name: ")
    roles = _read_roles_csv("Required roles (comma-separated): ")
    mission_obj = mission.create_mission(state, name, required_roles=roles)
    print(f"Created mission: {mission_obj.mission_id} ({mission_obj.name})")


def _assign_mission(state: SystemState) -> None:
    mission_id = _read_nonempty("Mission id: ")
    mission_obj = mission.validate_and_assign(state, mission_id)
    print(f"Mission active: {mission_obj.mission_id} assigned={mission_obj.assigned_members}")


def _show_summary(state: SystemState) -> None:
    print("\n=== Summary ===")
    print(f"Cash: {state.inventory.cash}")
    print(f"Crew: {[(m.name, m.role, m.skill_level, m.active) for m in state.crew.values()]}")
    print(f"Cars: {[(c.car_id, c.model, c.condition, c.available) for c in state.inventory.cars.values()]}")
    print(f"Races: {[(r.race_id, r.name, r.status, r.driver_name, r.car_id) for r in state.races.values()]}")
    print(f"Missions: {[(m.mission_id, m.name, m.status, m.required_roles, m.assigned_members) for m in state.missions.values()]}")
    print(f"Rankings: {state.rankings}")
    print(f"Ledger entries: {len(state.ledger)}")
