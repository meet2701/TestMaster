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

import crew
import finance
import inventory


REPAIR_THRESHOLD = 60  # if car condition falls below this, trigger repair flow


def process_damage(state: SystemState, car_id: str, damage_percent: int) -> Car:
    """Apply race damage without triggering repair workflows.

    This is used by the race simulation path.
    """

    return inventory.apply_damage(state, car_id, damage_percent)


def _trigger_repair_flow(state: SystemState, car_id: str) -> None:
    # Business rule: repairs require a mechanic.
    assigned = crew.require_roles_available(state, ["mechanic"])
    mechanic_name = assigned[0]
    crew.set_memberstatus(state, mechanic_name, "In Mission")

    car = inventory.get_car(state, car_id)
    if car.condition >= 100:
        crew.mark_available(state, mechanic_name)
        return

    # Keep repair simple: spend money, restore car.
    base_cost = max(100, int(car.price * 0.1)) + int((100 - car.condition) * 2)
    repair_cost = max(100, min(2000, base_cost))
    finance.record_expense(state, repair_cost, reason=f"Repair cost for {car_id}")

    # Repair to full in one step.

    needed = 100 - car.condition
    inventory.repair_car(state, car_id, needed)

    crew.mark_available(state, mechanic_name)


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

    car = inventory.get_car(state, car_id)
    inventory.use_part(state, part_name, quantity)
    if car.condition < 100:
        inventory.repair_car(state, car_id, min(5, 100 - car.condition))
    return inventory.get_car(state, car_id)


def use_tool_on_car(state: SystemState, car_id: str, tool_name: str, *, quantity: int = 1) -> Car:
    """Use a tool on a car.

    Same behavior as parts for this iteration.
    """

    if quantity <= 0:
        raise ValidationError("Quantity must be > 0")

    car = inventory.get_car(state, car_id)
    inventory.use_tool(state, tool_name, quantity)
    if car.condition < 100:
        inventory.repair_car(state, car_id, min(5, 100 - car.condition))
    return inventory.get_car(state, car_id)
