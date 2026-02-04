"""
Crime system for SimCity Clone.
Handles crime generation and police coverage.
"""

# Police station coverage radius (in tiles)
POLICE_RADIUS = 8

# Crime generation rates
CRIME_RATES = {
    'industrial': 0.3,      # High crime from industry
    'commercial': 0.1,      # Some crime from commercial
    'residential': 0.05,    # Low base crime from high-density residential
}


class CrimeSystem:
    """Manages crime levels across the city."""
    
    def update(self, grid):
        """Update crime levels for all tiles."""
        # First, find all police stations and their coverage
        police_coverage = self._calculate_police_coverage(grid)
        
        # Reset and recalculate crime for each tile
        for x in range(grid.width):
            for y in range(grid.height):
                tile = grid.tiles[x][y]
                
                # Calculate base crime from nearby sources
                base_crime = self._calculate_base_crime(grid, x, y)
                
                # Reduce crime based on police coverage
                coverage = police_coverage.get((x, y), 0.0)
                final_crime = base_crime * (1.0 - coverage * 0.8)  # Police reduce up to 80%
                
                tile.crime_level = max(0.0, min(1.0, final_crime))
    
    def _calculate_police_coverage(self, grid):
        """Calculate police coverage for each tile."""
        coverage = {}
        
        # Find all police stations
        for x in range(grid.width):
            for y in range(grid.height):
                if grid.tiles[x][y].type == 'police':
                    # Add coverage in radius
                    for dx in range(-POLICE_RADIUS, POLICE_RADIUS + 1):
                        for dy in range(-POLICE_RADIUS, POLICE_RADIUS + 1):
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < grid.width and 0 <= ny < grid.height:
                                # Distance-based falloff
                                dist = ((dx ** 2) + (dy ** 2)) ** 0.5
                                if dist <= POLICE_RADIUS:
                                    strength = 1.0 - (dist / POLICE_RADIUS)
                                    current = coverage.get((nx, ny), 0.0)
                                    coverage[(nx, ny)] = min(1.0, current + strength)
        
        return coverage
    
    def _calculate_base_crime(self, grid, x, y):
        """Calculate base crime level at a position from nearby sources."""
        total_crime = 0.0
        
        # Check tiles in a radius for crime sources
        radius = 6
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < grid.width and 0 <= ny < grid.height:
                    neighbor = grid.tiles[nx][ny]
                    crime_rate = CRIME_RATES.get(neighbor.type, 0.0)
                    
                    if crime_rate > 0 and neighbor.population > 0:
                        # Distance-based falloff
                        dist = max(1, ((dx ** 2) + (dy ** 2)) ** 0.5)
                        contribution = (crime_rate * neighbor.population / 10) / dist
                        total_crime += contribution
        
        return min(1.0, total_crime)
