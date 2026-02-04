# Changelog

All notable changes to this project will be documented in this file.

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
