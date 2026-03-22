"""Maintenance module (extra).

Responsibilities:
- Apply car damage
- Trigger a repair workflow when damage is significant

Integration points:
- Called from results.py after race completion
- Calls inventory.apply_damage / inventory.repair_car
- Calls mission.py to ensure a mechanic is available before repair
- Calls finance.py for repair expenses
"""

from __future__ import annotations

from models import Car, SystemState, ValidationError

import finance
import inventory
import mission


REPAIR_THRESHOLD = 60  # if car condition falls below this, trigger repair flow


def process_damage(state: SystemState, car_id: str, damage_percent: int) -> Car:
    """Apply race damage without triggering repair workflows.

    This is used by the race simulation path.
    """

    return inventory.apply_damage(state, car_id, damage_percent)


def process_race_damage(state: SystemState, car_id: str, damage_percent: int) -> Car:
    car = inventory.apply_damage(state, car_id, damage_percent)

    if damage_percent <= 0:
        return car

    # If condition is low, require mechanic and repair.
    if car.condition < REPAIR_THRESHOLD:
        _trigger_repair_flow(state, car_id)

    return car


def _trigger_repair_flow(state: SystemState, car_id: str) -> None:
    repair_mission = mission.create_mission(
        state,
        name=f"Repair vehicle {car_id}",
        required_roles=["mechanic"],
    )

    # Business rule: missions fail if roles are unavailable.
    mission.validate_and_assign(state, repair_mission.mission_id)

    # Keep repair simple: spend money, restore car.
    repair_cost = 200
    finance.record_expense(state, repair_cost, reason=f"Repair cost for {car_id}")

    # Repair to full in one step.
    car = inventory.get_car(state, car_id)
    if car.condition >= 100:
        return

    needed = 100 - car.condition
    inventory.repair_car(state, car_id, needed)

    mission.complete_mission(state, repair_mission.mission_id)


def request_manual_repair(state: SystemState, car_id: str) -> None:
    """Optional entry point to demonstrate maintenance without a race."""

    car = inventory.get_car(state, car_id)
    if car.condition == 100:
        raise ValidationError("Car does not need repair")
    _trigger_repair_flow(state, car_id)


def use_part_on_car(state: SystemState, car_id: str, part_name: str, *, quantity: int = 1) -> Car:
    """Use a part on a car.

    Business rules:
    - Decrements the part quantity from inventory.
    - Increases car condition by +5 (cap 100) per use action.
    """

    if quantity <= 0:
        raise ValidationError("Quantity must be > 0")

    inventory.use_part(state, part_name, quantity)
    car = inventory.get_car(state, car_id)
    if car.condition < 100:
        inventory.repair_car(state, car_id, min(5, 100 - car.condition))
    return inventory.get_car(state, car_id)


def use_tool_on_car(state: SystemState, car_id: str, tool_name: str, *, quantity: int = 1) -> Car:
    """Use a tool on a car.

    Same behavior as parts for this iteration.
    """

    if quantity <= 0:
        raise ValidationError("Quantity must be > 0")

    inventory.use_tool(state, tool_name, quantity)
    car = inventory.get_car(state, car_id)
    if car.condition < 100:
        inventory.repair_car(state, car_id, min(5, 100 - car.condition))
    return inventory.get_car(state, car_id)
