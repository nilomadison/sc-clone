"""Tests for 3x3 zones with density tiers (v0.9.0)."""
import random

import pygame
import pytest

from engine.grid import Grid
from engine.systems import GrowthSystem
from engine.zones import TIER_TILE_CAP, ZONE_SIZE, Zone, stamps_for_rect


@pytest.fixture(autouse=True)
def seeded_random():
    random.seed(11)


class FakeDemand:
    def __init__(self, r=0.0, c=0.0, i=0.0):
        self.residential = r
        self.commercial = c
        self.industrial = i


def make_zone(grid, x, y, zone_type='residential', powered=True):
    """Manually plumb a 3x3 zone (as Game._place_zone_stamp would)."""
    members = [(x + dx, y + dy) for dx in range(ZONE_SIZE) for dy in range(ZONE_SIZE)]
    zone = Zone(zone_type, members)
    for mx, my in members:
        grid.set_tile_type(mx, my, zone_type)
        grid.tiles[mx][my].structure = zone
        grid.tiles[mx][my].is_powered = powered
    grid.zones.append(zone)
    return zone


# ---------------------------------------------------------------------------
# Stamp geometry
# ---------------------------------------------------------------------------

def test_stamps_snap_across_drag_rect():
    assert stamps_for_rect(2, 2, 7, 7) == [(2, 2), (2, 5), (5, 2), (5, 5)]


def test_tiny_rect_yields_one_centered_stamp():
    assert stamps_for_rect(5, 5, 5, 5) == [(4, 4)]


# ---------------------------------------------------------------------------
# Growth and density tiers
# ---------------------------------------------------------------------------

def test_zone_grows_through_density_tiers():
    grid = Grid(12, 12)
    zone = make_zone(grid, 4, 4)
    for y in range(4, 7):
        grid.set_tile_type(7, y, 'road')

    growth = GrowthSystem()
    for _ in range(800):
        growth.update(grid, FakeDemand(r=1.0))

    assert zone.density == 3
    assert zone.population(grid) >= 80  # Near the 9 * 10 tier-3 cap


def test_zone_population_capped_by_tier():
    grid = Grid(12, 12)
    zone = make_zone(grid, 4, 4)
    grid.set_tile_type(7, 4, 'road')

    growth = GrowthSystem()
    # A tier-0 zone can't exceed cap until its average promotes it; population
    # never exceeds the current tier cap times member count
    for _ in range(50):
        growth.update(grid, FakeDemand(r=1.0))
        assert zone.population(grid) <= TIER_TILE_CAP[zone.density] * 9 + 9


def test_dead_zone_pruned_from_grid():
    grid = Grid(12, 12)
    zone = make_zone(grid, 4, 4)
    # A flood (or anything changing tile types) detaches all members
    for mx, my in zone.members:
        grid.set_tile_type(mx, my, 'water')

    GrowthSystem().update(grid)
    assert zone not in grid.zones


def test_legacy_unzoned_tiles_still_grow():
    grid = Grid(10, 10)
    grid.set_tile_type(3, 3, 'residential')
    grid.get_tile(3, 3).is_powered = True
    grid.set_tile_type(3, 4, 'road')

    growth = GrowthSystem()
    for _ in range(300):
        growth.update(grid, FakeDemand(r=1.0))

    assert grid.get_tile(3, 3).population > 0


# ---------------------------------------------------------------------------
# Placement and bulldozing via Game
# ---------------------------------------------------------------------------

class TestZonePlacement:
    @pytest.fixture()
    def game(self):
        from engine.game import Game
        g = Game(generate_terrain=False)
        yield g
        pygame.quit()

    def test_click_stamps_centered_zone(self, game):
        game.current_tool = 'residential'
        start = game.economy.money
        game.apply_tool(5, 5)

        assert len(game.grid.zones) == 1
        zone = game.grid.zones[0]
        assert set(zone.members) == {(x, y) for x in range(4, 7) for y in range(4, 7)}
        for x, y in zone.members:
            assert game.grid.get_tile(x, y).type == 'residential'
            assert game.grid.get_tile(x, y).structure is zone
        # One fee per zone, not per tile
        assert game.economy.money == start - 100

    def test_blocked_stamp_places_nothing(self, game):
        game.grid.set_tile_type(4, 4, 'road')
        game.current_tool = 'commercial'
        start = game.economy.money
        game.apply_tool(5, 5)  # Stamp 4..6 overlaps the road

        assert game.grid.zones == []
        assert game.economy.money == start

    def test_drag_places_snapped_stamps(self, game):
        game.current_tool = 'industrial'
        game.drag_start = (2, 2)
        game.drag_end = (7, 7)
        start = game.economy.money
        game.place_drag_zone()

        assert len(game.grid.zones) == 4
        assert game.economy.money == start - 400
        assert game.grid.count('industrial') == 36

    def test_bulldozing_any_member_clears_whole_zone(self, game):
        game.current_tool = 'residential'
        game.apply_tool(5, 5)
        zone = game.grid.zones[0]
        start = game.economy.money

        game.current_tool = 'grass'
        game.apply_tool(6, 6)  # A corner member

        assert game.grid.zones == []
        for x, y in zone.members:
            assert game.grid.get_tile(x, y).type == 'grass'
            assert game.grid.get_tile(x, y).structure is None
        assert game.economy.money == start - 1  # One bulldoze fee

    def test_cannot_build_over_zone_without_bulldozing(self, game):
        game.current_tool = 'residential'
        game.apply_tool(5, 5)
        start = game.economy.money

        game.current_tool = 'police'
        game.apply_tool(5, 5)

        assert game.grid.get_tile(5, 5).type == 'residential'
        assert game.economy.money == start

    def test_zones_survive_save_load(self, game, tmp_path):
        path = str(tmp_path / 'city.json')
        game.current_tool = 'commercial'
        game.apply_tool(10, 10)
        zone = game.grid.zones[0]
        zone.density = 2
        game.grid.get_tile(10, 10).population = 5

        game.save_game(path)
        game.current_tool = 'grass'
        game.apply_tool(10, 10)  # Bulldoze it all
        assert game.grid.zones == []

        assert game.load_game(path)
        assert len(game.grid.zones) == 1
        loaded = game.grid.zones[0]
        assert loaded.type == 'commercial'
        assert loaded.density == 2
        assert set(loaded.members) == set(zone.members)
        for x, y in loaded.members:
            assert game.grid.get_tile(x, y).structure is loaded
        assert game.grid.get_tile(10, 10).population == 5
