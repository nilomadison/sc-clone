"""Tests for the disasters system (v0.7.0)."""
import random

import pytest

from engine.disasters import DISASTERS, MESSAGES, DisasterSystem
from engine.fire import FireSystem
from engine.grid import Grid


@pytest.fixture(autouse=True)
def seeded_random():
    random.seed(31)


def make_city():
    """A 30x30 city block for disasters to chew on."""
    grid = Grid(30, 30)
    for x in range(5, 25):
        for y in range(5, 25):
            if x % 4 == 0:
                grid.set_tile_type(x, y, 'road')
            else:
                grid.set_tile_type(x, y, 'residential')
                grid.tiles[x][y].population = 5
    return grid


def all_tiles(grid):
    return [t for row in grid.tiles for t in row]


def test_every_disaster_has_a_message():
    assert set(MESSAGES) == set(DISASTERS)


def test_fire_disaster_ignites_a_building():
    grid = make_city()
    fs = FireSystem()
    ds = DisasterSystem()

    assert ds.trigger('fire', grid, fs)
    assert fs.get_fire_count() == 0  # Not yet ticked
    assert len(fs.burning) == 1
    assert ('disaster', 'fire') in ds.events


def test_fire_disaster_fails_on_empty_map():
    grid = Grid(10, 10)
    ds = DisasterSystem()
    assert not ds.trigger('fire', grid, FireSystem())
    assert ds.events == []


def test_earthquake_damages_buildings():
    grid = make_city()
    ds = DisasterSystem()

    assert ds.trigger('earthquake', grid, FireSystem())

    damaged = [t for t in all_tiles(grid)
               if t.building_health < 1.0 or t.is_burned]
    assert len(damaged) >= 20


def test_tornado_walks_and_expires():
    grid = make_city()
    fs = FireSystem()
    ds = DisasterSystem()

    assert ds.trigger('tornado', grid, fs)
    assert ds.active is not None
    assert ds.active['kind'] == 'tornado'

    for _ in range(DisasterSystem.WALKER_LIFETIME + 1):
        ds.update(grid, fs)

    assert ds.active is None
    damaged = [t for t in all_tiles(grid)
               if t.building_health < 1.0 or t.is_burned]
    assert damaged  # The tornado broke things on its way through


def test_monster_damages_and_emits_collapses():
    grid = make_city()
    fs = FireSystem()
    ds = DisasterSystem()

    assert ds.trigger('monster', grid, fs)
    for _ in range(DisasterSystem.WALKER_LIFETIME + 1):
        ds.update(grid, fs)

    damaged = [t for t in all_tiles(grid)
               if t.building_health < 1.0 or t.is_burned]
    assert damaged
    # The monster's 0.6 center damage twice over a tile collapses it
    collapses = [e for e in ds.events if e[0] == 'collapse']
    assert collapses
    for _, x, y in collapses:
        assert grid.tiles[x][y].is_burned
        assert grid.tiles[x][y].population == 0
