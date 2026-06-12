"""
Crime system for SimCity Clone.
Handles crime generation and police coverage.

Crime contributions and police coverage are maintained incrementally via
IncrementalField — only sources whose strength changed since last tick
re-scatter, so cost tracks city churn rather than map size.
"""

from engine.decay import is_functional
from engine.fields import IncrementalField, falloff_kernel, linear_kernel
from engine.tiles import field_map

# Police station coverage radius (in tiles)
POLICE_RADIUS = 8

# Radius crime spreads from its source
CRIME_RADIUS = 6

# Crime generation rates (from the tile type registry)
CRIME_RATES = field_map('crime_rate', lambda v: v > 0)


class CrimeSystem:
    """Manages crime levels across the city."""

    def __init__(self):
        self._crime_field = IncrementalField(falloff_kernel(CRIME_RADIUS))
        self._coverage_field = IncrementalField(linear_kernel(POLICE_RADIUS))

    def update(self, grid):
        """Update crime levels for all tiles."""
        self._crime_field.resize(grid.width, grid.height)
        self._coverage_field.resize(grid.width, grid.height)

        # Crime sources: populated RCI zones
        sources = {}
        for x, y in grid.positions('industrial', 'commercial', 'residential'):
            tile = grid.tiles[x][y]
            if tile.population > 0:
                rate = CRIME_RATES[tile.type]
                sources[(x, y)] = rate * tile.population / 10
        self._crime_field.refresh(sources)

        # Police coverage (1.0 at the station, linear falloff to the radius
        # edge); crumbling or burned stations provide none
        self._coverage_field.refresh(
            {(x, y): 1.0 for x, y in grid.positions('police')
             if is_functional(grid.tiles[x][y])})

        # Combine into per-tile crime levels (fields are flat: x * height + y)
        crime = self._crime_field.field
        coverage = self._coverage_field.field
        height = grid.height
        for x in range(grid.width):
            base_idx = x * height
            tile_col = grid.tiles[x]
            for y in range(height):
                base = crime[base_idx + y]
                if base <= 0.0:
                    tile_col[y].crime_level = 0.0
                    continue
                if base > 1.0:
                    base = 1.0
                cov = coverage[base_idx + y]
                if cov > 1.0:
                    cov = 1.0
                # Police reduce crime by up to 80%
                level = base * (1.0 - cov * 0.8)
                tile_col[y].crime_level = max(0.0, min(1.0, level))
