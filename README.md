# SimCity Clone

A simple city-building simulation game built with Python and Pygame-ce.

## Features

- **Zoning**: Residential, Commercial, and Industrial zones.
- **Infrastructure**: Roads and Power Lines.
- **Utilities**: Power Plants with power distribution logic.
- **City Services**: Police Stations reduce crime in their coverage radius.
- **Simulation**: Population growth, crime levels, and land value dynamics.
- **Tools**: Drag-and-drop placement for zones and roads.
- **Economy**: Starting funds ($20,000), zone placement costs, tax income, and service upkeep.
- **RCI Demand**: Visual meter showing zone type demand.
- **Data Overlays**: Toggle views for crime, land value, and power distribution.
- **Budget Panel**: Adjust tax rates and view income/expenses.
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
| **1-7** | Select tools (R/C/I/Road/Plant/Line/Police) |
| **0** | Bulldoze |
| **C** | Toggle crime overlay |
| **V** | Toggle land value overlay |
| **P** | Toggle power overlay |
| **B** | Open/close budget panel |
| **Up/Down** | Adjust tax rate (in budget) |
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
| Bulldoze | $1 | — |

Tax income is collected automatically based on zone population and current tax rate.
