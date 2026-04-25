"""
Santa 2018 TSP — neural-guided local search baseline.

This is the agent's playground in tsp_neural/. The goal is to add a
small learned move-scorer that guides the 2-opt / Or-opt inner loops
better than the geographic k-NN heuristic does.

The starting baseline below is intentionally simple:
    NN construction (cKDTree-walked) → 2-opt with k=10 candidate list

No learning yet. No Or-opt, no ILS, no prime-aware moves. The agent's
job is to introduce learning first (the whole point of this sibling
project), then add the rest of the pipeline as needed.

If you find yourself adding 2-opt/Or-opt/ILS without any learned
component, you are duplicating tsp_research/ and missing the point.
The differentiator here is the neural move scorer.

Contract: same as tsp_research — produce a numpy int64 array of length
N+1 starting and ending at START_CITY visiting every CityId once.
Print a summary block ending with `val_cost: <float>`.
"""

import os
import subprocess
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

import harvest as _harvest

K_NEIGHBORS = 10
HARVEST = os.environ.get("HARVEST", "0") == "1"


# ---------------------------------------------------------------------------
# Construction: cKDTree-walked nearest neighbor
# ---------------------------------------------------------------------------

def nearest_neighbor(xy, candidates, budget):
    n = len(xy)
    visited = np.zeros(n, dtype=bool)
    tour = np.empty(n + 1, dtype=np.int64)
    tour[0] = START_CITY
    tour[-1] = START_CITY
    visited[START_CITY] = True

    cur = START_CITY
    for step in range(1, n):
        if budget.expired():
            tour[step:-1] = np.where(~visited)[0]
            return tour
        # try candidates first
        nxt = -1
        for c in candidates[cur]:
            if not visited[c]:
                nxt = int(c)
                break
        if nxt < 0:
            d = xy - xy[cur]
            d2 = (d * d).sum(axis=1)
            d2[visited] = np.inf
            nxt = int(np.argmin(d2))
        tour[step] = nxt
        visited[nxt] = True
        cur = nxt
    return tour


# ---------------------------------------------------------------------------
# 2-opt with k-NN candidate list
# ---------------------------------------------------------------------------

@njit(cache=True, fastmath=True, inline='always')
def _euclid(xy, a, b):
    dx = xy[a, 0] - xy[b, 0]
    dy = xy[a, 1] - xy[b, 1]
    return (dx * dx + dy * dy) ** 0.5


@njit(cache=True, fastmath=True)
def two_opt_sweep(tour, pos, xy, candidates):
    """One greedy first-improvement 2-opt pass; returns # of improvements."""
    n = len(xy)
    K = candidates.shape[1]
    n_imp = 0
    for ai in range(1, n):
        a = tour[ai]
        a_next = tour[ai + 1]
        d_a_anext = _euclid(xy, a, a_next)
        for kk in range(K):
            c = candidates[a, kk]
            if c == 0:
                continue
            cj = pos[c]
            if cj > ai + 1 and cj < n:
                c_next = tour[cj + 1]
                gain = d_a_anext + _euclid(xy, c, c_next) \
                       - _euclid(xy, a, c) - _euclid(xy, a_next, c_next)
                if gain > 1e-12:
                    lo, hi = ai + 1, cj
                    while lo < hi:
                        x, y = tour[lo], tour[hi]
                        tour[lo], tour[hi] = y, x
                        pos[y], pos[x] = lo, hi
                        lo += 1
                        hi -= 1
                    n_imp += 1
                    a_next = tour[ai + 1]
                    d_a_anext = _euclid(xy, a, a_next)
            elif cj >= 1 and cj < ai - 1:
                c_next = tour[cj + 1]
                gain = d_a_anext + _euclid(xy, c, c_next) \
                       - _euclid(xy, a, c) - _euclid(xy, a_next, c_next)
                if gain > 1e-12:
                    lo, hi = cj + 1, ai
                    while lo < hi:
                        x, y = tour[lo], tour[hi]
                        tour[lo], tour[hi] = y, x
                        pos[y], pos[x] = lo, hi
                        lo += 1
                        hi -= 1
                    n_imp += 1
                    a = tour[ai]
                    a_next = tour[ai + 1]
                    d_a_anext = _euclid(xy, a, a_next)
    return n_imp


def run_2opt(tour, pos, xy, candidates, budget, max_sweeps=10_000):
    sweeps = 0
    while sweeps < max_sweeps and not budget.expired():
        n_imp = two_opt_sweep(tour, pos, xy, candidates)
        sweeps += 1
        if n_imp == 0:
            break
    return sweeps


@njit(cache=True, fastmath=True)
def two_opt_sweep_harvest(tour, pos, xy, candidates,
                          buf_a, buf_a_next, buf_c, buf_c_next,
                          buf_pos_delta, buf_gain, buf_accepted, count_arr):
    """Same as two_opt_sweep but logs every scored candidate."""
    n = len(xy)
    K = candidates.shape[1]
    cap = buf_a.shape[0]
    n_imp = 0
    for ai in range(1, n):
        a = tour[ai]
        a_next = tour[ai + 1]
        d_a_anext = _euclid(xy, a, a_next)
        for kk in range(K):
            c = candidates[a, kk]
            if c == 0:
                continue
            cj = pos[c]
            if cj > ai + 1 and cj < n:
                c_next = tour[cj + 1]
                gain = d_a_anext + _euclid(xy, c, c_next) \
                       - _euclid(xy, a, c) - _euclid(xy, a_next, c_next)
                idx = count_arr[0]
                if idx < cap:
                    buf_a[idx] = a
                    buf_a_next[idx] = a_next
                    buf_c[idx] = c
                    buf_c_next[idx] = c_next
                    buf_pos_delta[idx] = cj - ai
                    buf_gain[idx] = gain
                    buf_accepted[idx] = 1 if gain > 1e-12 else 0
                    count_arr[0] = idx + 1
                if gain > 1e-12:
                    lo, hi = ai + 1, cj
                    while lo < hi:
                        x, y = tour[lo], tour[hi]
                        tour[lo], tour[hi] = y, x
                        pos[y], pos[x] = lo, hi
                        lo += 1
                        hi -= 1
                    n_imp += 1
                    a_next = tour[ai + 1]
                    d_a_anext = _euclid(xy, a, a_next)
            elif cj >= 1 and cj < ai - 1:
                c_next = tour[cj + 1]
                gain = d_a_anext + _euclid(xy, c, c_next) \
                       - _euclid(xy, a, c) - _euclid(xy, a_next, c_next)
                idx = count_arr[0]
                if idx < cap:
                    buf_a[idx] = a
                    buf_a_next[idx] = a_next
                    buf_c[idx] = c
                    buf_c_next[idx] = c_next
                    buf_pos_delta[idx] = ai - cj
                    buf_gain[idx] = gain
                    buf_accepted[idx] = 1 if gain > 1e-12 else 0
                    count_arr[0] = idx + 1
                if gain > 1e-12:
                    lo, hi = cj + 1, ai
                    while lo < hi:
                        x, y = tour[lo], tour[hi]
                        tour[lo], tour[hi] = y, x
                        pos[y], pos[x] = lo, hi
                        lo += 1
                        hi -= 1
                    n_imp += 1
                    a = tour[ai]
                    a_next = tour[ai + 1]
                    d_a_anext = _euclid(xy, a, a_next)
    return n_imp


def run_2opt_harvest(tour, pos, xy, candidates, budget, bufs, max_sweeps=10_000):
    sweeps = 0
    while sweeps < max_sweeps and not budget.expired():
        n_imp = two_opt_sweep_harvest(
            tour, pos, xy, candidates,
            bufs["a"], bufs["a_next"], bufs["c"], bufs["c_next"],
            bufs["pos_delta"], bufs["gain"], bufs["accepted"], bufs["count"],
        )
        sweeps += 1
        if n_imp == 0:
            break
    return sweeps


# ---------------------------------------------------------------------------
# Solver entry point
# ---------------------------------------------------------------------------

def solve(xy, is_prime, budget, harvest_bufs=None):
    print("  building candidate list (cKDTree) ...")
    tree = cKDTree(xy)
    _, idx = tree.query(xy, k=K_NEIGHBORS + 1)
    candidates = idx[:, 1:].astype(np.int32)

    print("  building NN tour ...")
    tour = nearest_neighbor(xy, candidates, budget)
    print(f"  NN done, remaining {budget.remaining():.1f}s")

    if budget.remaining() < 1:
        return tour

    n = len(xy)
    pos = np.empty(n, dtype=np.int64)
    pos[tour[:-1]] = np.arange(n, dtype=np.int64)

    if harvest_bufs is not None:
        print("  running 2-opt (HARVEST=1, logging candidates) ...")
        sweeps = run_2opt_harvest(tour, pos, xy, candidates, budget, harvest_bufs)
    else:
        print("  running 2-opt ...")
        sweeps = run_2opt(tour, pos, xy, candidates, budget)
    print(f"  2-opt converged in {sweeps} sweeps, remaining {budget.remaining():.1f}s")

    return tour


def main():
    t_start = time.perf_counter()
    print(f"loading cities ...")
    xy, is_prime = load_cities()
    n = len(xy)
    print(f"  N = {n}")

    budget = TimeBudget(TIME_BUDGET)
    print(f"solving (budget = {TIME_BUDGET}s) ...")

    harvest_bufs = _harvest.make_buffers() if HARVEST else None
    if HARVEST:
        print(f"  HARVEST=1 — buffer cap = {len(harvest_bufs['a']):,} rows")

    tour = solve(xy, is_prime, budget, harvest_bufs=harvest_bufs)
    solve_seconds = budget.elapsed()

    print(f"scoring ...")
    cost = score_tour(tour, xy, is_prime)
    total_seconds = time.perf_counter() - t_start

    out_path = SUBMISSIONS_DIR / "submission.csv"
    write_submission(tour, out_path)

    moves_logged = 0
    moves_path = None
    if HARVEST:
        try:
            tag = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"]
            ).decode().strip()
        except Exception:
            tag = "uncommitted"
        moves_path, moves_logged = _harvest.save_buffers(harvest_bufs, tag)

    print("---")
    print(f"val_cost:         {cost:.4f}")
    print(f"solve_seconds:    {solve_seconds:.2f}")
    print(f"total_seconds:    {total_seconds:.2f}")
    print(f"n_cities:         {n}")
    print(f"submission:       {out_path}")
    if HARVEST:
        print(f"moves_logged:     {moves_logged}")
        print(f"moves_path:       {moves_path}")


if __name__ == "__main__":
    main()
