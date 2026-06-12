"""
Save/load serialization for SimCity Clone.

The save format is sparse — only non-default tiles are written — and every
field is read back with a default, so older saves keep loading.
"""

import json
import os

from engine.crime import CrimeSystem
from engine.decay import DecaySystem
from engine.fire import FireSystem
from engine.grid import Grid
from engine.land_value import LandValueSystem
from engine.traffic import TrafficSystem
from engine.zones import Zone

SAVE_VERSION = '0.9.0'
DEFAULT_PATH = 'saves/city.json'


def save_game(game, filepath=DEFAULT_PATH):
    """Serialize game state to JSON. Returns a status message."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    tiles_data = []
    for x in range(game.grid.width):
        for y in range(game.grid.height):
            tile = game.grid.tiles[x][y]
            # Only save non-default tiles to reduce file size
            if (tile.type != 'grass' or tile.has_power_line or tile.population > 0 or
                    tile.is_on_fire or tile.is_burned or tile.building_health < 1.0):
                tiles_data.append({
                    'x': x,
                    'y': y,
                    'type': tile.type,
                    'has_power_line': tile.has_power_line,
                    'population': tile.population,
                    'is_on_fire': tile.is_on_fire,
                    'fire_intensity': tile.fire_intensity,
                    'is_burned': tile.is_burned,
                    'building_health': tile.building_health,
                })

    save_data = {
        'version': SAVE_VERSION,
        'grid': {
            'width': game.grid.width,
            'height': game.grid.height,
            'tiles': tiles_data,
        },
        'zones': [zone.to_dict() for zone in game.grid.zones],
        'economy': game.economy.to_dict(),
        'camera': {
            'x': game.renderer.camera_x,
            'y': game.renderer.camera_y,
        },
        'clock': game.clock.to_dict(),
    }

    with open(filepath, 'w') as f:
        json.dump(save_data, f, indent=2)

    return "Game Saved!"


def load_game(game, filepath=DEFAULT_PATH):
    """Restore game state from a JSON file. Returns (success, message)."""
    if not os.path.exists(filepath):
        return False, "No save file found!"

    try:
        with open(filepath, 'r') as f:
            save_data = json.load(f)

        # Reset grid
        game.grid = Grid(save_data['grid']['width'], save_data['grid']['height'])
        game.renderer.grid = game.grid

        # Restore tiles (set_tile_type keeps the grid's type index in sync)
        for tile_data in save_data['grid']['tiles']:
            x, y = tile_data['x'], tile_data['y']
            tile = game.grid.get_tile(x, y)
            if tile:
                game.grid.set_tile_type(x, y, tile_data['type'])
                tile.has_power_line = tile_data.get('has_power_line', False)
                tile.population = tile_data.get('population', 0)
                tile.is_on_fire = tile_data.get('is_on_fire', False)
                tile.fire_intensity = tile_data.get('fire_intensity', 0.0)
                tile.is_burned = tile_data.get('is_burned', False)
                tile.building_health = tile_data.get('building_health', 1.0)

        # Restore zones and reattach member tiles (pre-0.9 saves have no
        # zones; their RCI tiles grow as legacy single-tile plots)
        for zone_data in save_data.get('zones', []):
            zone = Zone.from_dict(zone_data)
            for x, y in zone.members:
                tile = game.grid.get_tile(x, y)
                if tile is not None and tile.type == zone.type:
                    tile.structure = zone
            game.grid.zones.append(zone)

        # Restore economy, camera, and clock (older saves lack the clock)
        game.economy.from_dict(save_data.get('economy', {}))
        camera_data = save_data.get('camera', {})
        game.renderer.camera_x = camera_data.get('x', 0)
        game.renderer.camera_y = camera_data.get('y', 0)
        game.clock.from_dict(save_data.get('clock', {}))

        # Fresh system instances: the incremental field/fire caches are tied
        # to the old grid
        game.crime_system = CrimeSystem()
        game.land_value_system = LandValueSystem()
        game.fire_system = FireSystem()
        game.fire_system.rebuild(game.grid)
        game.decay_system = DecaySystem()
        game.traffic_system = TrafficSystem()

        # Run systems to refresh derived state
        game.power_system.update(game.grid)
        game.demand_system.update(game.grid)
        game.total_population = game._compute_population()

        return True, "Game Loaded!"
    except Exception as e:
        return False, f"Load failed: {e}"
