"""Board class representing the MoneyPoly game board and tile management."""

from moneypoly.property import Property, PropertyGroup
from moneypoly.config import (
    JAIL_POSITION,
    GO_TO_JAIL_POSITION,
    FREE_PARKING_POSITION,
    INCOME_TAX_POSITION,
    LUXURY_TAX_POSITION,
)

# Maps fixed board positions to their tile type.
# Properties are looked up separately via get_property_at().
SPECIAL_TILES = {
    0: "go",
    JAIL_POSITION: "jail",
    GO_TO_JAIL_POSITION: "go_to_jail",
    FREE_PARKING_POSITION: "free_parking",
    INCOME_TAX_POSITION: "income_tax",
    LUXURY_TAX_POSITION: "luxury_tax",
    2:  "community_chest",
    17: "community_chest",
    33: "community_chest",
    7:  "chance",
    22: "chance",
    36: "chance",
    5:  "railroad",
    15: "railroad",
    25: "railroad",
    35: "railroad",
}


class Board:
    """Represents the MoneyPoly game board and all its tiles."""

    def __init__(self):
        self.groups = self._create_groups()
        self.properties = self._create_properties()

    def _create_groups(self):
        """Create and return the eight colour groups."""
        return {
            "brown":      PropertyGroup("Brown",      "brown"),
            "light_blue": PropertyGroup("Light Blue", "light_blue"),
            "pink":       PropertyGroup("Pink",       "pink"),
            "orange":     PropertyGroup("Orange",     "orange"),
            "red":        PropertyGroup("Red",        "red"),
            "yellow":     PropertyGroup("Yellow",     "yellow"),
            "green":      PropertyGroup("Green",      "green"),
            "dark_blue":  PropertyGroup("Dark Blue",  "dark_blue"),
        }

    def _create_properties(self):
        """Instantiate every purchasable property and return as a list."""
        g = self.groups
        return [
            Property(
                {'name': 'Mediterranean Avenue', 'position': 1,
                 'price': 60, 'base_rent': 2}, g["brown"]),
            Property(
                {'name': 'Baltic Avenue', 'position': 3,
                 'price': 60, 'base_rent': 4}, g["brown"]),
            Property(
                {'name': 'Oriental Avenue', 'position': 6,
                 'price': 100, 'base_rent': 6}, g["light_blue"]),
            Property(
                {'name': 'Vermont Avenue', 'position': 8,
                 'price': 100, 'base_rent': 6}, g["light_blue"]),
            Property(
                {'name': 'Connecticut Avenue', 'position': 9,
                 'price': 120, 'base_rent': 8}, g["light_blue"]),
            Property(
                {'name': 'St. Charles Place', 'position': 11,
                 'price': 140, 'base_rent': 10}, g["pink"]),
            Property(
                {'name': 'States Avenue', 'position': 13,
                 'price': 140, 'base_rent': 10}, g["pink"]),
            Property(
                {'name': 'Virginia Avenue', 'position': 14,
                 'price': 160, 'base_rent': 12}, g["pink"]),
            Property(
                {'name': 'St. James Place', 'position': 16,
                 'price': 180, 'base_rent': 14}, g["orange"]),
            Property(
                {'name': 'Tennessee Avenue', 'position': 18,
                 'price': 180, 'base_rent': 14}, g["orange"]),
            Property(
                {'name': 'New York Avenue', 'position': 19,
                 'price': 200, 'base_rent': 16}, g["orange"]),
            Property(
                {'name': 'Kentucky Avenue', 'position': 21,
                 'price': 220, 'base_rent': 18}, g["red"]),
            Property(
                {'name': 'Indiana Avenue', 'position': 23,
                 'price': 220, 'base_rent': 18}, g["red"]),
            Property(
                {'name': 'Illinois Avenue', 'position': 24,
                 'price': 240, 'base_rent': 20}, g["red"]),
            Property(
                {'name': 'Atlantic Avenue', 'position': 26,
                 'price': 260, 'base_rent': 22}, g["yellow"]),
            Property(
                {'name': 'Ventnor Avenue', 'position': 27,
                 'price': 260, 'base_rent': 22}, g["yellow"]),
            Property(
                {'name': 'Marvin Gardens', 'position': 29,
                 'price': 280, 'base_rent': 24}, g["yellow"]),
            Property(
                {'name': 'Pacific Avenue', 'position': 31,
                 'price': 300, 'base_rent': 26}, g["green"]),
            Property(
                {'name': 'North Carolina Avenue', 'position': 32,
                 'price': 300, 'base_rent': 26}, g["green"]),
            Property(
                {'name': 'Pennsylvania Avenue', 'position': 34,
                 'price': 320, 'base_rent': 28}, g["green"]),
            Property(
                {'name': 'Park Place', 'position': 37,
                 'price': 350, 'base_rent': 35}, g["dark_blue"]),
            Property(
                {'name': 'Boardwalk', 'position': 39,
                 'price': 400, 'base_rent': 50}, g["dark_blue"]),
        ]

    def get_property_at(self, position):
        """Return the Property at `position`, or None if there is none."""
        for prop in self.properties:
            if prop.position == position:
                return prop
        return None

    def get_tile_type(self, position):
        """
        Return a string describing the tile at `position`.
        Possible values: 'go', 'jail', 'go_to_jail', 'free_parking',
        'income_tax', 'luxury_tax', 'community_chest', 'chance',
        'railroad', 'property', 'blank'.
        """
        if position in SPECIAL_TILES:
            return SPECIAL_TILES[position]
        if self.get_property_at(position) is not None:
            return "property"
        return "blank"

    def is_purchasable(self, position):
        """
        Return True if the tile at `position` is a property that can be bought.
        Mortgaged properties are not considered purchasable.
        """
        prop = self.get_property_at(position)
        if prop is None:
            return False
        if prop.is_mortgaged:
            return False
        return prop.owner is None

    def is_special_tile(self, position):
        """Return True if `position` holds a non-property special tile."""
        return position in SPECIAL_TILES

    def properties_owned_by(self, player):
        """Return a list of all properties currently owned by `player`."""
        return [p for p in self.properties if p.owner == player]

    def unowned_properties(self):
        """Return a list of all properties that have not yet been purchased."""
        return [p for p in self.properties if p.owner is None]

    def __repr__(self):
        owned = sum(1 for p in self.properties if p.owner is not None)
        return f"Board({len(self.properties)} properties, {owned} owned)"
