# SimCity Clone

A simple city-building simulation game built with Python and Pygame-ce.

## Features

- **Zoning**: Residential, Commercial, and Industrial zones.
- **Infrastructure**: Roads and Power Lines.
- **Utilities**: Power Plants with power distribution logic.
- **Simulation**: Basic population growth and decay mechanics.
- **Tools**: Drag-and-drop placement for zones and roads.
- **Economy**: Starting funds ($20,000), zone placement costs, and tax income.
- **RCI Demand**: Visual meter showing zone type demand.
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

- **Left Click**: Select tool / Place item
- **Right Click + Drag**: Pan camera
- **Number Keys (1-6)**: Select tools
- **0 Key**: Select Bulldoze tool
- **Ctrl+S**: Save game
- **Ctrl+L**: Load game

## Economy

| Item | Cost |
|------|------|
| Residential Zone | $100 |
| Commercial Zone | $100 |
| Industrial Zone | $100 |
| Road | $10 |
| Power Plant | $3,000 |
| Power Line | $5 |
| Bulldoze | $1 |

Tax income is collected automatically based on zone population.
