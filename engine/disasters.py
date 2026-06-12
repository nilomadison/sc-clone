"""
Disasters: classic SimCity-style catastrophes, triggered from the D panel.

Instant disasters (fire, earthquake) mutate the grid immediately. Moving
disasters (tornado, monster) become an active walker that steps once per
simulation tick via update(), damaging everything in its path.
"""

import random

from engine.fire import FireSystem
from engine.tiles import ZONE_TYPES

# Disaster names in panel order
DISASTERS = ['fire', 'tornado', 'earthquake', 'monster']

MESSAGES = {
    'fire': 'A fire has broken out!',
    'tornado': 'Tornado warning!',
    'earthquake': 'Earthquake!',
    'monster': 'A monster is attacking the city!',
}

# Building tile types disasters can damage
BUILDING_TYPES = ('residential', 'commercial', 'industrial',
                  'power_plant', 'police', 'fire_station')


class DisasterSystem:
    EARTHQUAKE_SHOCKS = 40       # Random tiles shaken per earthquake
    EARTHQUAKE_IGNITE_CHANCE = 0.15
    WALKER_LIFETIME = 40         # Ticks a tornado/monster stays active
    MONSTER_IGNITE_CHANCE = 0.3  # Monster breathes fire

    def __init__(self):
        self.active = None  # {'kind', 'x', 'y', 'dx', 'dy', 'ticks'} or None
        self.events = []    # ('disaster', name) and ('collapse', x, y)

    def trigger(self, name, grid, fire_system):
        """Start a disaster. Returns True if it could be triggered."""
        if name == 'fire':
            ok = self._trigger_fire(grid, fire_system)
        elif name == 'earthquake':
            ok = self._trigger_earthquake(grid, fire_system)
        elif name in ('tornado', 'monster'):
            ok = self._spawn_walker(name, grid)
        else:
            return False

        if ok:
            self.events.append(('disaster', name))
        return ok

    def update(self, grid, fire_system):
        """Advance the active walker (if any) one step."""
        if self.active is None:
            return

        walker = self.active
        walker['ticks'] -= 1
        if walker['ticks'] <= 0:
            self.active = None
            return

        # Drift with a random wobble, bouncing off map edges
        if random.random() < 0.3:
            walker['dx'], walker['dy'] = random.choice(
                [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)])
        walker['x'] = max(0, min(grid.width - 1, walker['x'] + walker['dx']))
        walker['y'] = max(0, min(grid.height - 1, walker['y'] + walker['dy']))

        # Trash the tile underneath and its neighbors
        ignite = self.MONSTER_IGNITE_CHANCE if walker['kind'] == 'monster' else 0.0
        for dx, dy in [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)]:
            damage = 0.6 if (dx, dy) == (0, 0) else 0.25
            self._damage_tile(grid, fire_system,
                              walker['x'] + dx, walker['y'] + dy, damage, ignite)

    def _trigger_fire(self, grid, fire_system):
        """Ignite a random flammable building."""
        candidates = [
            (x, y) for x, y in grid.positions(*FireSystem.IGNITABLE_TYPES)
            if not grid.tiles[x][y].is_on_fire and not grid.tiles[x][y].is_burned]
        if not candidates:
            return False
        x, y = random.choice(candidates)
        fire_system._start_fire(grid.tiles[x][y])
        return True

    def _trigger_earthquake(self, grid, fire_system):
        """Shake random buildings across the whole map; some catch fire."""
        buildings = list(grid.positions(*BUILDING_TYPES))
        roads = list(grid.positions('road'))
        if not buildings and not roads:
            return False

        for x, y in random.sample(buildings, min(self.EARTHQUAKE_SHOCKS, len(buildings))):
            self._damage_tile(grid, fire_system, x, y,
                              random.uniform(0.3, 0.7), self.EARTHQUAKE_IGNITE_CHANCE)

        # Cracked roads
        for x, y in random.sample(roads, min(10, len(roads))):
            if random.random() < 0.5:
                grid.set_tile_type(x, y, 'grass')
        return True

    def _spawn_walker(self, kind, grid):
        """Spawn a tornado/monster aimed across the populated area."""
        # Start near a random zone if any exist, otherwise the map center
        zones = list(grid.positions(*ZONE_TYPES))
        if zones:
            x, y = random.choice(zones)
        else:
            x, y = grid.width // 2, grid.height // 2

        self.active = {
            'kind': kind,
            'x': x, 'y': y,
            'dx': random.choice([-1, 1]), 'dy': random.choice([-1, 1]),
            'ticks': self.WALKER_LIFETIME,
        }
        return True

    def _damage_tile(self, grid, fire_system, x, y, damage, ignite_chance):
        tile = grid.get_tile(x, y)
        if tile is None or tile.type == 'grass' or tile.is_burned:
            return

        if tile.type == 'road':
            # Heavy disasters rip up roads
            if damage >= 0.5 and random.random() < 0.3:
                grid.set_tile_type(x, y, 'grass')
            return

        tile.building_health -= damage
        if tile.building_health <= 0:
            tile.building_health = 0
            tile.is_on_fire = False  # FireSystem._sync_burning cleans up tracking
            tile.fire_intensity = 0.0
            tile.is_burned = True
            tile.population = 0
            self.events.append(('collapse', x, y))
        elif (ignite_chance and not tile.is_on_fire and
                FireSystem.FLAMMABILITY.get(tile.type, 0.0) > 0 and
                random.random() < ignite_chance):
            fire_system._start_fire(tile)
