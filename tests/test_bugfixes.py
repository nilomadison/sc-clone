"""Tests for v0.5.0 bug fixes: inert rubble, no-op charging, decay/fire interaction."""
import random

import pygame
import pytest

from engine.decay import DecaySystem
from engine.economy import EconomySystem
from engine.fire import FireSystem
from engine.grid import Grid
from engine.systems import GrowthSystem, PowerSystem


@pytest.fixture(autouse=True)
def seeded_random():
    random.seed(42)


def make_burned_zone(grid, x, y, zone='residential'):
    grid.set_tile_type(x, y, zone)
    tile = grid.get_tile(x, y)
    tile.is_burned = True
    tile.building_health = 0.0
    return tile


def test_rubble_does_not_regrow_population():
    grid = Grid(10, 10)
    tile = make_burned_zone(grid, 5, 5)
    tile.is_powered = True
    grid.set_tile_type(5, 6, 'road')

    growth = GrowthSystem()
    for _ in range(500):
        growth.update(grid)

    assert tile.population == 0


def test_rubble_pays_no_taxes():
    grid = Grid(10, 10)
    tile = make_burned_zone(grid, 5, 5, 'commercial')
    tile.is_powered = True
    tile.population = 10  # Stale population should still not be taxed

    eco = EconomySystem()
    assert eco.tax_income_per_tick(grid) == 0


def test_rubble_does_not_conduct_power():
    grid = Grid(10, 10)
    # plant -> intact zone -> burned zone -> intact zone: power stops at rubble
    grid.set_tile_type(1, 1, 'power_plant')
    grid.set_tile_type(2, 1, 'residential')
    make_burned_zone(grid, 3, 1)
    grid.set_tile_type(4, 1, 'residential')

    PowerSystem().update(grid)

    assert grid.get_tile(2, 1).is_powered
    assert not grid.get_tile(4, 1).is_powered


def test_power_line_still_conducts_over_burned_tile():
    grid = Grid(10, 10)
    grid.set_tile_type(1, 1, 'power_plant')
    burned = make_burned_zone(grid, 2, 1)
    burned.has_power_line = True
    grid.set_tile_type(3, 1, 'residential')

    PowerSystem().update(grid)

    assert grid.get_tile(3, 1).is_powered


def test_repairs_skip_burning_buildings():
    grid = Grid(10, 10)
    grid.set_tile_type(5, 5, 'residential')
    tile = grid.get_tile(5, 5)
    tile.building_health = 0.5
    tile.is_on_fire = True

    decay = DecaySystem()
    decay.update(grid)

    assert tile.building_health == 0.5


def test_fire_destruction_emits_collapse_event():
    fs = FireSystem()
    grid = Grid(10, 10)
    grid.set_tile_type(5, 5, 'residential')
    tile = grid.get_tile(5, 5)
    tile.building_health = 0.01
    fs._start_fire(tile)

    for _ in range(5):
        fs.update(grid)

    assert tile.is_burned
    assert ('collapse', 5, 5) in fs.events


def test_decay_collapse_emits_collapse_event():
    grid = Grid(10, 10)
    grid.set_tile_type(5, 5, 'residential')
    tile = grid.get_tile(5, 5)
    tile.building_health = 0.0

    decay = DecaySystem()
    decay.update(grid)

    assert tile.is_burned
    assert ('collapse', 5, 5) in decay.events


class TestPlacement:
    """Placement charging fixes, via the real Game running headless."""

    @pytest.fixture()
    def game(self):
        from engine.game import Game
        g = Game(generate_terrain=False)
        yield g
        pygame.quit()

    def test_no_charge_for_same_type(self, game):
        game.current_tool = 'road'
        game.apply_tool(5, 5)
        money_after_first = game.economy.money
        game.apply_tool(5, 5)  # Same tile, same type: free no-op
        assert game.economy.money == money_after_first
        assert game.grid.get_tile(5, 5).type == 'road'

    def test_bulldozing_grass_is_free(self, game):
        game.current_tool = 'grass'
        start = game.economy.money
        game.apply_tool(5, 5)
        assert game.economy.money == start

    def test_out_of_bounds_click_is_free(self, game):
        game.current_tool = 'power_plant'
        start = game.economy.money
        game.apply_tool(-5, 200)
        assert game.economy.money == start

    def test_drag_zone_does_not_overwrite_buildings(self, game):
        game.grid.set_tile_type(5, 5, 'power_plant')
        game.current_tool = 'residential'
        game.drag_start = (4, 4)
        game.drag_end = (6, 6)
        start = game.economy.money
        game.place_drag_zone()

        assert game.grid.get_tile(5, 5).type == 'power_plant'
        # Paid for the 8 grass tiles only, not the power plant tile
        assert game.economy.money == start - 8 * 100

    def test_road_perimeter_skips_existing_roads(self, game):
        game.grid.set_tile_type(4, 4, 'road')
        game.current_tool = 'road'
        game.drag_start = (4, 4)
        game.drag_end = (6, 6)
        start = game.economy.money
        game.place_drag_zone()

        # Perimeter of 3x3 is 8 tiles; one was already a road
        assert game.economy.money == start - 7 * 10
