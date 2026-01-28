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

