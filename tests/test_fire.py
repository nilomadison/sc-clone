import random

import pytest

from engine.economy import EconomySystem
from engine.fire import FireSystem
from engine.grid import Grid


@pytest.fixture(autouse=True)
def seeded_random():
    random.seed(1234)


def make_grid_with_burning_tile(tile_type='industrial', surround='road'):
    """A 20x20 grid with one burning building at (10,10), isolated by firebreaks."""
    grid = Grid(20, 20)
    grid.set_tile_type(10, 10, tile_type)
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        grid.set_tile_type(10 + dx, 10 + dy, surround)
    return grid


def test_grass_and_roads_are_firebreaks():
    fs = FireSystem()
    grid = Grid(5, 5)
    grid.set_tile_type(2, 2, 'industrial')
    source = grid.get_tile(2, 2)
    source.is_on_fire = True
    source.fire_intensity = 1.0

    grass = grid.get_tile(2, 3)
    grid.set_tile_type(2, 1, 'road')
    road = grid.get_tile(2, 1)

    assert fs._calculate_spread_chance(source, grass) == 0.0
    assert fs._calculate_spread_chance(source, road) == 0.0


def test_spread_chance_scales_with_flammability():
    fs = FireSystem()
    grid = Grid(5, 5)
    source = grid.get_tile(2, 2)
    source.fire_intensity = 1.0

    grid.set_tile_type(2, 3, 'residential')
    grid.set_tile_type(2, 1, 'fire_station')
    res_chance = fs._calculate_spread_chance(source, grid.get_tile(2, 3))
    station_chance = fs._calculate_spread_chance(source, grid.get_tile(2, 1))

    expected_res = (fs.SPREAD_BASE_CHANCE + fs.SPREAD_INTENSITY_MULTIPLIER) * 0.8
    assert res_chance == pytest.approx(expected_res)
    # Intensity bonus is gated by flammability too
    assert station_chance == pytest.approx(expected_res * (0.3 / 0.8))


def test_uncovered_fire_burns_out_on_its_own():
    fs = FireSystem()
    grid = make_grid_with_burning_tile()
    tile = grid.get_tile(10, 10)
    fs._start_fire(tile)

    for _ in range(fs.BURN_DURATION + 1):
        fs.update(grid)

    assert not tile.is_on_fire
    assert (10, 10) not in fs.fire_ticks
    # Badly damaged but typically not destroyed
    assert tile.building_health < 0.7
    assert tile.building_health > 0.0
    assert not tile.is_burned


def test_covered_fire_extinguished_quickly_with_minimal_damage():
    fs = FireSystem()
    grid = make_grid_with_burning_tile()
    grid.set_tile_type(12, 10, 'fire_station')
    tile = grid.get_tile(10, 10)
    fs._start_fire(tile)

    for _ in range(fs.EXTINGUISH_TICKS_COVERED + 1):
        fs.update(grid)

    assert not tile.is_on_fire
    assert tile.building_health > 0.85


def test_zero_funding_halves_coverage_radius():
    fs = FireSystem()
    fs.fire_funding = 0.0
    fs.fire_stations = [(0, 0)]
    # Distance 6 is inside the full radius (8) but outside the halved radius (4)
    assert not fs._is_in_coverage(6, 0)
    assert fs._is_in_coverage(4, 0)

    fs.fire_funding = 1.0
    assert fs._is_in_coverage(6, 0)


def test_underfunding_slows_extinguishing():
    fs = FireSystem()
    fs.fire_funding = 1.0
    full = fs.extinguish_ticks()
    fs.fire_funding = 0.5
    half = fs.extinguish_ticks()
    fs.fire_funding = 0.0
    none = fs.extinguish_ticks()

    assert full == pytest.approx(fs.EXTINGUISH_TICKS_COVERED)
    assert full < half < none
    assert none == pytest.approx(fs.BURN_DURATION)


def test_funding_read_from_economy():
    fs = FireSystem()
    eco = EconomySystem()
    eco.service_funding['fire'] = 0.4
    fs.update(Grid(5, 5), eco)
    assert fs.fire_funding == 0.4


def test_non_flammable_tiles_never_ignite_even_with_crime():
    fs = FireSystem()
    grid = Grid(5, 5)
    grid.set_tile_type(2, 2, 'road')
    tile = grid.get_tile(2, 2)
    tile.crime_level = 1.0

    for _ in range(2000):
        fs._try_ignite_fires(grid)

    assert not tile.is_on_fire


def test_fire_can_destroy_building_if_reignited_repeatedly():
    """Sanity check: total destruction still possible, leaving burned rubble."""
    fs = FireSystem()
    grid = make_grid_with_burning_tile()
    tile = grid.get_tile(10, 10)

    # Burn it down across multiple fires
    for _ in range(5):
        if tile.is_burned:
            break
        fs._start_fire(tile)
        for _ in range(fs.BURN_DURATION + 1):
            fs.update(grid)

    assert tile.is_burned
    assert tile.building_health == 0
    assert tile.population == 0
    assert not tile.is_on_fire
