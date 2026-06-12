"""
Helpers for incremental scalar fields (crime, land value).

Instead of every tile gathering from its neighborhood each tick (O(map x
radius^2)), sources scatter their contribution into a 2D field once, and only
re-scatter a delta when their strength changes. Per-tick cost is proportional
to how much the city changed, not to map size.

The field is stored flat (index = x * height + y) so interior sources can
scatter through precomputed (offset, weight) pairs without bounds checks.
"""


def falloff_kernel(radius, exclude_center=False):
    """Precomputed (dx, dy, 1/dist) offsets for a square neighborhood.

    Distance is clamped to a minimum of 1, matching the original per-tile
    gather math.
    """
    kernel = []
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            if exclude_center and dx == 0 and dy == 0:
                continue
            dist = max(1.0, (dx * dx + dy * dy) ** 0.5)
            kernel.append((dx, dy, 1.0 / dist))
    return kernel


def linear_kernel(radius):
    """Precomputed (dx, dy, 1 - dist/radius) offsets within a circular radius."""
    kernel = []
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            dist = (dx * dx + dy * dy) ** 0.5
            if dist <= radius:
                kernel.append((dx, dy, 1.0 - dist / radius))
    return kernel


class IncrementalField:
    """A 2D contribution field maintained by diffing source strengths.

    Call refresh() each tick with the current {(x, y): strength} sources;
    only changed sources re-scatter their delta. Read values via at() or,
    for bulk loops, index .field directly with x * height + y.
    """

    def __init__(self, kernel):
        self.kernel = kernel
        self.radius = max(max(abs(dx), abs(dy)) for dx, dy, _ in kernel)
        self.field = None  # Flat list, index = x * height + y
        self.width = 0
        self.height = 0
        self._strengths = {}
        self._flat_kernel = None  # (flat offset, weight) pairs for interior scatter

    def resize(self, width, height):
        """(Re)allocate the field if grid dimensions changed; resets caches."""
        if self.width != width or self.height != height:
            self.width = width
            self.height = height
            self.field = [0.0] * (width * height)
            self._strengths = {}
            self._flat_kernel = [(dx * height + dy, weight)
                                 for dx, dy, weight in self.kernel]

    def at(self, x, y):
        return self.field[x * self.height + y]

    def refresh(self, sources):
        """Update the field to reflect the given {(x, y): strength} sources."""
        for pos, strength in sources.items():
            old = self._strengths.get(pos, 0.0)
            if strength != old:
                self._scatter(pos[0], pos[1], strength - old)
        for pos, old in self._strengths.items():
            if pos not in sources:
                self._scatter(pos[0], pos[1], -old)
        self._strengths = sources

    def _scatter(self, x, y, delta):
        radius = self.radius
        height = self.height
        field = self.field
        if (radius <= x < self.width - radius and
                radius <= y < height - radius):
            # Interior: no bounds checks needed
            base = x * height + y
            for offset, weight in self._flat_kernel:
                field[base + offset] += delta * weight
        else:
            for dx, dy, weight in self.kernel:
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.width and 0 <= ny < height:
                    field[nx * height + ny] += delta * weight
