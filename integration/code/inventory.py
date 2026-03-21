"""Inventory module.

Responsibilities:
- Track cars, parts, tools, and cash (cash is mutated via finance.py)
- Manage car condition and availability
"""

from __future__ import annotations

from models import Car, NotFoundError, SystemState, ValidationError


def add_car(state: SystemState, model: str, *, condition: int = 100) -> Car:
    model = model.strip()
    if not model:
        raise ValidationError("Car model cannot be empty")
    if condition < 0 or condition > 100:
        raise ValidationError("Car condition must be between 0 and 100")

    car_id = state.new_id("car")
    car = Car(car_id=car_id, model=model, condition=condition, available=True)
    state.inventory.cars[car_id] = car
    return car


def get_car(state: SystemState, car_id: str) -> Car:
    try:
        return state.inventory.cars[car_id]
    except KeyError as exc:
        raise NotFoundError(f"Car not found: {car_id}") from exc


def set_car_available(state: SystemState, car_id: str, available: bool) -> Car:
    car = get_car(state, car_id)
    car.available = available
    return car


def apply_damage(state: SystemState, car_id: str, damage_percent: int) -> Car:
    car = get_car(state, car_id)
    if damage_percent < 0 or damage_percent > 100:
        raise ValidationError("Damage percent must be between 0 and 100")

    damage_points = round(100 * (damage_percent / 100.0))
    car.condition = max(0, car.condition - damage_points)
    return car


def repair_car(state: SystemState, car_id: str, repair_points: int) -> Car:
    car = get_car(state, car_id)
    if repair_points <= 0:
        raise ValidationError("Repair points must be > 0")
    car.condition = min(100, car.condition + repair_points)
    return car


def add_part(state: SystemState, part_name: str, quantity: int = 1) -> None:
    part_name = part_name.strip().lower()
    if not part_name:
        raise ValidationError("Part name cannot be empty")
    if quantity <= 0:
        raise ValidationError("Quantity must be > 0")

    state.inventory.parts[part_name] = state.inventory.parts.get(part_name, 0) + quantity


def use_part(state: SystemState, part_name: str, quantity: int = 1) -> None:
    part_name = part_name.strip().lower()
    if quantity <= 0:
        raise ValidationError("Quantity must be > 0")

    current = state.inventory.parts.get(part_name, 0)
    if current < quantity:
        raise ValidationError(f"Not enough parts: {part_name}")

    new_value = current - quantity
    if new_value == 0:
        state.inventory.parts.pop(part_name, None)
    else:
        state.inventory.parts[part_name] = new_value


def add_tool(state: SystemState, tool_name: str, quantity: int = 1) -> None:
    tool_name = tool_name.strip().lower()
    if not tool_name:
        raise ValidationError("Tool name cannot be empty")
    if quantity <= 0:
        raise ValidationError("Quantity must be > 0")

    state.inventory.tools[tool_name] = state.inventory.tools.get(tool_name, 0) + quantity


def get_cash(state: SystemState) -> int:
    return state.inventory.cash


def _adjust_cash(state: SystemState, delta: int) -> int:
    """Internal helper.

    Cash adjustments should happen through finance.py to ensure ledger tracking.
    """

    new_value = state.inventory.cash + delta
    if new_value < 0:
        raise ValidationError("Insufficient cash")
    state.inventory.cash = new_value
    return new_value
