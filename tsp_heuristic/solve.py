"""
Santa 2018 TSP solver — the agent's playground.

This is the ONLY file the agent edits. Everything is fair game:
algorithms, data structures, heuristics, neural nets, whatever fits in
the TIME_BUDGET wall-clock budget defined in prepare.py.

Contract:
    - Read xy, is_prime via prepare.load_cities().
    - Produce a numpy int64 array of length N+1 starting and ending at
      prepare.START_CITY that visits every CityId exactly once.
    - Print a summary block (see end of file) so the loop driver can
      grep the result. The val_cost line is the canonical metric.

The baseline below is nearest-neighbor from city 0. It's intentionally
simple — beat it.
"""

import os
import sys
import time
from pathlib import Path

import numpy as np

from prepare import (
    TIME_BUDGET,
    START_CITY,
    SUBMISSIONS_DIR,
    TimeBudget,
    load_cities,
    score_tour,
    write_submission,
)

# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------

def nearest_neighbor(xy, budget):
    """Greedy nearest-neighbor tour starting at START_CITY.

    Vectorised with periodic chunking so we stay responsive to the
    time budget on large N (~2e5).
    """
    n = len(xy)
    visited = np.zeros(n, dtype=bool)
    tour = np.empty(n + 1, dtype=np.int64)
    tour[0] = START_CITY
    tour[-1] = START_CITY
    visited[START_CITY] = True

    cur = START_CITY
    for step in range(1, n):
        if budget.expired():
            # Fall back to filling remaining slots in original index order.
            remaining = np.where(~visited)[0]
            tour[step:step + len(remaining)] = remaining
            return tour

        d = xy - xy[cur]
        d2 = (d * d).sum(axis=1)
        d2[visited] = np.inf
        nxt = int(np.argmin(d2))
        tour[step] = nxt
        visited[nxt] = True
        cur = nxt

    return tour


def solve(xy, is_prime, budget):
    return nearest_neighbor(xy, budget)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def main():
    t_start = time.perf_counter()
    print(f"loading cities ...")
    xy, is_prime = load_cities()
    n = len(xy)
    print(f"  N = {n}")

    budget = TimeBudget(TIME_BUDGET)
    print(f"solving (budget = {TIME_BUDGET}s) ...")
    tour = solve(xy, is_prime, budget)
    solve_seconds = budget.elapsed()

    print(f"scoring ...")
    cost = score_tour(tour, xy, is_prime)
    total_seconds = time.perf_counter() - t_start

    out_path = SUBMISSIONS_DIR / "submission.csv"
    write_submission(tour, out_path)

    print("---")
    print(f"val_cost:         {cost:.4f}")
    print(f"solve_seconds:    {solve_seconds:.2f}")
    print(f"total_seconds:    {total_seconds:.2f}")
    print(f"n_cities:         {n}")
    print(f"submission:       {out_path}")


if __name__ == "__main__":
    main()
