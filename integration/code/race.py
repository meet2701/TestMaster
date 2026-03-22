"""Race Management module.

Responsibilities:
- Create races
- Enter race (select driver + car)
- Start race (ends immediately; results recorded)

This module calls:
- crew.validate_driver
- inventory.get_car / inventory.set_carstatus
- finance.record_expense (entry fee)
"""

from __future__ import annotations

from models import DummyDriver, NotFoundError, Race, SystemState, ValidationError

import crew
import finance
import inventory


def create_race(
    state: SystemState,
    title: str,
    *,
    location: str,
    track_difficulty: int,
    entry_fee: int,
    prize1: int,
    prize2: int,
) -> Race:
    title = title.strip()
    if not title:
        raise ValidationError("Race title cannot be empty")
    location = location.strip()
    if not location:
        raise ValidationError("Race location cannot be empty")
    if track_difficulty < 1 or track_difficulty > 10:
        raise ValidationError("Track difficulty must be between 1 and 10")
    if entry_fee < 0:
        raise ValidationError("Entry fee cannot be negative")
    if prize1 < 0 or prize2 < 0:
        raise ValidationError("Prizes cannot be negative")

    race_id = state.new_id("race")
    race_obj = Race(
        race_id=race_id,
        name=title,
        location=location,
        track_difficulty=track_difficulty,
        entry_fee=entry_fee,
        prize=prize1,
        second_prize=prize2,
    )
    state.races[race_id] = race_obj
    return race_obj


def get_race(state: SystemState, race_id: str) -> Race:
    try:
        return state.races[race_id]
    except KeyError as exc:
        raise NotFoundError(f"Race not found: {race_id}") from exc


def _ensure_dummy_drivers(state: SystemState) -> list[DummyDriver]:
    if state.dummy_drivers:
        return state.dummy_drivers

    # Simple, deterministic set.
    state.dummy_drivers.extend(
        [
            DummyDriver(name="Dummy-1", car_name="Phantom"),
            DummyDriver(name="Dummy-2", car_name="Viper"),
            DummyDriver(name="Dummy-3", car_name="Driftwood"),
            DummyDriver(name="Dummy-4", car_name="Reaper"),
            DummyDriver(name="Dummy-5", car_name="Comet"),
        ]
    )
    return state.dummy_drivers


def enter_race(state: SystemState, race_id: str, *, driver_name: str, car_id: str) -> Race:
    race_obj = get_race(state, race_id)

    if race_obj.status not in {"created", "scheduled"}:
        raise ValidationError(f"Race not open for enrollment: {race_obj.status}")

    crew.validate_driver(state, driver_name)

    car = inventory.get_car(state, car_id)
    if car.carstatus != "Available":
        raise ValidationError(f"Car is not available: {car_id}")
    if car.condition <= 0:
        raise ValidationError(f"Car is not drivable (condition=0): {car_id}")

    # Collect entry fee (expense) when enrolling.
    if race_obj.entry_fee > 0:
        finance.record_expense(state, race_obj.entry_fee, reason=f"Race entry fee: {race_obj.name}")

    race_obj.driver_name = driver_name
    race_obj.car_id = car_id
    race_obj.status = "scheduled"

    # Enforce "only one race OR one mission" via memberstatus.
    crew.mark_in_race(state, driver_name)

    # Lock car.
    inventory.set_carstatus(state, car_id, "In Race")

    # Attach participants (1 player + 5 dummy drivers).
    dummies = _ensure_dummy_drivers(state)
    race_obj.participants = [driver_name] + [d.name for d in dummies]
    return race_obj


def start_race(state: SystemState, race_id: str) -> Race:
    race_obj = get_race(state, race_id)
    if race_obj.status != "scheduled":
        raise ValidationError(f"Race cannot be started from status: {race_obj.status}")
    if not race_obj.driver_name or not race_obj.car_id:
        raise ValidationError("Race must have a driver and car before starting")

    # Re-validate role in case crew changed; driver may already be marked In Race.
    crew.validate_driver(state, race_obj.driver_name, require_available=False)
    car = inventory.get_car(state, race_obj.car_id)
    if car.condition <= 0:
        raise ValidationError("Car is not drivable")

    race_obj.status = "running"
    return race_obj


def start_race_and_record(state: SystemState, race_id: str):
    """Start the race and immediately record results (race ends immediately)."""

    start_race(state, race_id)
    import results  # local import to avoid module-level circular dependency

    return results.record_race_outcome(state, race_id)


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
        inventory.set_carstatus(state, race_obj.car_id, "Available")

    return race_obj
