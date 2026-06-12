from collections import deque
import random

from engine.decay import is_functional
from engine.tiles import TILE_TYPES, ZONE_TYPES


class PowerSystem:
    """Propagates power from plants, limited by total plant capacity.

    Each functional power plant supports TILE_TYPES['power_plant']
    ['power_capacity'] zone tiles. The BFS expands outward from the plants,
    so when demand exceeds capacity, the farthest zones brown out first.
    """

    def __init__(self):
        self.capacity = 0  # Total zone tiles the plants can support
        self.used = 0      # Zone tiles actually powered this tick

    def update(self, grid):
        # Reset power for all tiles
        for x in range(grid.width):
            for y in range(grid.height):
                grid.tiles[x][y].is_powered = False

        # Find functional power sources (damaged/burned plants produce nothing)
        sources = []
        for x, y in grid.positions('power_plant'):
            if is_functional(grid.tiles[x][y]):
                sources.append((x, y))
                grid.tiles[x][y].is_powered = True

        self.capacity = len(sources) * TILE_TYPES['power_plant']['power_capacity']
        self.used = 0

        # Propagate power (BFS) through power lines, plants, and intact zones.
        # Zone tiles each consume one unit of capacity; once the budget is
        # spent, further zones stay dark (and don't conduct).
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
                        if neighbor.has_power_line:
                            # Power lines conduct without consuming capacity
                            visited.add((nx, ny))
                            neighbor.is_powered = True
                            queue.append((nx, ny))
                        elif neighbor.type == 'power_plant' and not neighbor.is_burned:
                            visited.add((nx, ny))
                            neighbor.is_powered = True
                            queue.append((nx, ny))
                        elif neighbor.type in ZONE_TYPES and not neighbor.is_burned:
                            # Intact zones consume capacity and conduct onward
                            visited.add((nx, ny))
                            if self.used < self.capacity:
                                self.used += 1
                                neighbor.is_powered = True
                                queue.append((nx, ny))
                        # Roads receive power but don't propagate it
                        elif neighbor.type == 'road':
                            neighbor.is_powered = True


class GrowthSystem:
    """Zone population growth, gated by power, road access, and RCI demand.

    3x3 zones (engine/zones.py) grow as a unit and promote through density
    tiers that raise each member tile's population cap. RCI tiles without a
    zone (pre-0.9 saves, tests) grow as legacy single-tile plots capped at 10.
    """

    GROWTH_CHANCE = 0.04   # Per tile per tick at maximum demand (1.0)
    DECLINE_CHANCE = 0.03  # Per tile per tick at maximum oversupply (-1.0)
    DEFAULT_DEMAND = 0.5   # Used when no demand system is provided

    def update(self, grid, demand=None):
        # 3x3 zones grow as a unit
        for zone in list(grid.zones):
            members = zone.live_members(grid)
            if not members:
                grid.zones.remove(zone)
                continue
            self._update_zone(grid, zone, members, demand)

        # Legacy single-tile plots
        for x, y in grid.positions(*ZONE_TYPES):
            tile = grid.tiles[x][y]
            if tile.structure is None:
                self._grow_tile(grid, tile, cap=10,
                                has_road=tile.has_access and self._has_road(grid, x, y),
                                demand=demand)

    def _update_zone(self, grid, zone, members, demand):
        # A zone needs a road touching it AND a reachable trip destination
        # (TrafficSystem sets has_access)
        has_road = (zone.has_access and
                    any(self._has_road(grid, t.x, t.y) for t in members))
        for tile in members:
            self._grow_tile(grid, tile, cap=zone.tile_cap(),
                            has_road=has_road, demand=demand)
        zone.update_density(grid)

    def _grow_tile(self, grid, tile, cap, has_road, demand):
        # Burned rubble and crumbling buildings don't grow
        if not is_functional(tile):
            return
        if tile.is_powered:
            if has_road:
                demand_value = self._demand_for(tile.type, demand)
                if demand_value > 0:
                    # Grow population, faster under higher demand
                    if random.random() < self.GROWTH_CHANCE * demand_value:
                        tile.population = min(tile.population + 1, cap)
                elif demand_value < 0:
                    # Oversupply: people and businesses move out
                    if random.random() < self.DECLINE_CHANCE * -demand_value:
                        tile.population = max(tile.population - 1, 0)
            else:
                # Decay if no road
                if random.random() < 0.05:
                    tile.population = max(tile.population - 1, 0)
        else:
            # Decay if no power
            if random.random() < 0.1:
                tile.population = max(tile.population - 1, 0)

    def _has_road(self, grid, x, y):
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < grid.width and 0 <= ny < grid.height:
                if grid.tiles[nx][ny].type == 'road':
                    return True
        return False

    def _demand_for(self, zone_type, demand):
        if demand is None:
            return self.DEFAULT_DEMAND
        return {'residential': demand.residential,
                'commercial': demand.commercial,
                'industrial': demand.industrial}[zone_type]


class DemandSystem:
    """
    Calculates RCI (Residential/Commercial/Industrial) demand.
    Demand ranges from -1.0 (oversupply) to 1.0 (high demand).
    High taxes suppress demand; low taxes stimulate it (7% is neutral).
    """

    BASELINE_TAX_RATE = 7
    TAX_DEMAND_SHIFT = 0.05  # Demand shift per % of tax above/below baseline

    def __init__(self):
        self.residential = 0.0
        self.commercial = 0.0
        self.industrial = 0.0

    def update(self, grid, tax_rate=BASELINE_TAX_RATE):
        """Recalculate demand based on current city state."""
        # Population and zone counts by type
        r_pop = sum(grid.tiles[x][y].population for x, y in grid.positions('residential'))
        c_pop = sum(grid.tiles[x][y].population for x, y in grid.positions('commercial'))
        i_pop = sum(grid.tiles[x][y].population for x, y in grid.positions('industrial'))
        
        # Target-based demand: each type chases a target derived from the
        # others, chosen so a balanced city keeps growing (jobs support more
        # residents than they consume — the classic boom loop):
        #   residents chase jobs (with a base attraction so towns bootstrap)
        #   commerce and industry chase the resident population
        r_target = 2.0 * (c_pop + i_pop) + 10
        c_target = 0.3 * r_pop
        i_target = 0.4 * r_pop

        def toward(target, pop):
            return max(-1.0, min(1.0, (target - pop) / max(target, pop, 1)))

        self.residential = toward(r_target, r_pop)
        self.commercial = toward(c_target, c_pop)
        self.industrial = toward(i_target, i_pop)

        # Taxes shift all demand: high rates drive people away, low rates
        # attract them (so 20% tax is no longer free money)
        tax_shift = (self.BASELINE_TAX_RATE - tax_rate) * self.TAX_DEMAND_SHIFT
        self.residential = max(-1.0, min(1.0, self.residential + tax_shift))
        self.commercial = max(-1.0, min(1.0, self.commercial + tax_shift))
        self.industrial = max(-1.0, min(1.0, self.industrial + tax_shift))
