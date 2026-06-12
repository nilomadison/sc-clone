"""
Decay System for SimCity Clone v0.4.0

Manages building decay from underfunded services and natural deterioration.
"""


class DecaySystem:
    """System for managing building health and decay mechanics."""

    # Decay configuration
    DECAY_RATE_BASE = 0.001  # Base decay per tick for underfunded services
    REPAIR_RATE = 0.005  # Natural repair rate per tick when services are funded
    
    MIN_HEALTH_FUNCTIONAL = 0.25  # Below this, building stops functioning
    CRITICAL_HEALTH = 0.5  # Below this, building shows visual decay

    BUILDING_TYPES = ('residential', 'commercial', 'industrial',
                      'power_plant', 'police', 'fire_station')

    def __init__(self):
        self.events = []  # ('collapse', x, y) events for the notification system

    def update(self, grid, economy=None):
        """
        Update building health based on service funding levels.

        Args:
            grid: The game grid
            economy: The economy system; funding defaults to 1.0 without it
        """
        if economy is not None:
            police_funding = economy.service_funding.get('police', 1.0)
            fire_funding = economy.service_funding.get('fire', 1.0)
        else:
            police_funding = fire_funding = 1.0

        self._apply_decay(grid, police_funding, fire_funding)
        self._apply_repairs(grid, police_funding, fire_funding)
        self._check_collapsed_buildings(grid)

    def _apply_decay(self, grid, police_funding, fire_funding):
        """Apply decay to buildings based on service funding."""
        # Skip the whole pass when services are fully funded (no decay possible)
        if police_funding >= 1.0 and fire_funding >= 1.0:
            return

        for x, y in grid.positions(*self.BUILDING_TYPES):
            tile = grid.tiles[x][y]
            if tile.is_burned:
                continue

            decay_rate = 0.0

            # Underfunded police increases decay in high-crime areas
            if police_funding < 1.0 and tile.crime_level > 0.3:
                decay_rate += self.DECAY_RATE_BASE * (1.0 - police_funding) * tile.crime_level

            # Underfunded fire services increases decay risk
            if fire_funding < 1.0:
                decay_rate += self.DECAY_RATE_BASE * (1.0 - fire_funding) * 0.5

            # Apply decay
            if decay_rate > 0:
                tile.building_health = max(0.0, tile.building_health - decay_rate)

    def _apply_repairs(self, grid, police_funding, fire_funding):
        """Naturally repair buildings when services are properly funded."""
        # Only repair if both services are reasonably funded
        if police_funding < 0.5 or fire_funding < 0.5:
            return

        repair_rate = self.REPAIR_RATE * min(police_funding, fire_funding)

        for x, y in grid.positions(*self.BUILDING_TYPES):
            tile = grid.tiles[x][y]
            if tile.is_burned or tile.is_on_fire:
                continue

            # Only repair damaged buildings
            if tile.building_health < 1.0 and tile.building_health > 0:
                tile.building_health = min(1.0, tile.building_health + repair_rate)

    def _check_collapsed_buildings(self, grid):
        """Check for buildings that have collapsed due to neglect."""
        for x, y in grid.positions('residential', 'commercial', 'industrial'):
            tile = grid.tiles[x][y]

            # Buildings with 0 health collapse into rubble
            if tile.building_health <= 0 and not tile.is_burned:
                tile.is_burned = True  # Reuse burned state for collapsed
                tile.population = 0
                self.events.append(('collapse', x, y))

MIN_HEALTH_FUNCTIONAL = DecaySystem.MIN_HEALTH_FUNCTIONAL


def is_functional(tile):
    """A building works only while intact and above the health threshold.

    Non-functional buildings stop providing service coverage, producing
    power, growing, and paying taxes.
    """
    return tile.building_health >= MIN_HEALTH_FUNCTIONAL and not tile.is_burned
