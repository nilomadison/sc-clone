"""
Fire System for SimCity Clone v0.4.0

Manages fire ignition, spread, damage, and extinguishing mechanics.
"""

import random


class FireSystem:
    """System for managing fire mechanics in the city."""

    # Fire configuration
    IGNITION_CHANCE_INDUSTRIAL = 0.0001  # Per tick chance for industrial zones
    IGNITION_CHANCE_POWER_PLANT = 0.00005  # Per tick chance for power plants
    IGNITION_CHANCE_CRIME_BONUS = 0.00005  # Additional chance based on crime level

    SPREAD_BASE_CHANCE = 0.03  # Base chance to spread to adjacent tile
    SPREAD_INTENSITY_MULTIPLIER = 0.1  # How much intensity affects spread chance

    DAMAGE_PER_TICK = 0.02  # Health damage per tick while on fire
    INTENSITY_GROWTH = 0.03  # How fast fire intensity grows
    INTENSITY_DECAY = 0.05  # How fast fire intensity decays (when fighting)

    FIRE_STATION_RADIUS = 8  # Coverage radius for fire stations
    EXTINGUISH_TICKS_COVERED = 3  # Ticks to extinguish in coverage
    EXTINGUISH_TICKS_UNCOVERED = 6  # Ticks to extinguish outside coverage

    # Flammability by tile type (0.0 = non-flammable, 1.0 = highly flammable)
    FLAMMABILITY = {
        'grass': 0.1,
        'road': 0.0,  # Roads don't burn
        'residential': 0.8,
        'commercial': 0.7,
        'industrial': 0.6,
        'power_plant': 0.4,
        'power_line': 0.0,  # Power lines don't burn (overlay)
        'police': 0.5,
        'fire_station': 0.3,  # Fire stations are more fire-resistant
    }

    def __init__(self):
        self.fire_stations = []  # List of (x, y) positions
        self.active_fires = []  # List of tiles currently on fire
        self.fire_ticks = {}  # Track how long each tile has been on fire: {(x,y): ticks}

    def update(self, grid):
        """Main update loop for fire system. Call once per game tick."""
        self._update_fire_stations(grid)
        self._try_ignite_fires(grid)
        self._spread_fires(grid)
        self._apply_fire_damage(grid)
        self._try_extinguish_fires(grid)
        self._update_active_fires(grid)

    def _update_fire_stations(self, grid):
        """Scan grid for fire station positions."""
        self.fire_stations = []
        for x in range(grid.width):
            for y in range(grid.height):
                tile = grid.get_tile(x, y)
                if tile and tile.type == 'fire_station':
                    self.fire_stations.append((x, y))

    def _try_ignite_fires(self, grid):
        """Attempt to start new fires based on tile types and conditions."""
        for x in range(grid.width):
            for y in range(grid.height):
                tile = grid.get_tile(x, y)
                if tile is None or tile.is_on_fire or tile.is_burned:
                    continue

                ignition_chance = 0.0

                # Industrial zones can catch fire
                if tile.type == 'industrial':
                    ignition_chance += self.IGNITION_CHANCE_INDUSTRIAL

                # Power plants can catch fire
                elif tile.type == 'power_plant':
                    ignition_chance += self.IGNITION_CHANCE_POWER_PLANT

                # Crime increases fire risk (arson)
                ignition_chance += tile.crime_level * self.IGNITION_CHANCE_CRIME_BONUS

                # Roll for ignition
                if ignition_chance > 0 and random.random() < ignition_chance:
                    self._start_fire(tile)

    def _start_fire(self, tile):
        """Ignite a tile."""
        tile.is_on_fire = True
        tile.fire_intensity = 0.3  # Starting intensity
        self.fire_ticks[(tile.x, tile.y)] = 0

    def _spread_fires(self, grid):
        """Spread fire from burning tiles to adjacent tiles."""
        new_fires = []

        for x in range(grid.width):
            for y in range(grid.height):
                tile = grid.get_tile(x, y)
                if tile is None or not tile.is_on_fire:
                    continue

                # Check each neighbor
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    neighbor = grid.get_tile(x + dx, y + dy)
                    if neighbor is None:
                        continue
                    if neighbor.is_on_fire or neighbor.is_burned:
                        continue

                    # Calculate spread chance
                    spread_chance = self._calculate_spread_chance(tile, neighbor)

                    # Reduce spread in fire station coverage
                    if self._is_in_coverage(neighbor.x, neighbor.y):
                        spread_chance *= 0.5

                    if random.random() < spread_chance:
                        new_fires.append(neighbor)

        # Ignite new fires
        for tile in new_fires:
            if not tile.is_on_fire:  # Double-check to avoid duplicates
                self._start_fire(tile)

    def _calculate_spread_chance(self, source, target):
        """Calculate probability of fire spreading from source to target."""
        flammability = self.FLAMMABILITY.get(target.type, 0.0)
        if flammability == 0:
            return 0.0

        base_chance = self.SPREAD_BASE_CHANCE * flammability
        intensity_bonus = source.fire_intensity * self.SPREAD_INTENSITY_MULTIPLIER

        return base_chance + intensity_bonus

    def _apply_fire_damage(self, grid):
        """Apply damage to burning tiles and grow fire intensity."""
        for x in range(grid.width):
            for y in range(grid.height):
                tile = grid.get_tile(x, y)
                if tile is None or not tile.is_on_fire:
                    continue

                # Increase fire intensity
                tile.fire_intensity = min(1.0, tile.fire_intensity + self.INTENSITY_GROWTH)

                # Apply damage to building health
                tile.building_health -= self.DAMAGE_PER_TICK * tile.fire_intensity

                # If building is destroyed, mark as burned rubble
                if tile.building_health <= 0:
                    tile.building_health = 0
                    tile.is_on_fire = False
                    tile.fire_intensity = 0.0
                    tile.is_burned = True
                    tile.population = 0
                    # Remove from fire tracking
                    self.fire_ticks.pop((x, y), None)

    def _try_extinguish_fires(self, grid):
        """Attempt to extinguish fires, especially in fire station coverage."""
        tiles_to_extinguish = []

        for x in range(grid.width):
            for y in range(grid.height):
                tile = grid.get_tile(x, y)
                if tile is None or not tile.is_on_fire:
                    continue

                # Increment fire tick counter
                key = (x, y)
                self.fire_ticks[key] = self.fire_ticks.get(key, 0) + 1
                ticks = self.fire_ticks[key]

                # Check if fire should be extinguished
                # Only fires within fire station coverage can be extinguished
                # Fires outside coverage burn until the building is destroyed
                if self._is_in_coverage(x, y):
                    if ticks >= self.EXTINGUISH_TICKS_COVERED:
                        tiles_to_extinguish.append(tile)

        # Extinguish fires
        for tile in tiles_to_extinguish:
            self._extinguish_fire(tile)

    def _extinguish_fire(self, tile):
        """Put out a fire on a tile."""
        tile.is_on_fire = False
        tile.fire_intensity = 0.0
        self.fire_ticks.pop((tile.x, tile.y), None)

    def _is_in_coverage(self, x, y):
        """Check if a position is within fire station coverage."""
        for sx, sy in self.fire_stations:
            distance = abs(x - sx) + abs(y - sy)  # Manhattan distance
            if distance <= self.FIRE_STATION_RADIUS:
                return True
        return False

    def _update_active_fires(self, grid):
        """Update the list of tiles currently on fire."""
        self.active_fires = []
        for x in range(grid.width):
            for y in range(grid.height):
                tile = grid.get_tile(x, y)
                if tile and tile.is_on_fire:
                    self.active_fires.append(tile)

    def get_fire_count(self):
        """Return the number of tiles currently on fire."""
        return len(self.active_fires)

    def get_coverage_tiles(self, grid):
        """Return set of (x, y) positions covered by fire stations."""
        covered = set()
        for sx, sy in self.fire_stations:
            for dx in range(-self.FIRE_STATION_RADIUS, self.FIRE_STATION_RADIUS + 1):
                for dy in range(-self.FIRE_STATION_RADIUS, self.FIRE_STATION_RADIUS + 1):
                    if abs(dx) + abs(dy) <= self.FIRE_STATION_RADIUS:
                        x, y = sx + dx, sy + dy
                        if 0 <= x < grid.width and 0 <= y < grid.height:
                            covered.add((x, y))
        return covered
