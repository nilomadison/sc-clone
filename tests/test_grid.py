from engine.grid import Grid


def test_get_tile_in_bounds():
    grid = Grid(10, 10)
    tile = grid.get_tile(5, 5)
    assert tile is not None
    assert tile.x == 5 and tile.y == 5
    assert tile.type == 'grass'


def test_get_tile_out_of_bounds():
    grid = Grid(10, 10)
    assert grid.get_tile(-1, 0) is None
    assert grid.get_tile(0, -1) is None
    assert grid.get_tile(10, 0) is None
    assert grid.get_tile(0, 10) is None


def test_set_tile_type_resets_state():
    grid = Grid(10, 10)
    tile = grid.get_tile(3, 3)
    tile.is_powered = True
    tile.population = 5
    grid.set_tile_type(3, 3, 'residential')
    assert tile.type == 'residential'
    assert tile.is_powered is False
    assert tile.population == 0


def test_bulldoze_clears_fire_and_power_line():
    grid = Grid(10, 10)
    grid.set_tile_type(2, 2, 'industrial')
    tile = grid.get_tile(2, 2)
    tile.has_power_line = True
    tile.is_on_fire = True
    tile.fire_intensity = 0.8
    tile.is_burned = True
    tile.building_health = 0.0
    grid.set_tile_type(2, 2, 'grass')
    assert tile.has_power_line is False
    assert tile.is_on_fire is False
    assert tile.fire_intensity == 0.0
    assert tile.is_burned is False
    assert tile.building_health == 1.0


def test_toggle_power_line():
    grid = Grid(10, 10)
    assert grid.toggle_power_line(4, 4)
    assert grid.get_tile(4, 4).has_power_line is True
    assert grid.toggle_power_line(4, 4)
    assert grid.get_tile(4, 4).has_power_line is False


def test_needs_power():
    grid = Grid(10, 10)
    for zone in ['residential', 'commercial', 'industrial']:
        grid.set_tile_type(1, 1, zone)
        assert grid.get_tile(1, 1).needs_power
    for non_zone in ['grass', 'road', 'police', 'fire_station', 'power_plant']:
        grid.set_tile_type(1, 1, non_zone)
        assert not grid.get_tile(1, 1).needs_power
