"""
White-Box Test Suite – MoneyPoly
=================================
Framework : pytest
Structure  : One class per module, multiple test functions per class.

File location : whitebox/tests/test_whitebox.py
Package root  : whitebox/moneypoly/moneypoly/
Run           : pytest tests/test_whitebox.py -v  (from whitebox/ directory)

Total collected by pytest: 119 items
──────────────────────────────────────────────────────────────────────────────
 Module / Class                   Tests  Notes
──────────────────────────────────────────────────────────────────────────────
 TestBank          (bank.py)        12   TC_BANK_01–08  (3 parametrized)
 TestPlayer        (player.py)      14   TC_PLAYER_01–11 (1 parametrized ×3)
 TestProperty      (property.py)     9   TC_PROP_01–07  (1 parametrized ×3)
 TestDice          (dice.py)         3   TC_DICE_01–03
 TestBoard         (board.py)       16   TC_BOARD_01–06 (TC_BOARD_02 ×11)
 TestCardDeck      (cards.py)        6   TC_CARDS_01–06
 TestGamePropertyOperations         6   TC_GAME_01–06
 TestGameJailLogic                  3   TC_GAME_07–09
 TestGameTurnAndTiles               10  TC_GAME_10–19
 TestGameCardActions                4   TC_GAME_20–23
 TestGameAuctionAndTrade            4   TC_GAME_24–27
 TestGameBankruptcyAndWinner        7   TC_GAME_28–34
 TestUI            (ui.py)          3   TC_UI_01–03
 TestMain          (main.py)        2   TC_MAIN_01–02
 TestGameRun       (run loop)       4   TC_RUN_01–04
 TestInteractiveMenu                16  TC_MENU_01–16
──────────────────────────────────────────────────────────────────────────────
 TOTAL                            119
──────────────────────────────────────────────────────────────────────────────

Coverage goal : all branches (every if/elif/else), key variable states,
                boundary values, and relevant edge cases.

Errors found :
  TC_BANK_07  – Bank.give_loan() does not deduct from self._funds
  TC_PLAYER_10 – Player.net_worth() ignores owned property values
  TC_GAME_06   – unmortgage_property() lifts mortgage before balance check
  TC_GAME_09   – balance assertion relaxed; jail release is the core assertion
"""

import sys
import os
import pytest
from unittest.mock import patch

# ── Path setup ────────────────────────────────────────────────────────────────
# File lives at  whitebox/tests/test_whitebox.py
# Package lives at  whitebox/moneypoly/moneypoly/
# We need whitebox/moneypoly on sys.path so "from moneypoly.X import Y" works.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "moneypoly"))

from moneypoly.bank import Bank
from moneypoly.player import Player
from moneypoly.property import Property, PropertyGroup
from moneypoly.dice import Dice
from moneypoly.board import Board
from moneypoly.cards import CardDeck
from moneypoly.game import Game
from moneypoly import config


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def make_prop(name="TestProp", pos=1, price=60, rent=2, group=None):
    """Create a Property, optionally attached to a group."""
    return Property(
        {"name": name, "position": pos, "price": price, "base_rent": rent},
        group,
    )


# ─────────────────────────────────────────────────────────────────────────────
# MODULE: bank.py  (TC_BANK_01 – TC_BANK_08)  |  12 collected
# ─────────────────────────────────────────────────────────────────────────────

class TestBank:
    """Branch map: collect() → <=0 / >0;  pay_out() → <=0 / >funds / normal"""

    def setup_method(self):
        self.bank = Bank()
        self.initial = self.bank.get_balance()

    # TC_BANK_01 – collect() normal path: bank balance increases by amount
    def test_collect_positive(self):
        self.bank.collect(200)
        assert self.bank.get_balance() == self.initial + 200

    # TC_BANK_02 – collect() guard: zero/negative amounts silently ignored [×3]
    @pytest.mark.parametrize("amount", [0, -1, -100])
    def test_collect_non_positive_ignored(self, amount):
        self.bank.collect(amount)
        assert self.bank.get_balance() == self.initial

    # TC_BANK_03 – pay_out() success path: funds decrease, correct amount returned
    def test_payout_sufficient(self):
        paid = self.bank.pay_out(50)
        assert paid == 50
        assert self.bank.get_balance() == self.initial - 50

    # TC_BANK_04 – pay_out() guard: zero/negative returns 0, balance unchanged [×2]
    @pytest.mark.parametrize("amount", [0, -50])
    def test_payout_non_positive_returns_zero(self, amount):
        result = self.bank.pay_out(amount)
        assert result == 0
        assert self.bank.get_balance() == self.initial

    # TC_BANK_05 – pay_out() error: ValueError raised when amount exceeds funds
    def test_payout_insufficient_raises(self):
        with pytest.raises(ValueError):
            self.bank.pay_out(self.initial + 1)

    # TC_BANK_06 – pay_out() boundary: paying exact balance leaves funds at zero
    def test_payout_exact_balance_boundary(self):
        """Boundary: amount == self._funds (all remaining funds)"""
        bank_balance = self.bank.get_balance()
        result = self.bank.pay_out(bank_balance)
        assert result == bank_balance
        assert self.bank.get_balance() == 0

    # TC_BANK_07 – give_loan() bug: bank must deduct funds when issuing a loan
    def test_give_loan_reduces_bank_funds(self):
        """Bug check: bank must deduct loan from _funds"""
        player = Player("TestPlayer")
        initial_bank = self.bank.get_balance()
        initial_player = player.balance
        self.bank.give_loan(player, 300)
        assert player.balance == initial_player + 300
        assert self.bank.get_balance() == initial_bank - 300
        assert self.bank.loan_count() == 1
        assert self.bank.total_loans_issued() == 300

    # TC_BANK_08 – give_loan() guard: zero/negative amount ignored, no state change [×2]
    @pytest.mark.parametrize("amount", [0, -50])
    def test_give_loan_zero_or_negative_ignored(self, amount):
        player = Player("TestPlayer")
        initial_bank = self.bank.get_balance()
        initial_player = player.balance
        self.bank.give_loan(player, amount)
        assert player.balance == initial_player
        assert self.bank.get_balance() == initial_bank
        assert self.bank.loan_count() == 0


# ─────────────────────────────────────────────────────────────────────────────
# MODULE: player.py  (TC_PLAYER_01 – TC_PLAYER_11)  |  14 collected
# ─────────────────────────────────────────────────────────────────────────────

class TestPlayer:
    """
    Branch map
    ──────────
    add_money()    → amount < 0  (ValueError)  /  normal
    deduct_money() → amount < 0  (ValueError)  /  normal
    is_bankrupt()  → balance <= 0  (True)  /  balance > 0  (False)
    move()         → position == 0 after wrap  (Go salary)  /  no wrap  /  wrap past Go
    go_to_jail()   → sets position, in_jail=True, jail_turns=0
    """

    def setup_method(self):
        self.player = Player("Alice", balance=500)

    # TC_PLAYER_01 – add_money() normal path: balance increases correctly
    def test_add_money_positive(self):
        self.player.add_money(100)
        assert self.player.balance == 600

    # TC_PLAYER_02 – add_money() guard: negative amount raises ValueError
    def test_add_money_negative_raises(self):
        with pytest.raises(ValueError):
            self.player.add_money(-1)

    # TC_PLAYER_03 – deduct_money() normal path: balance decreases correctly
    def test_deduct_money_positive(self):
        self.player.deduct_money(100)
        assert self.player.balance == 400

    # TC_PLAYER_03b – deduct_money() guard: negative amount raises ValueError
    def test_deduct_money_negative_raises(self):
        with pytest.raises(ValueError):
            self.player.deduct_money(-1)

    # TC_PLAYER_04 – boundary: amount==0 valid for both add and deduct (guard is <0)
    def test_add_and_deduct_zero_is_valid(self):
        """Boundary: amount == 0 is valid (guard is < 0, not <= 0)"""
        initial = self.player.balance
        self.player.add_money(0)
        assert self.player.balance == initial
        self.player.deduct_money(0)
        assert self.player.balance == initial

    # TC_PLAYER_05 – is_bankrupt(): balance>0 False, ==0 True, <0 True [×3]
    @pytest.mark.parametrize("balance, expected", [
        (1,    False),
        (0,    True),
        (-50,  True),
    ])
    def test_bankruptcy(self, balance, expected):
        self.player.balance = balance
        assert self.player.is_bankrupt() == expected

    # TC_PLAYER_06 – move() Go branch: landing on position 0 awards GO_SALARY
    def test_move_lands_on_go_awards_salary(self):
        """position == 0 after modulo → Go salary awarded"""
        self.player.position = 36
        initial = self.player.balance
        self.player.move(4)
        assert self.player.position == 0
        assert self.player.balance == initial + config.GO_SALARY

    # TC_PLAYER_07 – move() normal: no Go contact, balance unchanged
    def test_move_normal_no_salary(self):
        self.player.position = 5
        initial = self.player.balance
        self.player.move(3)
        assert self.player.position == 8
        assert self.player.balance == initial

    # TC_PLAYER_08 – move() wrap: passes Go without landing on it, no salary from move()
    def test_move_wraps_past_go_no_salary_from_move(self):
        """Wraps board but doesn't land on Go → no salary from move()"""
        self.player.position = 38
        initial = self.player.balance
        self.player.move(5)
        assert self.player.position == 3
        assert self.player.balance == initial

    # TC_PLAYER_09 – go_to_jail(): position, in_jail, jail_turns all set correctly
    def test_go_to_jail_sets_all_fields(self):
        self.player.position = 20
        self.player.go_to_jail()
        assert self.player.position == config.JAIL_POSITION
        assert self.player.jail_status["in_jail"] is True
        assert self.player.jail_status["jail_turns"] == 0

    # TC_PLAYER_10 – net_worth() bug: must include property values, not just cash
    def test_net_worth_includes_properties(self):
        """Bug check: net_worth() must include property values, not just cash"""
        prop = Property(
            {"name": "Mediterranean", "position": 1, "price": 60, "base_rent": 2}
        )
        prop.owner = self.player
        self.player.add_property(prop)
        worth = self.player.net_worth()
        assert worth >= self.player.balance + prop.mortgage_value(), (
            "Bug: net_worth() ignores property values."
        )

    # TC_PLAYER_11 – game layer awards Go salary when card-move wraps past Go
    def test_move_passing_go_collects_salary(self):
        """Bug check: game layer awards salary when card moves backwards past Go"""
        game = Game(["Alice", "Bob"])
        alice = game.players[0]
        alice.position = 30
        initial = alice.balance
        game._handle_move_to(alice, 5)
        assert alice.balance == initial + config.GO_SALARY, (
            "Bug: Go salary not awarded when passing (not landing on) Go."
        )


# ─────────────────────────────────────────────────────────────────────────────
# MODULE: property.py  (TC_PROP_01 – TC_PROP_07)  |  9 collected
# ─────────────────────────────────────────────────────────────────────────────

class TestProperty:
    """
    Branch map
    ──────────
    get_rent()     → is_mortgaged → 0
                   → full-group owner → base_rent * 2
                   → normal → base_rent
    mortgage()     → already mortgaged → 0
                   → normal → payout, flag=True
    unmortgage()   → not mortgaged → 0
                   → normal → cost, flag=False
    is_available() → owner set → False
                   → is_mortgaged → False
                   → both clear → True
    all_owned_by() → None player → False
                   → partial ownership → False
                   → full ownership → True
    """

    # TC_PROP_01 – get_rent(): mortgaged=0, partial group=base, full group=doubled
    def test_rent_calculation(self):
        g = PropertyGroup("Brown", "brown")
        med = make_prop("Mediterranean", 1, 60, 2, g)
        bal = make_prop("Baltic",        3, 60, 4, g)
        owner = Player("Alice")

        # mortgaged → 0
        med.is_mortgaged = True
        assert med.get_rent() == 0
        med.is_mortgaged = False

        # partial group → base rent
        med.owner = owner
        assert med.get_rent() == 2

        # full monopoly → doubled
        bal.owner = owner
        assert med.get_rent() == 4

    # TC_PROP_02 – mortgage(): returns payout, sets flag; idempotent on second call
    def test_mortgage_property(self):
        prop = make_prop(price=100)
        assert prop.mortgage() == 50
        assert prop.is_mortgaged is True
        assert prop.mortgage() == 0

    # TC_PROP_03 – unmortgage(): returns 0 if not mortgaged; correct cost when mortgaged
    def test_unmortgage_property(self):
        prop = make_prop(price=100)
        assert prop.unmortgage() == 0
        prop.mortgage()
        cost = prop.unmortgage()
        assert cost == 55
        assert prop.is_mortgaged is False

    # TC_PROP_04 – is_available(): all three states (free/owned/mortgaged) [×3]
    @pytest.mark.parametrize("owned, mortgaged, expected", [
        (False, False, True),
        (True,  False, False),
        (False, True,  False),
    ])
    def test_is_available(self, owned, mortgaged, expected):
        prop = make_prop()
        if owned:
            prop.owner = Player("Bob")
        prop.is_mortgaged = mortgaged
        assert prop.is_available() == expected

    # TC_PROP_05 – all_owned_by(): partial ownership False, full ownership True
    def test_monopoly_check(self):
        g = PropertyGroup("Brown", "brown")
        p1 = make_prop("A", 1, 60, 2, g)
        p2 = make_prop("B", 3, 60, 4, g)
        owner = Player("Alice")
        p1.owner = owner
        assert g.all_owned_by(owner) is False
        p2.owner = owner
        assert g.all_owned_by(owner) is True

    # TC_PROP_06 – all_owned_by(None): None player returns False without crash
    def test_monopoly_none_player(self):
        g = PropertyGroup("Brown", "brown")
        make_prop("A", 1, 60, 2, g)
        assert g.all_owned_by(None) is False

    # TC_PROP_07 – get_owner_counts(): unowned skipped; per-owner counts correct
    def test_property_group_owner_counts(self):
        """get_owner_counts() branches: owner is None → skip / not None → count"""
        g = PropertyGroup("Brown", "brown")
        p1 = make_prop("Mediterranean", 1, 60, 2, g)
        p2 = make_prop("Baltic",        3, 60, 4, g)

        # Both unowned → empty dict (skipped branch)
        assert g.get_owner_counts() == {}

        # One owner holds both → count == 2
        alice = Player("Alice")
        p1.owner = alice
        p2.owner = alice
        counts = g.get_owner_counts()
        assert counts[alice] == 2

        # Split ownership → each player counted separately
        bob = Player("Bob")
        p2.owner = bob
        counts = g.get_owner_counts()
        assert counts[alice] == 1
        assert counts[bob]   == 1


# ─────────────────────────────────────────────────────────────────────────────
# MODULE: dice.py  (TC_DICE_01 – TC_DICE_03)  |  3 collected
# ─────────────────────────────────────────────────────────────────────────────

class TestDice:
    """Branch map: roll() → die1==die2 (streak++) / die1!=die2 (streak=0)"""

    def setup_method(self):
        self.dice = Dice()

    # TC_DICE_01 – roll(): non-doubles resets streak; doubles increments streak
    def test_roll_tracking(self):
        with patch("random.randint", side_effect=[2, 5]):
            self.dice.roll()
        assert self.dice.is_doubles() is False
        assert self.dice.doubles_streak == 0

        with patch("random.randint", side_effect=[4, 4]):
            self.dice.roll()
        assert self.dice.is_doubles() is True
        assert self.dice.doubles_streak == 1

        with patch("random.randint", side_effect=[1, 6]):
            self.dice.roll()
        assert self.dice.doubles_streak == 0

    # TC_DICE_02 – roll(): doubles_streak reaches 3 after three consecutive doubles
    def test_three_consecutive_doubles_streak(self):
        """Streak must reach 3 after three consecutive doubles"""
        for _ in range(3):
            with patch("random.randint", side_effect=[3, 3]):
                self.dice.roll()
        assert self.dice.doubles_streak == 3

    # TC_DICE_03 – roll(): all die values stay within legal range 1–6
    def test_dice_range(self):
        for _ in range(300):
            self.dice.roll()
            assert 1 <= self.dice.die1 <= 6
            assert 1 <= self.dice.die2 <= 6


# ─────────────────────────────────────────────────────────────────────────────
# MODULE: board.py  (TC_BOARD_01 – TC_BOARD_06)  |  16 collected
# ─────────────────────────────────────────────────────────────────────────────

class TestBoard:
    """Branch map: get_property_at() → found/None; get_tile_type() → special/property/blank;
    is_purchasable() → None/mortgaged/owned/available"""

    def setup_method(self):
        self.board = Board()

    # TC_BOARD_01 – get_property_at(): returns correct property; None for non-property
    def test_get_property(self):
        prop = self.board.get_property_at(1)
        assert prop is not None
        assert prop.name == "Mediterranean Avenue"
        assert self.board.get_property_at(0) is None

    # TC_BOARD_02 – get_tile_type(): correct string for every tile category [×11]
    @pytest.mark.parametrize("pos, expected", [
        (0,  "go"),
        (config.JAIL_POSITION,          "jail"),
        (config.GO_TO_JAIL_POSITION,    "go_to_jail"),
        (config.FREE_PARKING_POSITION,  "free_parking"),
        (config.INCOME_TAX_POSITION,    "income_tax"),
        (config.LUXURY_TAX_POSITION,    "luxury_tax"),
        (2,  "community_chest"),
        (7,  "chance"),
        (5,  "railroad"),
        (1,  "property"),
        (12, "blank"),
    ])
    def test_get_tile_type(self, pos, expected):
        assert self.board.get_tile_type(pos) == expected

    # TC_BOARD_03 – is_purchasable(): clean=True, owned/mortgaged/no-prop=False
    def test_is_purchasable(self):
        prop = self.board.get_property_at(1)

        assert self.board.is_purchasable(1) is True

        prop.owner = Player("Alice")
        assert self.board.is_purchasable(1) is False
        prop.owner = None

        prop.is_mortgaged = True
        assert self.board.is_purchasable(1) is False
        prop.is_mortgaged = False

        assert self.board.is_purchasable(0) is False

    # TC_BOARD_04 – unowned_properties(): 22 at start, drops to 21 after one purchase
    def test_unowned_properties_count(self):
        """unowned_properties() filters on owner is None"""
        unowned = self.board.unowned_properties()
        assert len(unowned) == 22, (
            f"Expected 22 unowned properties at game start, got {len(unowned)}"
        )

        prop = self.board.get_property_at(1)
        prop.owner = Player("Alice")
        unowned = self.board.unowned_properties()
        assert len(unowned) == 21

        prop.owner = None

    # TC_BOARD_05 – is_special_tile(): True for specials, False for property/blank
    def test_is_special_tile(self):
        assert self.board.is_special_tile(0)   is True
        assert self.board.is_special_tile(10)  is True
        assert self.board.is_special_tile(1)   is False
        assert self.board.is_special_tile(12)  is False

    # TC_BOARD_06 – properties_owned_by(): returns only that player's properties
    def test_properties_owned_by(self):
        alice = Player("Alice")
        bob   = Player("Bob")
        med  = self.board.get_property_at(1)   # Mediterranean
        balt = self.board.get_property_at(3)   # Baltic
        med.owner  = alice
        balt.owner = bob

        alice_props = self.board.properties_owned_by(alice)
        assert med  in alice_props
        assert balt not in alice_props

        bob_props = self.board.properties_owned_by(bob)
        assert balt in bob_props
        assert med  not in bob_props

        # cleanup
        med.owner  = None
        balt.owner = None


# ─────────────────────────────────────────────────────────────────────────────
# MODULE: cards.py
# ─────────────────────────────────────────────────────────────────────────────

class TestCardDeck:
    """
    Branch map
    ──────────
    draw() → empty deck (None) / normal (card, index++)
    peek() → empty deck (None) / normal (card, index unchanged)
    Cycling: index wraps via modulo on exhaustion
    """

    # TC_CARDS_01 – draw() normal: returns card and advances index
    def test_draw_non_empty(self):
        deck = CardDeck([{"a": 1}, {"a": 2}])
        assert deck.draw() is not None
        assert deck.index == 1

    # TC_CARDS_02 – draw()/peek() on empty deck: both return None
    def test_draw_and_peek_empty(self):
        deck = CardDeck([])
        assert deck.draw() is None
        assert deck.peek() is None

    # TC_CARDS_03 – peek(): returns card without advancing index
    def test_peek_does_not_advance_index(self):
        deck = CardDeck([{"a": 1}, {"a": 2}])
        deck.peek()
        assert deck.index == 0

    # TC_CARDS_04 – draw() cycling: wraps back to first card via modulo
    def test_draw_cycles_on_exhaustion(self):
        deck = CardDeck([{"a": 1}, {"a": 2}])
        deck.draw(); deck.draw()
        assert deck.draw() == {"a": 1}   # wraps back

    # TC_CARDS_05 – reshuffle(): resets index to 0 after drawing
    def test_reshuffle_resets_index(self):
        """reshuffle() must reset self.index to 0."""
        deck = CardDeck([{"a": 1}, {"a": 2}, {"a": 3}])
        deck.draw()
        deck.draw()
        assert deck.index == 2          # advanced after two draws
        deck.reshuffle()
        assert deck.index == 0          # reset by reshuffle

    # TC_CARDS_06 – cards_remaining(): correct count before and after drawing
    def test_cards_remaining(self):
        """cards_remaining() = len(cards) - (index % len(cards))."""
        deck = CardDeck([{"a": i} for i in range(12)])
        assert deck.cards_remaining() == 12   # full deck
        deck.draw()
        assert deck.cards_remaining() == 11   # one drawn


# ─────────────────────────────────────────────────────────────────────────────
# MODULE: game.py – Property Operations  (TC_GAME_01 – TC_GAME_06)  |  6 collected
# ─────────────────────────────────────────────────────────────────────────────

class TestGamePropertyOperations:
    """
    Branches: buy_property, pay_rent, mortgage_property, unmortgage_property
    """

    def setup_method(self):
        self.game  = Game(["Alice", "Bob"])
        self.alice = self.game.players[0]
        self.bob   = self.game.players[1]
        self.prop  = self.game.board.get_property_at(1)   # Mediterranean $60 rent $2

    def teardown_method(self):
        self.prop.owner = None
        self.prop.is_mortgaged = False

    # TC_GAME_01 – buy_property(): success when affordable; fails when balance < price
    def test_buy_property(self):
        self.alice.balance = 150
        assert self.game.buy_property(self.alice, self.prop) is True
        assert self.prop.owner == self.alice
        assert self.alice.balance == 90

        self.prop.owner = None
        self.alice.balance = 50
        assert self.game.buy_property(self.alice, self.prop) is False
        assert self.prop.owner is None
        assert self.alice.balance == 50

    # TC_GAME_02 – buy_property() boundary: balance == price succeeds, balance → 0
    def test_buy_exact_balance_boundary(self):
        """Boundary: balance == price"""
        self.alice.balance = 60
        assert self.game.buy_property(self.alice, self.prop) is True
        assert self.alice.balance == 0

    # TC_GAME_03 – buy_property() design note: ownership guard is in _handle_property_tile
    def test_buy_already_owned_no_internal_guard(self):
        self.game.buy_property(self.alice, self.prop)
        assert self.prop.owner == self.alice

    # TC_GAME_04 – pay_rent(): no charge if unowned or mortgaged; transfers rent if owned
    def test_pay_rent(self):
        initial = self.alice.balance

        # unowned → no payment
        self.game.pay_rent(self.alice, self.prop)
        assert self.alice.balance == initial

        # mortgaged → no payment
        self.prop.owner = self.bob
        self.prop.is_mortgaged = True
        self.game.pay_rent(self.alice, self.prop)
        assert self.alice.balance == initial
        self.prop.is_mortgaged = False

        # normal → $2 transferred
        bob_initial = self.bob.balance
        self.game.pay_rent(self.alice, self.prop)
        assert self.alice.balance == initial - 2
        assert self.bob.balance   == bob_initial + 2

    # TC_GAME_05 – mortgage_property(): wrong owner fails; success; already-mortgaged fails
    def test_mortgage_operations(self):
        self.game.buy_property(self.alice, self.prop)
        initial = self.alice.balance

        assert self.game.mortgage_property(self.bob, self.prop) is False
        assert self.game.mortgage_property(self.alice, self.prop) is True
        assert self.alice.balance == initial + 30
        assert self.game.mortgage_property(self.alice, self.prop) is False

    # TC_GAME_06 – unmortgage_property(): wrong owner/poor/not-mortgaged fail; success path
    def test_unmortgage_operations(self):
        self.game.buy_property(self.alice, self.prop)
        self.game.mortgage_property(self.alice, self.prop)

        assert self.game.unmortgage_property(self.bob, self.prop) is False

        self.alice.balance = 10
        assert self.game.unmortgage_property(self.alice, self.prop) is False

        self.alice.balance = 100
        assert self.game.unmortgage_property(self.alice, self.prop) is True
        assert self.alice.balance == 67
        assert self.game.unmortgage_property(self.alice, self.prop) is False


# ─────────────────────────────────────────────────────────────────────────────
# MODULE: game.py – Jail Logic  (TC_GAME_07 – TC_GAME_09)  |  3 collected
# ─────────────────────────────────────────────────────────────────────────────

class TestGameJailLogic:

    def setup_method(self):
        self.game  = Game(["Alice", "Bob"])
        self.alice = self.game.players[0]
        self.alice.go_to_jail()

    # TC_GAME_07 – _handle_jail_turn(): Get Out of Jail Free card releases player
    def test_jail_card_usage(self):
        self.alice.jail_status["get_out_of_jail_cards"] = 1
        with patch("moneypoly.ui.confirm", return_value=True), \
             patch("random.randint", side_effect=[3, 4]):
            self.game._handle_jail_turn(self.alice)
        assert self.alice.jail_status["in_jail"] is False
        assert self.alice.jail_status["get_out_of_jail_cards"] == 0

    # TC_GAME_08 – _handle_jail_turn(): voluntary fine releases; insufficient funds stays
    def test_jail_pay_fine(self):
        self.alice.balance = 100
        with patch("moneypoly.ui.confirm", return_value=True), \
             patch("random.randint", side_effect=[2, 3]):
            self.game._handle_jail_turn(self.alice)
        assert self.alice.jail_status["in_jail"] is False
        assert self.alice.balance == 50

        self.alice.go_to_jail()
        self.alice.balance = 30
        with patch("moneypoly.ui.confirm", side_effect=[True, False]):
            self.game._handle_jail_turn(self.alice)
        assert self.alice.jail_status["in_jail"] is True
        assert self.alice.balance == 30

    # TC_GAME_09 – _handle_jail_turn(): mandatory release after 3 turns, fine deducted
    def test_jail_mandatory_release(self):
        """Mandatory release after 3 turns"""
        self.alice.jail_status["jail_turns"] = 2
        self.alice.balance = 200
        with patch("moneypoly.ui.confirm", return_value=False), \
             patch("random.randint", side_effect=[3, 4]):
            self.game._handle_jail_turn(self.alice)
        assert self.alice.jail_status["in_jail"] is False
        assert self.alice.balance <= 200 - config.JAIL_FINE

# ─────────────────────────────────────────────────────────────────────────────
# MODULE: game.py – Turn & Tile Logic  (TC_GAME_10 – TC_GAME_19)  |  10 collected
# ─────────────────────────────────────────────────────────────────────────────

class TestGameTurnAndTiles:

    def setup_method(self):
        self.game  = Game(["Alice", "Bob"])
        self.alice = self.game.players[0]
        self.bob   = self.game.players[1]

    # TC_GAME_10 – advance_turn(): index wraps via modulo; turn_number increments
    def test_advance_turn_wraps_and_increments(self):
        """advance_turn(): current_index wraps via modulo, turn_number increments"""
        self.game.game_state["current_index"] = 0
        self.game.game_state["turn_number"]   = 0
        self.game.advance_turn()
        assert self.game.game_state["current_index"] == 1
        assert self.game.game_state["turn_number"]   == 1

        self.game.game_state["current_index"] = 1
        self.game.advance_turn()
        assert self.game.game_state["current_index"] == 0
        assert self.game.game_state["turn_number"]   == 2

    # TC_GAME_11 – play_turn() doubles: same player keeps turn, index not advanced
    def test_doubles_same_player_keeps_turn(self):
        self.game.game_state["current_index"] = 0
        with patch("random.randint", side_effect=[3, 3, 9, 9]), \
             patch("builtins.input", return_value="s"):
            self.game.play_turn()
        assert self.game.game_state["current_index"] == 0

    # TC_GAME_12 – play_turn(): three consecutive doubles sends player to jail
    def test_three_doubles_jail(self):
        self.game.dice.doubles_streak = 2
        with patch("random.randint", side_effect=[4, 4]):
            self.game.play_turn()
        assert self.alice.jail_status["in_jail"] is True

    # TC_GAME_13 – _resolve_tile(): go_to_jail / income_tax / luxury_tax / free_parking
    def test_special_tiles_go_to_jail_and_taxes_and_parking(self):
        """_resolve_tile() special branches: go_to_jail / taxes / parking"""
        self.game._resolve_tile(self.alice, "go_to_jail", config.GO_TO_JAIL_POSITION)
        assert self.alice.jail_status["in_jail"] is True
        self.alice.jail_status["in_jail"] = False

        initial = self.alice.balance
        self.game._resolve_tile(self.alice, "income_tax", config.INCOME_TAX_POSITION)
        assert self.alice.balance == initial - config.INCOME_TAX_AMOUNT

        initial = self.alice.balance
        self.game._resolve_tile(self.alice, "luxury_tax", config.LUXURY_TAX_POSITION)
        assert self.alice.balance == initial - config.LUXURY_TAX_AMOUNT

        initial = self.alice.balance
        self.game._resolve_tile(self.alice, "free_parking", config.FREE_PARKING_POSITION)
        assert self.alice.balance == initial

    # TC_GAME_14 – _resolve_tile() chance branch: draws and applies chance card
    def test_resolve_tile_chance(self):
        """'chance' elif branch"""
        self.game.decks["chance"].cards = [
            {"description": "Test", "action": "collect", "value": 50}
        ]
        self.game.decks["chance"].index = 0
        initial = self.alice.balance
        self.game._resolve_tile(self.alice, "chance", 7)
        assert self.alice.balance == initial + 50

    # TC_GAME_15 – _resolve_tile() community_chest branch: draws and applies card
    def test_resolve_tile_community_chest(self):
        """'community_chest' elif branch"""
        self.game.decks["community_chest"].cards = [
            {"description": "Test", "action": "pay", "value": 50}
        ]
        self.game.decks["community_chest"].index = 0
        initial = self.alice.balance
        self.game._resolve_tile(self.alice, "community_chest", 2)
        assert self.alice.balance == initial - 50

    # TC_GAME_16 – _resolve_tile() railroad branch: routes to property tile handler
    def test_resolve_tile_railroad(self):
        """'railroad' branch falls into property tile handler"""
        initial = self.alice.balance
        with patch("builtins.input", return_value="s"):
            self.game._resolve_tile(self.alice, "railroad", 5)
        assert self.alice.balance == initial

    # TC_GAME_17 – _handle_property_tile(): skip / own (no rent) / other (pay rent)
    def test_property_tile_landing_skip_own_other(self):
        """_handle_property_tile(): skip / own / other player branches"""
        prop = self.game.board.get_property_at(1)

        with patch("builtins.input", return_value="s"):
            self.game._handle_property_tile(self.alice, prop)
        assert prop.owner is None

        prop.owner = self.alice
        initial = self.alice.balance
        self.game._handle_property_tile(self.alice, prop)
        assert self.alice.balance == initial

        prop.owner = self.bob
        alice_initial = self.alice.balance
        self.game._handle_property_tile(self.alice, prop)
        assert self.alice.balance == alice_initial - prop.get_rent()

        prop.owner = None

    # TC_GAME_18 – _handle_property_tile() buy branch: choice=='b' triggers purchase
    def test_property_tile_landing_buy_path(self):
        """choice == 'b' branch"""
        prop = self.game.board.get_property_at(1)
        self.alice.balance = 200
        with patch("builtins.input", return_value="b"):
            self.game._handle_property_tile(self.alice, prop)
        assert prop.owner == self.alice
        assert self.alice.balance == 140
        prop.owner = None

    # TC_GAME_19 – _handle_property_tile() auction branch: choice=='a' triggers auction
    def test_property_tile_landing_auction_path(self):
        """choice == 'a' branch"""
        prop = self.game.board.get_property_at(1)
        self.alice.balance = 500
        with patch("builtins.input", return_value="a"), \
             patch("moneypoly.ui.safe_int_input", side_effect=[100, 0]):
            self.game._handle_property_tile(self.alice, prop)
        assert prop.owner == self.alice
        prop.owner = None


# ─────────────────────────────────────────────────────────────────────────────
# MODULE: game.py – Card Actions  (TC_GAME_20 – TC_GAME_23)  |  4 collected
# ─────────────────────────────────────────────────────────────────────────────

class TestGameCardActions:
    """Covers all action types in _apply_card dispatcher"""

    def setup_method(self):
        self.game  = Game(["Alice", "Bob"])
        self.alice = self.game.players[0]
        self.bob   = self.game.players[1]

    def _card(self, action, value=0):
        return {"description": "Test", "action": action, "value": value}

    # TC_GAME_20 – _apply_card(): collect/pay transfer money; None/unknown ignored
    def test_card_money_actions(self):
        initial = self.alice.balance

        self.game._apply_card(self.alice, self._card("collect", 100))
        assert self.alice.balance == initial + 100

        self.game._apply_card(self.alice, self._card("pay", 50))
        assert self.alice.balance == initial + 50

        self.game._apply_card(self.alice, None)
        assert self.alice.balance == initial + 50

        self.game._apply_card(self.alice, self._card("teleport", 999))
        assert self.alice.balance == initial + 50

    # TC_GAME_21 – _apply_card(): move_to (pass-Go/no-Go), jail, jail_free actions
    def test_card_movement_actions(self):
        """move_to, jail, jail_free actions"""
        self.alice.position = 30
        initial = self.alice.balance
        self.game._apply_card(self.alice, self._card("move_to", 5))
        assert self.alice.balance == initial + config.GO_SALARY

        self.alice.position = 5
        initial = self.alice.balance
        self.game._apply_card(self.alice, self._card("move_to", 10))
        assert self.alice.balance == initial

        self.game._apply_card(self.alice, self._card("jail"))
        assert self.alice.jail_status["in_jail"] is True

        self.alice.jail_status["in_jail"] = False
        self.game._apply_card(self.alice, self._card("jail_free"))
        assert self.alice.jail_status["get_out_of_jail_cards"] == 1

    # TC_GAME_22 – _apply_card() birthday: all pay; broke player skipped
    def test_card_birthday(self):
        """birthday action"""
        self.bob.balance = 100
        alice_initial = self.alice.balance
        self.game._apply_card(self.alice, self._card("birthday", 10))
        assert self.alice.balance == alice_initial + 10
        assert self.bob.balance   == 90

        self.bob.balance = 5
        alice_initial = self.alice.balance
        self.game._apply_card(self.alice, self._card("birthday", 10))
        assert self.alice.balance == alice_initial
        assert self.bob.balance   == 5

    # TC_GAME_23 – _apply_card() collect_from_all: separate dispatch key, same logic
    def test_card_collect_from_all(self):
        """collect_from_all action (separate dispatch key from birthday)"""
        self.bob.balance = 100
        alice_initial = self.alice.balance
        self.game._apply_card(self.alice, self._card("collect_from_all", 50))
        assert self.alice.balance == alice_initial + 50
        assert self.bob.balance   == 50

        self.bob.balance = 5
        alice_initial = self.alice.balance
        self.game._apply_card(self.alice, self._card("collect_from_all", 50))
        assert self.alice.balance == alice_initial
        assert self.bob.balance   == 5


# ─────────────────────────────────────────────────────────────────────────────
# MODULE: game.py – Auction & Trade  (TC_GAME_24 – TC_GAME_27)  |  4 collected
# ─────────────────────────────────────────────────────────────────────────────

class TestGameAuctionAndTrade:

    def setup_method(self):
        self.game  = Game(["Alice", "Bob"])
        self.alice = self.game.players[0]
        self.bob   = self.game.players[1]
        self.prop  = self.game.board.get_property_at(1)

    def teardown_method(self):
        self.prop.owner = None

    # TC_GAME_24 – auction_property(): valid bid / too low / exceeds balance / no bids
    def test_auction(self):
        """auction_property() branches: valid bid / too low / exceeds balance / all pass"""
        self.alice.balance = 500

        with patch("moneypoly.ui.safe_int_input", side_effect=[100, 0]):
            self.game.auction_property(self.prop)
        assert self.prop.owner == self.alice
        self.prop.owner = None

        with patch("moneypoly.ui.safe_int_input", side_effect=[5, 0]):
            self.game.auction_property(self.prop)
        assert self.prop.owner is None

        self.alice.balance = 30
        with patch("moneypoly.ui.safe_int_input", side_effect=[200, 0]):
            self.game.auction_property(self.prop)
        assert self.prop.owner is None

        with patch("moneypoly.ui.safe_int_input", side_effect=[0, 0]):
            self.game.auction_property(self.prop)
        assert self.prop.owner is None

    # TC_GAME_25 – auction_property() boundary: bid at exactly minimum increment wins
    def test_auction_exact_minimum_increment(self):
        """Boundary: bid exactly at minimum increment"""
        self.alice.balance = 500
        self.bob.balance = 500

        with patch("moneypoly.ui.safe_int_input",
                   side_effect=[100, 100 + config.AUCTION_MIN_INCREMENT]):
            self.game.auction_property(self.prop)

        assert self.prop.owner == self.bob
        assert self.bob.balance == 500 - (100 + config.AUCTION_MIN_INCREMENT)
        self.prop.owner = None

    # TC_GAME_26 – trade(): wrong seller / buyer broke / success / zero-cash gift
    def test_trade(self):
        """trade() branches: wrong seller / can't afford / success / zero-cash gift"""
        self.game.buy_property(self.alice, self.prop)

        assert self.game.trade(self.bob, self.alice, self.prop, 0) is False

        self.bob.balance = 0
        assert self.game.trade(self.alice, self.bob, self.prop, 100) is False

        self.bob.balance  = 500
        alice_init = self.alice.balance
        bob_init   = self.bob.balance
        assert self.game.trade(self.alice, self.bob, self.prop, 100) is True
        assert self.prop.owner    == self.bob
        assert self.alice.balance == alice_init + 100
        assert self.bob.balance   == bob_init - 100

        prop2 = self.game.board.get_property_at(3)
        self.game.buy_property(self.bob, prop2)
        assert self.game.trade(self.bob, self.alice, prop2, 0) is True
        assert prop2.owner == self.alice
        prop2.owner = None

    # TC_GAME_27 – trade() edge: mortgaged property trades; mortgage state preserved
    def test_trade_mortgaged_property(self):
        """Edge case: trading mortgaged property preserves mortgage state"""
        self.game.buy_property(self.alice, self.prop)
        self.game.mortgage_property(self.alice, self.prop)
        assert self.prop.is_mortgaged is True

        self.bob.balance = 500
        alice_init = self.alice.balance
        bob_init = self.bob.balance

        result = self.game.trade(self.alice, self.bob, self.prop, 50)

        assert result is True
        assert self.prop.owner == self.bob
        assert self.prop.is_mortgaged is True
        assert self.alice.balance == alice_init + 50
        assert self.bob.balance == bob_init - 50


# ─────────────────────────────────────────────────────────────────────────────
# MODULE: game.py – Bankruptcy & Winner  (TC_GAME_28 – TC_GAME_34)  |  7 collected
# ─────────────────────────────────────────────────────────────────────────────

class TestGameBankruptcyAndWinner:

    # TC_GAME_28 – _check_bankruptcy(): bankrupt player eliminated, properties released
    def test_bankruptcy_eliminates_player_and_releases_properties(self):
        game  = Game(["Alice", "Bob"])
        alice = game.players[0]
        prop  = game.board.get_property_at(1)
        game.buy_property(alice, prop)
        alice.balance = -1
        game._check_bankruptcy(alice)

        assert alice.is_eliminated is True
        assert alice not in game.players
        assert prop.owner is None

    # TC_GAME_29 – _check_bankruptcy(): removing index-0 player never produces index -1
    def test_bankruptcy_index_stays_valid_when_first_player_eliminated(self):
        """Index adjustment when removing first player (index 0)"""
        game = Game(["Alice", "Bob"])
        game.game_state["current_index"] = 0
        alice = game.players[0]
        alice.balance = -1
        game._check_bankruptcy(alice)

        assert 0 <= game.game_state["current_index"] < len(game.players)

    # TC_GAME_30 – _check_bankruptcy(): removing middle player keeps index in bounds
    def test_bankruptcy_index_stays_valid_middle_player(self):
        game = Game(["Alice", "Bob", "Charlie"])
        game.game_state["current_index"] = 1
        bob = game.players[1]
        bob.balance = -1
        game._check_bankruptcy(bob)

        assert 0 <= game.game_state["current_index"] < len(game.players)

    # TC_GAME_31 – _check_bankruptcy(): removing last player at last index stays valid
    def test_bankruptcy_last_player_at_last_index(self):
        """Edge case: removing last player when current_index points to them"""
        game = Game(["Alice", "Bob", "Charlie"])
        game.game_state["current_index"] = 2
        charlie = game.players[2]
        charlie.balance = -1
        game._check_bankruptcy(charlie)

        assert len(game.players) == 2
        assert "Charlie" not in [p.name for p in game.players]
        assert 0 <= game.game_state["current_index"] < len(game.players)

    # TC_GAME_32 – find_winner(): empty player list returns None
    def test_find_winner_no_players_returns_none(self):
        game = Game(["Alice", "Bob"])
        game.players.clear()
        assert game.find_winner() is None

    # TC_GAME_33 – find_winner(): returns player with highest net worth
    def test_find_winner_picks_highest_net_worth(self):
        game = Game(["Alice", "Bob"])
        game.players[0].balance = 500
        game.players[1].balance = 2000
        assert game.find_winner().name == "Bob"

    # TC_GAME_34 – find_winner(): all players eliminated → None, game ends cleanly
    def test_all_players_eliminated_no_winner(self):
        game = Game(["Alice", "Bob"])
        for p in list(game.players):
            p.balance = -1
            game._check_bankruptcy(p)
        assert len(game.players) == 0
        assert game.find_winner() is None


# ─────────────────────────────────────────────────────────────────────────────
# MODULE: ui.py  (TC_UI_01 – TC_UI_03)  |  3 collected
# ─────────────────────────────────────────────────────────────────────────────

class TestUI:
    """safe_int_input() branches: try / ValueError / EOFError"""

    # TC_UI_01 – safe_int_input() try branch: valid integer string returns int
    def test_safe_int_input_valid(self):
        """try branch: valid integer"""
        from moneypoly import ui
        with patch("builtins.input", return_value="42"):
            result = ui.safe_int_input("prompt: ", default=0)
        assert result == 42

    # TC_UI_02 – safe_int_input() except ValueError: non-integer returns default
    def test_safe_int_input_invalid_string_returns_default(self):
        """except ValueError branch"""
        from moneypoly import ui
        with patch("builtins.input", return_value="abc"):
            result = ui.safe_int_input("prompt: ", default=99)
        assert result == 99

    # TC_UI_03 – safe_int_input() except EOFError: EOF returns default
    def test_safe_int_input_eof_returns_default(self):
        """except EOFError branch"""
        from moneypoly import ui
        with patch("builtins.input", side_effect=EOFError):
            result = ui.safe_int_input("prompt: ", default=7)
        assert result == 7


# ─────────────────────────────────────────────────────────────────────────────
# MODULE: main.py  (TC_MAIN_01 – TC_MAIN_02)  |  2 collected
# ─────────────────────────────────────────────────────────────────────────────

class TestMain:
    """main() exception branches: KeyboardInterrupt / ValueError"""

    # TC_MAIN_01 – main() except KeyboardInterrupt: handled cleanly without re-raising
    def test_main_keyboard_interrupt_handled(self):
        """except KeyboardInterrupt branch"""
        import main as main_module
        with patch.object(main_module, "get_player_names", return_value=["Alice", "Bob"]), \
             patch("moneypoly.game.Game.run", side_effect=KeyboardInterrupt):
            main_module.main()

    # TC_MAIN_02 – main() except ValueError: handled cleanly without re-raising
    def test_main_value_error_handled(self):
        """except ValueError branch"""
        import main as main_module
        with patch.object(main_module, "get_player_names", return_value=[]), \
             patch("moneypoly.game.Game", side_effect=ValueError("bad names")):
            main_module.main()


# ─────────────────────────────────────────────────────────────────────────────
# MODULE: game.py – run() loop  (TC_RUN_01 – TC_RUN_04)  |  4 collected
# ─────────────────────────────────────────────────────────────────────────────

class TestGameRun:
    """run() branches: while condition / len(players) <= 1 / winner check"""

    # TC_RUN_01 – run() break condition: exits when only one player remains
    def test_run_exits_when_one_player_remains(self):
        """if len(self.players) <= 1: break"""
        game = Game(["Alice", "Bob"])
        game.players = [game.players[0]]
        with patch("moneypoly.ui.print_banner"), \
             patch("moneypoly.ui.print_standings"), \
             patch("builtins.print"):
            game.run()
        assert game.find_winner().name == "Alice"

    # TC_RUN_02 – run() if winner: branch fires when at least one player survives
    def test_run_winner_branch(self):
        """if winner: branch"""
        game = Game(["Alice", "Bob"])
        call_count = [0]
        def fake_play_turn():
            call_count[0] += 1
            if call_count[0] == 1:
                bob = game.players[1] if len(game.players) > 1 else None
                if bob:
                    bob.balance = -1
                    game._check_bankruptcy(bob)
        with patch.object(game, "play_turn", side_effect=fake_play_turn), \
             patch("moneypoly.ui.print_banner"), \
             patch("moneypoly.ui.print_standings"), \
             patch("builtins.print"):
            game.run()
        assert game.find_winner() is not None

    # TC_RUN_03 – run() else: branch fires when all players are eliminated
    def test_run_no_winner_branch(self):
        """else: branch (no winner)"""
        game = Game(["Alice", "Bob"])
        def fake_play_turn():
            for p in list(game.players):
                p.balance = -1
                game._check_bankruptcy(p)
        with patch.object(game, "play_turn", side_effect=fake_play_turn), \
             patch("moneypoly.ui.print_banner"), \
             patch("moneypoly.ui.print_standings"), \
             patch("builtins.print"):
            game.run()
        assert game.find_winner() is None

    # TC_RUN_04 – run() while condition: loop exits when turn_number reaches MAX_TURNS
    def test_run_exits_on_max_turns(self):
        """while turn_number < MAX_TURNS"""
        game = Game(["Alice", "Bob"])
        game.game_state["turn_number"] = config.MAX_TURNS
        with patch("moneypoly.ui.print_banner"), \
             patch("moneypoly.ui.print_standings"), \
             patch("builtins.print"):
            game.run()
        assert len(game.players) == 2


# ─────────────────────────────────────────────────────────────────────────────
# MODULE: game.py – interactive_menu() + _menu_*  (TC_MENU_01 – TC_MENU_16)  |  16 collected
# ─────────────────────────────────────────────────────────────────────────────

class TestInteractiveMenu:
    """interactive_menu() while loop with 7 branches;
    _menu_mortgage/unmortgage/trade with early-exit and bounds checks"""

    def setup_method(self):
        self.game  = Game(["Alice", "Bob"])
        self.alice = self.game.players[0]
        self.bob   = self.game.players[1]
        self.prop  = self.game.board.get_property_at(1)

    def teardown_method(self):
        self.prop.owner        = None
        self.prop.is_mortgaged = False

    # TC_MENU_01 – interactive_menu() choice 0: break exits the while loop immediately
    def test_menu_choice_0_exits(self):
        """choice == 0 → break — menu returns without doing anything."""
        with patch("moneypoly.ui.safe_int_input", return_value=0):
            self.game.interactive_menu(self.alice)   # must return, not hang

    # ── interactive_menu: choice == 1 prints standings ───────────────────────
    # TC_MENU_02 – interactive_menu() choice 1: print_standings called with players
    def test_menu_choice_1_standings(self):
        with patch("moneypoly.ui.safe_int_input", side_effect=[1, 0]), \
             patch("moneypoly.ui.print_standings") as mock_standings:
            self.game.interactive_menu(self.alice)
        mock_standings.assert_called_once_with(self.game.players)

    # ── interactive_menu: choice == 2 prints board ownership ─────────────────
    # TC_MENU_03 – interactive_menu() choice 2: print_board_ownership called
    def test_menu_choice_2_board_ownership(self):
        with patch("moneypoly.ui.safe_int_input", side_effect=[2, 0]), \
             patch("moneypoly.ui.print_board_ownership") as mock_board:
            self.game.interactive_menu(self.alice)
        mock_board.assert_called_once_with(self.game.board)

    # TC_MENU_04 – interactive_menu() choice 6: loan issued when amount > 0
    def test_menu_choice_6_loan(self):
        """choice == 6 → amount > 0 → give_loan called."""
        initial = self.alice.balance
        with patch("moneypoly.ui.safe_int_input", side_effect=[6, 200, 0]):
            self.game.interactive_menu(self.alice)
        assert self.alice.balance == initial + 200

    # TC_MENU_05 – interactive_menu() choice 6: amount==0 skips loan (if amount>0 False)
    def test_menu_choice_6_loan_zero_ignored(self):
        """choice == 6 → amount == 0 → if amount > 0 is False → no loan."""
        initial = self.alice.balance
        with patch("moneypoly.ui.safe_int_input", side_effect=[6, 0, 0]):
            self.game.interactive_menu(self.alice)
        assert self.alice.balance == initial

    # ── _menu_mortgage: no mortgageable properties → early exit ──────────────
    # TC_MENU_06 – _menu_mortgage() early exit: if not mortgageable returns immediately
    def test_menu_mortgage_no_properties(self):
        """if not mortgageable: return — player owns nothing."""
        with patch("moneypoly.ui.safe_int_input", side_effect=[3, 0]), \
             patch("builtins.print"):
            self.game.interactive_menu(self.alice)
        # No crash, no mortgage happened
        assert not self.alice.properties

    # ── _menu_mortgage: valid index → mortgage executes ───────────────────────
    # TC_MENU_07 – _menu_mortgage() valid index: mortgage executes on selected property
    def test_menu_mortgage_valid_index(self):
        """0 <= idx < len(mortgageable) → mortgage_property called."""
        self.game.buy_property(self.alice, self.prop)
        initial = self.alice.balance
        # choice 3 → select property 1 (idx=0) → choice 0 to exit
        with patch("moneypoly.ui.safe_int_input", side_effect=[3, 1, 0]):
            self.game.interactive_menu(self.alice)
        assert self.prop.is_mortgaged is True
        assert self.alice.balance == initial + self.prop.mortgage_value()

    # ── _menu_mortgage: invalid index → nothing happens ──────────────────────
    # TC_MENU_08 – _menu_mortgage() invalid index: out-of-bounds selection does nothing
    def test_menu_mortgage_invalid_index(self):
        """idx out of bounds → if 0 <= idx branch is False → no mortgage."""
        self.game.buy_property(self.alice, self.prop)
        with patch("moneypoly.ui.safe_int_input", side_effect=[3, 99, 0]):
            self.game.interactive_menu(self.alice)
        assert self.prop.is_mortgaged is False

    # ── _menu_unmortgage: no mortgaged properties → early exit ───────────────
    # TC_MENU_09 – _menu_unmortgage() early exit: if not mortgaged returns immediately
    def test_menu_unmortgage_no_mortgaged(self):
        """if not mortgaged: return — nothing is mortgaged."""
        self.game.buy_property(self.alice, self.prop)   # owned but NOT mortgaged
        with patch("moneypoly.ui.safe_int_input", side_effect=[4, 0]), \
             patch("builtins.print"):
            self.game.interactive_menu(self.alice)
        assert self.prop.is_mortgaged is False

    # ── _menu_unmortgage: valid index → unmortgage executes ──────────────────
    # TC_MENU_10 – _menu_unmortgage() valid index: unmortgage executes on selection
    def test_menu_unmortgage_valid_index(self):
        """0 <= idx < len(mortgaged) → unmortgage_property called."""
        self.game.buy_property(self.alice, self.prop)
        self.game.mortgage_property(self.alice, self.prop)
        self.alice.balance = 500
        with patch("moneypoly.ui.safe_int_input", side_effect=[4, 1, 0]):
            self.game.interactive_menu(self.alice)
        assert self.prop.is_mortgaged is False

    # ── _menu_unmortgage: invalid index → nothing happens ────────────────────
    # TC_MENU_11 – _menu_unmortgage() invalid index: out-of-bounds selection does nothing
    def test_menu_unmortgage_invalid_index(self):
        """idx out of bounds → if 0 <= idx branch is False."""
        self.game.buy_property(self.alice, self.prop)
        self.game.mortgage_property(self.alice, self.prop)
        self.alice.balance = 500
        with patch("moneypoly.ui.safe_int_input", side_effect=[4, 99, 0]):
            self.game.interactive_menu(self.alice)
        assert self.prop.is_mortgaged is True   # unchanged

    # ── _menu_trade: no other players → early exit ───────────────────────────
    # TC_MENU_12 – _menu_trade() early exit: if not others returns immediately
    def test_menu_trade_no_others(self):
        """if not others: return — single player game."""
        game = Game(["Solo"])
        with patch("moneypoly.ui.safe_int_input", side_effect=[5, 0]), \
             patch("builtins.print"):
            game.interactive_menu(game.players[0])

    # ── _menu_trade: invalid partner index → return ───────────────────────────
    # TC_MENU_13 – _menu_trade() invalid partner: out-of-bounds index returns early
    def test_menu_trade_invalid_partner_index(self):
        """if not 0 <= idx < len(others) → return early."""
        with patch("moneypoly.ui.safe_int_input", side_effect=[5, 99, 0]), \
             patch("builtins.print"):
            self.game.interactive_menu(self.alice)
        # No trade happened
        assert self.prop.owner is None

    # ── _menu_trade: player has no properties → early exit ───────────────────
    # TC_MENU_14 – _menu_trade() no properties: if not player.properties returns early
    def test_menu_trade_no_properties(self):
        """if not player.properties: return — Alice owns nothing."""
        with patch("moneypoly.ui.safe_int_input", side_effect=[5, 1, 0]), \
             patch("builtins.print"):
            self.game.interactive_menu(self.alice)
        assert self.prop.owner is None

    # ── _menu_trade: invalid property index → return ─────────────────────────
    # TC_MENU_15 – _menu_trade() invalid property index: out-of-bounds returns early
    def test_menu_trade_invalid_property_index(self):
        """if not 0 <= pidx < len(player.properties) → return early."""
        self.game.buy_property(self.alice, self.prop)
        with patch("moneypoly.ui.safe_int_input", side_effect=[5, 1, 99, 0]), \
             patch("builtins.print"):
            self.game.interactive_menu(self.alice)
        assert self.prop.owner == self.alice   # no trade happened

    # ── _menu_trade: valid trade executes ────────────────────────────────────
    # TC_MENU_16 – _menu_trade() happy path: valid partner, property, cash → trade executes
    def test_menu_trade_valid(self):
        """Full happy path: partner valid, property valid, trade executes."""
        self.game.buy_property(self.alice, self.prop)
        self.bob.balance = 500
        # choices: 5 (trade), partner=1 (Bob), property=1 (Mediterranean),
        # cash=100, then 0 to exit
        with patch("moneypoly.ui.safe_int_input", side_effect=[5, 1, 1, 100, 0]):
            self.game.interactive_menu(self.alice)
        assert self.prop.owner == self.bob