"""Results module.

Responsibilities:
- Record race outcomes
- Update rankings
- Distribute prize money
- Trigger maintenance if the car is damaged

Integration points:
- Calls race.mark_completed
- Calls finance.record_income (which updates inventory cash)
- Calls maintenance.process_race_damage
"""

from __future__ import annotations

from models import RaceOutcome, SystemState, ValidationError

import finance
import maintenance
import race


def record_race_outcome(
    state: SystemState,
    race_id: str,
    *,
    position: int,
    damage_percent: int,
    notes: str = "",
) -> RaceOutcome:
    race_obj = race.get_race(state, race_id)

    if race_obj.status != "running":
        raise ValidationError("Race must be running before recording results")
    if position < 1:
        raise ValidationError("Position must be >= 1")

    prize_won = race_obj.prize if position == 1 else 0

    # Mark completed + release car.
    race.mark_completed(state, race_id)

    # Apply race damage and trigger maintenance if needed.
    if race_obj.car_id:
        maintenance.process_race_damage(state, race_obj.car_id, damage_percent)

    # Pay prize money (updates inventory cash via finance -> inventory).
    if prize_won > 0:
        finance.record_income(state, prize_won, reason=f"Prize for race: {race_obj.name}")

    # Update rankings: simple points system.
    driver = race_obj.driver_name
    if driver:
        points = _points_for_position(position)
        state.rankings[driver] = state.rankings.get(driver, 0) + points

    outcome = RaceOutcome(
        outcome_id=state.new_id("out"),
        race_id=race_id,
        position=position,
        prize_won=prize_won,
        damage_percent=damage_percent,
        notes=notes,
    )
    state.outcomes.append(outcome)
    return outcome


def _points_for_position(position: int) -> int:
    if position == 1:
        return 10
    if position == 2:
        return 6
    if position == 3:
        return 3
    return 1
