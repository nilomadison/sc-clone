"""
3x3 zones with density tiers, classic SimCity style.

A Zone groups member tiles under one plot: placement stamps a validated 3x3
grass area, bulldozing any member clears the whole zone, and growth promotes
the zone through density tiers that raise each member tile's population cap.

Member tiles point back at their zone via Tile.structure. Population still
lives on the tiles, so crime/demand/tax systems keep reading tiles as before.
Pre-0.9 saves load as zoneless RCI tiles, which GrowthSystem treats as legacy
single-tile plots.
"""

ZONE_SIZE = 3

# Population cap per member tile at each density tier. A zone promotes to the
# next tier when its average member population reaches the current cap.
TIER_TILE_CAP = (2, 4, 7, 10)


class Zone:
    def __init__(self, zone_type, members, density=0):
        self.type = zone_type
        self.members = list(members)  # [(x, y)] positions
        self.density = density  # 0-3
        self.has_access = True  # Counterpart reachable by road (TrafficSystem)

    def live_members(self, grid):
        """Member tiles that still belong to this zone (floods etc. can
        steal tiles by changing their type, which clears Tile.structure)."""
        return [grid.tiles[x][y] for x, y in self.members
                if grid.tiles[x][y].structure is self]

    def population(self, grid):
        return sum(tile.population for tile in self.live_members(grid))

    def update_density(self, grid):
        """Recompute the density tier from average member population."""
        members = self.live_members(grid)
        if not members:
            self.density = 0
            return
        average = sum(t.population for t in members) / len(members)
        tier = 0
        while tier < len(TIER_TILE_CAP) - 1 and average >= TIER_TILE_CAP[tier]:
            tier += 1
        self.density = tier

    def tile_cap(self):
        return TIER_TILE_CAP[self.density]

    def to_dict(self):
        return {'type': self.type, 'members': [list(m) for m in self.members],
                'density': self.density}

    @classmethod
    def from_dict(cls, data):
        return cls(data['type'], [tuple(m) for m in data['members']],
                   data.get('density', 0))


def stamps_for_rect(min_x, min_y, max_x, max_y):
    """Top-left corners of the 3x3 stamps that tile a drag rectangle.

    A rectangle too small for a full stamp yields one stamp centered on it,
    so a plain click still places a zone.
    """
    stamps = []
    for zx in range(min_x, max_x - ZONE_SIZE + 2, ZONE_SIZE):
        for zy in range(min_y, max_y - ZONE_SIZE + 2, ZONE_SIZE):
            stamps.append((zx, zy))
    if not stamps:
        cx = (min_x + max_x) // 2
        cy = (min_y + max_y) // 2
        stamps = [(cx - ZONE_SIZE // 2, cy - ZONE_SIZE // 2)]
    return stamps
