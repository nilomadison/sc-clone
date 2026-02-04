"""
Economy system for SimCity Clone.
Handles money, zone placement costs, and tax collection.
"""

# Starting money for new games
STARTING_MONEY = 20000

# Cost to place each tile type
ZONE_COSTS = {
    'residential': 100,
    'commercial': 100,
    'industrial': 100,
    'road': 10,
    'power_plant': 3000,
    'power_line': 5,
    'police': 500,
    'grass': 1,  # Bulldoze cost
}

# Monthly upkeep costs for service buildings
UPKEEP_COSTS = {
    'police': 100,
    'power_plant': 200,
}

# Base tax income per population per simulation tick
BASE_TAX_RATES = {
    'residential': 0.5,   # Property tax
    'commercial': 2.0,    # Business tax
    'industrial': 1.5,    # Industrial tax
}


class EconomySystem:
    """Manages city treasury, costs, and tax collection."""
    
    def __init__(self):
        self.money = STARTING_MONEY
        self.tax_rate = 7  # Percentage (1-20)
        self.last_upkeep = 0  # Track for display
    
    def get_placement_cost(self, tile_type):
        """Get the cost to place a tile of the given type."""
        return ZONE_COSTS.get(tile_type, 0)
    
    def can_afford(self, tile_type):
        """Check if we have enough money to place this tile type."""
        return self.money >= self.get_placement_cost(tile_type)
    
    def deduct_cost(self, tile_type):
        """
        Deduct the cost of placing a tile from treasury.
        Returns True if successful, False if insufficient funds.
        """
        cost = self.get_placement_cost(tile_type)
        if self.money >= cost:
            self.money -= cost
            return True
        return False
    
    def collect_taxes(self, grid):
        """
        Collect taxes from all powered zones based on their population.
        Returns the total income collected this tick.
        """
        income = 0
        tax_multiplier = self.tax_rate / 7.0  # 7% is baseline
        
        for x in range(grid.width):
            for y in range(grid.height):
                tile = grid.tiles[x][y]
                
                # Only powered tiles generate tax income
                if tile.is_powered and tile.population > 0:
                    rate = BASE_TAX_RATES.get(tile.type, 0)
                    income += tile.population * rate * tax_multiplier
        
        # Round to avoid floating point accumulation issues
        income = round(income)
        self.money += income
        return income
    
    def deduct_upkeep(self, grid):
        """Deduct upkeep costs for service buildings. Returns total upkeep."""
        upkeep = 0
        
        for x in range(grid.width):
            for y in range(grid.height):
                tile = grid.tiles[x][y]
                cost = UPKEEP_COSTS.get(tile.type, 0)
                upkeep += cost
        
        # Upkeep is deducted per tick (scaled down since it runs frequently)
        upkeep_per_tick = upkeep // 60  # Spread monthly cost over ~60 ticks
        self.money -= upkeep_per_tick
        self.last_upkeep = upkeep_per_tick
        return upkeep_per_tick
    
    def to_dict(self):
        """Serialize economy state for saving."""
        return {
            'money': self.money,
            'tax_rate': self.tax_rate,
        }
    
    def from_dict(self, data):
        """Restore economy state from saved data."""
        self.money = data.get('money', STARTING_MONEY)
        self.tax_rate = data.get('tax_rate', 7)
