"""Command-line UI for StreetRace Manager.

This UI is intentionally thin. Integration tests should import module functions
and operate on SystemState directly (do not test this interactive UI).
"""

from __future__ import annotations

from typing import Callable

from models import SystemState, StreetRaceError, ValidationError

import crew
import finance
import inventory
import maintenance
import mission
import race
import registration
import results


def run_cli() -> None:
    state = SystemState()

    print("StreetRace Manager (CLI)")
    print(f"Cash: {_fmt_money(inventory.get_cash(state))}")

    actions: dict[str, tuple[str, Callable[[], None]]] = {
        "1": ("Registration", lambda: _registration_menu(state)),
        "2": ("Crew Management", lambda: _crew_management_menu(state)),
        "3": ("Inventory", lambda: _inventory_menu(state)),
        "4": ("Maintenance", lambda: _maintenance_menu(state)),
        "5": ("Missions", lambda: _missions_menu(state)),
        "6": ("Race", lambda: _race_menu(state)),
        "7": ("Results", lambda: _results_menu(state)),
        "8": ("Show Summary", lambda: _show_summary(state)),
        "9": ("Finance", lambda: _finance_menu(state)),
        "10": ("Exit", lambda: None),
    }

    while True:
        print("\n=== Main Menu ===")
        for key in sorted(actions.keys(), key=lambda x: int(x) if x.isdigit() else 999):
            print(f"{key}. {actions[key][0]}")

        choice = input("Choose an option: ").strip()
        if choice == "10":
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


def _read_int(prompt: str, *, min_value: int | None = None, max_value: int | None = None) -> int:
    raw = input(prompt).strip()
    value = int(raw)
    if min_value is not None and value < min_value:
        raise ValidationError(f"Value must be >= {min_value}")
    if max_value is not None and value > max_value:
        raise ValidationError(f"Value must be <= {max_value}")
    return value


def _prompt_int(prompt: str, *, min_value: int | None = None, max_value: int | None = None) -> int:
    while True:
        raw = input(prompt).strip()
        try:
            value = int(raw)
        except ValueError:
            print("Please enter a valid integer.")
            continue

        if min_value is not None and value < min_value:
            print(f"Value must be >= {min_value}")
            continue
        if max_value is not None and value > max_value:
            print(f"Value must be <= {max_value}")
            continue
        return value


def _prompt_choice(prompt: str, valid: set[str]) -> str:
    while True:
        choice = input(prompt).strip()
        if choice in valid:
            return choice
        print("Invalid option.")


def _read_nonempty(prompt: str) -> str:
    value = input(prompt).strip()
    if not value:
        raise ValidationError("Input cannot be empty")
    return value


def _fmt_money(amount: int) -> str:
    return f"${amount}"


def _choose_role() -> str:
    """Fixed role selection (no free input)."""

    role_map = {
        "1": "driver",
        "2": "mechanic",
        "3": "strategist",
        "4": "spotter",
        "5": "doctor",
    }
    while True:
        print("\nRole Selection")
        print("1. Driver")
        print("2. Mechanic")
        print("3. Strategist")
        print("4. Spotter")
        print("5. Doctor")
        choice = input("Choose role: ").strip()
        role = role_map.get(choice)
        if role:
            return role
        print("Invalid role option.")


def _other_modules_placeholder() -> None:
    print("Other modules are not implemented in this UI yet.")


# ---- Missions module ----


def _missions_menu(state: SystemState) -> None:
    actions: dict[str, tuple[str, Callable[[], None]]] = {
        "1": ("View Missions", lambda: _missions_view_all(state)),
        "2": ("Assign Mission", lambda: _missions_assign(state)),
        "3": ("Complete Mission", lambda: _missions_complete(state)),
        "4": ("Abort Mission", lambda: _missions_abort(state)),
        "5": ("Back", lambda: None),
    }

    while True:
        print("\n=== Missions Menu ===")
        for key in ("1", "2", "3", "4", "5"):
            print(f"{key}. {actions[key][0]}")

        choice = input("Choose an option: ").strip()
        if choice == "5":
            return
        action = actions.get(choice)
        if not action:
            print("Invalid option.")
            continue
        action[1]()


def _missions_view_all(state: SystemState) -> None:
    missions = mission.get_all_missions(state)
    print("\n--- Missions (Board) ---")
    if not missions:
        print("(none)")
        return
    for m in missions:
        bounty_text = "Free" if m.bounty == 0 else _fmt_money(m.bounty)
        assigned = ",".join(m.assigned_members) if m.assigned_members else "-"
        roles = ",".join(m.required_roles)
        print(f"- {m.mission_id} | {m.name} | roles=[{roles}] | bounty={bounty_text} | status={m.status} | assigned=[{assigned}]")
        if m.description:
            print(f"  {m.description}")


def _missions_assign(state: SystemState) -> None:
    missions = mission.get_all_missions(state)
    available = [m for m in missions if m.status != "assigned"]
    print("\nAssignable missions:")
    if not available:
        print("(none)")
        return
    for m in available:
        bounty_text = "Free" if m.bounty == 0 else _fmt_money(m.bounty)
        print(f"- {m.mission_id} | {m.name} | bounty={bounty_text} | last_status={m.status}")

    mission_id = _read_nonempty("Select mission id: ")
    m = mission.assign_mission(state, mission_id)
    print(f"Assigned: {m.mission_id} | {m.name} | members={m.assigned_members}")


def _missions_complete(state: SystemState) -> None:
    missions = mission.get_all_missions(state)
    active = [m for m in missions if m.status == "assigned"]
    print("\nAssigned missions:")
    if not active:
        print("(none)")
        return
    for m in active:
        print(f"- {m.mission_id} | {m.name} | members={m.assigned_members}")

    mission_id = _read_nonempty("Select mission id: ")
    m = mission.complete_mission(state, mission_id)
    bounty_text = "Free" if m.bounty == 0 else _fmt_money(m.bounty)
    print(f"Completed: {m.mission_id} | bounty={bounty_text}")


def _missions_abort(state: SystemState) -> None:
    missions = mission.get_all_missions(state)
    active = [m for m in missions if m.status == "assigned"]
    print("\nAssigned missions:")
    if not active:
        print("(none)")
        return
    for m in active:
        print(f"- {m.mission_id} | {m.name} | members={m.assigned_members}")

    mission_id = _read_nonempty("Select mission id: ")
    m = mission.abort_mission(state, mission_id)
    print(f"Aborted: {m.mission_id} | {m.name}")


# ---- Registration module ----


def _registration_menu(state: SystemState) -> None:
    actions: dict[str, tuple[str, Callable[[], None]]] = {
        "1": ("Register new crew member", lambda: _register_new_member(state)),
        "2": ("View all crew members", lambda: _view_registered_members(state)),
        "3": ("Back", lambda: None),
    }

    while True:
        print("\n=== Registration Menu ===")
        for key in ("1", "2", "3"):
            print(f"{key}. {actions[key][0]}")

        choice = input("Choose an option: ").strip()
        if choice == "3":
            return
        action = actions.get(choice)
        if not action:
            print("Invalid option.")
            continue
        action[1]()


def _register_new_member(state: SystemState) -> None:
    name = _read_nonempty("Name: ")
    age = _prompt_int("Age: ", min_value=1)

    # Per-field loop: experience must be 0-100 and < age.
    while True:
        experience = _prompt_int("Experience (0-100): ", min_value=0, max_value=100)
        if experience < age:
            break
        print("Experience must be less than age. Re-enter experience.")

    skills = _prompt_int("Skills (0-100): ", min_value=0, max_value=100)
    role = _choose_role()

    member = registration.register_member(
        state,
        name,
        role=role,
        age=age,
        experience=experience,
        skills=skills,
    )
    print(f"Registered: {member.name} (role={member.role})")


def _view_registered_members(state: SystemState) -> None:
    members = registration.get_all_members(state)
    if not members:
        print("No crew members registered.")
        return
    print("\n--- Crew Members ---")
    for m in members:
        print(f"- {m.name} | role={m.role} | age={m.age} | exp={m.experience} | skills={m.skills} | rating={m.rating} | status={m.memberstatus}")


# ---- Crew Management module ----


def _crew_management_menu(state: SystemState) -> None:
    actions: dict[str, tuple[str, Callable[[], None]]] = {
        "1": ("View all members", lambda: _crew_view_all(state)),
        "2": ("View members by role", lambda: _crew_view_by_role(state)),
        "3": ("View individual member details", lambda: _crew_view_details(state)),
        "4": ("Back", lambda: None),
    }

    while True:
        print("\n=== Crew Management Menu ===")
        for key in ("1", "2", "3", "4"):
            print(f"{key}. {actions[key][0]}")

        choice = input("Choose an option: ").strip()
        if choice == "4":
            return
        action = actions.get(choice)
        if not action:
            print("Invalid option.")
            continue
        action[1]()


def _crew_view_all(state: SystemState) -> None:
    members = crew.get_all_members(state)
    if not members:
        print("No crew members found.")
        return
    print("\n--- All Members ---")
    for m in members:
        print(f"- {m.name} | role={m.role} | rating={m.rating} | status={m.memberstatus}")


def _crew_view_by_role(state: SystemState) -> None:
    role = _choose_role()
    members = crew.get_members_by_role(state, role)
    print(f"\n--- Members with role={role} ---")
    if not members:
        print("None.")
        return
    for m in members:
        print(f"- {m.name} | age={m.age} | exp={m.experience} | skills={m.skills} | rating={m.rating} | status={m.memberstatus}")


def _crew_view_details(state: SystemState) -> None:
    name = _read_nonempty("Member name: ")
    m = crew.get_member_details(state, name)
    print("\n--- Member Details ---")
    print(f"Name: {m.name}")
    print(f"Role: {m.role}")
    print(f"Age: {m.age}")
    print(f"Experience: {m.experience}")
    print(f"Skills: {m.skills}")
    print(f"Rating: {m.rating}")
    print(f"Status: {m.memberstatus}")


# ---- Inventory module ----


def _inventory_menu(state: SystemState) -> None:
    actions: dict[str, tuple[str, Callable[[], None]]] = {
        "1": ("Add Car", lambda: _inventory_add_car(state)),
        "2": ("View Cars", lambda: _inventory_view_cars(state)),
        "3": ("Add Part", lambda: _inventory_add_part(state)),
        "4": ("Add Tool", lambda: _inventory_add_tool(state)),
        "5": ("View Inventory Summary", lambda: _inventory_summary(state)),
        "6": ("Back", lambda: None),
    }

    while True:
        print("\n=== Inventory Menu ===")
        for key in ("1", "2", "3", "4", "5", "6"):
            print(f"{key}. {actions[key][0]}")

        choice = input("Choose an option: ").strip()
        if choice == "6":
            return
        action = actions.get(choice)
        if not action:
            print("Invalid option.")
            continue
        action[1]()


def _inventory_add_car(state: SystemState) -> None:
    name = _read_nonempty("Car name: ")
    model = _read_nonempty("Car model: ")
    condition = _prompt_int("Condition (0-100): ", min_value=0, max_value=100)
    price = _prompt_int("Price: $", min_value=0)

    full_model = f"{name} {model}".strip()

    car = inventory.purchase_car(state, full_model, condition=condition, status="Available", price=price)
    print(
        f"Added car: {car.car_id} | {car.model} | condition={car.condition} | carstatus={car.carstatus} | price={_fmt_money(price)}"
    )


def _inventory_view_cars(state: SystemState) -> None:
    cars = list(state.inventory.cars.values())
    cars.sort(key=lambda c: c.car_id)
    if not cars:
        print("No cars in inventory.")
        return
    print("\n--- Cars ---")
    for c in cars:
        print(f"- {c.car_id} | {c.model} | condition={c.condition} | carstatus={c.carstatus}")


def _inventory_add_part(state: SystemState) -> None:
    part_name = _read_nonempty("Part name: ")
    quantity = _prompt_int("Quantity: ", min_value=1)
    unit_price = _prompt_int("Unit price: $", min_value=0)

    inventory.purchase_part(state, part_name, quantity=quantity, unit_price=unit_price)
    print(f"Added part: {part_name} x{quantity} (spent {_fmt_money(unit_price * quantity)})")


def _inventory_add_tool(state: SystemState) -> None:
    tool_name = _read_nonempty("Tool name: ")
    quantity = _prompt_int("Quantity: ", min_value=1)
    unit_price = _prompt_int("Unit price: $", min_value=0)

    inventory.purchase_tool(state, tool_name, quantity=quantity, unit_price=unit_price)
    print(f"Added tool: {tool_name} x{quantity} (spent {_fmt_money(unit_price * quantity)})")


def _inventory_summary(state: SystemState) -> None:
    print("\n=== Inventory Summary ===")
    print(f"Cash balance: {_fmt_money(inventory.get_cash(state))}")

    print("\nCars:")
    if not state.inventory.cars:
        print("(none)")
    else:
        for c in sorted(state.inventory.cars.values(), key=lambda x: x.car_id):
            print(f"- {c.car_id} | {c.model} | condition={c.condition} | carstatus={c.carstatus}")

    print("\nParts:")
    if not state.inventory.parts:
        print("(none)")
    else:
        for name, qty in sorted(state.inventory.parts.items()):
            print(f"- {name}: {qty}")

    print("\nTools:")
    if not state.inventory.tools:
        print("(none)")
    else:
        for name, qty in sorted(state.inventory.tools.items()):
            print(f"- {name}: {qty}")


# ---- Maintenance module ----


def _maintenance_menu(state: SystemState) -> None:
    actions: dict[str, tuple[str, Callable[[], None]]] = {
        "1": ("Use Part on Car", lambda: _maintenance_use_part(state)),
        "2": ("Use Tool on Car", lambda: _maintenance_use_tool(state)),
        "3": ("Manual Repair", lambda: _maintenance_manual_repair(state)),
        "4": ("Back", lambda: None),
    }

    while True:
        print("\n=== Maintenance Menu ===")
        for key in ("1", "2", "3", "4"):
            print(f"{key}. {actions[key][0]}")

        choice = input("Choose an option: ").strip()
        if choice == "4":
            return
        action = actions.get(choice)
        if not action:
            print("Invalid option.")
            continue
        action[1]()


def _maintenance_use_part(state: SystemState) -> None:
    _print_cars(state, only_available=False)
    _print_parts(state)

    car_id = _read_nonempty("Select car id: ")
    part_name = _read_nonempty("Select part name: ")
    quantity = _prompt_int("Quantity: ", min_value=1)

    car = maintenance.use_part_on_car(state, car_id, part_name, quantity=quantity)
    print(f"Updated car: {car.car_id} | condition={car.condition} | carstatus={car.carstatus}")


def _maintenance_use_tool(state: SystemState) -> None:
    _print_cars(state, only_available=False)
    _print_tools(state)

    car_id = _read_nonempty("Select car id: ")
    tool_name = _read_nonempty("Select tool name: ")
    car = maintenance.use_tool_on_car(state, car_id, tool_name, quantity=1)
    print(f"Updated car: {car.car_id} | condition={car.condition} | carstatus={car.carstatus}")


def _maintenance_manual_repair(state: SystemState) -> None:
    _print_cars(state, only_available=False)
    car_id = _read_nonempty("Select car id: ")
    maintenance.request_manual_repair(state, car_id)
    car = inventory.get_car(state, car_id)
    print(f"Repaired car: {car.car_id} | condition={car.condition} | carstatus={car.carstatus}")


def _print_cars(state: SystemState, *, only_available: bool) -> None:
    cars = sorted(state.inventory.cars.values(), key=lambda c: c.car_id)
    if only_available:
        cars = [c for c in cars if c.carstatus == "Available"]
    print("\nCars:")
    if not cars:
        print("(none)")
        return
    for c in cars:
        print(f"- {c.car_id} | {c.model} | condition={c.condition} | carstatus={c.carstatus}")


def _print_parts(state: SystemState) -> None:
    print("\nParts:")
    if not state.inventory.parts:
        print("(none)")
        return
    for name, qty in sorted(state.inventory.parts.items()):
        print(f"- {name}: {qty}")


def _print_tools(state: SystemState) -> None:
    print("\nTools:")
    if not state.inventory.tools:
        print("(none)")
        return
    for name, qty in sorted(state.inventory.tools.items()):
        print(f"- {name}: {qty}")


# ---- Race module ----


def _race_menu(state: SystemState) -> None:
    actions: dict[str, tuple[str, Callable[[], None]]] = {
        "1": ("Create Race", lambda: _race_create(state)),
        "2": ("Enter Race", lambda: _race_enter(state)),
        "3": ("Start Race (ends immediately)", lambda: _race_start(state)),
        "4": ("View Races", lambda: _race_view_races(state)),
        "5": ("Back", lambda: None),
    }

    while True:
        print("\n=== Race Menu ===")
        for key in ("1", "2", "3", "4", "5"):
            print(f"{key}. {actions[key][0]}")

        choice = input("Choose an option: ").strip()
        if choice == "5":
            return
        action = actions.get(choice)
        if not action:
            print("Invalid option.")
            continue
        action[1]()


def _race_create(state: SystemState) -> None:
    title = _read_nonempty("Title: ")
    location = _read_nonempty("Location: ")
    track_difficulty = _prompt_int("Track difficulty (1-10): ", min_value=1, max_value=10)
    entry_fee = _prompt_int("Entry fee: $", min_value=0)
    prize1 = _prompt_int("Prize 1 (1st): $", min_value=0)
    prize2 = _prompt_int("Prize 2 (2nd): $", min_value=0)

    race_obj = race.create_race(
        state,
        title,
        location=location,
        track_difficulty=track_difficulty,
        entry_fee=entry_fee,
        prize1=prize1,
        prize2=prize2,
    )
    print(f"Created race: {race_obj.race_id} | {race_obj.name} @ {race_obj.location} | difficulty={race_obj.track_difficulty}")


def _race_enter(state: SystemState) -> None:
    races_open = [r for r in state.races.values() if r.status == "created"]
    races_open.sort(key=lambda r: r.race_id)
    print("\nOpen races:")
    if not races_open:
        print("(none)")
        return
    for r in races_open:
        print(f"- {r.race_id} | {r.name} | entry={_fmt_money(r.entry_fee)} | prizes={_fmt_money(r.prize)}/{_fmt_money(r.second_prize)}")

    while True:
        race_id = _read_nonempty("Select race id: ")
        try:
            race_obj = race.get_race(state, race_id)
        except StreetRaceError as exc:
            print(f"Error: {exc}")
            continue
        if race_obj.status != "created":
            print(f"Race is not open for enrollment (status={race_obj.status}).")
            continue
        break

    drivers = [m for m in state.crew.values() if m.role == "driver" and m.memberstatus == "Available"]
    drivers.sort(key=lambda m: m.name)
    print("\nAvailable drivers:")
    if not drivers:
        print("(none)")
        return
    for d in drivers:
        print(f"- {d.name} | skills={d.skills} | exp={d.experience} | rating={d.rating}")

    driver_name = _read_nonempty("Select driver id (name): ")

    _print_cars(state, only_available=True)
    car_id = _read_nonempty("Select car id: ")

    race_obj = race.enter_race(state, race_id, driver_name=driver_name, car_id=car_id)
    print(f"Entered race: {race_obj.race_id} | driver={race_obj.driver_name} | car={race_obj.car_id} | status={race_obj.status}")


def _race_start(state: SystemState) -> None:
    scheduled = [r for r in state.races.values() if r.status == "scheduled"]
    scheduled.sort(key=lambda r: r.race_id)
    print("\nScheduled races:")
    if not scheduled:
        print("(none)")
        return
    for r in scheduled:
        print(f"- {r.race_id} | {r.name} | driver={r.driver_name} | car={r.car_id}")

    while True:
        race_id = _read_nonempty("Select race id: ")
        try:
            race_obj = race.get_race(state, race_id)
        except StreetRaceError as exc:
            print(f"Error: {exc}")
            continue
        if race_obj.status != "scheduled":
            print(f"Race is not scheduled (status={race_obj.status}).")
            continue
        break
    leaderboard = race.start_race_and_record(state, race_id)
    print("\nRace finished. Leaderboard:")
    for name, rank, score in leaderboard:
        print(f"{rank}. {name} | score={score:.2f}")


def _race_view_races(state: SystemState) -> None:
    races_all = list(state.races.values())
    races_all.sort(key=lambda r: r.race_id)
    print("\n--- Races ---")
    if not races_all:
        print("(none)")
        return
    for r in races_all:
        print(
            f"- {r.race_id} | {r.name} | location={r.location} | difficulty={r.track_difficulty} | status={r.status}"
        )


# ---- Finance module ----


def _finance_menu(state: SystemState) -> None:
    actions: dict[str, tuple[str, Callable[[], None]]] = {
        "1": ("View Income Entries", lambda: _finance_view_income(state)),
        "2": ("View Expense Entries", lambda: _finance_view_expenses(state)),
        "3": ("Add Income", lambda: _finance_add_income(state)),
        "4": ("Add Expense", lambda: _finance_add_expense(state)),
        "5": ("Back", lambda: None),
    }

    while True:
        print("\n=== Finance Menu ===")
        cash = inventory.get_cash(state)
        print(f"Current Cash: {_fmt_money(cash)}\n")
        for key in ("1", "2", "3", "4", "5"):
            print(f"{key}. {actions[key][0]}")

        choice = input("Choose an option: ").strip()
        if choice == "5":
            return

        action = actions.get(choice)
        if not action:
            print("Invalid option.")
            continue
        action[1]()


def _finance_view_income(state: SystemState) -> None:
    entries = [e for e in state.ledger if e.kind == "income"]
    print("\n--- Income Entries ---")
    if not entries:
        print("(none)")
        return
    for e in entries:
        print(f"- {e.entry_id} | amount={_fmt_money(e.amount)} | reason={e.reason}")


def _finance_view_expenses(state: SystemState) -> None:
    entries = [e for e in state.ledger if e.kind == "expense"]
    print("\n--- Expense Entries ---")
    if not entries:
        print("(none)")
        return
    for e in entries:
        print(f"- {e.entry_id} | amount={_fmt_money(e.amount)} | reason={e.reason}")


def _finance_add_income(state: SystemState) -> None:
    """Add manual income to the system."""
    print("\n--- Add Income ---")
    amount = _prompt_int("Enter income amount: ", min_value=1)
    reason = _read_nonempty("Enter reason for income: ")

    try:
        finance.record_income(state, amount, reason=reason)
        print(f"Successfully added income of {_fmt_money(amount)}")
        print(f"New cash balance: {_fmt_money(inventory.get_cash(state))}")
    except ValidationError as exc:
        print(f"Error: {exc}")


def _finance_add_expense(state: SystemState) -> None:
    """Add manual expense to the system."""
    print("\n--- Add Expense ---")
    amount = _prompt_int("Enter expense amount: ", min_value=1)
    reason = _read_nonempty("Enter reason for expense: ")

    try:
        finance.record_expense(state, amount, reason=reason)
        print(f"Successfully deducted expense of {_fmt_money(amount)}")
        print(f"New cash balance: {_fmt_money(inventory.get_cash(state))}")
    except ValidationError as exc:
        print(f"Error: {exc}")


# ---- Results module ----


def _results_menu(state: SystemState) -> None:
    actions: dict[str, tuple[str, Callable[[], None]]] = {
        "1": ("View Leaderboard (overall)", lambda: _results_overall_leaderboard(state)),
        "2": ("View Race Outcomes", lambda: _results_race_outcomes(state)),
        "3": ("Back", lambda: None),
    }

    while True:
        print("\n=== Results Menu ===")
        for key in ("1", "2", "3"):
            print(f"{key}. {actions[key][0]}")

        choice = input("Choose an option: ").strip()
        if choice == "3":
            return
        action = actions.get(choice)
        if not action:
            print("Invalid option.")
            continue
        action[1]()


def _results_overall_leaderboard(state: SystemState) -> None:
    members = list(state.crew.values())
    members.sort(key=lambda m: m.rating, reverse=True)
    print("\n--- Overall Leaderboard (by rating) ---")
    if not members:
        print("(none)")
        return
    for m in members:
        print(f"- {m.name} | role={m.role} | rating={m.rating} | status={m.memberstatus}")


def _results_race_outcomes(state: SystemState) -> None:
    if not state.race_results:
        print("No race outcomes recorded yet.")
        return

    print("\nRaces with outcomes:")
    for race_id in sorted(state.race_results.keys()):
        r = state.races.get(race_id)
        title = r.name if r else "(unknown)"
        print(f"- {race_id} | {title}")

    race_id = _read_nonempty("Select race id: ")
    leaderboard = state.race_results.get(race_id)
    if not leaderboard:
        print("No outcomes for that race.")
        return
    print("\n--- Race Outcome ---")
    for name, rank, score in leaderboard:
        print(f"{rank}. {name} | score={score:.2f}")


def _show_summary(state: SystemState) -> None:
    print("\n=== Summary ===")
    print(f"Cash: {_fmt_money(inventory.get_cash(state))}")
    print(f"Crew: {[(m.name, m.role, m.rating, m.memberstatus) for m in state.crew.values()]}")
    print(f"Cars: {[(c.car_id, c.model, c.condition, c.carstatus) for c in state.inventory.cars.values()]}")
    print(f"Parts: {state.inventory.parts}")
    print(f"Tools: {state.inventory.tools}")
    print(f"Ledger entries: {len(state.ledger)}")
