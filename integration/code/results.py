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


def _compute_leaderboard(state: SystemState, race_id: str) -> list[tuple[str, int, float]]:
    race_obj = race.get_race(state, race_id)
    if not race_obj.driver_name or not race_obj.car_id:
        raise ValidationError("Race must have a driver and car")

    player_name = race_obj.driver_name
    player = crew.get_member_details(state, player_name)
    player_car = inventory.get_car(state, race_obj.car_id)

    participants = race_obj.participants or [player_name]

    scored: list[tuple[str, float]] = []
    for name in participants:
        if name == player_name:
            skills = player.skills
            experience = player.experience
            car_condition = player_car.condition
        else:
            skills = random.randint(40, 95)
            experience = random.randint(0, 30)
            car_condition = random.randint(55, 100)

        rand_component = random.uniform(0.15, 0.30) * 100
        score = 0.5 * skills + 0.3 * experience + 0.2 * car_condition + rand_component
        scored.append((name, float(score)))

    if player.skills >= 80 and player.experience >= 10 and player_car.condition >= 80:
        if random.random() < 0.75:
            max_dummy = max(s for n, s in scored if n != player_name)
            player_score = next(s for n, s in scored if n == player_name)
            boosted = max(player_score + random.uniform(5.0, 15.0), max_dummy + random.uniform(0.5, 3.0))
            scored = [(n, (boosted if n == player_name else s)) for n, s in scored]

    scored.sort(key=lambda x: x[1], reverse=True)
    leaderboard: list[tuple[str, int, float]] = [(name, idx + 1, score) for idx, (name, score) in enumerate(scored)]
    return leaderboard


def _update_rating(state: SystemState, leaderboard: list[tuple[str, int, float]]) -> None:
    deltas = {1: 20, 2: 15, 3: 10, 4: 8, 5: 5}
    for name, rank, _score in leaderboard:
        member = state.crew.get(name)
        if not member:
            continue
        member.rating += deltas.get(rank, 0)


def _handle_prizes(state: SystemState, race_id: str, leaderboard: list[tuple[str, int, float]]) -> None:
    race_obj = race.get_race(state, race_id)

    for name, rank, _score in leaderboard:
        if rank not in {1, 2}:
            continue
        if name not in state.crew:
            continue

        amount = race_obj.prize if rank == 1 else race_obj.second_prize
        if amount <= 0:
            continue
        finance.record_income(state, amount, reason=f"Prize ({rank}) for race: {race_obj.name}")


def _apply_damage(state: SystemState, race_id: str, leaderboard: list[tuple[str, int, float]]) -> None:
    race_obj = race.get_race(state, race_id)
    if not race_obj.driver_name or not race_obj.car_id:
        return

    player = state.crew.get(race_obj.driver_name)
    if not player:
        return

    player_rank = next(rank for (name, rank, _score) in leaderboard if name == race_obj.driver_name)

    damage = race_obj.track_difficulty * 5 - (player.skills * 0.05) + (player_rank * 2)
    damage_percent = int(round(max(0.0, min(30.0, damage))))
    maintenance.process_damage(state, race_obj.car_id, damage_percent)


def record_race_outcome(state: SystemState, race_id: str, *, notes: str = "") -> list[tuple[str, int, float]]:
    race_obj = race.get_race(state, race_id)

    if race_obj.status != "running":
        raise ValidationError("Race must be running before recording results")

    leaderboard = _compute_leaderboard(state, race_id)

    state.race_results[race_id] = leaderboard

    race.mark_completed(state, race_id)

    _update_rating(state, leaderboard)
    _handle_prizes(state, race_id, leaderboard)
    _apply_damage(state, race_id, leaderboard)

    # Release real crew members back to Available.
    for name, _rank, _score in leaderboard:
        if name in state.crew:
            crew.mark_available(state, name)

    # Ensure carstatus consistent with condition for the player's car.
    if race_obj.car_id:
        car = inventory.get_car(state, race_obj.car_id)
        inventory.set_carstatus(state, race_obj.car_id, "Damaged" if car.condition <= 0 else "Available")

    return leaderboard
