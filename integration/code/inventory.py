"""Inventory module.

Responsibilities:
- Track cars, parts, tools, and cash (cash is mutated via finance.py)
- Manage car condition and status
"""

from __future__ import annotations

from models import Car, NotFoundError, SystemState, ValidationError


CAR_STATUSES = {"Available", "In Race", "In Mission", "Damaged"}


def purchase_car(
    state: SystemState,
    model: str,
    *,
    condition: int = 100,
    price: int,
    status: str = "Available",
) -> Car:
    """Purchase a car and record the expense via finance.

    This is the preferred integration entry point for buying cars.
    """

    if price < 0:
        raise ValidationError("Car price cannot be negative")
    if price > 0:
        import finance  # local import to avoid a module-level circular dependency

        finance.record_expense(state, price, reason=f"Car purchase: {model}")

    return add_car(state, model, condition=condition, status=status, price=price)


def purchase_part(state: SystemState, part_name: str, *, quantity: int, unit_price: int) -> None:
    if unit_price < 0:
        raise ValidationError("Unit price cannot be negative")
    total = unit_price * quantity
    if total > 0:
        import finance  # local import to avoid a module-level circular dependency

        finance.record_expense(state, total, reason=f"Part purchase: {part_name} x{quantity}")

    add_part(state, part_name, quantity)


def purchase_tool(state: SystemState, tool_name: str, *, quantity: int, unit_price: int) -> None:
    if unit_price < 0:
        raise ValidationError("Unit price cannot be negative")
    total = unit_price * quantity
    if total > 0:
        import finance  # local import to avoid a module-level circular dependency

        finance.record_expense(state, total, reason=f"Tool purchase: {tool_name} x{quantity}")

    add_tool(state, tool_name, quantity)


def add_car(
    state: SystemState,
    model: str,
    *,
    condition: int = 100,
    status: str = "Available",
    price: int = 0,
) -> Car:
    model = model.strip()
    if not model:
        raise ValidationError("Car model cannot be empty")
    if condition < 0 or condition > 100:
        raise ValidationError("Car condition must be between 0 and 100")
    if status not in CAR_STATUSES:
        raise ValidationError(f"Invalid car status: {status}")
    if price < 0:
        raise ValidationError("Car price cannot be negative")

    car_id = state.new_id("car")
    car = Car(car_id=car_id, model=model, condition=condition, carstatus=status, price=price)
    state.inventory.cars[car_id] = car
    return car


def get_car(state: SystemState, car_id: str) -> Car:
    try:
        return state.inventory.cars[car_id]
    except KeyError as exc:
        raise NotFoundError(f"Car not found: {car_id}") from exc


def set_carstatus(state: SystemState, car_id: str, carstatus: str) -> Car:
    if carstatus not in CAR_STATUSES:
        raise ValidationError(f"Invalid car status: {carstatus}")
    car = get_car(state, car_id)
    car.carstatus = carstatus
    return car


def apply_damage(state: SystemState, car_id: str, damage_percent: int) -> Car:
    car = get_car(state, car_id)
    if damage_percent < 0 or damage_percent > 100:
        raise ValidationError("Damage percent must be between 0 and 100")

    damage_points = round(100 * (damage_percent / 100.0))
    car.condition = max(0, car.condition - damage_points)
    if car.condition <= 0:
        car.carstatus = "Damaged"
    return car


def repair_car(state: SystemState, car_id: str, repair_points: int) -> Car:
    car = get_car(state, car_id)
    if repair_points <= 0:
        raise ValidationError("Repair points must be > 0")
    car.condition = min(100, car.condition + repair_points)
    if car.condition > 0 and car.carstatus == "Damaged":
        car.carstatus = "Available"
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


def use_tool(state: SystemState, tool_name: str, quantity: int = 1) -> None:
    tool_name = tool_name.strip().lower()
    if quantity <= 0:
        raise ValidationError("Quantity must be > 0")

    current = state.inventory.tools.get(tool_name, 0)
    if current < quantity:
        raise ValidationError(f"Not enough tools: {tool_name}")

    new_value = current - quantity
    if new_value == 0:
        state.inventory.tools.pop(tool_name, None)
    else:
        state.inventory.tools[tool_name] = new_value


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
