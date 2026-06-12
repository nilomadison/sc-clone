"""Tests for terrain generation and the flood disaster (v0.8.0)."""
import random

import pygame
import pytest

from engine import mapgen
from engine.disasters import DisasterSystem
from engine.fire import FireSystem
from engine.grid import Grid


@pytest.fixture(autouse=True)
def seeded_random():
    random.seed(77)


def test_mapgen_produces_water_and_trees():
    grid = Grid(100, 100)
    mapgen.generate(grid, seed=42)

    water = grid.count('water')
    trees = grid.count('trees')
    # River (~200-300 tiles) plus lakes
    assert water > 150
    assert trees > 80
    # Terrain shouldn't drown the map
    assert water + trees < 100 * 100 * 0.3


def test_mapgen_deterministic_with_seed():
    grid_a = Grid(60, 60)
    grid_b = Grid(60, 60)
    mapgen.generate(grid_a, seed=5)
    mapgen.generate(grid_b, seed=5)
    assert set(grid_a.positions('water')) == set(grid_b.positions('water'))
    assert set(grid_a.positions('trees')) == set(grid_b.positions('trees'))


def test_fire_spreads_into_trees_but_not_water():
    fs = FireSystem()
    grid = Grid(5, 5)
    grid.set_tile_type(2, 2, 'industrial')
    source = grid.get_tile(2, 2)
    source.fire_intensity = 1.0

    grid.set_tile_type(2, 3, 'trees')
    grid.set_tile_type(2, 1, 'water')

    assert fs._calculate_spread_chance(source, grid.get_tile(2, 3)) > 0
    assert fs._calculate_spread_chance(source, grid.get_tile(2, 1)) == 0.0


def test_flood_spreads_and_recedes():
    grid = Grid(20, 20)
    # A pond with houses on the shore
    for x in range(8, 12):
        for y in range(8, 12):
            grid.set_tile_type(x, y, 'water')
    grid.set_tile_type(7, 8, 'residential')
    grid.get_tile(7, 8).population = 5

    ds = DisasterSystem()
    fs = FireSystem()
    assert ds.trigger('flood', grid, fs)
    flooded_at_peak = grid.count('water')
    assert flooded_at_peak > 16  # Original pond plus flooding

    # Let the flood run its course (duration + spread headroom)
    for _ in range(DisasterSystem.FLOOD_DURATION * 3):
        ds.update(grid, fs)

    assert not ds.flooded
    assert grid.count('water') == 16  # Only the original pond remains


def test_flood_requires_water():
    grid = Grid(10, 10)
    ds = DisasterSystem()
    assert not ds.trigger('flood', grid, FireSystem())


class TestWaterPlacement:
    @pytest.fixture()
    def game(self):
        from engine.game import Game
        g = Game(generate_terrain=False)
        yield g
        pygame.quit()

    def test_cannot_build_or_bulldoze_water(self, game):
        game.grid.set_tile_type(5, 5, 'water')
        start = game.economy.money

        for tool in ('residential', 'road', 'power_plant', 'grass'):
            game.current_tool = tool
            game.apply_tool(5, 5)
            assert game.grid.get_tile(5, 5).type == 'water'
        assert game.economy.money == start

    def test_power_lines_can_cross_water(self, game):
        game.grid.set_tile_type(5, 5, 'water')
        game.current_tool = 'power_line'
        game.apply_tool(5, 5)
        assert game.grid.get_tile(5, 5).has_power_line

    def test_trees_tool_plants_trees(self, game):
        game.current_tool = 'trees'
        start = game.economy.money
        game.apply_tool(3, 3)
        assert game.grid.get_tile(3, 3).type == 'trees'
        assert game.economy.money == start - 25
