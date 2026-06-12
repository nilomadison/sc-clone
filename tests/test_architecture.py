"""Tests for the v0.6.0 architecture refactor: tile registry, game clock,
pause/speed, and the save module (incl. loading pre-0.6 saves)."""
import json

import pygame
import pytest

from engine.clock import GameClock
from engine.tiles import TILE_TYPES, TOOL_ORDER

REQUIRED_FIELDS = {'label', 'hotkey', 'color', 'button_color', 'cost', 'upkeep',
                   'tax_rate', 'flammability', 'crime_rate', 'value_modifier',
                   'conducts_power', 'needs_power', 'is_zone'}


def test_registry_completeness():
    for type_name, config in TILE_TYPES.items():
        missing = REQUIRED_FIELDS - set(config)
        assert not missing, f"{type_name} missing fields: {missing}"


def test_tool_order_covers_registry():
    assert set(TOOL_ORDER) == set(TILE_TYPES)


def test_hotkeys_unique():
    hotkeys = [cfg['hotkey'] for cfg in TILE_TYPES.values() if cfg['hotkey']]
    assert len(hotkeys) == len(set(hotkeys))


def test_clock_month_and_year_rollover():
    clock = GameClock(start_year=2000)
    assert clock.date_string == 'Jan 2000'

    rolled = [clock.advance() for _ in range(GameClock.TICKS_PER_MONTH)]
    assert rolled.count(True) == 1
    assert rolled[-1] is True  # Month rolls exactly on the boundary
    assert clock.date_string == 'Feb 2000'

    for _ in range(GameClock.TICKS_PER_MONTH * 11):
        clock.advance()
    assert clock.date_string == 'Jan 2001'


def test_clock_serialization():
    clock = GameClock(start_year=1990)
    for _ in range(150):
        clock.advance()
    data = clock.to_dict()

    clock2 = GameClock()
    clock2.from_dict(data)
    assert clock2.tick == 150
    assert clock2.start_year == 1990


class TestGameIntegration:
    @pytest.fixture()
    def game(self):
        from engine.game import Game
        g = Game()
        yield g
        pygame.quit()

    def test_pause_blocks_simulation(self, game):
        game.paused = True
        for _ in range(200):
            game.update()
        assert game.clock.tick == 0

    def test_speed_changes_tick_rate(self, game):
        game.speed_index = 2  # 3x: a tick every 20 frames
        for _ in range(20):
            game.update()
        assert game.clock.tick == 1

    def test_monthly_budget_settlement(self, game):
        game.grid.set_tile_type(10, 10, 'power_plant')
        game.grid.set_tile_type(11, 10, 'commercial')
        tile = game.grid.get_tile(11, 10)
        tile.population = 10

        game.speed_index = 2
        start = game.economy.money
        # Run one full month of ticks (plus one frame slack)
        for _ in range(GameClock.TICKS_PER_MONTH * 20 + 1):
            game.update()

        assert game.clock.total_months == 1
        # Commercial taxes collected monthly; power plant upkeep deducted
        assert game.last_income > 0
        assert game.economy.last_upkeep == 200
        assert game.economy.money == start + game.last_income - 200

    def test_save_load_round_trip(self, game, tmp_path):
        path = str(tmp_path / 'city.json')
        game.grid.set_tile_type(10, 10, 'power_plant')
        game.grid.set_tile_type(11, 10, 'residential')
        game.grid.get_tile(11, 10).population = 7
        game.grid.toggle_power_line(12, 10)
        game.economy.money = 5555
        game.economy.tax_rate = 11
        for _ in range(100):
            game.clock.advance()

        game.save_game(path)

        # Trash the state, then load
        game.grid.set_tile_type(10, 10, 'grass')
        game.economy.money = 0
        game.clock.tick = 0

        assert game.load_game(path)
        assert game.grid.get_tile(10, 10).type == 'power_plant'
        assert game.grid.get_tile(11, 10).population == 7
        assert game.grid.get_tile(12, 10).has_power_line
        assert game.economy.money == 5555
        assert game.economy.tax_rate == 11
        assert game.clock.tick == 100
        # Grid index rebuilt correctly
        assert set(game.grid.positions('power_plant')) == {(10, 10)}

    def test_load_pre_0_6_save(self, game, tmp_path):
        """Old saves have no clock and may omit newer tile fields."""
        path = str(tmp_path / 'old_city.json')
        old_save = {
            'version': '0.4.0',
            'grid': {
                'width': 100,
                'height': 100,
                'tiles': [
                    {'x': 5, 'y': 5, 'type': 'residential',
                     'has_power_line': False, 'population': 3},
                    {'x': 6, 'y': 5, 'type': 'police',
                     'has_power_line': True, 'population': 0},
                ],
            },
            'economy': {'money': 9999, 'tax_rate': 9},
        }
        with open(path, 'w') as f:
            json.dump(old_save, f)

        assert game.load_game(path)
        assert game.grid.get_tile(5, 5).type == 'residential'
        assert game.grid.get_tile(5, 5).population == 3
        assert game.grid.get_tile(5, 5).building_health == 1.0
        assert game.economy.money == 9999
        assert game.clock.tick == 0
        assert game.economy.service_funding == {'police': 1.0, 'fire': 1.0}
