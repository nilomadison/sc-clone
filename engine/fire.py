"""
Fire System for SimCity Clone v0.5.0

Manages fire ignition, spread, damage, and extinguishing mechanics.

Design (classic SimCity style):
- Fires are rare events that burn out on their own after BURN_DURATION ticks,
  badly damaging (but usually not destroying) the building.
- Spread is fully gated by flammability, so grass and roads act as firebreaks.
- Fire stations extinguish fires in their radius much faster; fire funding
  scales both the effective radius and the extinguish speed.
"""

import random


class FireSystem:
    """System for managing fire mechanics in the city."""

    # Ignition (per tile, per tick — ticks run ~1/sec)
    IGNITION_CHANCE_INDUSTRIAL = 0.00001
    IGNITION_CHANCE_POWER_PLANT = 0.000005
    IGNITION_CHANCE_CRIME_BONUS = 0.000005  # Arson, scaled by crime level

    # Spread: chance = (base + intensity * mult) * flammability, per neighbor per tick.
    # Tuned so a fire's reproduction rate in dense city is near 1 — it consumes a
    # small cluster, not the map.
    SPREAD_BASE_CHANCE = 0.005
    SPREAD_INTENSITY_MULTIPLIER = 0.01

    DAMAGE_PER_TICK = 0.02  # Health damage per tick while on fire (scaled by intensity)
    INTENSITY_GROWTH = 0.03  # How fast fire intensity grows

    BURN_DURATION = 40  # Ticks before a fire burns out on its own
    FIRE_STATION_RADIUS = 8  # Coverage radius at full funding
    EXTINGUISH_TICKS_COVERED = 3  # Ticks to extinguish in coverage at full funding

    # Flammability by tile type (0.0 = non-flammable / firebreak)
    FLAMMABILITY = {
        'grass': 0.0,  # Open land is a firebreak
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
        self.fire_funding = 1.0  # Mirrors economy.service_funding['fire']
        self.events = []  # ('collapse', x, y) events for the notification system

    def update(self, grid, economy=None):
        """Main update loop for fire system. Call once per game tick."""
        if economy is not None:
            self.fire_funding = economy.service_funding.get('fire', 1.0)
        self._update_fire_stations(grid)
        self._try_ignite_fires(grid)
        self._spread_fires(grid)
        self._apply_fire_damage(grid)
        self._try_extinguish_fires(grid)
        self._update_active_fires(grid)

    def effective_radius(self):
        """Coverage radius scaled by funding: 50% radius at zero funding."""
        return self.FIRE_STATION_RADIUS * (0.5 + 0.5 * self.fire_funding)

    def extinguish_ticks(self):
        """Ticks to put out a covered fire; underfunding degrades toward burnout."""
        return self.EXTINGUISH_TICKS_COVERED + (1.0 - self.fire_funding) * (
            self.BURN_DURATION - self.EXTINGUISH_TICKS_COVERED)

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

                # Only flammable tiles can ignite
                if self.FLAMMABILITY.get(tile.type, 0.0) <= 0:
                    continue

                ignition_chance = 0.0

                if tile.type == 'industrial':
                    ignition_chance += self.IGNITION_CHANCE_INDUSTRIAL
                elif tile.type == 'power_plant':
                    ignition_chance += self.IGNITION_CHANCE_POWER_PLANT

                # Crime increases fire risk (arson) — buildings only
                ignition_chance += tile.crime_level * self.IGNITION_CHANCE_CRIME_BONUS

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
        if flammability <= 0:
            return 0.0

        return (self.SPREAD_BASE_CHANCE +
                source.fire_intensity * self.SPREAD_INTENSITY_MULTIPLIER) * flammability

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
                    self.events.append(('collapse', x, y))

    def _try_extinguish_fires(self, grid):
        """Extinguish fires: fast in fire station coverage, by burnout elsewhere."""
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

                if self._is_in_coverage(x, y) and ticks >= self.extinguish_ticks():
                    tiles_to_extinguish.append(tile)
                elif ticks >= self.BURN_DURATION:
                    # Fires burn out on their own
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
        radius = self.effective_radius()
        for sx, sy in self.fire_stations:
            distance = abs(x - sx) + abs(y - sy)  # Manhattan distance
            if distance <= radius:
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
        radius = int(self.effective_radius())
        for sx, sy in self.fire_stations:
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if abs(dx) + abs(dy) <= radius:
                        x, y = sx + dx, sy + dy
                        if 0 <= x < grid.width and 0 <= y < grid.height:
                            covered.add((x, y))
        return covered
