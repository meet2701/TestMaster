"""StreetRace Manager (command-line system).

This project keeps business logic in separate modules to support integration testing.

Entry points:
- Interactive CLI (default): `python3 main.py`
- Scripted demo flow: `python3 main.py --demo`

For integration testing, tests should import module functions and operate on a
fresh SystemState instance (avoid testing the interactive UI directly).
"""

from __future__ import annotations

import argparse

from models import SystemState

import crew
import finance
import inventory
import mission
import race
import registration
import results

import ui


def demo_flow() -> None:
    state = SystemState()

    # Seed cash so entry fees / repairs are possible.
    finance.record_income(state, 1000, reason="Initial cash")

    # --- Registration + Crew management ---
    registration.register_member(state, "Aisha")
    registration.register_member(state, "Dev")
    registration.register_member(state, "Mina")

    crew.set_role(state, "Aisha", "driver")
    crew.set_skill_level(state, "Aisha", 7)

    crew.set_role(state, "Dev", "mechanic")
    crew.set_skill_level(state, "Dev", 6)

    crew.set_role(state, "Mina", "strategist")
    crew.set_skill_level(state, "Mina", 5)

    # --- Inventory ---
    car = inventory.add_car(state, "Nissan Skyline", condition=95)

    # --- Mission planning (checks role availability) ---
    scouting = mission.create_mission(state, "Scouting Route", required_roles=["strategist"]) 
    mission.validate_and_assign(state, scouting.mission_id)
    mission.complete_mission(state, scouting.mission_id)

    # --- Race management ---
    race_obj = race.create_race(state, "Midnight Sprint", entry_fee=150, prize=600)
    race.enroll_driver_and_car(state, race_obj.race_id, driver_name="Aisha", car_id=car.car_id)
    race.start_race(state, race_obj.race_id)

    # --- Results (updates rankings + money + maintenance) ---
    results.record_race_outcome(
        state,
        race_obj.race_id,
        position=1,
        damage_percent=50,  # triggers maintenance + repair mission if threshold crossed
        notes="Clean launch, heavy scrape on exit.",
    )

    # Print a compact summary for the demo.
    print("=== StreetRace Manager Demo Summary ===")
    print(f"Cash: {state.inventory.cash}")
    print(f"Cars: {[(c.car_id, c.model, c.condition, c.available) for c in state.inventory.cars.values()]}")
    print(f"Crew: {[(m.name, m.role, m.skill_level, m.active) for m in state.crew.values()]}")
    print(f"Rankings: {state.rankings}")
    print(f"Races: {[(r.race_id, r.name, r.status, r.driver_name, r.car_id) for r in state.races.values()]}")
    print(f"Missions: {[(m.mission_id, m.name, m.status, m.required_roles, m.assigned_members) for m in state.missions.values()]}")
    print(f"Ledger entries: {len(state.ledger)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="StreetRace Manager")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run a scripted demo flow (useful for quick sanity checks).",
    )
    args = parser.parse_args()

    if args.demo:
        demo_flow()
    else:
        ui.run_cli()
