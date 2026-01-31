from collections import deque
import random

class PowerSystem:
    def update(self, grid):
        # Reset power for all tiles
        for x in range(grid.width):
            for y in range(grid.height):
                grid.tiles[x][y].is_powered = False

        # Find power sources
        sources = []
        for x in range(grid.width):
            for y in range(grid.height):
                if grid.tiles[x][y].type == 'power_plant':
                    sources.append((x, y))
                    grid.tiles[x][y].is_powered = True

        # Propagate power (BFS) through power lines
        # Assumption: Power travels through 'power_line' and 'power_plant'
        # Zones get powered if they are adjacent to a powered tile? 
        # Or do they need to be adjacent to a line/plant? 
        # Let's say power flows through lines, and any building adjacent to a powered line gets power.
        
        queue = deque(sources)
        visited = set(sources)

        while queue:
            cx, cy = queue.popleft()
            
            # Check neighbors
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < grid.width and 0 <= ny < grid.height:
                    neighbor = grid.tiles[nx][ny]
                    
                    if (nx, ny) not in visited:
                        # Power conductors: power_line (overlay), power_plant, and RCI zones
                        if neighbor.has_power_line or neighbor.type in ['power_plant', 'residential', 'commercial', 'industrial']:
                            neighbor.is_powered = True
                            visited.add((nx, ny))
                            queue.append((nx, ny))
                        # Roads receive power but don't propagate it
                        elif neighbor.type == 'road':
                            neighbor.is_powered = True


class GrowthSystem:
    def update(self, grid):
        # Very basic growth logic
        # 1. Needs Power
        # 2. Needs Road Access (adjacent to road)
        # 3. Random chance to grow
        
        for x in range(grid.width):
            for y in range(grid.height):
                tile = grid.tiles[x][y]
                if tile.type in ['residential', 'commercial', 'industrial']:
                    if tile.is_powered:
                        # Check for road adjacency
                        has_road = False
                        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < grid.width and 0 <= ny < grid.height:
                                if grid.tiles[nx][ny].type == 'road':
                                    has_road = True
                                    break
                        
                        if has_road:
                            # Grow population
                            if random.random() < 0.01: # 1% chance per tick
                                tile.population = min(tile.population + 1, 10)
                        else:
                             # Decay if no road
                             if random.random() < 0.05:
                                 tile.population = max(tile.population - 1, 0)
                    else:
                        # Decay if no power
                        if random.random() < 0.1:
                            tile.population = max(tile.population - 1, 0)


class DemandSystem:
    """
    Calculates RCI (Residential/Commercial/Industrial) demand.
    Demand ranges from -1.0 (oversupply) to 1.0 (high demand).
    """
    
    def __init__(self):
        self.residential = 0.0
        self.commercial = 0.0
        self.industrial = 0.0
    
    def update(self, grid):
        """Recalculate demand based on current city state."""
        # Count total population by zone type
        r_pop = 0  # Residential population (workers/consumers)
        c_pop = 0  # Commercial population (jobs/services)
        i_pop = 0  # Industrial population (jobs/goods)
        
        # Count zones
        r_zones = 0
        c_zones = 0
        i_zones = 0
        
        for x in range(grid.width):
            for y in range(grid.height):
                tile = grid.tiles[x][y]
                if tile.type == 'residential':
                    r_pop += tile.population
                    r_zones += 1
                elif tile.type == 'commercial':
                    c_pop += tile.population
                    c_zones += 1
                elif tile.type == 'industrial':
                    i_pop += tile.population
                    i_zones += 1
        
        # Calculate demand based on balance
        # Residential demand: driven by available jobs (C + I)
        total_jobs = c_pop + i_pop
        if r_pop == 0:
            self.residential = 0.5  # Need some residents to start
        else:
            # More jobs than workers = need more residential
            job_ratio = total_jobs / r_pop if r_pop > 0 else 1.0
            self.residential = max(-1.0, min(1.0, (job_ratio - 1.0)))
        
        # Commercial demand: driven by residential population
        if r_pop == 0:
            self.commercial = -0.5  # No customers
        else:
            # Need commercial to serve residents
            service_ratio = c_pop / r_pop if r_pop > 0 else 0
            # Ideal ratio is about 0.3 commercial per resident
            self.commercial = max(-1.0, min(1.0, (0.3 - service_ratio) * 3))
        
        # Industrial demand: driven by commercial (goods needed)
        if c_pop == 0:
            self.industrial = 0.3  # Base industrial need
        else:
            # Industrial supplies commercial
            supply_ratio = i_pop / c_pop if c_pop > 0 else 0
            # Ideal ratio is about 0.5 industrial per commercial
            self.industrial = max(-1.0, min(1.0, (0.5 - supply_ratio) * 2))
        
        # Boost demand for empty zone types to encourage building
        if r_zones == 0:
            self.residential = 1.0
        if c_zones == 0 and r_pop > 5:
            self.commercial = 0.8
        if i_zones == 0 and c_pop > 3:
            self.industrial = 0.8
