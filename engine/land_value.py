"""
Land value system for SimCity Clone.
Handles calculation of property values based on surroundings.

Neighbor modifiers are maintained incrementally via IncrementalField — only
tiles whose type changed re-scatter, so cost tracks city churn rather than
map size.
"""

from engine.fields import IncrementalField, falloff_kernel
from engine.tiles import field_map

# Radius within which buildings affect land value
VALUE_RADIUS = 4

# Land value modifiers (from the tile type registry)
VALUE_MODIFIERS = field_map('value_modifier', lambda v: v != 0)


class LandValueSystem:
    """Calculates land value for all tiles."""

    def __init__(self):
        # Original gather skipped the tile itself, so exclude the center
        self._modifier_field = IncrementalField(
            falloff_kernel(VALUE_RADIUS, exclude_center=True))

    def update(self, grid):
        """Recalculate land values based on surroundings and crime."""
        self._modifier_field.resize(grid.width, grid.height)

        sources = {}
        for type_name, modifier in VALUE_MODIFIERS.items():
            for pos in grid.positions(type_name):
                sources[pos] = modifier
        self._modifier_field.refresh(sources)

        # Field is flat: x * height + y
        modifiers = self._modifier_field.field
        height = grid.height
        for x in range(grid.width):
            base_idx = x * height
            tile_col = grid.tiles[x]
            for y in range(height):
                tile = tile_col[y]
                # Base value, neighbor modifiers, heavy crime penalty
                value = 50 + modifiers[base_idx + y] - tile.crime_level * 40
                tile.land_value = max(0, min(100, int(value)))
