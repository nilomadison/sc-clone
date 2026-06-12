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

## Running the Tests

```bash
pip install -r requirements-dev.txt
pytest
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
| **Space** | Pause/resume simulation |
| **- / +** | Simulation speed (1x/2x/3x) |
| **B** | Open/close budget panel |
| **D** | Open/close disasters panel (1-4 to trigger) |
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

The game runs on a calendar (one month per real-time minute at 1x speed). Taxes are collected and service upkeep is paid at the start of each month, based on zone population, land value, and the current tax rate.

Key feedback loops, in the spirit of the classics:
- **RCI demand drives growth** — zones only develop while their demand bar is positive, and empty out under oversupply.
- **Taxes shift demand** — 7% is neutral; raise rates for short-term cash at the cost of growth.
- **Land value scales income** — desirable neighborhoods (near police, commerce, away from industry and crime) pay more tax.
- **Power plants have capacity** — each supports 200 zone tiles; overload causes brownouts in the farthest zones (watch the power meter).
- **Damaged buildings stop working** — below 25% health, stations lose coverage, plants stop producing, and zones stop paying taxes until they recover or collapse.

## Disasters

Press **D** and pick your poison: **Fire**, **Tornado**, **Earthquake**, or **Monster**. Tornadoes and monsters rampage across the map for a while, earthquakes damage buildings citywide and crack roads, and monsters set things on fire as they go.

## Fire Safety

Fires occasionally start in industrial zones and power plants (crime raises the arson risk). A fire spreads to adjacent flammable buildings, but grass and roads act as firebreaks. Left alone, a fire burns out on its own after a while — badly damaging the building and possibly a few neighbors.

Place **Fire Stations** ($500, $150/mo) to:
- Extinguish fires within their 8-tile radius in seconds, with minimal damage
- Cut fire spread chance in half inside their coverage

Buildings on fire lose health. If a building's health reaches zero, it collapses into rubble and must be bulldozed before rebuilding.

## Service Funding

In the budget panel, you can adjust funding levels for services:
- **Police Funding**: Lower funding increases crime and building decay
- **Fire Funding**: Lower funding shrinks fire station coverage (down to half radius at 0%) and slows extinguishing

Underfunded services cost less upkeep but provide reduced protection.
