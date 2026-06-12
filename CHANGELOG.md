# Changelog

All notable changes to this project will be documented in this file.

## [v0.9.0] - 2026-06-11

### Added
- **3×3 zones with density tiers**: RCI zones now place as classic 3×3 plots ($100 per zone, not per tile). Zones grow as a unit through four density tiers that raise their population caps; bulldozing any tile clears the whole plot. Zones render as single buildings (outline only)
- **Traffic simulation**: zones periodically route trips along roads to their counterpart (residents→jobs, shops→customers, industry→shops). A zone with no reachable destination within 30 road tiles stops growing. Trips lay traffic on roads, which decays over time
- **Traffic overlay (T)**: green (free-flowing) to red (jammed) on roads
- Busy roads drag down nearby land value instead of raising it

### Changed
- **Demand model rebuilt**: the old formulas had no growing equilibrium (jobs targets covered only ~45% of residents, so residential demand went permanently negative once demand actually gated growth). Each zone type now chases a target derived from the others, giving balanced cities the classic boom loop
- Save format 0.9.0 stores zones; older saves load fine, with their RCI tiles behaving as legacy single-tile plots

## [v0.8.0] - 2026-06-11

### Added
- **Terrain generation**: new cities start with a winding river, lakes, and forests (`engine/mapgen.py`)
- **Water**: unbuildable and fireproof, raises nearby land value; power lines can cross it
- **Trees**: plantable with the new Trees tool (9, $25), raise land value, highly flammable — forest fires are now a thing; bulldoze them to clear land
- **Flood disaster**: water spills over its banks, swallowing shoreline buildings, then recedes leaving mud

### Changed
- Tornadoes and monsters flatten forests as they pass

## [v0.7.0] - 2026-06-11

### Added
- **Disasters menu (D)**: trigger Fire, Tornado, Earthquake, or Monster, classic-style. Tornadoes and monsters walk the map for ~40 ticks wrecking everything in their path; earthquakes shake buildings across the city and crack roads
- **Power plant capacity**: each plant supports 200 zone tiles; over capacity, the farthest zones brown out. The HUD shows power load (red when maxed)
- **Land value matters**: tax income per capita scales 0.5x-1.5x with land value

### Changed
- **The RCI demand meter now drives growth**: zones grow in proportion to their demand and shrink under oversupply (it was previously cosmetic)
- **Tax rate now affects demand**: 7% is neutral; higher rates suppress demand and can empty the city, lower rates stimulate it (20% is no longer free money)
- **Building health matters**: buildings below 25% health stop functioning — stations lose their coverage, power plants stop producing, zones stop growing and paying taxes

## [v0.6.0] - 2026-06-11

### Added
- **Game clock**: in-game calendar (month/year in the HUD); taxes and upkeep now settle monthly instead of per-tick (same average cash flow, classic budget feel)
- **Pause & speed controls**: Space pauses; -/+ cycles 1x/2x/3x simulation speed
- **Tile type registry** (`engine/tiles.py`): every per-type table (costs, upkeep, tax rates, flammability, crime, land value, colors, toolbar) now derives from one registry

### Changed
- **Massive simulation speedup (~35x)**: crime and land value are now incremental scatter fields (`engine/fields.py`), the grid keeps a type→positions index, and the fire system tracks burning tiles incrementally. A dense 100×100 city went from ~1160ms to ~33ms per tick
- `Game` split up: UI drawing moved to `engine/ui.py`, save/load to `engine/save.py`
- Toast notifications are now the only notification system (legacy banner removed)
- Population HUD stat is cached per tick instead of recomputed every frame

### Fixed
- Loading a save now fully rebuilds system state (burning fires resume burning; stale crime/land-value fields are reset)

## [v0.5.0] - 2026-06-11

### Added
- **Test suite**: pytest harness with headless smoke test (`pip install -r requirements-dev.txt`, then `pytest`)
- **Collapse notifications**: building collapses (fire or decay) now raise toast alerts
- **Underfunding warnings**: dropping police/fire funding below 50% warns via notification

### Changed
- **Fire rebalance (major)**: fires now burn out on their own after ~40 ticks instead of burning forever outside fire station coverage — an uncovered fire badly damages a building and possibly a few neighbors, then dies
- Fire spread is now fully gated by flammability; grass and roads act as firebreaks (fire no longer crosses open land)
- Fire ignition is ~10x rarer and only flammable building tiles can ignite (no more arson on roads)
- **Fire funding now works**: low funding shrinks fire station coverage radius (down to 50%) and slows extinguishing, as the README always claimed

### Fixed
- Burned rubble no longer regrows population, pays taxes, or conducts power — it must be bulldozed before rebuilding, as documented
- Tools no longer charge money for no-ops: painting a tile with its existing type, bulldozing grass, or clicking out of bounds is free; drag-painting charges once per tile instead of once per mouse event
- Drag-placed zones and roads only build on empty grass — no more silently paving over power plants and stations
- Buildings on fire are no longer repaired by the decay system while burning

## [v0.4.0] - 2026-02-06

### Added
- **Fire System**: Fires can randomly ignite on industrial zones and power plants
- **Fire Spread**: Active fires spread to adjacent buildings, damaging them over time
- **Fire Stations**: New building type ($500, $150/mo upkeep) that protects an 8-tile radius
- **Auto-Extinguish**: Fires in fire station coverage are extinguished faster
- **Building Decay**: Underfunded services cause buildings to deteriorate
- **Building Health**: Structures now have health; damaged buildings appear darker
- **Toast Notifications**: Pop-up alerts for fires, budget warnings, and building collapses
- **Service Funding**: Control police and fire department funding levels (0-100%)
- **Fire Overlay**: Press F to view fire risk and active fires

### Changed
- Budget panel now allows navigation (Up/Down) and value adjustment (Left/Right)
- Upkeep costs scale with service funding levels
- Tiles now store `is_on_fire`, `fire_intensity`, `is_burned`, and `building_health` properties
- Save format updated to version 0.4.0 with fire state persistence
- Updated controls: 1-8 for tools, F for fire overlay

## [v0.3.0] - 2026-02-04

### Added
- **Crime System**: Crime now generates from industrial and commercial zones, spreading to nearby areas
- **Police Stations**: New building type ($500) that reduces crime in an 8-tile radius
- **Land Value System**: Property values now calculated based on surroundings and crime levels
- **Data Overlays**: Toggle views for crime (C), land value (V), and power (P)
- **Budget Panel**: Press B to view treasury, adjust tax rates (1-20%), and see income/expenses
- **Service Upkeep**: Police stations and power plants now have ongoing maintenance costs

### Changed
- Economy system now tracks and displays upkeep costs
- Tiles now store `land_value` and `crime_level` properties
- Updated controls documentation in README

## [v0.2.0] - 2026-01-27

### Added
- Power system with power plants and power lines
- Zone growth based on power connectivity
- RCI demand meter visualization
- Save/Load functionality (Ctrl+S / Ctrl+L)
- Drag-to-place for zones and roads
- Camera panning with right-click drag
- Visual indicator for unpowered tiles

### Changed
- Zones now require power to generate population and tax income

## [v0.1.0] - 2026-01-20

### Added
- Initial release
- Basic zoning (Residential, Commercial, Industrial)
- Road placement
- Simple economy with zone placement costs
- Population simulation
