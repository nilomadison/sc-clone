# SimCity Clone

A simple city-building simulation game built with Python and Pygame-ce.

## Features

- **Zoning**: Residential, Commercial, and Industrial zones.
- **Infrastructure**: Roads and Power Lines.
- **Utilities**: Power Plants with power distribution logic.
- **City Services**: Police and Fire Stations protect your city.
- **Fire System**: Fires can start and spread; fire stations auto-extinguish in their radius.
- **Building Decay**: Underfunded services cause buildings to deteriorate over time.
- **Simulation**: Population growth, crime levels, land value, and fire dynamics.
- **Tools**: Drag-and-drop placement for zones and roads.
- **Economy**: Starting funds ($20,000), zone placement costs, tax income, and service upkeep.
- **Service Funding**: Control funding levels for police and fire departments.
- **RCI Demand**: Visual meter showing zone type demand.
- **Data Overlays**: Toggle views for crime, land value, power, and fire risk.
- **Budget Panel**: Adjust tax rates, service funding, and view income/expenses.
- **Notifications**: Toast alerts for fires, budget warnings, and building collapses.
- **Save/Load**: Persist your city to disk and load it later.

## Setup

1. **Create a Virtual Environment**:
   ```bash
   python -m venv venv
   ```

2. **Activate the Virtual Environment**:
   - Windows: `.\venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Game

```bash
python main.py
```

## Controls

| Key | Action |
|-----|--------|
| **Left Click** | Place item / Select tool |
| **Right Click + Drag** | Pan camera |
| **1-8** | Select tools (R/C/I/Road/Plant/Line/Police/Fire) |
| **0** | Bulldoze |
| **C** | Toggle crime overlay |
| **V** | Toggle land value overlay |
| **P** | Toggle power overlay |
| **F** | Toggle fire risk overlay |
| **B** | Open/close budget panel |
| **Up/Down** | Navigate budget options |
| **Left/Right** | Adjust selected budget value |
| **Esc** | Close overlays/budget |
| **Ctrl+S** | Save game |
| **Ctrl+L** | Load game |

## Economy

| Item | Cost | Upkeep |
|------|------|--------|
| Residential Zone | $100 | — |
| Commercial Zone | $100 | — |
| Industrial Zone | $100 | — |
| Road | $10 | — |
| Power Plant | $3,000 | $200/mo |
| Power Line | $5 | — |
| Police Station | $500 | $100/mo |
| Fire Station | $500 | $150/mo |
| Bulldoze | $1 | — |

Tax income is collected automatically based on zone population and current tax rate.

## Fire Safety

Fires can randomly start in industrial zones and power plants. They spread to adjacent tiles and damage buildings over time. Place **Fire Stations** to:
- Reduce fire spread speed by 50% in their coverage area
- Auto-extinguish fires within 8 tiles

Buildings on fire lose health. If a building's health reaches zero, it collapses into rubble and must be bulldozed before rebuilding.

## Service Funding

In the budget panel, you can adjust funding levels for services:
- **Police Funding**: Lower funding increases crime and building decay
- **Fire Funding**: Lower funding reduces fire protection effectiveness

Underfunded services cost less upkeep but provide reduced protection.
