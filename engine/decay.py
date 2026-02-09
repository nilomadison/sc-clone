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

    def __init__(self):
        self.police_funding = 1.0  # 0.0 to 1.0
        self.fire_funding = 1.0  # 0.0 to 1.0

    def update(self, grid, economy=None):
        """
        Update building health based on service funding levels.
        
        Args:
            grid: The game grid
            economy: The economy system (optional, for reading funding levels)
        """
        if economy:
            self._update_funding_from_economy(economy)
        
        self._apply_decay(grid)
        self._apply_repairs(grid)
        self._check_collapsed_buildings(grid)

    def _update_funding_from_economy(self, economy):
        """Read funding levels from economy system."""
        if hasattr(economy, 'service_funding'):
            self.police_funding = economy.service_funding.get('police', 1.0)
            self.fire_funding = economy.service_funding.get('fire', 1.0)

    def _apply_decay(self, grid):
        """Apply decay to buildings based on service funding."""
        for x in range(grid.width):
            for y in range(grid.height):
                tile = grid.get_tile(x, y)
                if tile is None or tile.is_burned:
                    continue
                
                # Only buildings can decay
                if tile.type not in ['residential', 'commercial', 'industrial', 
                                     'power_plant', 'police', 'fire_station']:
                    continue
                
                decay_rate = 0.0
                
                # Underfunded police increases decay in high-crime areas
                if self.police_funding < 1.0 and tile.crime_level > 0.3:
                    decay_rate += self.DECAY_RATE_BASE * (1.0 - self.police_funding) * tile.crime_level
                
                # Underfunded fire services increases decay risk
                if self.fire_funding < 1.0:
                    decay_rate += self.DECAY_RATE_BASE * (1.0 - self.fire_funding) * 0.5
                
                # Apply decay
                if decay_rate > 0:
                    tile.building_health = max(0.0, tile.building_health - decay_rate)

    def _apply_repairs(self, grid):
        """Naturally repair buildings when services are properly funded."""
        # Only repair if both services are reasonably funded
        if self.police_funding < 0.5 or self.fire_funding < 0.5:
            return
        
        repair_rate = self.REPAIR_RATE * min(self.police_funding, self.fire_funding)
        
        for x in range(grid.width):
            for y in range(grid.height):
                tile = grid.get_tile(x, y)
                if tile is None or tile.is_burned:
                    continue
                
                # Only repair damaged buildings
                if tile.building_health < 1.0 and tile.building_health > 0:
                    tile.building_health = min(1.0, tile.building_health + repair_rate)

    def _check_collapsed_buildings(self, grid):
        """Check for buildings that have collapsed due to neglect."""
        for x in range(grid.width):
            for y in range(grid.height):
                tile = grid.get_tile(x, y)
                if tile is None:
                    continue
                
                # Buildings with 0 health collapse into rubble
                if tile.building_health <= 0 and not tile.is_burned:
                    if tile.type in ['residential', 'commercial', 'industrial']:
                        tile.is_burned = True  # Reuse burned state for collapsed
                        tile.population = 0

    def get_building_status(self, tile):
        """
        Get the operational status of a building.
        
        Returns:
            'functional' - Building is fully operational
            'degraded' - Building is damaged but functional
            'non_functional' - Building has stopped working
            'collapsed' - Building has been destroyed
        """
        if tile.is_burned:
            return 'collapsed'
        if tile.building_health <= 0:
            return 'collapsed'
        if tile.building_health < self.MIN_HEALTH_FUNCTIONAL:
            return 'non_functional'
        if tile.building_health < self.CRITICAL_HEALTH:
            return 'degraded'
        return 'functional'

    def is_functional(self, tile):
        """Check if a building is still functional."""
        return tile.building_health >= self.MIN_HEALTH_FUNCTIONAL and not tile.is_burned
