"""
Santa 2018 TSP solver — the agent's playground.

Current experiment: L5 — numba-jit'd 2-opt with k=10 cKDTree candidate list,
seeded by nearest-neighbor from city 0.
"""

import time
import numpy as np
from scipy.spatial import cKDTree
from numba import njit

from prepare import (
    TIME_BUDGET,
    START_CITY,
    SUBMISSIONS_DIR,
    TimeBudget,
    load_cities,
    score_tour,
    write_submission,
)

K_NEIGHBORS = 10


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

def nearest_neighbor(xy, budget):
    n = len(xy)
    visited = np.zeros(n, dtype=bool)
    tour = np.empty(n + 1, dtype=np.int64)
    tour[0] = START_CITY
    tour[-1] = START_CITY
    visited[START_CITY] = True
    cur = START_CITY
    for step in range(1, n):
        if budget.expired():
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


# ---------------------------------------------------------------------------
# 2-opt with candidate lists (numba)
# ---------------------------------------------------------------------------

@njit(cache=True, fastmath=True, inline='always')
def _euclid(xy, a, b):
    dx = xy[a, 0] - xy[b, 0]
    dy = xy[a, 1] - xy[b, 1]
    return (dx * dx + dy * dy) ** 0.5


@njit(cache=True, fastmath=True)
def two_opt_sweep(tour, pos, xy, candidates):
    """One greedy first-improvement pass; returns number of improvements applied.

    For each city a at position ai, scans a's k nearest neighbours c and tries the
    2-opt that introduces edge (a, c). Two cases depending on whether c sits later
    or earlier in the tour — both produce the same gain formula but reverse a
    different sub-segment.
    """
    n = len(xy)
    K = candidates.shape[1]
    n_improvements = 0
    for ai in range(1, n):
        a = tour[ai]
        a_next = tour[ai + 1]
        d_a_anext = _euclid(xy, a, a_next)
        for kk in range(K):
            c = candidates[a, kk]
            if c == 0:
                continue
            cj = pos[c]
            # Case A: c is later in the tour (cj > ai+1). Move = reverse tour[ai+1..cj].
            # Case B: c is earlier in the tour (cj < ai-1). Move = reverse tour[cj+1..ai].
            if cj > ai + 1 and cj < n:
                c_next = tour[cj + 1]
                d_a_c = _euclid(xy, a, c)
                d_c_cnext = _euclid(xy, c, c_next)
                d_anext_cnext = _euclid(xy, a_next, c_next)
                gain = d_a_anext + d_c_cnext - d_a_c - d_anext_cnext
                if gain > 1e-12:
                    lo = ai + 1
                    hi = cj
                    while lo < hi:
                        x = tour[lo]
                        y = tour[hi]
                        tour[lo] = y
                        tour[hi] = x
                        pos[y] = lo
                        pos[x] = hi
                        lo += 1
                        hi -= 1
                    n_improvements += 1
                    a_next = tour[ai + 1]
                    d_a_anext = _euclid(xy, a, a_next)
                    continue
            elif cj >= 1 and cj < ai - 1:
                c_next = tour[cj + 1]
                d_a_c = _euclid(xy, a, c)
                d_c_cnext = _euclid(xy, c, c_next)
                d_anext_cnext = _euclid(xy, a_next, c_next)
                gain = d_a_anext + d_c_cnext - d_a_c - d_anext_cnext
                if gain > 1e-12:
                    lo = cj + 1
                    hi = ai
                    while lo < hi:
                        x = tour[lo]
                        y = tour[hi]
                        tour[lo] = y
                        tour[hi] = x
                        pos[y] = lo
                        pos[x] = hi
                        lo += 1
                        hi -= 1
                    n_improvements += 1
                    # `a` itself moved (it's now at position cj+1). Re-fetch from current ai.
                    a = tour[ai]
                    a_next = tour[ai + 1]
                    d_a_anext = _euclid(xy, a, a_next)
                    continue
    return n_improvements


def build_candidates(xy, k):
    tree = cKDTree(xy)
    _, idx = tree.query(xy, k=k + 1)
    return idx[:, 1:].astype(np.int32)


def two_opt(tour, xy, candidates, budget):
    n = len(xy)
    pos = np.empty(n, dtype=np.int64)
    pos[tour[:-1]] = np.arange(n, dtype=np.int64)
    sweep = 0
    while not budget.expired():
        t0 = time.perf_counter()
        n_imp = two_opt_sweep(tour, pos, xy, candidates)
        sweep += 1
        print(f"  2-opt sweep {sweep}: {n_imp} improvements ({time.perf_counter() - t0:.2f}s, "
              f"budget remaining {budget.remaining():.1f}s)")
        if n_imp == 0:
            break
    return tour


# ---------------------------------------------------------------------------
# Solver entry point
# ---------------------------------------------------------------------------

def solve(xy, is_prime, budget):
    print("  building NN tour ...")
    tour = nearest_neighbor(xy, budget)
    print(f"  NN done in {budget.elapsed():.2f}s, remaining {budget.remaining():.1f}s")

    if budget.remaining() < 5:
        return tour

    print("  building cKDTree + candidate list ...")
    t0 = time.perf_counter()
    candidates = build_candidates(xy, K_NEIGHBORS)
    print(f"  candidates built in {time.perf_counter() - t0:.2f}s")

    if budget.remaining() < 1:
        return tour

    print("  running 2-opt ...")
    tour = two_opt(tour, xy, candidates, budget)
    return tour


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def main():
    t_start = time.perf_counter()
    print("loading cities ...")
    xy, is_prime = load_cities()
    n = len(xy)
    print(f"  N = {n}")

    budget = TimeBudget(TIME_BUDGET)
    print(f"solving (budget = {TIME_BUDGET}s) ...")
    tour = solve(xy, is_prime, budget)
    solve_seconds = budget.elapsed()

    print("scoring ...")
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
