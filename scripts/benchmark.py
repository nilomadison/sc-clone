"""Per-system tick timing on a large city. Run: python scripts/benchmark.py"""
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.crime import CrimeSystem
from engine.decay import DecaySystem
from engine.economy import EconomySystem
from engine.fire import FireSystem
from engine.grid import Grid
from engine.land_value import LandValueSystem
from engine.systems import DemandSystem, GrowthSystem, PowerSystem
from engine.traffic import TrafficSystem


def build_city(grid):
    """Fill most of the map: road grid, RCI blocks, sprinkled services."""
    random.seed(99)
    zones = ['residential', 'commercial', 'industrial']
    for x in range(2, grid.width - 2):
        for y in range(2, grid.height - 2):
            if x % 5 == 0 or y % 5 == 0:
                grid.set_tile_type(x, y, 'road')
            else:
                grid.set_tile_type(x, y, zones[(x // 5 + y // 5) % 3])
                grid.get_tile(x, y).population = random.randint(0, 10)
    for i in range(10):
        grid.set_tile_type(5 + i * 9, 5, 'power_plant')
        grid.set_tile_type(5 + i * 9, 50, 'police')
        grid.set_tile_type(5 + i * 9, 95 - 2, 'fire_station')


def main():
    grid = Grid(100, 100)
    build_city(grid)
    economy = EconomySystem()

    systems = [
        ('power', PowerSystem(), lambda s: s.update(grid)),
        ('growth', GrowthSystem(), lambda s: s.update(grid)),
        ('demand', DemandSystem(), lambda s: s.update(grid)),
        ('traffic', TrafficSystem(), lambda s: s.update(grid)),
        ('crime', CrimeSystem(), lambda s: s.update(grid)),
        ('land_value', LandValueSystem(), lambda s: s.update(grid)),
        ('fire', FireSystem(), lambda s: s.update(grid, economy)),
        ('decay', DecaySystem(), lambda s: s.update(grid, economy)),
        ('taxes', economy, lambda s: s.collect_monthly_taxes(grid, 60)),
        ('upkeep', economy, lambda s: s.deduct_monthly_upkeep(grid)),
    ]

    # Warmup: the incremental fields do a full build on their first tick
    for _ in range(3):
        for name, system, run in systems:
            run(system)

    ticks = 20
    totals = {name: 0.0 for name, _, _ in systems}
    for _ in range(ticks):
        for name, system, run in systems:
            t0 = time.perf_counter()
            run(system)
            totals[name] += time.perf_counter() - t0

    print(f"Average per-tick cost over {ticks} ticks (100x100 map, dense city):")
    grand = 0.0
    for name, _, _ in systems:
        ms = totals[name] / ticks * 1000
        grand += ms
        print(f"  {name:<12} {ms:8.2f} ms")
    print(f"  {'TOTAL':<12} {grand:8.2f} ms   (budget: 16.7 ms/frame at 60fps)")


if __name__ == '__main__':
    main()
