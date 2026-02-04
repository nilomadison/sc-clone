"""
Land value system for SimCity Clone.
Handles calculation of property values based on surroundings.
"""

# Land value modifiers
VALUE_MODIFIERS = {
    'road': 5,          # Roads increase value
    'police': 15,       # Police stations increase value
    'residential': 3,   # Residential slightly increases
    'commercial': 5,    # Commercial increases value
    'industrial': -10,  # Industrial decreases value
    'power_plant': -15, # Power plants decrease value
}


class LandValueSystem:
    """Calculates land value for all tiles."""
    
    def update(self, grid):
        """Recalculate land values based on surroundings and crime."""
        for x in range(grid.width):
            for y in range(grid.height):
                tile = grid.tiles[x][y]
                
                # Start with base value
                base_value = 50
                
                # Add modifiers from nearby tiles
                modifier = self._calculate_neighbor_modifier(grid, x, y)
                
                # Crime reduces land value significantly
                crime_penalty = tile.crime_level * 40
                
                # Calculate final value
                final_value = base_value + modifier - crime_penalty
                tile.land_value = max(0, min(100, int(final_value)))
    
    def _calculate_neighbor_modifier(self, grid, x, y):
        """Calculate value modifier from neighboring tiles."""
        total_modifier = 0.0
        
        # Check tiles in a small radius
        radius = 4
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if dx == 0 and dy == 0:
                    continue
                    
                nx, ny = x + dx, y + dy
                if 0 <= nx < grid.width and 0 <= ny < grid.height:
                    neighbor = grid.tiles[nx][ny]
                    modifier = VALUE_MODIFIERS.get(neighbor.type, 0)
                    
                    if modifier != 0:
                        # Distance-based falloff
                        dist = max(1, ((dx ** 2) + (dy ** 2)) ** 0.5)
                        total_modifier += modifier / dist
        
        return total_modifier
