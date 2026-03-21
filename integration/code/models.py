"""Shared models and exceptions for StreetRace Manager.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---- Exceptions ----


class StreetRaceError(Exception):
    """Base error for StreetRace Manager."""


class ValidationError(StreetRaceError):
    """Raised when a business rule is violated."""


class NotFoundError(StreetRaceError):
    """Raised when an entity does not exist in state."""


# ---- Models ----


@dataclass
class CrewMember:
    name: str
    role: Optional[str] = None  # e.g., driver, mechanic, strategist
    skill_level: int = 1
    active: bool = True


@dataclass
class Car:
    car_id: str
    model: str
    condition: int = 100  # 0..100
    available: bool = True


@dataclass
class Inventory:
    cash: int = 0
    cars: Dict[str, Car] = field(default_factory=dict)
    parts: Dict[str, int] = field(default_factory=dict)
    tools: Dict[str, int] = field(default_factory=dict)


@dataclass
class Race:
    race_id: str
    name: str
    entry_fee: int
    prize: int
    driver_name: Optional[str] = None
    car_id: Optional[str] = None
    status: str = "created"  # created -> scheduled -> running -> completed


@dataclass
class RaceOutcome:
    outcome_id: str
    race_id: str
    position: int
    prize_won: int
    damage_percent: int
    notes: str = ""


@dataclass
class Mission:
    mission_id: str
    name: str
    required_roles: List[str]
    assigned_members: List[str] = field(default_factory=list)
    status: str = "planned"  #planned -> active -> completed | failed


@dataclass
class LedgerEntry:
    entry_id: str
    kind: str  # income | expense
    amount: int
    reason: str


@dataclass
class SystemState:
    """In-memory state container passed between modules.

    For making integration-testing easy: tests can build state, call module
    functions, and assert outcomes without hidden globals.
    """

    crew: Dict[str, CrewMember] = field(default_factory=dict)  # key = name
    inventory: Inventory = field(default_factory=Inventory)

    races: Dict[str, Race] = field(default_factory=dict)
    outcomes: List[RaceOutcome] = field(default_factory=list)

    missions: Dict[str, Mission] = field(default_factory=dict)
    ledger: List[LedgerEntry] = field(default_factory=list)

    rankings: Dict[str, int] = field(default_factory=dict)  # driver_name -> points

    _counters: Dict[str, int] = field(default_factory=dict, repr=False)

    def new_id(self, prefix: str) -> str:
        next_value = self._counters.get(prefix, 0) + 1
        self._counters[prefix] = next_value
        return f"{prefix}-{next_value:04d}"
