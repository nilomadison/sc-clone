"""Tests for the v0.7.0 classic gameplay loops: demand-driven growth,
tax-sensitive demand, power plant capacity, land-value taxation, and
building functionality gating."""
import random

import pytest

from engine.crime import CrimeSystem
from engine.economy import EconomySystem
from engine.fire import FireSystem
from engine.grid import Grid
from engine.systems import DemandSystem, GrowthSystem, PowerSystem
from engine.tiles import TILE_TYPES


@pytest.fixture(autouse=True)
def seeded_random():
    random.seed(7)


class FakeDemand:
    def __init__(self, r=0.0, c=0.0, i=0.0):
        self.residential = r
        self.commercial = c
        self.industrial = i


def make_powered_zone_grid(zone='residential', n=30):
    """A row of zones, each powered and road-adjacent."""
    grid = Grid(n + 2, 4)
    for x in range(1, n + 1):
        grid.set_tile_type(x, 1, zone)
        grid.get_tile(x, 1).is_powered = True
        grid.set_tile_type(x, 2, 'road')
    return grid


def total_population(grid):
    return sum(t.population for row in grid.tiles for t in row)


def test_growth_scales_with_demand():
    growth = GrowthSystem()

    grid_high = make_powered_zone_grid()
    for _ in range(200):
        growth.update(grid_high, FakeDemand(r=1.0))
        for x, y in grid_high.positions('residential'):
            grid_high.tiles[x][y].is_powered = True

    grid_zero = make_powered_zone_grid()
    for _ in range(200):
        growth.update(grid_zero, FakeDemand(r=0.0))
        for x, y in grid_zero.positions('residential'):
            grid_zero.tiles[x][y].is_powered = True

    assert total_population(grid_high) > 0
    assert total_population(grid_zero) == 0  # No demand = no growth


def test_negative_demand_shrinks_population():
    growth = GrowthSystem()
    grid = make_powered_zone_grid()
    for x, y in grid.positions('residential'):
        grid.tiles[x][y].population = 10

    start = total_population(grid)
    for _ in range(200):
        growth.update(grid, FakeDemand(r=-1.0))
        for x, y in grid.positions('residential'):
            grid.tiles[x][y].is_powered = True

    assert total_population(grid) < start


def test_high_taxes_suppress_demand():
    grid = Grid(10, 10)
    grid.set_tile_type(2, 2, 'residential')
    grid.get_tile(2, 2).population = 5
    grid.set_tile_type(3, 3, 'commercial')
    grid.get_tile(3, 3).population = 5

    low = DemandSystem()
    low.update(grid, tax_rate=1)
    high = DemandSystem()
    high.update(grid, tax_rate=20)

    assert high.residential < low.residential
    assert high.commercial < low.commercial
    assert high.industrial < low.industrial


def test_power_capacity_brownouts(monkeypatch):
    monkeypatch.setitem(TILE_TYPES['power_plant'], 'power_capacity', 5)

    # A plant feeding a chain of 8 zones: only 5 get power, farthest dark
    grid = Grid(12, 3)
    grid.set_tile_type(0, 1, 'power_plant')
    for x in range(1, 9):
        grid.set_tile_type(x, 1, 'residential')

    power = PowerSystem()
    power.update(grid)

    assert power.capacity == 5
    assert power.used == 5
    powered = [grid.get_tile(x, 1).is_powered for x in range(1, 9)]
    assert powered == [True] * 5 + [False] * 3  # Farthest brown out first


def test_damaged_power_plant_produces_nothing():
    grid = Grid(5, 5)
    grid.set_tile_type(1, 1, 'power_plant')
    grid.set_tile_type(2, 1, 'residential')
    grid.get_tile(1, 1).building_health = 0.1  # Below functional threshold

    power = PowerSystem()
    power.update(grid)

    assert power.capacity == 0
    assert not grid.get_tile(2, 1).is_powered


def test_land_value_scales_tax_income():
    eco = EconomySystem()
    grid = Grid(10, 10)
    grid.set_tile_type(1, 1, 'commercial')
    tile = grid.get_tile(1, 1)
    tile.population = 10
    tile.is_powered = True

    tile.land_value = 50  # Neutral
    assert eco.tax_income_per_tick(grid) == pytest.approx(20.0)

    tile.land_value = 100  # Prime real estate: 1.5x
    assert eco.tax_income_per_tick(grid) == pytest.approx(30.0)

    tile.land_value = 0  # Slum: 0.5x
    assert eco.tax_income_per_tick(grid) == pytest.approx(10.0)


def test_non_functional_zone_pays_no_tax_and_does_not_grow():
    eco = EconomySystem()
    growth = GrowthSystem()
    grid = make_powered_zone_grid(n=5)
    for x, y in grid.positions('residential'):
        tile = grid.tiles[x][y]
        tile.population = 5
        tile.building_health = 0.1  # Below MIN_HEALTH_FUNCTIONAL

    assert eco.tax_income_per_tick(grid) == 0

    start = total_population(grid)
    for _ in range(100):
        growth.update(grid, FakeDemand(r=1.0))
    assert total_population(grid) == start  # Frozen, neither grows nor shrinks


def test_non_functional_police_station_gives_no_coverage():
    grid = Grid(20, 20)
    grid.set_tile_type(10, 10, 'industrial')
    grid.get_tile(10, 10).population = 10
    grid.set_tile_type(11, 10, 'police')

    crime = CrimeSystem()
    crime.update(grid)
    covered_crime = grid.get_tile(10, 10).crime_level

    grid.get_tile(11, 10).building_health = 0.1
    crime.update(grid)
    uncovered_crime = grid.get_tile(10, 10).crime_level

    assert uncovered_crime > covered_crime


def test_non_functional_fire_station_gives_no_coverage():
    grid = Grid(20, 20)
    grid.set_tile_type(5, 5, 'fire_station')

    fs = FireSystem()
    fs.update(grid)
    assert fs.fire_stations == [(5, 5)]

    grid.get_tile(5, 5).building_health = 0.1
    fs.update(grid)
    assert fs.fire_stations == []
