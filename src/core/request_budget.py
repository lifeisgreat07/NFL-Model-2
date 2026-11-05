"""A run's season-schedule read: retried like every other read, and stopped at a budget
(Stage 93 item 18, audit 7 R12).

The day sports read a season's schedule in dozens of requests (32 club lists
for the NHL, a day at a time for the NBA). The NHL's went through a plain
`urlopen` with no retry, so one dropped connection failed the whole run; the
NBA's retried through `history.fetch` but had no ceiling, so a slow feed could
run the step into its timeout, which kills the job with nothing kept. Both now
read through their sport's retrying `history.fetch`, wrapped in a `Budget`: a
request asked for after `SCHEDULE_SECONDS` raises `BudgetSpent`, a clean
failure the run reports, well inside the step's 25-minute timeout.
"""
from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar('T')

#: Ten minutes for one season's schedule. A normal read takes well under one
#: (the NHL's 32 lists, the NBA's season of days); the daily step's timeout is 25.
SCHEDULE_SECONDS = 600.0


class BudgetSpent(RuntimeError):
    """The run asked for another request after its budget ran out."""


class Budget:
    def __init__(self, seconds: float = SCHEDULE_SECONDS, clock: Callable[[], float] = time.monotonic) -> None:
        self.seconds = seconds
        self.clock = clock
        self.start = clock()
        self.requests = 0

    def wrap(self, get: Callable[[str], T]) -> Callable[[str], T]:
        """`get`, refusing any request asked for once the budget is spent."""
        def budgeted(url: str) -> T:
            spent = self.clock() - self.start
            if spent > self.seconds:
                raise BudgetSpent(f'{self.requests} requests in {spent:.0f} s, past the budget of '
                                  f'{self.seconds:.0f} s; stopped before {url}')
            self.requests += 1
            return get(url)
        return budgeted
