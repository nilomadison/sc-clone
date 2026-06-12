from engine.economy import EconomySystem, STARTING_MONEY, ZONE_COSTS
from engine.grid import Grid


def test_starting_money():
    eco = EconomySystem()
    assert eco.money == STARTING_MONEY


def test_can_afford_and_deduct():
    eco = EconomySystem()
    eco.money = 100
    assert eco.can_afford('residential')
    assert eco.deduct_cost('residential')
    assert eco.money == 100 - ZONE_COSTS['residential']
    assert not eco.can_afford('power_plant')
    assert not eco.deduct_cost('power_plant')


def test_tax_income_only_from_powered_populated():
    eco = EconomySystem()
    grid = Grid(10, 10)
    grid.set_tile_type(1, 1, 'commercial')
    tile = grid.get_tile(1, 1)
    tile.population = 10

    # Unpowered: no income
    assert eco.tax_income_per_tick(grid) == 0

    # Powered: income at baseline 7% tax = pop * rate
    tile.is_powered = True
    assert eco.tax_income_per_tick(grid) == 20  # 10 pop * 2.0 commercial rate


def test_collect_monthly_taxes():
    eco = EconomySystem()
    grid = Grid(10, 10)
    grid.set_tile_type(1, 1, 'commercial')
    tile = grid.get_tile(1, 1)
    tile.population = 10
    tile.is_powered = True

    start = eco.money
    income = eco.collect_monthly_taxes(grid, ticks_per_month=60)
    assert income == 20 * 60
    assert eco.money == start + income


def test_tax_rate_scales_income():
    eco = EconomySystem()
    grid = Grid(10, 10)
    grid.set_tile_type(1, 1, 'commercial')
    tile = grid.get_tile(1, 1)
    tile.population = 10
    tile.is_powered = True

    eco.tax_rate = 14
    assert eco.tax_income_per_tick(grid) == 40


def test_monthly_upkeep_scales_with_funding():
    eco = EconomySystem()
    grid = Grid(10, 10)
    # 6 police stations at $100/mo each
    for i in range(6):
        grid.set_tile_type(i, 0, 'police')

    assert eco.monthly_upkeep(grid) == 600

    eco.service_funding['police'] = 0.5
    assert eco.monthly_upkeep(grid) == 300

    start = eco.money
    deducted = eco.deduct_monthly_upkeep(grid)
    assert deducted == 300
    assert eco.money == start - 300
    assert eco.last_upkeep == 300


def test_serialization_round_trip():
    eco = EconomySystem()
    eco.money = 12345
    eco.tax_rate = 12
    eco.service_funding = {'police': 0.6, 'fire': 0.3}
    data = eco.to_dict()

    eco2 = EconomySystem()
    eco2.from_dict(data)
    assert eco2.money == 12345
    assert eco2.tax_rate == 12
    assert eco2.service_funding == {'police': 0.6, 'fire': 0.3}
