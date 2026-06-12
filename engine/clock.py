"""
Game clock: simulation ticks -> calendar months/years, classic SimCity style.

One game month passes every TICKS_PER_MONTH simulation ticks. Taxes and
upkeep are settled on month boundaries (see Game.update), which preserves the
same average cash flow as the old per-tick collection.
"""

MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


class GameClock:
    TICKS_PER_MONTH = 60  # At 1x speed (1 tick/sec) a month is one real minute

    def __init__(self, start_year=2000):
        self.start_year = start_year
        self.tick = 0

    def advance(self):
        """Advance one tick. Returns True when a new month begins."""
        self.tick += 1
        return self.tick % self.TICKS_PER_MONTH == 0

    @property
    def total_months(self):
        return self.tick // self.TICKS_PER_MONTH

    @property
    def month(self):
        """Month index 0-11."""
        return self.total_months % 12

    @property
    def year(self):
        return self.start_year + self.total_months // 12

    @property
    def date_string(self):
        return f"{MONTH_NAMES[self.month]} {self.year}"

    def to_dict(self):
        return {'tick': self.tick, 'start_year': self.start_year}

    def from_dict(self, data):
        self.tick = data.get('tick', 0)
        self.start_year = data.get('start_year', 2000)
