"""
Terrain generation for new games: a river, lakes, and tree clusters.

Pure random-walk/blob growth — no noise library needed. Only ever converts
grass tiles, so it can safely run on a fresh Grid.
"""

import random


def generate(grid, seed=None):
    """Generate terrain on a fresh grid (river, lakes, forests)."""
    rng = random.Random(seed)
    _carve_river(grid, rng)
    for _ in range(rng.randint(2, 4)):
        _grow_blob(grid, rng, 'water', rng.randint(30, 80))
    for _ in range(rng.randint(6, 10)):
        _grow_blob(grid, rng, 'trees', rng.randint(20, 50))


def _carve_river(grid, rng):
    """A wobbling river, 2-3 tiles wide, crossing the whole map."""
    vertical = rng.random() < 0.5
    length = grid.height if vertical else grid.width
    span = grid.width if vertical else grid.height
    pos = rng.randint(span // 4, 3 * span // 4)
    width = rng.randint(2, 3)

    for i in range(length):
        pos += rng.choice([-1, 0, 0, 1])
        pos = max(2, min(span - 3 - width, pos))
        for w in range(width):
            if vertical:
                grid.set_tile_type(pos + w, i, 'water')
            else:
                grid.set_tile_type(i, pos + w, 'water')


def _grow_blob(grid, rng, tile_type, target_size):
    """Grow a roughly circular blob of tile_type from a random grass seed."""
    for _ in range(20):
        cx = rng.randrange(grid.width)
        cy = rng.randrange(grid.height)
        if grid.get_tile(cx, cy).type == 'grass':
            break
    else:
        return

    frontier = [(cx, cy)]
    placed = 0
    while frontier and placed < target_size:
        x, y = frontier.pop(rng.randrange(len(frontier)))
        tile = grid.get_tile(x, y)
        if tile is None or tile.type != 'grass':
            continue
        grid.set_tile_type(x, y, tile_type)
        placed += 1
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            if rng.random() < 0.8:
                frontier.append((x + dx, y + dy))
