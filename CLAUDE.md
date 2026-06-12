# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
pip install -r requirements-dev.txt   # pygame-ce + pytest
python main.py                        # Run the game (requires a display)
pytest                                # Tests run headless (SDL dummy driver via tests/conftest.py)
pytest tests/test_fire.py -k burnout  # Single file / test
python scripts/benchmark.py           # Per-system tick timing on a dense city
```

There is no linter or build step.

## Architecture

A SimCity-style game built on pygame-ce. `main.py` instantiates `engine.game.Game` and calls `run()`, which loops `handle_input()` → `update()` → `render()` at 60 FPS.

### Simulation tick and clock

`Game.update()` (engine/game.py) runs the simulation once every `SPEED_FRAMES[speed_index]` frames (60/30/20 for 1x/2x/3x; Space pauses). Each system is a class with an `update(grid)` method, called in a fixed order that matters because later systems read state written by earlier ones:

power → growth → demand → crime → land_value → disasters → fire → decay

Growth reads the *previous* tick's demand (`GrowthSystem.update(grid, demand_system)`); demand reads the tax rate (7% neutral — high taxes suppress demand). Power plants have finite capacity (registry `power_capacity`); the BFS browns out the farthest zones when over budget. Tax income scales with land value (0.5x–1.5x). Buildings below `decay.MIN_HEALTH_FUNCTIONAL` (25%) are gated everywhere via `decay.is_functional(tile)` — no coverage, power, growth, or taxes.

`engine/clock.py` (`GameClock`) converts ticks to a calendar (60 ticks = 1 month). Taxes (`economy.collect_monthly_taxes`) and upkeep (`deduct_monthly_upkeep`) settle on month boundaries, not per tick.

### Tile type registry — single source of truth

`engine/tiles.py` defines `TILE_TYPES`: per-type label, hotkey, colors, cost, upkeep, tax rate, flammability, crime rate, land-value modifier, power behavior, and zone flag. Economy/fire/crime/land-value tables and the toolbar all derive from it via `field_map()`. **Adding a tile type is one registry entry** plus, if needed, a special draw case in renderer.py. `tests/test_architecture.py` enforces registry completeness.

### State model and the grid index

- All persistent per-tile state lives as flat attributes on `Tile` (engine/grid.py). The grid is 100×100, indexed `grid.tiles[x][y]`.
- Tile types are plain strings. `'grass'` doubles as the bulldoze tool. Power lines are NOT a tile type — they're the `has_power_line` overlay flag; the `'power_line'` tool is special-cased in `Game.apply_tool()`.
- `Grid` maintains a type→positions index (`grid.positions(*types)`, `grid.count(type)`), kept in sync by `set_tile_type` — **never assign `tile.type` directly**. Systems iterate the index instead of scanning the map.

### Performance pattern: incremental fields

Crime and land value use `engine/fields.py` `IncrementalField`: sources scatter kernel-weighted contributions into a flat field, and only sources whose strength changed since last tick re-scatter a delta. Per-tick cost tracks city churn, not map size (~35x speedup on dense maps). `tests/test_performance_refactor.py` holds reference gather implementations that the incremental versions must match exactly — keep those tests passing when touching crime/land-value math. The fire system similarly tracks a `burning` set incrementally rather than scanning.

### Fire behavior (rebalanced in v0.5.0)

- Fires always burn out on their own after `FireSystem.BURN_DURATION` ticks; fire-station coverage just extinguishes them much faster.
- Spread chance is multiplied by target flammability, so 0-flammability tiles (grass, roads) are firebreaks.
- Fire funding (`economy.service_funding['fire']`) scales coverage radius and extinguish speed — `FireSystem.update(grid, economy)` takes the economy for this.
- `is_burned` rubble is inert: skipped by growth, taxes, and power conduction until bulldozed.

### Events and notifications

Systems that destroy buildings (`FireSystem`, `DecaySystem`, `DisasterSystem`) append `('collapse', x, y)` to their `events` list — disasters also append `('disaster', name)`; `Game._drain_system_events()` forwards these to the toast `NotificationSystem` (engine/notifications.py) — the only notification mechanism.

### Disasters and terrain

`engine/disasters.py`: instant disasters (fire, earthquake) mutate the grid in `trigger()`; tornado/monster become an `active` walker stepped by `update()` each tick and drawn by `Renderer.draw_disaster`; flood tracks a `flooded` dict of tiles that spread (inheriting remaining duration) and recede to grass. The D panel triggers them (number keys while open).

`engine/mapgen.py` generates terrain (river/lakes/trees) on new games — `Game(generate_terrain=False)` for tests. `'water'` is the one registry type that isn't a tool: unbuildable and un-bulldozable (checked in `Game.apply_tool`), but power lines may cross it. `'trees'` are plantable, highly flammable, and raise land value.

### UI and save modules

- `engine/ui.py` (`UI`) owns all HUD/toolbar/budget-panel drawing and toolbar hit-testing; it reads game state but never mutates it. `Game` keeps input handling and orchestration.
- `engine/save.py` owns serialization. The format is sparse (only non-default tiles) with a `version` string; every field is read back via `.get()` with a default so older saves keep loading — preserve that pattern when adding fields. Loading re-instantiates the field-based systems and calls `fire_system.rebuild(grid)` because their caches are tied to the old grid.

### Other conventions

- Power propagates by BFS from power plants through power-line overlays and intact RCI zones (engine/systems.py); roads receive power but don't conduct it.
- Police and fire stations both use an 8-tile radius for coverage (police: Euclidean with falloff; fire: Manhattan, scaled by funding).
- Service funding (0.0–1.0) scales upkeep cost and effectiveness (crime reduction, decay rate, fire response).
- Placement charges only on real changes: same-type placement is a free no-op, and drag placement only builds on grass (`Game._place_on_grass`).
