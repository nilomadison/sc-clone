"""Headless smoke test: boot the real Game and run frames without a display."""
import pygame


def test_game_boots_and_runs_frames():
    from engine.game import Game

    game = Game()
    try:
        # Build a tiny city so systems have something to chew on
        game.grid.set_tile_type(10, 10, 'power_plant')
        for x in range(11, 15):
            game.grid.set_tile_type(x, 10, 'road')
            game.grid.set_tile_type(x, 11, 'residential')
            game.grid.set_tile_type(x, 12, 'commercial')

        # Run enough frames to cross several simulation ticks
        for _ in range(180):
            game.update()
            game.render()
    finally:
        pygame.quit()
