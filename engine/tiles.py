"""
Tile type registry — the single source of truth for per-type configuration.

Every tile type defines the full set of fields below. Systems derive their
own lookup tables from this registry (see economy.py, fire.py, crime.py,
land_value.py), so adding a new tile type is one entry here plus a renderer
draw case if it needs special visuals.

Fields:
    label           Toolbar button text
    hotkey          Keyboard digit that selects the tool ('' = no hotkey)
    color           Map tile color
    button_color    Toolbar button color
    cost            Placement cost ($)
    upkeep          Monthly upkeep ($/month, 0 = none)
    tax_rate        Tax income per population per tick (0 = not taxed)
    flammability    0.0 (firebreak) to 1.0 (highly flammable)
    crime_rate      Crime generated per population (0 = none)
    value_modifier  Effect on nearby land value (+/-)
    conducts_power  Whether the power BFS flows through this type
    needs_power     Whether the tile requires power to function
    power_capacity  Zone tiles this building can power (power plants only)
    is_zone         RCI zone (grows population, drag-to-fill placement)
"""

TILE_TYPES = {
    'grass': {
        'label': 'Bulldoze', 'hotkey': '0',
        'color': (139, 90, 43), 'button_color': (100, 50, 50),
        'cost': 1, 'upkeep': 0, 'tax_rate': 0.0,
        'flammability': 0.0, 'crime_rate': 0.0, 'value_modifier': 0,
        'conducts_power': False, 'needs_power': False, 'power_capacity': 0, 'is_zone': False,
    },
    'residential': {
        'label': 'Residential', 'hotkey': '1',
        'color': (0, 255, 0), 'button_color': (0, 200, 0),
        'cost': 100, 'upkeep': 0, 'tax_rate': 0.5,
        'flammability': 0.8, 'crime_rate': 0.05, 'value_modifier': 3,
        'conducts_power': True, 'needs_power': True, 'power_capacity': 0, 'is_zone': True,
    },
    'commercial': {
        'label': 'Commercial', 'hotkey': '2',
        'color': (0, 0, 255), 'button_color': (0, 0, 200),
        'cost': 100, 'upkeep': 0, 'tax_rate': 2.0,
        'flammability': 0.7, 'crime_rate': 0.1, 'value_modifier': 5,
        'conducts_power': True, 'needs_power': True, 'power_capacity': 0, 'is_zone': True,
    },
    'industrial': {
        'label': 'Industrial', 'hotkey': '3',
        'color': (255, 255, 0), 'button_color': (200, 200, 0),
        'cost': 100, 'upkeep': 0, 'tax_rate': 1.5,
        'flammability': 0.6, 'crime_rate': 0.3, 'value_modifier': -10,
        'conducts_power': True, 'needs_power': True, 'power_capacity': 0, 'is_zone': True,
    },
    'road': {
        'label': 'Road', 'hotkey': '4',
        'color': (105, 105, 105), 'button_color': (100, 100, 100),
        'cost': 10, 'upkeep': 0, 'tax_rate': 0.0,
        'flammability': 0.0, 'crime_rate': 0.0, 'value_modifier': 5,
        'conducts_power': False, 'needs_power': False, 'power_capacity': 0, 'is_zone': False,
    },
    'power_plant': {
        'label': 'Power Plant', 'hotkey': '5',
        'color': (255, 69, 0), 'button_color': (200, 50, 0),
        'cost': 3000, 'upkeep': 200, 'tax_rate': 0.0,
        'flammability': 0.4, 'crime_rate': 0.0, 'value_modifier': -15,
        'conducts_power': True, 'needs_power': False, 'power_capacity': 200, 'is_zone': False,
    },
    'power_line': {
        # Pseudo-type: a tool that toggles the has_power_line overlay,
        # never an actual tile.type
        'label': 'Power Line', 'hotkey': '6',
        'color': (255, 215, 0), 'button_color': (200, 180, 0),
        'cost': 5, 'upkeep': 0, 'tax_rate': 0.0,
        'flammability': 0.0, 'crime_rate': 0.0, 'value_modifier': 0,
        'conducts_power': True, 'needs_power': False, 'power_capacity': 0, 'is_zone': False,
    },
    'police': {
        'label': 'Police', 'hotkey': '7',
        'color': (0, 100, 255), 'button_color': (0, 100, 255),
        'cost': 500, 'upkeep': 100, 'tax_rate': 0.0,
        'flammability': 0.5, 'crime_rate': 0.0, 'value_modifier': 15,
        'conducts_power': False, 'needs_power': False, 'power_capacity': 0, 'is_zone': False,
    },
    'fire_station': {
        'label': 'Fire Stn', 'hotkey': '8',
        'color': (178, 34, 34), 'button_color': (178, 34, 34),
        'cost': 500, 'upkeep': 150, 'tax_rate': 0.0,
        'flammability': 0.3, 'crime_rate': 0.0, 'value_modifier': 0,
        'conducts_power': False, 'needs_power': False, 'power_capacity': 0, 'is_zone': False,
    },
    'trees': {
        'label': 'Trees', 'hotkey': '9',
        'color': (20, 120, 40), 'button_color': (20, 120, 40),
        'cost': 25, 'upkeep': 0, 'tax_rate': 0.0,
        'flammability': 0.9, 'crime_rate': 0.0, 'value_modifier': 6,
        'conducts_power': False, 'needs_power': False, 'power_capacity': 0, 'is_zone': False,
    },
    'water': {
        # Terrain only — not placeable or bulldozable. Power lines may cross.
        'label': 'Water', 'hotkey': '',
        'color': (30, 90, 200), 'button_color': (30, 90, 200),
        'cost': 0, 'upkeep': 0, 'tax_rate': 0.0,
        'flammability': 0.0, 'crime_rate': 0.0, 'value_modifier': 8,
        'conducts_power': False, 'needs_power': False, 'power_capacity': 0, 'is_zone': False,
    },
}

# Toolbar order (also defines hotkey display order). Water is terrain, not a tool.
TOOL_ORDER = ['residential', 'commercial', 'industrial', 'road', 'power_plant',
              'power_line', 'police', 'fire_station', 'trees', 'grass']

# Derived lookups
ZONE_TYPES = tuple(t for t, cfg in TILE_TYPES.items() if cfg['is_zone'])
POWER_CONDUCTOR_TYPES = tuple(
    t for t, cfg in TILE_TYPES.items()
    if cfg['conducts_power'] and t != 'power_line')


def field_map(field, predicate=lambda value: True):
    """Build a {type: value} lookup for one registry field, optionally filtered."""
    return {t: cfg[field] for t, cfg in TILE_TYPES.items() if predicate(cfg[field])}
