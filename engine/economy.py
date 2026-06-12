"""
Economy system for SimCity Clone.
Handles money, zone placement costs, and tax collection.
"""

from engine.tiles import field_map

# Starting money for new games
STARTING_MONEY = 20000

# Cost to place each tile type
ZONE_COSTS = field_map('cost')

# Monthly upkeep costs for service buildings
UPKEEP_COSTS = field_map('upkeep', lambda v: v > 0)

# Base tax income per population per simulation tick
BASE_TAX_RATES = field_map('tax_rate', lambda v: v > 0)


class EconomySystem:
    """Manages city treasury, costs, and tax collection."""
    
    def __init__(self):
        self.money = STARTING_MONEY
        self.tax_rate = 7  # Percentage (1-20)
        self.last_upkeep = 0  # Track for display
        # v0.4.0: Service funding levels (0.0 to 1.0)
        self.service_funding = {
            'police': 1.0,
            'fire': 1.0,
        }
    
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
    
    def tax_income_per_tick(self, grid):
        """Tax income rate from all intact, powered, populated zones."""
        income = 0.0
        tax_multiplier = self.tax_rate / 7.0  # 7% is baseline

        for x, y in grid.positions(*BASE_TAX_RATES):
            tile = grid.tiles[x][y]

            # Only intact, powered tiles generate tax income
            if tile.is_powered and tile.population > 0 and not tile.is_burned:
                income += tile.population * BASE_TAX_RATES[tile.type] * tax_multiplier

        return income

    def collect_monthly_taxes(self, grid, ticks_per_month):
        """Collect a month's taxes at once. Returns the income collected."""
        income = round(self.tax_income_per_tick(grid) * ticks_per_month)
        self.money += income
        return income

    def monthly_upkeep(self, grid):
        """Total monthly upkeep for service buildings, scaled by funding."""
        upkeep = 0.0

        for x, y in grid.positions(*UPKEEP_COSTS):
            tile = grid.tiles[x][y]
            base_cost = UPKEEP_COSTS[tile.type]

            # v0.4.0: Scale upkeep by funding level
            if tile.type == 'police':
                cost = base_cost * self.service_funding.get('police', 1.0)
            elif tile.type == 'fire_station':
                cost = base_cost * self.service_funding.get('fire', 1.0)
            else:
                cost = base_cost

            upkeep += cost

        return int(upkeep)

    def deduct_monthly_upkeep(self, grid):
        """Deduct a month's upkeep at once. Returns the amount deducted."""
        upkeep = self.monthly_upkeep(grid)
        self.money -= upkeep
        self.last_upkeep = upkeep
        return upkeep
    
    def to_dict(self):
        """Serialize economy state for saving."""
        return {
            'money': self.money,
            'tax_rate': self.tax_rate,
            'service_funding': self.service_funding,  # v0.4.0
        }
    
    def from_dict(self, data):
        """Restore economy state from saved data."""
        self.money = data.get('money', STARTING_MONEY)
        self.tax_rate = data.get('tax_rate', 7)
        # v0.4.0: Restore service funding
        self.service_funding = data.get('service_funding', {'police': 1.0, 'fire': 1.0})
