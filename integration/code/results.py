"""Results module.

Responsibilities:
- Simulate race results (1 player driver + 5 dummy drivers)
- Store full leaderboard per race
- Update player rating
- Distribute prize money
- Apply car damage based on track difficulty and performance

Integration points:
- Calls race.mark_completed
- Calls finance.record_income (which updates inventory cash)
- Calls inventory.apply_damage
"""

from __future__ import annotations

import random

from models import SystemState, ValidationError

import crew
import finance
import inventory
import maintenance
import race


def record_race_outcome(state: SystemState, race_id: str, *, notes: str = "") -> list[tuple[str, int, float]]:
    race_obj = race.get_race(state, race_id)

    if race_obj.status != "running":
        raise ValidationError("Race must be running before recording results")

    if not race_obj.driver_name or not race_obj.car_id:
        raise ValidationError("Race must have a driver and car")

    player_name = race_obj.driver_name
    player = crew.get_member_details(state, player_name)
    player_car = inventory.get_car(state, race_obj.car_id)

    participants = race_obj.participants or [player_name]

    # Generate scores.
    scored: list[tuple[str, float]] = []

    for name in participants:
        if name == player_name:
            skills = player.skills
            experience = player.experience
            car_condition = player_car.condition
        else:
            # Dummy stats are generated only during the race.
            skills = random.randint(40, 95)
            experience = random.randint(0, 30)
            car_condition = random.randint(55, 100)

        rand_component = random.uniform(0.15, 0.30) * 100
        score = 0.5 * skills + 0.3 * experience + 0.2 * car_condition + rand_component
        scored.append((name, float(score)))

    # Boost rule (player advantage when above threshold, most of the time).
    if player.skills >= 80 and player.experience >= 10 and player_car.condition >= 80:
        if random.random() < 0.75:
            max_dummy = max(s for n, s in scored if n != player_name)
            player_score = next(s for n, s in scored if n == player_name)
            boosted = max(player_score + random.uniform(5.0, 15.0), max_dummy + random.uniform(0.5, 3.0))
            scored = [(n, (boosted if n == player_name else s)) for n, s in scored]

    # Sort and rank.
    scored.sort(key=lambda x: x[1], reverse=True)
    leaderboard: list[tuple[str, int, float]] = [(name, idx + 1, score) for idx, (name, score) in enumerate(scored)]

    # Persist full leaderboard.
    state.race_results[race_id] = leaderboard

    # Mark completed (also frees car).
    race.mark_completed(state, race_id)

    # Apply rating updates to player.
    player_rank = next(rank for (name, rank, _score) in leaderboard if name == player_name)
    rating_delta = {1: 20, 2: 15, 3: 10, 4: 8, 5: 5}.get(player_rank, 0)
    player.rating += rating_delta

    # Prize money (player only).
    if player_rank == 1 and race_obj.prize > 0:
        finance.record_income(state, race_obj.prize, reason=f"Prize (1st) for race: {race_obj.name}")
    elif player_rank == 2 and race_obj.second_prize > 0:
        finance.record_income(state, race_obj.second_prize, reason=f"Prize (2nd) for race: {race_obj.name}")

    # Car damage (player car only).
    damage = race_obj.track_difficulty * 5 - (player.skills * 0.05) + (player_rank * 2)
    damage_percent = int(round(max(0.0, min(30.0, damage))))
    maintenance.process_damage(state, race_obj.car_id, damage_percent)

    # Release driver back to available.
    crew.mark_available(state, player_name)

    # Ensure carstatus consistent with condition.
    car = inventory.get_car(state, race_obj.car_id)
    if car.condition <= 0:
        inventory.set_carstatus(state, race_obj.car_id, "Damaged")
    else:
        inventory.set_carstatus(state, race_obj.car_id, "Available")

    return leaderboard
