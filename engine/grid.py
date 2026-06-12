from engine.tiles import TILE_TYPES


class Tile:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.type = 'grass'  # Types: grass, road, residential, commercial, industrial, power_plant, police
        self.has_power_line = False  # Power lines are an overlay, not a type
        self.is_powered = False
        self.population = 0
        self.structure = None # For complex structures if needed later
        self.sprite_index = 0 # For variation
        # v0.3.0: City services
        self.land_value = 50  # 0-100 scale
        self.crime_level = 0.0  # 0.0-1.0 scale
        # v0.4.0: Fire & Safety
        self.is_on_fire = False
        self.fire_intensity = 0.0  # 0.0-1.0 scale
        self.is_burned = False  # True if building was destroyed by fire
        self.building_health = 1.0  # 0.0-1.0 scale, decays over time

    @property
    def needs_power(self):
        """Return True if this tile type needs power to function."""
        return TILE_TYPES[self.type]['needs_power']

    def __repr__(self):
        return f"Tile({self.x}, {self.y}, {self.type}, power_line={self.has_power_line})"

class Grid:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.tiles = [[Tile(x, y) for y in range(height)] for x in range(width)]
        # Index of non-grass tile positions by type, so systems can iterate
        # buildings without scanning the whole map. Kept in sync by
        # set_tile_type — never assign tile.type directly.
        self.index = {}

    def get_tile(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[x][y]
        return None

    def positions(self, *types):
        """Iterate (x, y) positions of all tiles of the given types."""
        for type_name in types:
            yield from self.index.get(type_name, ())

    def count(self, type_name):
        """Number of tiles of the given type."""
        return len(self.index.get(type_name, ()))

    def set_tile_type(self, x, y, type_name):
        tile = self.get_tile(x, y)
        if tile:
            if tile.type != type_name:
                old_set = self.index.get(tile.type)
                if old_set:
                    old_set.discard((x, y))
                if type_name != 'grass':
                    self.index.setdefault(type_name, set()).add((x, y))
            tile.type = type_name
            # Reset properties when type changes
            tile.is_powered = False
            tile.population = 0
            # Clear power line when bulldozing to grass
            if type_name == 'grass':
                tile.has_power_line = False
                # v0.4.0: Clear fire/damage state
                tile.is_on_fire = False
                tile.fire_intensity = 0.0
                tile.is_burned = False
                tile.building_health = 1.0
            return True
        return False

    def toggle_power_line(self, x, y):
        """Toggle power line overlay on a tile without changing its type."""
        tile = self.get_tile(x, y)
        if tile:
            tile.has_power_line = not tile.has_power_line
            return True
        return False
