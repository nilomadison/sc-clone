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


def test_collect_taxes_only_from_powered_populated():
    eco = EconomySystem()
    grid = Grid(10, 10)
    grid.set_tile_type(1, 1, 'commercial')
    tile = grid.get_tile(1, 1)
    tile.population = 10

    # Unpowered: no income
    start = eco.money
    assert eco.collect_taxes(grid) == 0
    assert eco.money == start

    # Powered: income at baseline 7% tax = pop * rate
    tile.is_powered = True
    income = eco.collect_taxes(grid)
    assert income == 20  # 10 pop * 2.0 commercial rate * (7/7)
    assert eco.money == start + 20


def test_tax_rate_scales_income():
    eco = EconomySystem()
    grid = Grid(10, 10)
    grid.set_tile_type(1, 1, 'commercial')
    tile = grid.get_tile(1, 1)
    tile.population = 10
    tile.is_powered = True

    eco.tax_rate = 14
    assert eco.collect_taxes(grid) == 40


def test_upkeep_scales_with_funding():
    eco = EconomySystem()
    grid = Grid(10, 10)
    # 6 police stations: 600/mo => 10 per tick at full funding
    for i in range(6):
        grid.set_tile_type(i, 0, 'police')

    eco.collect_taxes(grid)
    eco.deduct_upkeep(grid)
    assert eco.last_upkeep == 10

    eco.service_funding['police'] = 0.5
    eco.deduct_upkeep(grid)
    assert eco.last_upkeep == 5


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
