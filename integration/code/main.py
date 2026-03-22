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

    # --- Registration + Crew management ---
    registration.register_member(state, "Aisha", role="driver", age=22, experience=8, skills=85)
    registration.register_member(state, "Dev", role="mechanic", age=26, experience=12, skills=60)
    registration.register_member(state, "Mina", role="strategist", age=24, experience=10, skills=70)

    # --- Inventory ---
    car = inventory.add_car(state, "Nissan Skyline", condition=95)

    # --- Mission planning (checks role availability) ---
    scouting = mission.create_mission(state, "Scouting Route", required_roles=["strategist"]) 
    mission.validate_and_assign(state, scouting.mission_id)
    mission.complete_mission(state, scouting.mission_id)

    # --- Race management + Results (race ends immediately) ---
    race_obj = race.create_race(
        state,
        "Midnight Sprint",
        location="Dockyard",
        track_difficulty=6,
        entry_fee=150,
        prize1=600,
        prize2=300,
    )
    race.enter_race(state, race_obj.race_id, driver_name="Aisha", car_id=car.car_id)
    race.start_race_and_record(state, race_obj.race_id)

    # Print a compact summary for the demo.
    print("=== StreetRace Manager Demo Summary ===")
    print(f"Cash: {state.inventory.cash}")
    print(f"Cars: {[(c.car_id, c.model, c.condition, c.carstatus) for c in state.inventory.cars.values()]}")
    print(f"Crew: {[(m.name, m.role, m.rating, m.playerstatus) for m in state.crew.values()]}")
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
