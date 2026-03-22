"""Race Management module.

Responsibilities:
- Create races
- Enroll driver + car (validations across crew/inventory)

This module calls:
- crew.validate_driver
- inventory.get_car / inventory.set_car_status
- finance.record_expense (entry fee)
"""

from __future__ import annotations

from models import NotFoundError, Race, SystemState, ValidationError

import crew
import finance
import inventory


def create_race(state: SystemState, name: str, *, entry_fee: int, prize: int) -> Race:
    name = name.strip()
    if not name:
        raise ValidationError("Race name cannot be empty")
    if entry_fee < 0:
        raise ValidationError("Entry fee cannot be negative")
    if prize < 0:
        raise ValidationError("Prize cannot be negative")

    race_id = state.new_id("race")
    race_obj = Race(race_id=race_id, name=name, entry_fee=entry_fee, prize=prize)
    state.races[race_id] = race_obj
    return race_obj


def get_race(state: SystemState, race_id: str) -> Race:
    try:
        return state.races[race_id]
    except KeyError as exc:
        raise NotFoundError(f"Race not found: {race_id}") from exc


def enroll_driver_and_car(state: SystemState, race_id: str, driver_name: str, car_id: str) -> Race:
    race_obj = get_race(state, race_id)

    if race_obj.status not in {"created", "scheduled"}:
        raise ValidationError(f"Race not open for enrollment: {race_obj.status}")

    crew.validate_driver(state, driver_name)

    car = inventory.get_car(state, car_id)
    if car.status != "Available":
        raise ValidationError(f"Car is not available: {car_id}")
    if car.condition <= 0:
        raise ValidationError(f"Car is not drivable (condition=0): {car_id}")

    # Collect entry fee (expense) when enrolling.
    if race_obj.entry_fee > 0:
        finance.record_expense(state, race_obj.entry_fee, reason=f"Race entry fee: {race_obj.name}")

    race_obj.driver_name = driver_name
    race_obj.car_id = car_id
    race_obj.status = "scheduled"

    inventory.set_car_status(state, car_id, "In Race")
    return race_obj


def start_race(state: SystemState, race_id: str) -> Race:
    race_obj = get_race(state, race_id)
    if race_obj.status != "scheduled":
        raise ValidationError(f"Race cannot be started from status: {race_obj.status}")
    if not race_obj.driver_name or not race_obj.car_id:
        raise ValidationError("Race must have a driver and car before starting")

    # Re-validate in case crew/car changed.
    crew.validate_driver(state, race_obj.driver_name)
    car = inventory.get_car(state, race_obj.car_id)
    if car.condition <= 0:
        raise ValidationError("Car is not drivable")

    race_obj.status = "running"
    return race_obj


def mark_completed(state: SystemState, race_id: str) -> Race:
    """Mark race as completed.

    Results recording is done in results.py; that module calls this function.
    """

    race_obj = get_race(state, race_id)
    if race_obj.status != "running":
        raise ValidationError(f"Race cannot be completed from status: {race_obj.status}")

    race_obj.status = "completed"

    # Release car back to inventory.
    if race_obj.car_id:
        inventory.set_car_status(state, race_obj.car_id, "Available")

    return race_obj
