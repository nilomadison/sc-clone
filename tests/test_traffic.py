"""Tests for the traffic simulation (v0.9.0)."""
import random

import pytest

from engine.crime import CrimeSystem
from engine.grid import Grid
from engine.land_value import LandValueSystem
from engine.systems import GrowthSystem
from engine.traffic import TrafficSystem
from engine.zones import Zone, ZONE_SIZE


@pytest.fixture(autouse=True)
def seeded_random():
    random.seed(13)


class FakeDemand:
    def __init__(self, r=0.0, c=0.0, i=0.0):
        self.residential = r
        self.commercial = c
        self.industrial = i


def make_zone(grid, x, y, zone_type, powered=True):
    members = [(x + dx, y + dy) for dx in range(ZONE_SIZE) for dy in range(ZONE_SIZE)]
    zone = Zone(zone_type, members)
    for mx, my in members:
        grid.set_tile_type(mx, my, zone_type)
        grid.tiles[mx][my].structure = zone
        grid.tiles[mx][my].is_powered = powered
    grid.zones.append(zone)
    return zone


def run_routing(traffic, grid, ticks=10):
    """Run enough ticks for the staggered router to cover every plot."""
    for _ in range(ticks):
        traffic.update(grid)


def test_trip_grants_access_and_lays_traffic():
    grid = Grid(20, 20)
    res = make_zone(grid, 2, 2, 'residential')
    com = make_zone(grid, 10, 2, 'commercial')
    # Road connecting the two zones along y=5
    for x in range(2, 13):
        grid.set_tile_type(x, 5, 'road')

    traffic = TrafficSystem()
    run_routing(traffic, grid)

    assert res.has_access
    assert com.has_access
    road_traffic = sum(grid.tiles[x][5].traffic for x in range(2, 13))
    assert road_traffic > 0


def test_no_destination_blocks_growth():
    grid = Grid(20, 20)
    res = make_zone(grid, 2, 2, 'residential')  # No jobs anywhere
    for x in range(2, 13):
        grid.set_tile_type(x, 5, 'road')

    traffic = TrafficSystem()
    run_routing(traffic, grid)
    assert not res.has_access

    growth = GrowthSystem()
    for _ in range(300):
        growth.update(grid, FakeDemand(r=1.0))
    assert res.population(grid) == 0


def test_destination_beyond_max_distance_is_unreachable():
    grid = Grid(80, 10)
    res = make_zone(grid, 1, 1, 'residential')
    com = make_zone(grid, 70, 1, 'commercial')
    # A 60+ tile road — beyond MAX_TRIP_DISTANCE (30)
    for x in range(1, 73):
        grid.set_tile_type(x, 5, 'road')

    traffic = TrafficSystem()
    run_routing(traffic, grid)

    assert not res.has_access


def test_traffic_decays_without_trips():
    grid = Grid(10, 10)
    grid.set_tile_type(5, 5, 'road')
    grid.get_tile(5, 5).traffic = 50.0

    traffic = TrafficSystem()
    for _ in range(50):
        traffic.update(grid)

    assert grid.get_tile(5, 5).traffic < 10.0


def test_legacy_tile_routing():
    grid = Grid(20, 20)
    grid.set_tile_type(2, 2, 'industrial')  # Unzoned legacy plot
    grid.set_tile_type(2, 3, 'road')
    grid.set_tile_type(2, 4, 'commercial')

    traffic = TrafficSystem()
    run_routing(traffic, grid)
    assert grid.get_tile(2, 2).has_access

    # Remove the destination: access is lost on the next routing pass
    grid.set_tile_type(2, 4, 'grass')
    run_routing(traffic, grid)
    assert not grid.get_tile(2, 2).has_access


def test_busy_roads_lower_nearby_land_value():
    def land_value_next_to_road(traffic_level):
        grid = Grid(20, 20)
        for x in range(5, 15):
            grid.set_tile_type(x, 10, 'road')
            grid.tiles[x][10].traffic = traffic_level
        CrimeSystem().update(grid)
        system = LandValueSystem()
        system.update(grid)
        return grid.get_tile(10, 11).land_value

    assert land_value_next_to_road(60.0) < land_value_next_to_road(0.0)
