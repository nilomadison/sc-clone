"""Tests for the v0.6.0 performance refactor: grid index, incremental fields,
and incremental fire tracking. The incremental systems must produce the same
results as the original full-grid gather implementations."""
import random

import pytest

from engine.crime import CRIME_RATES, CRIME_RADIUS, POLICE_RADIUS, CrimeSystem
from engine.fire import FireSystem
from engine.grid import Grid
from engine.land_value import VALUE_MODIFIERS, VALUE_RADIUS, LandValueSystem


# ---------------------------------------------------------------------------
# Grid index
# ---------------------------------------------------------------------------

def test_index_tracks_placement_and_bulldoze():
    grid = Grid(10, 10)
    grid.set_tile_type(3, 4, 'police')
    grid.set_tile_type(5, 6, 'police')
    assert set(grid.positions('police')) == {(3, 4), (5, 6)}
    assert grid.count('police') == 2

    grid.set_tile_type(3, 4, 'grass')  # Bulldoze
    assert set(grid.positions('police')) == {(5, 6)}

    grid.set_tile_type(5, 6, 'road')  # Replace
    assert grid.count('police') == 0
    assert set(grid.positions('road')) == {(5, 6)}


def test_index_positions_multiple_types():
    grid = Grid(10, 10)
    grid.set_tile_type(1, 1, 'residential')
    grid.set_tile_type(2, 2, 'commercial')
    grid.set_tile_type(3, 3, 'road')
    assert set(grid.positions('residential', 'commercial')) == {(1, 1), (2, 2)}


# ---------------------------------------------------------------------------
# Reference (original O(map * radius^2) gather) implementations
# ---------------------------------------------------------------------------

def reference_crime(grid):
    """The original CrimeSystem.update, kept as a behavioral reference."""
    coverage = {}
    for x in range(grid.width):
        for y in range(grid.height):
            if grid.tiles[x][y].type == 'police':
                for dx in range(-POLICE_RADIUS, POLICE_RADIUS + 1):
                    for dy in range(-POLICE_RADIUS, POLICE_RADIUS + 1):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < grid.width and 0 <= ny < grid.height:
                            dist = ((dx ** 2) + (dy ** 2)) ** 0.5
                            if dist <= POLICE_RADIUS:
                                strength = 1.0 - (dist / POLICE_RADIUS)
                                current = coverage.get((nx, ny), 0.0)
                                coverage[(nx, ny)] = min(1.0, current + strength)

    result = {}
    for x in range(grid.width):
        for y in range(grid.height):
            total_crime = 0.0
            for dx in range(-CRIME_RADIUS, CRIME_RADIUS + 1):
                for dy in range(-CRIME_RADIUS, CRIME_RADIUS + 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < grid.width and 0 <= ny < grid.height:
                        neighbor = grid.tiles[nx][ny]
                        crime_rate = CRIME_RATES.get(neighbor.type, 0.0)
                        if crime_rate > 0 and neighbor.population > 0:
                            dist = max(1, ((dx ** 2) + (dy ** 2)) ** 0.5)
                            total_crime += (crime_rate * neighbor.population / 10) / dist
            base = min(1.0, total_crime)
            cov = coverage.get((x, y), 0.0)
            result[(x, y)] = max(0.0, min(1.0, base * (1.0 - cov * 0.8)))
    return result


def reference_land_value(grid):
    """The original LandValueSystem.update, kept as a behavioral reference."""
    result = {}
    for x in range(grid.width):
        for y in range(grid.height):
            total_modifier = 0.0
            for dx in range(-VALUE_RADIUS, VALUE_RADIUS + 1):
                for dy in range(-VALUE_RADIUS, VALUE_RADIUS + 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < grid.width and 0 <= ny < grid.height:
                        modifier = VALUE_MODIFIERS.get(grid.tiles[nx][ny].type, 0)
                        if modifier != 0:
                            dist = max(1, ((dx ** 2) + (dy ** 2)) ** 0.5)
                            total_modifier += modifier / dist
            crime_penalty = grid.tiles[x][y].crime_level * 40
            value = 50 + total_modifier - crime_penalty
            result[(x, y)] = max(0, min(100, int(value)))
    return result


def random_city(seed, size=16):
    random.seed(seed)
    grid = Grid(size, size)
    types = ['grass', 'road', 'residential', 'commercial', 'industrial',
             'police', 'power_plant', 'fire_station']
    for x in range(size):
        for y in range(size):
            t = random.choice(types)
            grid.set_tile_type(x, y, t)
            if t in ('residential', 'commercial', 'industrial'):
                grid.tiles[x][y].population = random.randint(0, 10)
    return grid


def mutate_city(grid, seed):
    random.seed(seed)
    types = ['grass', 'road', 'residential', 'commercial', 'industrial', 'police']
    for _ in range(30):
        x = random.randrange(grid.width)
        y = random.randrange(grid.height)
        t = random.choice(types)
        grid.set_tile_type(x, y, t)
        if t in ('residential', 'commercial', 'industrial'):
            grid.tiles[x][y].population = random.randint(0, 10)


def test_incremental_crime_matches_reference_through_mutations():
    grid = random_city(seed=1)
    system = CrimeSystem()

    for round_no in range(4):
        system.update(grid)
        expected = reference_crime(grid)
        for (x, y), value in expected.items():
            assert grid.tiles[x][y].crime_level == pytest.approx(value, abs=1e-9), \
                f"crime mismatch at ({x},{y}) round {round_no}"
        mutate_city(grid, seed=100 + round_no)


def test_incremental_land_value_matches_reference_through_mutations():
    grid = random_city(seed=2)
    crime = CrimeSystem()
    system = LandValueSystem()

    for round_no in range(4):
        crime.update(grid)  # Land value reads crime levels
        system.update(grid)
        expected = reference_land_value(grid)
        for (x, y), value in expected.items():
            assert grid.tiles[x][y].land_value == value, \
                f"land value mismatch at ({x},{y}) round {round_no}"
        mutate_city(grid, seed=200 + round_no)


# ---------------------------------------------------------------------------
# Incremental fire tracking
# ---------------------------------------------------------------------------

def test_burning_set_self_heals_after_bulldoze():
    fs = FireSystem()
    grid = Grid(10, 10)
    grid.set_tile_type(5, 5, 'industrial')
    fs._start_fire(grid.get_tile(5, 5))
    assert (5, 5) in fs.burning

    grid.set_tile_type(5, 5, 'grass')  # Bulldoze clears is_on_fire
    fs.update(grid)
    assert (5, 5) not in fs.burning
    assert fs.get_fire_count() == 0


def test_rebuild_tracks_loaded_fires():
    fs = FireSystem()
    grid = Grid(10, 10)
    grid.set_tile_type(4, 4, 'residential')
    tile = grid.get_tile(4, 4)
    tile.is_on_fire = True  # As restored by a game load
    tile.fire_intensity = 0.5

    fs.rebuild(grid)
    assert (4, 4) in fs.burning
    assert fs.get_fire_count() == 1

    # Loaded fires keep taking damage and eventually go out
    for _ in range(fs.BURN_DURATION + 1):
        fs.update(grid)
    assert not tile.is_on_fire
    assert tile.building_health < 1.0
