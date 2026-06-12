# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
pip install -r requirements-dev.txt   # pygame-ce + pytest
python main.py                        # Run the game (requires a display)
pytest                                # Tests run headless (SDL dummy driver via tests/conftest.py)
pytest tests/test_fire.py -k burnout  # Single file / test
```

There is no linter or build step.

## Architecture

A SimCity-style game built on pygame-ce. `main.py` instantiates `engine.game.Game` and calls `run()`, which loops `handle_input()` → `update()` → `render()` at 60 FPS.

### Simulation tick

`Game.update()` (engine/game.py) runs the simulation once every 60 frames (~1/sec). Each simulation system is a class with an `update(grid)` method, called in a fixed order that matters because later systems read state written by earlier ones:

power → growth → demand → crime → land_value → fire → decay → tax collection → upkeep

(e.g. fire ignition reads `tile.crime_level` set by CrimeSystem; LandValueSystem reads crime; DecaySystem reads funding from EconomySystem.)

### State model

- All persistent per-tile state lives as flat attributes on `Tile` (engine/grid.py): `type`, `has_power_line`, `is_powered`, `population`, `land_value`, `crime_level`, `is_on_fire`, `fire_intensity`, `is_burned`, `building_health`. The grid is 100×100, indexed `grid.tiles[x][y]`.
- Tile types are plain strings (`'grass'`, `'road'`, `'residential'`, `'commercial'`, `'industrial'`, `'power_plant'`, `'police'`, `'fire_station'`). `'grass'` doubles as the bulldoze tool. Power lines are NOT a tile type — they're the `has_power_line` overlay flag, toggled by `Grid.toggle_power_line()`; the `'power_line'` tool is special-cased in `Game.use_current_tool()`.
- Systems are mostly stateless: they rescan the whole grid every tick (FireSystem re-finds fire stations, EconomySystem re-counts service buildings). Transient system state like `FireSystem.fire_ticks` is not saved.

### Adding a new tile/building type touches multiple files

1. `TOOLS` list in engine/game.py (toolbar button) plus a number-key binding in `handle_input()`
2. `ZONE_COSTS` (and `UPKEEP_COSTS` if it has upkeep) in engine/economy.py
3. A color constant and draw case in engine/renderer.py
4. `FLAMMABILITY` in engine/fire.py (defaults to 0.0 = fireproof if omitted)
5. Other systems' per-type tables if relevant: `CRIME_RATES` (crime.py), `VALUE_MODIFIERS` (land_value.py), `BASE_TAX_RATES` (economy.py), `needs_power` property (grid.py)

### Save/load

`Game.save_game()`/`load_game()` write JSON to `saves/city.json` (gitignored). The format is sparse — only non-default tiles are serialized — and carries a `version` string. Loading uses `.get()` with defaults for every field, so old saves keep working; preserve that pattern when adding tile fields, and add new fields to both the save filter condition and the per-tile dict in `save_game()`.

### Conventions

- Power propagates by BFS from power plants through power-line overlays and RCI zones (engine/systems.py); roads receive power but don't conduct it.
- Police and fire stations both use an 8-tile Manhattan-distance radius for coverage.
- Service funding (`economy.service_funding`, 0.0–1.0 for `'police'`/`'fire'`) scales upkeep cost and service effectiveness (crime reduction, decay rate, fire coverage radius and extinguish speed — `FireSystem.update(grid, economy)` takes the economy for this).
- Fires always burn out on their own after `FireSystem.BURN_DURATION` ticks; coverage just extinguishes them much faster. Spread chance is multiplied by target flammability, so 0-flammability tiles (grass, roads) are firebreaks.
- `is_burned` rubble is inert: skipped by growth, taxes, and power conduction until bulldozed.
- Systems that destroy buildings (`FireSystem`, `DecaySystem`) append `('collapse', x, y)` to their `events` list; `Game.update()` drains these into the toast `NotificationSystem`.
