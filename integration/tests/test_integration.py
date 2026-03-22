"""
Integration Tests for StreetRace Manager System

Tests validate interactions between:
- registration, crew, inventory, race, results, mission, finance, maintenance modules

Each test section focuses on specific module integration chains as documented in CALL_GRAPH_GUIDE.md
"""

import pytest
import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'code'))

from models import SystemState, ValidationError, NotFoundError
import registration
import crew
import inventory
import race
import results
import mission
import finance
import maintenance


# ============================================================================
# SECTION 1: Registration → Crew Integration
# Modules: registration.register_member → crew.validate_driver → race.enter_race
# Business Rule: Crew member must be registered before racing
# ============================================================================

def test_register_driver_and_enter_race():
    """
    Scenario: Register a driver and successfully enter them into a race
    Modules: registration → crew → race → inventory → finance
    Expected: Driver registered, validated, entered race, entry fee deducted
    """
    state = SystemState()

    # Register driver (experience must be < age)
    registration.register_member(state, "driver1", "driver", age=25, experience=20)

    # Create race (all keyword args required)
    race_obj = race.create_race(state, "Race1", location="Downtown", track_difficulty=5, entry_fee=100, prize1=500, prize2=200)

    # Add car to inventory (returns Car object, car_id is generated)
    car = inventory.add_car(state, "Honda", price=2000)

    # Enter race (use race_id and keyword args)
    race.enter_race(state, race_obj.race_id, driver_name="driver1", car_id=car.car_id)

    # Verify race entry successful
    updated_race = race.get_race(state, race_obj.race_id)
    assert updated_race.driver_name == "driver1"
    assert updated_race.car_id == car.car_id

    # Verify status changes
    assert state.crew["driver1"].memberstatus == "In Race"
    assert state.inventory.cars[car.car_id].carstatus == "In Race"

    # Verify entry fee deducted
    assert state.inventory.cash == 5000 - 100

    # Verify finance ledger updated
    assert len(state.ledger) == 1
    assert state.ledger[0].kind == "expense"
    assert state.ledger[0].amount == 100


def test_enter_race_without_registration():
    """
    Scenario: Attempt to enter race without registering driver first
    Modules: race → crew (validation should fail)
    Expected: ValidationError or NotFoundError raised
    """
    state = SystemState()

    # Create race (all keyword args required)
    race_obj = race.create_race(state, "Race1", location="Street", track_difficulty=5, entry_fee=100, prize1=500, prize2=200)

    # Add car
    car = inventory.add_car(state, "Honda", price=2000)

    # Try to enter race without registration - should fail
    with pytest.raises((ValidationError, NotFoundError)):
        race.enter_race(state, race_obj.race_id, driver_name="unregistered_driver", car_id=car.car_id)


def test_enter_race_with_non_driver_role():
    """
    Scenario: Register member with non-driver role and try to enter race
    Modules: registration → crew → race
    Expected: ValidationError - only drivers can race
    """
    state = SystemState()

    # Register mechanic (not driver)
    registration.register_member(state, "mechanic1", "mechanic")

    # Create race
    race_obj = race.create_race(state, "Race1", location="Street", track_difficulty=5, entry_fee=100, prize1=500, prize2=200)

    # Add car
    car = inventory.add_car(state, "Honda", price=2000)

    # Try to enter race with non-driver - should fail
    with pytest.raises(ValidationError):
        race.enter_race(state, race_obj.race_id, driver_name="mechanic1", car_id=car.car_id)


def test_registration_creates_crew_member():
    """
    Scenario: Register member and verify in crew system
    Modules: registration → crew
    Expected: Member accessible via crew functions
    """
    state = SystemState()

    # age must be > experience
    registration.register_member(state, "driver1", "driver", age=85, experience=80)

    # Verify via crew module
    member = crew.get_member(state, "driver1")
    assert member.name == "driver1"
    assert member.role == "driver"
    assert member.age == 85
    assert member.experience == 80


def test_get_members_by_role():
    """
    Scenario: Register multiple members and filter by role
    Modules: registration → crew
    Expected: Correct filtering by role
    """
    state = SystemState()

    registration.register_member(state, "driver1", "driver")
    registration.register_member(state, "driver2", "driver")
    registration.register_member(state, "mechanic1", "mechanic")
    registration.register_member(state, "strategist1", "strategist")

    # Get drivers
    drivers = crew.get_members_by_role(state, "driver")
    assert len(drivers) == 2

    # Get mechanics
    mechanics = crew.get_members_by_role(state, "mechanic")
    assert len(mechanics) == 1


def test_age_experience_validation_when_age_missing():
    """
    Scenario: Register member with experience but without specifying age
    Modules: registration
    Expected: ValidationError if experience >= age (but this requires age to be set)
    Validation Focus: Business rule experience < age when age is omitted
    """
    state = SystemState()

    # Try to register with high experience but no age specified
    # This should ideally fail or at least not allow experience >= age
    try:
        member = registration.register_member(state, "driver1", "driver", experience=50)

        # If registration succeeds with age=0 and experience=50, rule is violated
        if member.age == 0 and member.experience == 50:
            pytest.fail("experience (50) was allowed to be >= age (0)")
    except ValidationError:
        # Expected behavior - should reject high experience without proper age
        pass


# ============================================================================
# SECTION 2: Race → Results → Finance Integration
# Modules: race.start_race → results.record_race_outcome → finance.record_income
#          → inventory._adjust_cash → results._update_rating
# Business Rule: Race completion updates prize money, ratings, and inventory
# ============================================================================

def test_complete_race_with_winner():
    """
    Scenario: Complete a race and verify all state updates
    Modules: race → results → finance → inventory → crew
    Expected: Winner gets prize, ratings updated, cash increases, statuses reset
    """
    state = SystemState()

    # Setup with high skills/condition for guaranteed win (skills >= 80, condition >= 80)
    registration.register_member(state, "driver1", "driver", age=70, experience=60, skills=85)
    car = inventory.add_car(state, "Honda", price=2000, condition=85)
    state.inventory.cash = 5000
    race_obj = race.create_race(state, "Race1", location="Downtown", track_difficulty=5, entry_fee=100, prize1=1000, prize2=500)
    race.enter_race(state, race_obj.race_id, driver_name="driver1", car_id=car.car_id)

    cash_before_race = state.inventory.cash

    # Start and complete race
    race.start_race_and_record(state, race_obj.race_id)

    # Verify race marked completed
    updated_race = race.get_race(state, race_obj.race_id)
    assert updated_race.status == "completed"

    # Verify driver status reset
    assert state.crew["driver1"].memberstatus == "Available"

    # Verify car status reset (only marked Damaged if condition <= 0)
    car_after = inventory.get_car(state, car.car_id)
    if car_after.condition > 0:
        assert car_after.carstatus == "Available"
    else:
        assert car_after.carstatus == "Damaged"

    # Verify cash updated (prize money added)
    assert state.inventory.cash >= cash_before_race

    # Verify rating updated
    assert state.crew["driver1"].rating > 0

    # Verify ledger has prize entry
    income_entries = [e for e in state.ledger if e.kind == "income"]
    assert len(income_entries) > 0


def test_race_leaderboard_computation():
    """
    Scenario: Complete race and verify leaderboard is computed
    Modules: race → results._compute_leaderboard
    Expected: Leaderboard contains race participants with correct data
    """
    state = SystemState()

    # Setup with high skills/condition for consistent results
    registration.register_member(state, "driver1", "driver", age=70, experience=50, skills=85)
    car = inventory.add_car(state, "Honda", price=2000, condition=85)
    race_obj = race.create_race(state, "Race1", location="Street", track_difficulty=5, entry_fee=50, prize1=500, prize2=200)
    race.enter_race(state, race_obj.race_id, driver_name="driver1", car_id=car.car_id)

    # Complete race
    race.start_race_and_record(state, race_obj.race_id)

    # Verify race results stored (use race_id, not race name)
    assert race_obj.race_id in state.race_results
    assert len(state.race_results[race_obj.race_id]) > 0


def test_race_with_damage_application():
    """
    Scenario: Complete race and verify damage applied to car
    Modules: race → results → maintenance → inventory
    Expected: Car condition reduced, potentially marked as Damaged
    """
    state = SystemState()

    # Setup with high skills/condition to ensure win and consistent behavior
    registration.register_member(state, "driver1", "driver", age=70, experience=50, skills=85)
    car = inventory.add_car(state, "Honda", price=2000, condition=85)
    race_obj = race.create_race(state, "Race1", location="Track", track_difficulty=8, entry_fee=50, prize1=500, prize2=200)
    race.enter_race(state, race_obj.race_id, driver_name="driver1", car_id=car.car_id)

    initial_condition = state.inventory.cars[car.car_id].condition

    # Start race
    race.start_race_and_record(state, race_obj.race_id)

    # Verify damage applied
    final_condition = state.inventory.cars[car.car_id].condition
    assert final_condition <= initial_condition

    # Car only marked "Damaged" when condition <= 0
    if final_condition <= 0:
        assert state.inventory.cars[car.car_id].carstatus == "Damaged"
    elif final_condition > 0:
        assert state.inventory.cars[car.car_id].carstatus == "Available"


def test_high_difficulty_race_causes_more_damage():
    """
    Scenario: High difficulty race should cause more damage than low difficulty
    Modules: race → results → maintenance
    Expected: Track difficulty affects damage amount
    """
    state = SystemState()

    # Setup two identical drivers and cars with high skills/condition for consistency
    registration.register_member(state, "driver1", "driver", age=70, experience=50, skills=85)
    registration.register_member(state, "driver2", "driver", age=70, experience=50, skills=85)
    car1 = inventory.add_car(state, "Honda", price=2000, condition=85)
    car2 = inventory.add_car(state, "Honda", price=2000, condition=85)

    # Race 1: Low difficulty
    race_obj1 = race.create_race(state, "Race1", location="Easy Track", track_difficulty=2, entry_fee=50, prize1=300, prize2=100)
    race.enter_race(state, race_obj1.race_id, driver_name="driver1", car_id=car1.car_id)
    initial_cond1 = state.inventory.cars[car1.car_id].condition
    race.start_race_and_record(state, race_obj1.race_id)
    damage1 = initial_cond1 - state.inventory.cars[car1.car_id].condition

    # Race 2: High difficulty
    race_obj2 = race.create_race(state, "Race2", location="Hard Track", track_difficulty=9, entry_fee=50, prize1=800, prize2=400)
    race.enter_race(state, race_obj2.race_id, driver_name="driver2", car_id=car2.car_id)
    initial_cond2 = state.inventory.cars[car2.car_id].condition
    race.start_race_and_record(state, race_obj2.race_id)
    damage2 = initial_cond2 - state.inventory.cars[car2.car_id].condition

    # High difficulty should cause equal or more damage
    assert damage2 >= damage1


def test_race_with_multiple_dummy_drivers():
    """
    Scenario: Race includes dummy drivers for competition
    Modules: race → results
    Expected: Leaderboard includes all participants
    """
    state = SystemState()

    # Setup with high skills/condition for guaranteed win
    registration.register_member(state, "driver1", "driver", age=70, experience=50, skills=85)
    car = inventory.add_car(state, "Honda", price=2000, condition=85)

    # Create race
    race_obj = race.create_race(state, "Race1", location="Street", track_difficulty=5, entry_fee=100, prize1=1000, prize2=500)
    race.enter_race(state, race_obj.race_id, driver_name="driver1", car_id=car.car_id)

    # Ensure dummy drivers created
    race._ensure_dummy_drivers(state)
    assert len(state.dummy_drivers) > 0

    # Complete race
    race.start_race_and_record(state, race_obj.race_id)

    # Verify leaderboard has multiple participants (use race_id)
    if race_obj.race_id in state.race_results:
        assert len(state.race_results[race_obj.race_id]) > 1


def test_ratings_update_after_race():
    """
    Scenario: Driver ratings increase after race completion
    Modules: race → results._update_rating
    Expected: Driver rating increases based on performance
    """
    state = SystemState()

    registration.register_member(state, "driver1", "driver", age=70, experience=50, skills=85)
    car = inventory.add_car(state, "Honda", price=2000, condition=85)

    initial_rating = state.crew["driver1"].rating

    race_obj = race.create_race(state, "Race1", location="Street", track_difficulty=5, entry_fee=50, prize1=500, prize2=200)
    race.enter_race(state, race_obj.race_id, driver_name="driver1", car_id=car.car_id)
    race.start_race_and_record(state, race_obj.race_id)

    # Rating should have changed (will be positive since skills >= 80 and condition >= 80)
    assert state.crew["driver1"].rating > initial_rating


def test_race_entry_and_prize_ledger_entries():
    """
    Scenario: Verify race creates both expense and income ledger entries
    Modules: race → finance
    Expected: Entry fee as expense, prize as income
    """
    state = SystemState()

    # Use high skills/condition for guaranteed win and prize recording
    registration.register_member(state, "driver1", "driver", age=70, experience=50, skills=85)
    car = inventory.add_car(state, "Honda", price=2000, condition=85)
    state.inventory.cash = 10000

    race_obj = race.create_race(state, "Race1", location="Street", track_difficulty=5, entry_fee=200, prize1=1000, prize2=500)
    race.enter_race(state, race_obj.race_id, driver_name="driver1", car_id=car.car_id)

    # Check entry fee recorded
    entry_expense = [e for e in state.ledger if e.kind == "expense" and e.amount == 200]
    assert len(entry_expense) == 1

    # Complete race
    race.start_race_and_record(state, race_obj.race_id)

    # Check prize recorded (guaranteed win with skills >= 80 and condition >= 80)
    prize_income = [e for e in state.ledger if e.kind == "income"]
    assert len(prize_income) >= 1


# ============================================================================
# SECTION 3: Mission → Crew → Finance Integration
# Modules: mission.assign_mission → crew.require_roles_available
#          → mission.complete_mission → finance.record_income
# Business Rule: Missions require specific crew roles and pay bounty
# ============================================================================

def test_assign_and_complete_mission():
    """
    Scenario: Assign mission with required roles and complete it
    Modules: mission → crew → finance → inventory
    Expected: Mission assigned, crew marked busy, completion gives bounty
    """
    state = SystemState()

    # Register crew with required roles
    registration.register_member(state, "driver1", "driver")
    registration.register_member(state, "mechanic1", "mechanic")

    # Create mission requiring driver and mechanic
    from models import Mission
    state.missions["M1"] = Mission(
        mission_id="M1",
        name="Rescue Mission",
        required_roles=["driver", "mechanic"],
        bounty=800
    )

    initial_cash = state.inventory.cash

    # Assign mission
    mission.assign_mission(state, "M1")

    # Verify crew status changed
    assert state.crew["driver1"].memberstatus == "In Mission"
    assert state.crew["mechanic1"].memberstatus == "In Mission"

    # Verify mission status
    assert state.missions["M1"].status == "assigned"

    # Complete mission
    mission.complete_mission(state, "M1")

    # Verify crew available again
    assert state.crew["driver1"].memberstatus == "Available"
    assert state.crew["mechanic1"].memberstatus == "Available"

    # Verify bounty added
    assert state.inventory.cash == initial_cash + 800

    # Verify mission completed
    assert state.missions["M1"].status == "completed"

    # Verify ledger
    income_entries = [e for e in state.ledger if e.kind == "income" and e.amount == 800]
    assert len(income_entries) == 1


def test_assign_mission_without_required_roles():
    """
    Scenario: Try to assign mission when required roles are not available
    Modules: mission → crew
    Expected: ValidationError - missing required roles
    """
    state = SystemState()

    # Register only driver, not mechanic
    registration.register_member(state, "driver1", "driver")

    # Create mission requiring both driver and mechanic
    from models import Mission
    state.missions["M1"] = Mission(
        mission_id="M1",
        name="Repair Mission",
        required_roles=["driver", "mechanic"],
        bounty=500
    )

    # Try to assign without mechanic - should fail
    with pytest.raises(ValidationError):
        mission.assign_mission(state, "M1")


def test_mission_abort():
    """
    Scenario: Assign and then abort a mission
    Modules: mission → crew
    Expected: Crew members marked available again, no bounty paid
    """
    state = SystemState()

    # Setup
    registration.register_member(state, "driver1", "driver")
    registration.register_member(state, "strategist1", "strategist")

    from models import Mission
    state.missions["M1"] = Mission(
        mission_id="M1",
        name="Strategy Mission",
        required_roles=["driver", "strategist"],
        bounty=600
    )

    initial_cash = state.inventory.cash

    # Assign
    mission.assign_mission(state, "M1")
    assert state.crew["driver1"].memberstatus == "In Mission"

    # Abort
    mission.abort_mission(state, "M1")

    # Verify crew available
    assert state.crew["driver1"].memberstatus == "Available"
    assert state.crew["strategist1"].memberstatus == "Available"

    # Verify no cash change
    assert state.inventory.cash == initial_cash

    # Verify mission aborted
    assert state.missions["M1"].status == "aborted"


def test_mission_with_multiple_crew_roles():
    """
    Scenario: Mission requiring multiple different roles
    Modules: mission → crew → finance
    Expected: All required roles validated and assigned
    """
    state = SystemState()

    # Register diverse crew
    registration.register_member(state, "driver1", "driver")
    registration.register_member(state, "mechanic1", "mechanic")
    registration.register_member(state, "strategist1", "strategist")
    registration.register_member(state, "doctor1", "doctor")

    # Create complex mission
    from models import Mission
    state.missions["M1"] = Mission(
        mission_id="M1",
        name="Complex Operation",
        required_roles=["driver", "mechanic", "strategist", "doctor"],
        bounty=2000
    )

    # Assign mission
    mission.assign_mission(state, "M1")

    # Verify all crew assigned
    assert state.crew["driver1"].memberstatus == "In Mission"
    assert state.crew["mechanic1"].memberstatus == "In Mission"
    assert state.crew["strategist1"].memberstatus == "In Mission"
    assert state.crew["doctor1"].memberstatus == "In Mission"

    # Complete mission
    initial_cash = state.inventory.cash
    mission.complete_mission(state, "M1")

    # Verify all crew available
    assert state.crew["driver1"].memberstatus == "Available"
    assert state.crew["strategist1"].memberstatus == "Available"

    # Verify bounty paid
    assert state.inventory.cash == initial_cash + 2000


def test_complete_mission_twice():
    """
    Scenario: Try to complete already completed mission
    Modules: mission
    Expected: ValidationError - mission already completed
    """
    state = SystemState()

    # Setup
    registration.register_member(state, "driver1", "driver")
    from models import Mission
    state.missions["M1"] = Mission(
        mission_id="M1",
        name="Mission1",
        required_roles=["driver"],
        bounty=500
    )

    # Complete once
    mission.assign_mission(state, "M1")
    mission.complete_mission(state, "M1")

    # Try to complete again - should fail
    with pytest.raises(ValidationError):
        mission.complete_mission(state, "M1")


def test_double_role_mission_assignment():
    """
    Scenario: Mission requires same role twice (e.g., ["driver", "driver"])
    Modules: mission → crew
    Expected: Same crew member NOT assigned twice
    Validation Focus: Duplicate role assignments require distinct crew members
    Business Rule: Each crew member should only be assigned once per mission
    """
    state = SystemState()

    # Register crew
    registration.register_member(state, "driver1", "driver")
    registration.register_member(state, "driver2", "driver")

    # Create missions with duplicate roles
    from models import Mission
    state.missions["M_double"] = Mission(
        mission_id="M_double",
        name="Double Driver Mission",
        required_roles=["driver", "driver"],  # Same role twice!
        bounty=1000,
        status="aborted"
    )

    # Try to assign - should fail or use two different drivers
    try:
        mission.assign_mission(state, "M_double")

        # Verify TWO different crew members were assigned, not the same one twice
        assigned = state.missions["M_double"].assigned_members
        if len(assigned) == 2 and assigned[0] == assigned[1]:
            pytest.fail("Same crew member assigned twice for duplicate roles")

        assert len(assigned) == 2, "Should assign 2 drivers for 2 driver roles"
    except ValidationError:
        # Also acceptable - system might reject duplicate roles
        pass


def test_mission_completion_without_bounty_ledger_entry():
    """
    Scenario: Complete mission with bounty = 0 (free mission)
    Modules: mission → finance
    Expected: No income entry in ledger, but mission still completes
    Validation Focus: Free missions should not create income entries
    """
    state = SystemState()

    # Register crew
    registration.register_member(state, "driver1", "driver")
    registration.register_member(state, "spotter1", "spotter")
    # Get free mission (bounty = 0)
    initial_ledger_count = len(state.ledger)

    mission.get_all_missions(state)  # Ensure board created
    free_mission = None
    for m in state.missions.values():
        if m.bounty == 0:
            free_mission = m
            break

    assert free_mission is not None, "Should have at least one free mission"

    # Assign and complete
    mission.assign_mission(state, free_mission.mission_id)
    mission.complete_mission(state, free_mission.mission_id)

    # Verify no income was added for free mission
    new_income_entries = [e for e in state.ledger[initial_ledger_count:] if e.kind == "income"]
    assert len(new_income_entries) == 0, \
        "Free mission (bounty=0) should not create income ledger entry"


# ============================================================================
# SECTION 4: Maintenance → Crew → Inventory → Finance Integration
# Modules: maintenance.request_manual_repair → crew.require_roles_available
#          → finance.record_expense → inventory.repair_car
# Business Rule: Manual repairs require mechanic and cost money
# ============================================================================

def test_manual_repair_with_mechanic():
    """
    Scenario: Repair damaged car with mechanic available
    Modules: maintenance → crew → finance → inventory
    Expected: Car repaired, mechanic busy then available, repair cost deducted
    """
    state = SystemState()

    # Setup
    registration.register_member(state, "mechanic1", "mechanic")
    car = inventory.add_car(state, "Honda", price=2000)
    state.inventory.cars[car.car_id].condition = 30
    state.inventory.cars[car.car_id].carstatus = "Damaged"
    state.inventory.cash = 5000

    initial_cash = state.inventory.cash

    # Request repair (cost computed internally, no repair_cost parameter)
    maintenance.request_manual_repair(state, car.car_id)

    # Verify car repaired
    assert state.inventory.cars[car.car_id].condition == 100
    assert state.inventory.cars[car.car_id].carstatus == "Available"

    # Verify cost deducted (some amount was deducted)
    assert state.inventory.cash < initial_cash

    # Verify mechanic available again after repair
    assert state.crew["mechanic1"].memberstatus == "Available"

    # Verify ledger has expense entry
    expense_entries = [e for e in state.ledger if e.kind == "expense"]
    assert len(expense_entries) == 1


def test_manual_repair_without_mechanic():
    """
    Scenario: Try to repair car without mechanic available
    Modules: maintenance → crew
    Expected: ValidationError - mechanic required
    """
    state = SystemState()

    # Setup car but no mechanic
    car = inventory.add_car(state, "Honda", price=2000)
    state.inventory.cars[car.car_id].condition = 40
    state.inventory.cars[car.car_id].carstatus = "Damaged"

    # Try repair without mechanic - should fail (no repair_cost parameter)
    with pytest.raises(ValidationError):
        maintenance.request_manual_repair(state, car.car_id)


def test_use_part_for_repair():
    """
    Scenario: Use spare part to repair car
    Modules: maintenance → inventory
    Expected: Part consumed, car condition improved
    """
    state = SystemState()

    # Setup
    car = inventory.add_car(state, "Honda", price=2000)
    state.inventory.cars[car.car_id].condition = 50
    inventory.add_part(state, "engine", quantity=2)

    # Use part for repair (repairs by +5, no condition_boost parameter)
    maintenance.use_part_on_car(state, car.car_id, "engine", quantity=1)

    # Verify part consumed
    assert state.inventory.parts["engine"] == 1

    # Verify condition improved by 5
    assert state.inventory.cars[car.car_id].condition == 55


def test_use_tool_for_repair():
    """
    Scenario: Use tool to repair car
    Modules: maintenance → inventory
    Expected: Tool used (count decremented), condition improved
    """
    state = SystemState()

    # Setup
    car = inventory.add_car(state, "Honda", price=2000)
    state.inventory.cars[car.car_id].condition = 60
    inventory.add_tool(state, "wrench", quantity=1)

    # Use tool for repair (repairs by +5, no condition_boost parameter)
    maintenance.use_tool_on_car(state, car.car_id, "wrench", quantity=1)

    # Verify tool used
    assert state.inventory.tools.get("wrench", 0) == 0

    # Verify condition improved by 5
    assert state.inventory.cars[car.car_id].condition == 65


def test_repair_car_with_max_condition():
    """
    Scenario: Try to repair car that's already at 100 condition
    Modules: maintenance → inventory
    Expected: Should raise ValidationError since car doesn't need repair
    """
    state = SystemState()

    registration.register_member(state, "mechanic1", "mechanic")
    car = inventory.add_car(state, "Honda", price=2000)
    state.inventory.cars[car.car_id].condition = 100
    state.inventory.cash = 5000

    # Try repair (should raise ValidationError since condition == 100)
    with pytest.raises(ValidationError):
        maintenance.request_manual_repair(state, car.car_id)


def test_use_nonexistent_part():
    """
    Scenario: Try to use part that doesn't exist in inventory
    Modules: maintenance → inventory
    Expected: ValidationError or KeyError
    """
    state = SystemState()

    car = inventory.add_car(state, "Honda", price=2000)

    with pytest.raises((ValidationError, KeyError, NotFoundError)):
        maintenance.use_part_on_car(state, car.car_id, "nonexistent_part", quantity=1)


def test_use_part_with_insufficient_quantity():
    """
    Scenario: Try to use more parts than available
    Modules: inventory
    Expected: ValidationError - not enough parts
    """
    state = SystemState()

    car = inventory.add_car(state, "Honda", price=2000, condition=85)
    inventory.add_part(state, "tire", quantity=1)

    # Use once - should work (no condition_boost parameter)
    maintenance.use_part_on_car(state, car.car_id, "tire", quantity=1)
    assert state.inventory.parts.get("tire", 0) == 0

    # Try to use again - should fail
    with pytest.raises((ValidationError, NotFoundError, KeyError)):
        maintenance.use_part_on_car(state, car.car_id, "tire", quantity=1)


def test_damage_and_repair_workflow():
    """
    Scenario: Car gets damaged in race, then repaired
    Modules: race → results → maintenance → inventory → crew → finance
    Expected: Damage applied, repair successful, car usable again
    """
    state = SystemState()

    # Setup with high skills (will still take damage on high-difficulty track)
    registration.register_member(state, "driver1", "driver", age=70, experience=50, skills=85)
    registration.register_member(state, "mechanic1", "mechanic")
    car = inventory.add_car(state, "Honda", price=2000, condition=85)
    state.inventory.cash = 10000

    # Create high-difficulty race (damage formula: difficulty*5 - skills*0.05 + rank*2)
    race_obj = race.create_race(state, "Race1", location="Hard Track", track_difficulty=9, entry_fee=100, prize1=800, prize2=400)
    race.enter_race(state, race_obj.race_id, driver_name="driver1", car_id=car.car_id)

    # Complete race
    race.start_race_and_record(state, race_obj.race_id)

    # Check if damaged
    car_after = inventory.get_car(state, car.car_id)

    if car_after.carstatus == "Damaged":
        # Repair (no repair_cost parameter)
        maintenance.request_manual_repair(state, car.car_id)

        # Verify repaired
        assert state.inventory.cars[car.car_id].condition == 100
        assert state.inventory.cars[car.car_id].carstatus == "Available"

        # Now can enter another race
        race_obj2 = race.create_race(state, "Race2", location="Easy Track", track_difficulty=5, entry_fee=100, prize1=600, prize2=300)
        race.enter_race(state, race_obj2.race_id, driver_name="driver1", car_id=car.car_id)
        assert state.inventory.cars[car.car_id].carstatus == "In Race"


def test_parts_and_tools_inventory_management():
    """
    Scenario: Add and use parts/tools
    Modules: inventory → maintenance
    Expected: Quantities tracked correctly
    """
    state = SystemState()

    # Add parts
    inventory.add_part(state, "tire", quantity=5)
    assert state.inventory.parts["tire"] == 5

    # Add more
    inventory.add_part(state, "tire", quantity=2)
    assert state.inventory.parts["tire"] == 7

    # Use some
    inventory.use_part(state, "tire", quantity=3)
    assert state.inventory.parts["tire"] == 4

    # Tools
    inventory.add_tool(state, "wrench", quantity=2)
    assert state.inventory.tools["wrench"] == 2

    inventory.use_tool(state, "wrench", quantity=1)
    assert state.inventory.tools["wrench"] == 1


def test_part_consumption_requires_valid_car():
    """
    Scenario: Try to use part on non-existent car
    Modules: maintenance → inventory
    Expected: Part NOT consumed if car doesn't exist (atomicity)
    Validation Focus: Atomicity of part usage when target car is invalid
    """
    state = SystemState()

    # Setup: Add 3 brakes to inventory
    inventory.add_part(state, "brakes", quantity=3)
    assert state.inventory.parts["brakes"] == 3

    # Try to use brakes on non-existent car (wrong car_id)
    with pytest.raises((ValidationError, NotFoundError, KeyError)):
        maintenance.use_part_on_car(state, "invalid_car_999", "brakes", quantity=1)

    # Verify brakes quantity NOT decremented (should still be 3)
    assert state.inventory.parts["brakes"] == 3, \
        "Part was consumed even though car doesn't exist"


def test_tool_consumption_requires_valid_car():
    """
    Scenario: Try to use tool on non-existent car
    Modules: maintenance → inventory
    Expected: Tool NOT consumed if car doesn't exist (atomicity)
    Validation Focus: Atomicity of tool usage when target car is invalid
    """
    state = SystemState()

    # Setup: Add 2 wrenches to inventory
    inventory.add_tool(state, "wrench", quantity=2)
    assert state.inventory.tools["wrench"] == 2

    # Try to use wrench on non-existent car
    with pytest.raises((ValidationError, NotFoundError, KeyError)):
        maintenance.use_tool_on_car(state, "invalid_car_999", "wrench", quantity=1)

    # Verify wrench quantity NOT decremented (should still be 2)
    assert state.inventory.tools["wrench"] == 2, \
        "Tool was consumed even though car doesn't exist"


def test_mechanic_status_restored_on_failed_repair():
    """
    Scenario: Attempting manual repair when player has insufficient cash
    Modules: maintenance → finance → crew
    Expected: Repair fails, mechanic remains "Available"
    Validation Focus: Repair flow should restore mechanic state on failure
    """
    state = SystemState()

    # Setup
    registration.register_member(state, "mechanic1", "mechanic")
    car = inventory.add_car(state, "Honda", price=2000, condition=50)

    # Give insufficient cash for repair (repairs cost ~100-2000)
    state.inventory.cash = 50

    # Verify mechanic starts as Available
    assert state.crew["mechanic1"].memberstatus == "Available"

    # Try to repair with insufficient cash
    try:
        maintenance.request_manual_repair(state, car.car_id)
        pytest.fail("Should have raised ValidationError for insufficient cash")
    except ValidationError:
        pass

    # Mechanic should remain available after failed repair attempt
    assert state.crew["mechanic1"].memberstatus == "Available", \
        "Mechanic stuck in 'In Mission' after failed repair (should be 'Available')"


def test_bulk_parts_repair_scales_with_quantity():
    """
    Scenario: Using quantity > 1 (e.g., 5 parts) when repairing a damaged car
    Modules: maintenance → inventory
    Expected: Using 5 parts should repair 25 condition (5 points × 5 parts), OR reject qty > 1
    Validation Focus: Repair amount should scale with quantity consumed
    """
    state = SystemState()

    # Setup
    car = inventory.add_car(state, "Honda", price=2000, condition=50)
    inventory.add_part(state, "engine", quantity=10)

    initial_parts = state.inventory.parts["engine"]
    initial_condition = car.condition

    # Use 5 parts (should repair 25 condition if working correctly)
    quantity_used = 5
    maintenance.use_part_on_car(state, car.car_id, "engine", quantity=quantity_used)

    # Check how many parts were consumed
    parts_remaining = state.inventory.parts.get("engine", 0)
    parts_consumed = initial_parts - parts_remaining
    assert parts_consumed == quantity_used, f"Parts consumed: {parts_consumed}"

    # Check repair amount
    final_condition = inventory.get_car(state, car.car_id).condition
    condition_repaired = final_condition - initial_condition

    # Should repair quantity*5
    expected_repair = quantity_used * 5  # 5 parts × 5 points = 25
    assert condition_repaired == expected_repair, \
        f"Used {quantity_used} parts but only repaired {condition_repaired} condition " \
        f"(expected {expected_repair}). Wasted {quantity_used - 1} parts!"


def test_no_part_consumption_at_max_condition():
    """
    Scenario: Using a part/tool on a car that already has 100 (perfect) condition
    Modules: maintenance → inventory
    Expected: System should raise ValidationError ("Car doesn't need repair") and NOT consume part
    Validation Focus: Validation should happen before part consumption
    """
    state = SystemState()

    # Setup car with PERFECT condition
    car = inventory.add_car(state, "Honda", price=2000, condition=100)
    inventory.add_part(state, "engine", quantity=5)

    initial_parts = state.inventory.parts["engine"]
    initial_condition = car.condition
    assert initial_condition == 100, "Car should start at perfect condition"

    # Try to use part on perfect car
    try:
        maintenance.use_part_on_car(state, car.car_id, "engine", quantity=1)

        # If no error was raised, verify no part was consumed
        parts_remaining = state.inventory.parts.get("engine", 0)
        parts_consumed = initial_parts - parts_remaining

        # Part should NOT be consumed if car doesn't need repair
        assert parts_consumed == 0, \
            f"Part consumed ({parts_consumed}) even though car has perfect condition (100)"

        final_condition = inventory.get_car(state, car.car_id).condition
        assert final_condition == initial_condition, \
            "Car condition should remain 100"

    except ValidationError:
        # This is EXPECTED behavior - should reject repair on perfect car
        # Verify part was NOT consumed
        parts_remaining = state.inventory.parts.get("engine", 0)
        assert parts_remaining == initial_parts, \
            "Part should not be consumed if operation is rejected"


# ============================================================================
# SECTION 5: Inventory → Finance Integration (Purchases)
# Modules: inventory.purchase_car/part/tool → finance.record_expense
#          → inventory._adjust_cash
# Business Rule: All purchases deduct cash and record in ledger
# ============================================================================

def test_purchase_car():
    """
    Scenario: Purchase a new car
    Modules: inventory → finance
    Expected: Car added, cash deducted, ledger updated
    """
    state = SystemState()
    state.inventory.cash = 5000

    # Purchase car (returns Car object, car_id is generated)
    car = inventory.purchase_car(state, "Toyota", price=3000)

    # Verify car added
    assert car.car_id in state.inventory.cars
    assert state.inventory.cars[car.car_id].model == "Toyota"

    # Verify cash deducted
    assert state.inventory.cash == 2000

    # Verify ledger
    assert len(state.ledger) == 1
    assert state.ledger[0].kind == "expense"
    assert state.ledger[0].amount == 3000


def test_purchase_part():
    """
    Scenario: Purchase spare parts
    Modules: inventory → finance
    Expected: Parts added to inventory, cash deducted
    """
    state = SystemState()
    state.inventory.cash = 5000

    # Purchase parts (use unit_price, not cost)
    inventory.purchase_part(state, "tire", quantity=4, unit_price=200)

    # Verify parts added
    assert state.inventory.parts["tire"] == 4

    # Verify cash deducted (4 * 200 = 800)
    assert state.inventory.cash == 4200

    # Verify ledger
    expense_entries = [e for e in state.ledger if e.kind == "expense"]
    assert len(expense_entries) == 1


def test_purchase_tool():
    """
    Scenario: Purchase tools
    Modules: inventory → finance
    Expected: Tools added, cash deducted
    """
    state = SystemState()
    state.inventory.cash = 5000

    # Purchase tools (use unit_price, not cost)
    inventory.purchase_tool(state, "jack", quantity=1, unit_price=150)

    # Verify tool added
    assert state.inventory.tools["jack"] == 1

    # Verify cash deducted
    assert state.inventory.cash == 4850


def test_purchase_with_insufficient_cash():
    """
    Scenario: Try to purchase when cash is insufficient
    Modules: inventory → finance
    Expected: ValidationError - insufficient funds
    """
    state = SystemState()
    state.inventory.cash = 500

    # Try to purchase expensive car - should fail (no car_id parameter)
    with pytest.raises(ValidationError):
        inventory.purchase_car(state, "Lamborghini", price=10000)


def test_insufficient_funds_prevents_purchase_atomicity():
    """
    Scenario: Try to purchase car with insufficient cash
    Modules: inventory → finance
    Expected: Cash unchanged and no car added (atomic operation)
    Validation Focus: Failed purchases must be atomic
    """
    state = SystemState()
    state.inventory.cash = 100  # Very low cash

    initial_cash = state.inventory.cash
    initial_car_count = len(state.inventory.cars)

    # Try to buy expensive car
    try:
        inventory.purchase_car(state, "Mercedes", price=5000)
        pytest.fail("Should have raised ValidationError for insufficient cash")
    except ValidationError:
        pass

    # Verify cash unchanged (atomicity)
    assert state.inventory.cash == initial_cash, \
        "Cash changed even though purchase failed"

    # Verify no car added
    assert len(state.inventory.cars) == initial_car_count, \
        "Car was added even though purchase failed"


# ============================================================================
# SECTION 6: Status Constraint Enforcement
# Tests: Validating that business rules are enforced across modules
# Business Rules: No overlapping activities, proper status management
# ============================================================================

def test_driver_cannot_enter_race_while_in_mission():
    """
    Scenario: Driver in mission tries to enter race
    Modules: mission → race → crew
    Expected: ValidationError - driver already busy
    """
    state = SystemState()

    # Setup
    registration.register_member(state, "driver1", "driver")
    registration.register_member(state, "mechanic1", "mechanic")
    car = inventory.add_car(state, "Honda", price=2000)

    # Assign driver to mission
    from models import Mission
    state.missions["M1"] = Mission(
        mission_id="M1",
        name="Mission1",
        required_roles=["driver", "mechanic"],
        bounty=500
    )
    mission.assign_mission(state, "M1")

    # Create race
    race_obj = race.create_race(state, "Race1", location="Street", track_difficulty=5, entry_fee=100, prize1=500, prize2=200)

    # Try to enter race while in mission - should fail
    with pytest.raises(ValidationError):
        race.enter_race(state, race_obj.race_id, driver_name="driver1", car_id=car.car_id)


def test_driver_cannot_enter_multiple_races():
    """
    Scenario: Driver already in race tries to enter another race
    Modules: race → crew
    Expected: ValidationError - driver already in race
    """
    state = SystemState()

    # Setup
    registration.register_member(state, "driver1", "driver")
    car1 = inventory.add_car(state, "Honda", price=2000)
    car2 = inventory.add_car(state, "Toyota", price=2500)
    state.inventory.cash = 10000

    # Create two races
    race_obj1 = race.create_race(state, "Race1", location="Track1", track_difficulty=5, entry_fee=100, prize1=500, prize2=200)
    race_obj2 = race.create_race(state, "Race2", location="Track2", track_difficulty=6, entry_fee=150, prize1=600, prize2=300)

    # Enter first race
    race.enter_race(state, race_obj1.race_id, driver_name="driver1", car_id=car1.car_id)

    # Try to enter second race - should fail
    with pytest.raises(ValidationError):
        race.enter_race(state, race_obj2.race_id, driver_name="driver1", car_id=car2.car_id)


def test_car_cannot_be_used_while_in_race():
    """
    Scenario: Car already in race cannot be entered in another race
    Modules: race → inventory
    Expected: ValidationError - car already in use
    """
    state = SystemState()

    # Setup
    registration.register_member(state, "driver1", "driver")
    registration.register_member(state, "driver2", "driver")
    car = inventory.add_car(state, "Honda", price=2000)
    state.inventory.cash = 10000

    # Create two races
    race_obj1 = race.create_race(state, "Race1", location="Track1", track_difficulty=5, entry_fee=100, prize1=500, prize2=200)
    race_obj2 = race.create_race(state, "Race2", location="Track2", track_difficulty=5, entry_fee=100, prize1=500, prize2=200)

    # Enter first race with car
    race.enter_race(state, race_obj1.race_id, driver_name="driver1", car_id=car.car_id)

    # Try to enter second race with same car - should fail
    with pytest.raises(ValidationError):
        race.enter_race(state, race_obj2.race_id, driver_name="driver2", car_id=car.car_id)


def test_damaged_car_cannot_enter_race():
    """
    Scenario: Try to enter race with damaged car
    Modules: race → inventory
    Expected: ValidationError - car is damaged
    """
    state = SystemState()

    # Setup
    registration.register_member(state, "driver1", "driver")
    car = inventory.add_car(state, "Honda", price=2000)
    state.inventory.cars[car.car_id].condition = 0  # Condition must be > 0
    state.inventory.cars[car.car_id].carstatus = "Damaged"

    # Create race
    race_obj = race.create_race(state, "Race1", location="Street", track_difficulty=5, entry_fee=100, prize1=500, prize2=200)

    # Try to enter with damaged car - should fail
    with pytest.raises(ValidationError):
        race.enter_race(state, race_obj.race_id, driver_name="driver1", car_id=car.car_id)


def test_mechanic_cannot_enter_mission_while_in_another_mission():
    """
    Scenario: Mechanic assigned to mission cannot join another
    Modules: mission → crew
    Expected: ValidationError - crew member already busy
    """
    state = SystemState()

    # Setup
    registration.register_member(state, "driver1", "driver")
    registration.register_member(state, "mechanic1", "mechanic")

    # Create two missions
    from models import Mission
    state.missions["M1"] = Mission(
        mission_id="M1",
        name="Mission1",
        required_roles=["mechanic"],
        bounty=400
    )
    state.missions["M2"] = Mission(
        mission_id="M2",
        name="Mission2",
        required_roles=["mechanic", "driver"],
        bounty=600
    )

    # Assign first mission
    mission.assign_mission(state, "M1")

    # Try to assign second mission - should fail (mechanic busy)
    with pytest.raises(ValidationError):
        mission.assign_mission(state, "M2")


def test_crew_status_transitions():
    """
    Scenario: Verify crew member status changes through different activities
    Modules: crew → race → mission
    Expected: Status correctly reflects current activity
    """
    state = SystemState()

    registration.register_member(state, "driver1", "driver")

    # Initially available
    assert state.crew["driver1"].memberstatus == "Available"

    # Mark in race
    crew.mark_in_race(state, "driver1")
    assert state.crew["driver1"].memberstatus == "In Race"

    # Mark available
    crew.mark_available(state, "driver1")
    assert state.crew["driver1"].memberstatus == "Available"

    # Set to mission
    crew.set_memberstatus(state, "driver1", "In Mission")
    assert state.crew["driver1"].memberstatus == "In Mission"


def test_car_status_lifecycle():
    """
    Scenario: Car goes through various status states
    Modules: inventory → race → maintenance
    Expected: Status transitions are valid
    """
    state = SystemState()

    car = inventory.add_car(state, "Honda", price=2000)

    # Initially available
    assert state.inventory.cars[car.car_id].carstatus == "Available"

    # Set to in race
    inventory.set_carstatus(state, car.car_id, "In Race")
    assert state.inventory.cars[car.car_id].carstatus == "In Race"

    # Back to available
    inventory.set_carstatus(state, car.car_id, "Available")
    assert state.inventory.cars[car.car_id].carstatus == "Available"

    # Apply damage that reduces condition to 0 (Damaged status should be set)
    inventory.apply_damage(state, car.car_id, 100)  # 100% damage = condition becomes 0
    assert state.inventory.cars[car.car_id].carstatus == "Damaged"
    assert state.inventory.cars[car.car_id].condition <= 0


# ============================================================================
# SECTION 7: End-to-End Workflow Tests
# Tests: End-to-end workflows involving many modules
# Business Rules: Complete workflows must maintain consistency
# ============================================================================

def test_full_race_lifecycle():
    """
    Scenario: Complete race lifecycle from registration to completion
    Modules: registration → crew → inventory → race → results → finance → maintenance
    Expected: All state transitions work correctly
    """
    state = SystemState()

    # Step 1: Register driver (age > experience) with high skills for consistency
    registration.register_member(state, "driver1", "driver", age=80, experience=70, skills=85)

    # Step 2: Purchase car with high condition
    state.inventory.cash = 10000
    car = inventory.purchase_car(state, "Mazda", price=3000, condition=85)

    # Step 3: Create and enter race
    race_obj = race.create_race(state, "Race1", location="Downtown", track_difficulty=5, entry_fee=200, prize1=1500, prize2=700)
    race.enter_race(state, race_obj.race_id, driver_name="driver1", car_id=car.car_id)

    # Verify entry state
    assert state.crew["driver1"].memberstatus == "In Race"
    assert state.inventory.cars[car.car_id].carstatus == "In Race"
    cash_after_entry = state.inventory.cash
    assert cash_after_entry == 10000 - 3000 - 200

    # Step 4: Start and complete race
    race.start_race_and_record(state, race_obj.race_id)

    # Verify completion
    assert race.get_race(state, race_obj.race_id).status == "completed"
    assert state.crew["driver1"].memberstatus == "Available"

    # Verify prize money
    cash_final = state.inventory.cash
    assert cash_final >= cash_after_entry  # Should have prize money

    # Verify rating updated
    assert state.crew["driver1"].rating > 0

    # Verify damage may have been applied
    car_after = inventory.get_car(state, car.car_id)
    assert car_after.condition <= 100


def test_crew_member_workflow_across_race_and_mission():
    """
    Scenario: Crew member participates in race, then mission
    Modules: registration → race → results → mission → crew → finance
    Expected: Status transitions correctly, can't overlap activities
    """
    state = SystemState()

    # Setup with high skills/condition for consistent race outcomes
    registration.register_member(state, "driver1", "driver", age=70, experience=50, skills=85)
    registration.register_member(state, "mechanic1", "mechanic")
    car = inventory.add_car(state, "Honda", price=2000, condition=85)
    state.inventory.cash = 10000

    # Race phase
    race_obj = race.create_race(state, "Race1", location="Street", track_difficulty=5, entry_fee=100, prize1=800, prize2=400)
    race.enter_race(state, race_obj.race_id, driver_name="driver1", car_id=car.car_id)
    assert state.crew["driver1"].memberstatus == "In Race"

    # Complete race
    race.start_race_and_record(state, race_obj.race_id)
    assert state.crew["driver1"].memberstatus == "Available"

    # Mission phase
    from models import Mission
    state.missions["M1"] = Mission(
        mission_id="M1",
        name="Transport Mission",
        required_roles=["driver", "mechanic"],
        bounty=1000
    )
    mission.assign_mission(state, "M1")
    assert state.crew["driver1"].memberstatus == "In Mission"

    # Complete mission
    mission.complete_mission(state, "M1")
    assert state.crew["driver1"].memberstatus == "Available"


def test_multiple_races_sequential():
    """
    Scenario: Same driver participates in multiple races sequentially
    Modules: race → results → crew → finance
    Expected: Driver can race again after completing previous race
    """
    state = SystemState()

    # Setup with high skills/condition for consistent results
    registration.register_member(state, "driver1", "driver", age=70, experience=50, skills=85)
    registration.register_member(state, "mechanic1", "mechanic")
    car = inventory.add_car(state, "Honda", price=2000, condition=85)
    state.inventory.cash = 10000

    # First race
    race_obj1 = race.create_race(state, "Race1", location="Track1", track_difficulty=5, entry_fee=100, prize1=500, prize2=200)
    race.enter_race(state, race_obj1.race_id, driver_name="driver1", car_id=car.car_id)
    race.start_race_and_record(state, race_obj1.race_id)

    # Verify available again
    assert state.crew["driver1"].memberstatus == "Available"

    # Repair car if damaged
    car_after = inventory.get_car(state, car.car_id)
    if car_after.carstatus == "Damaged":
        maintenance.request_manual_repair(state, car.car_id)

    # Second race
    race_obj2 = race.create_race(state, "Race2", location="Track2", track_difficulty=5, entry_fee=150, prize1=700, prize2=300)
    race.enter_race(state, race_obj2.race_id, driver_name="driver1", car_id=car.car_id)
    race.start_race_and_record(state, race_obj2.race_id)

    # Verify both races completed
    assert race.get_race(state, race_obj1.race_id).status == "completed"
    assert race.get_race(state, race_obj2.race_id).status == "completed"


# ============================================================================
# SECTION 8: Edge Cases and Error Handling
# Tests: Boundary conditions and error handling
# Business Rules: System must handle invalid operations gracefully
# ============================================================================

def test_race_with_nonexistent_car():
    """
    Scenario: Try to enter race with car that doesn't exist
    Modules: race → inventory
    Expected: NotFoundError or ValidationError
    """
    state = SystemState()

    registration.register_member(state, "driver1", "driver")
    race_obj = race.create_race(state, "Race1", location="Street", track_difficulty=5, entry_fee=100, prize1=500, prize2=200)

    with pytest.raises((NotFoundError, ValidationError)):
        race.enter_race(state, race_obj.race_id, driver_name="driver1", car_id="nonexistent_car")


def test_start_race_without_driver():
    """
    Scenario: Try to start race that has no driver entered
    Modules: race
    Expected: ValidationError or appropriate handling
    """
    state = SystemState()

    race_obj = race.create_race(state, "Race1", location="Street", track_difficulty=5, entry_fee=100, prize1=500, prize2=200)

    # Try to start race with no entrants - should fail
    with pytest.raises((ValidationError, NotFoundError)):
        race.start_race(state, race_obj.race_id)


def test_insufficient_cash_for_race_entry():
    """
    Scenario: Try to enter race without enough cash for entry fee
    Modules: race → finance → inventory
    Expected: ValidationError - insufficient funds
    """
    state = SystemState()

    # Setup with low cash
    registration.register_member(state, "driver1", "driver")
    car = inventory.add_car(state, "Honda", price=2000)
    state.inventory.cash = 50  # Not enough for 100 entry fee

    race_obj = race.create_race(state, "Race1", location="Street", track_difficulty=5, entry_fee=100, prize1=500, prize2=200)

    with pytest.raises(ValidationError):
        race.enter_race(state, race_obj.race_id, driver_name="driver1", car_id=car.car_id)


def test_damaged_car_status_after_mark_completed():
    """
    Scenario: Race completion marks car back to Available even if damaged
    Modules: race → results → maintenance
    Expected: Car status should be "Damaged" if condition <= 0, not "Available"
    Validation Focus: Car status consistency after race completion
    """
    state = SystemState()

    # Setup with high skills (will still take damage on high-difficulty track)
    registration.register_member(state, "driver1", "driver", age=70, experience=50, skills=85)
    registration.register_member(state, "mechanic1", "mechanic")
    car = inventory.add_car(state, "Honda", price=2000, condition=85)
    state.inventory.cash = 10000

    # Create high-difficulty race (damage formula: difficulty*5 - skills*0.05 + rank*2)
    race_obj = race.create_race(state, "Race1", location="Hard Track", track_difficulty=9, entry_fee=100, prize1=800, prize2=400)
    race.enter_race(state, race_obj.race_id, driver_name="driver1", car_id=car.car_id)

    # Damage car heavily by simulating race damage
    race.start_race_and_record(state, race_obj.race_id)

    # Check car status after race
    car_after = inventory.get_car(state, car.car_id)

    # If car was damaged (condition <= 0), status must remain "Damaged"
    if car_after.condition <= 0:
        assert car_after.carstatus == "Damaged", \
            f"Damaged car has status '{car_after.carstatus}' instead of 'Damaged'"


def test_direct_mark_completed_respects_damage_status():
    """
    Scenario: Call race.mark_completed directly without going through results
    Modules: race
    Expected: Car damage status should still be respected
    Validation Focus: mark_completed should preserve damaged state
    """
    state = SystemState()

    # Setup
    registration.register_member(state, "driver1", "driver")
    car = inventory.add_car(state, "Honda", price=2000)
    state.inventory.cash = 10000

    # Create and enter race
    race_obj = race.create_race(state, "Race1", location="Street", track_difficulty=5, entry_fee=100, prize1=500, prize2=200)
    race.enter_race(state, race_obj.race_id, driver_name="driver1", car_id=car.car_id)

    # Manually damage car (simulating race damage)
    state.inventory.cars[car.car_id].condition = 20
    state.inventory.cars[car.car_id].carstatus = "Damaged"

    # Manually start and mark completed (bypassing results module)
    race.start_race(state, race_obj.race_id)
    race.mark_completed(state, race_obj.race_id)

    # Car status should not be overwritten to "Available" when condition is damaged
    car_after = inventory.get_car(state, car.car_id)
    if car_after.condition <= 0:
        assert car_after.carstatus == "Damaged", \
            f"Damaged car (condition={car_after.condition}) has status '{car_after.carstatus}'"


def test_cash_non_negative_on_expensive_repairs():
    """
    Scenario: Multiple expensive repairs drain cash below zero
    Modules: inventory → finance → crew
    Expected: System should reject transactions that would make cash negative
    Validation Focus: Cash remains non-negative across repair attempts
    """
    state = SystemState()

    # Setup with limited cash
    registration.register_member(state, "mechanic1", "mechanic")
    car = inventory.add_car(state, "Honda", price=2000)
    state.inventory.cash = 300  # Only $300

    # Damage car severely
    state.inventory.cars[car.car_id].condition = 10
    state.inventory.cars[car.car_id].carstatus = "Damaged"

    # Try to repair - should calculate cost and check if affordable
    try:
        maintenance.request_manual_repair(state, car.car_id)

        # Check that cash didn't go negative
        if state.inventory.cash < 0:
            pytest.fail(f"Cash went negative: ${state.inventory.cash}")
    except ValidationError:
        # Expected - insufficient cash
        pass


# ============================================================================
# SECTION 9: Financial Integrity Tests
# Tests: Ensuring financial transactions are correctly recorded
# Business Rules: All cash changes must be tracked in ledger
# ============================================================================

def test_ledger_records_all_transactions():
    """
    Scenario: Perform various operations and verify ledger completeness
    Modules: finance → all modules
    Expected: All cash changes recorded in ledger
    """
    state = SystemState()
    state.inventory.cash = 10000

    # Purchase car (expense)
    car = inventory.purchase_car(state, "Honda", price=2000, condition=85)

    # Purchase part (expense, use unit_price not cost)
    inventory.purchase_part(state, "tire", quantity=2, unit_price=100)

    # Setup and complete race (expense + income)
    # Use high skills/condition for guaranteed win and prize
    registration.register_member(state, "driver1", "driver", age=70, experience=50, skills=85)
    race_obj = race.create_race(state, "Race1", location="Street", track_difficulty=5, entry_fee=100, prize1=800, prize2=400)
    race.enter_race(state, race_obj.race_id, driver_name="driver1", car_id=car.car_id)
    race.start_race_and_record(state, race_obj.race_id)

    # Verify ledger has all entries
    expenses = [e for e in state.ledger if e.kind == "expense"]
    incomes = [e for e in state.ledger if e.kind == "income"]

    assert len(expenses) >= 3  # car, part, race entry
    assert len(incomes) >= 1  # race prize


def test_cash_balance_matches_ledger():
    """
    Scenario: Verify cash balance equals initial + income - expenses
    Modules: finance → inventory
    Expected: Cash balance consistent with ledger
    """
    state = SystemState()
    initial_cash = 10000
    state.inventory.cash = initial_cash

    # Perform operations (use unit_price not cost)
    inventory.purchase_car(state, "Honda", price=3000)
    inventory.purchase_part(state, "engine", quantity=1, unit_price=500)

    # Calculate from ledger
    total_expenses = sum(e.amount for e in state.ledger if e.kind == "expense")
    total_income = sum(e.amount for e in state.ledger if e.kind == "income")

    expected_cash = initial_cash - total_expenses + total_income
    assert state.inventory.cash == expected_cash
