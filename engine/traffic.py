"""
Traffic simulation, simplified classic style.

Each zone periodically runs a bounded BFS along the road network looking for
its counterpart (residents commute to jobs, shops need customers, industry
ships goods). Success grants the zone road *access* — required for growth —
and lays traffic along the trip's path. Road traffic decays each tick, and
busy roads drag down nearby land value (see LandValueSystem).

Routing is staggered: only SAMPLE_PER_TICK zones route per tick, cycling
through the whole city, so cost stays bounded on big maps.
"""

from collections import deque
import random

from engine.tiles import ZONE_TYPES

# Trip destinations by zone type
DESTINATIONS = {
    'residential': ('commercial', 'industrial'),  # Commute to jobs
    'commercial': ('residential',),               # Customers
    'industrial': ('commercial',),                # Ship goods to shops
}

DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]


class TrafficSystem:
    MAX_TRIP_DISTANCE = 30  # Road tiles a trip may traverse
    SAMPLE_PER_TICK = 20    # Zones/plots routed per tick
    TRAFFIC_PER_TRIP = 2.0  # Traffic added to each road on a successful trip
    TRAFFIC_DECAY = 0.95    # Per-tick decay multiplier
    TRAFFIC_CAP = 100.0

    def __init__(self):
        self._queue = []  # Pending ('zone', Zone) / ('tile', (x, y)) entries

    def update(self, grid):
        self._decay_traffic(grid)

        if not self._queue:
            self._queue = self._build_queue(grid)
        for _ in range(min(self.SAMPLE_PER_TICK, len(self._queue))):
            self._route_entry(grid, self._queue.pop())

    def _build_queue(self, grid):
        queue = [('zone', zone) for zone in grid.zones]
        for x, y in grid.positions(*ZONE_TYPES):
            if grid.tiles[x][y].structure is None:
                queue.append(('tile', (x, y)))
        random.shuffle(queue)
        return queue

    def _route_entry(self, grid, entry):
        kind, obj = entry
        if kind == 'zone':
            if obj not in grid.zones:
                return  # Bulldozed since queued
            members = [(t.x, t.y) for t in obj.live_members(grid)]
            if not members:
                return
            obj.has_access = self._route(grid, members, DESTINATIONS[obj.type])
        else:
            x, y = obj
            tile = grid.tiles[x][y]
            if tile.structure is not None or tile.type not in DESTINATIONS:
                return  # Changed since queued
            tile.has_access = self._route(grid, [(x, y)], DESTINATIONS[tile.type])

    def _route(self, grid, members, dest_types):
        """BFS along roads from the plot; lay traffic if a destination is
        reachable within MAX_TRIP_DISTANCE. Returns success."""
        # Trip starts on roads adjacent to the plot
        parents = {}
        queue = deque()
        for x, y in members:
            for dx, dy in DIRECTIONS:
                tile = grid.get_tile(x + dx, y + dy)
                if tile is not None and tile.type == 'road' and (tile.x, tile.y) not in parents:
                    parents[(tile.x, tile.y)] = None
                    queue.append(((tile.x, tile.y), 0))
        if not queue:
            return False

        while queue:
            (x, y), dist = queue.popleft()
            for dx, dy in DIRECTIONS:
                nx, ny = x + dx, y + dy
                tile = grid.get_tile(nx, ny)
                if tile is None:
                    continue
                if tile.type in dest_types and not tile.is_burned:
                    self._lay_traffic(grid, parents, (x, y))
                    return True
                if (tile.type == 'road' and (nx, ny) not in parents and
                        dist + 1 <= self.MAX_TRIP_DISTANCE):
                    parents[(nx, ny)] = (x, y)
                    queue.append(((nx, ny), dist + 1))
        return False

    def _lay_traffic(self, grid, parents, end):
        pos = end
        while pos is not None:
            tile = grid.tiles[pos[0]][pos[1]]
            tile.traffic = min(self.TRAFFIC_CAP, tile.traffic + self.TRAFFIC_PER_TRIP)
            pos = parents[pos]

    def _decay_traffic(self, grid):
        for x, y in grid.positions('road'):
            tile = grid.tiles[x][y]
            if tile.traffic > 0:
                tile.traffic *= self.TRAFFIC_DECAY
                if tile.traffic < 0.1:
                    tile.traffic = 0.0
