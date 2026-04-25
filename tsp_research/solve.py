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

@njit(cache=True, fastmath=True)
def fast_nn(xy, candidates, start):
    """Greedy NN tour using a precomputed k-NN candidate list. When all of a
    city's k neighbours are already visited, fall back to a numba brute scan."""
    n = xy.shape[0]
    K = candidates.shape[1]
    visited = np.zeros(n, dtype=np.bool_)
    tour = np.empty(n + 1, dtype=np.int64)
    tour[0] = start
    tour[-1] = start
    visited[start] = True
    cur = start
    fallbacks = 0
    for step in range(1, n):
        nxt = -1
        for kk in range(K):
            c = candidates[cur, kk]
            if not visited[c]:
                nxt = c
                break
        if nxt < 0:
            best_d = 1e30
            for i in range(n):
                if visited[i]:
                    continue
                dx = xy[i, 0] - xy[cur, 0]
                dy = xy[i, 1] - xy[cur, 1]
                d = dx * dx + dy * dy
                if d < best_d:
                    best_d = d
                    nxt = i
            fallbacks += 1
        tour[step] = nxt
        visited[nxt] = True
        cur = nxt
    return tour, fallbacks


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


@njit(cache=True, fastmath=True)
def or_seg_sweep(tour, pos, xy, candidates, L):
    """Or-opt with segment length L (1, 2, or 3). Inserts forward (no reversal)
    after the best position drawn from the k-NN of the segment's first city."""
    n = len(xy)
    K = candidates.shape[1]
    n_imp = 0
    for s in range(1, n - L + 1):
        x0 = tour[s]
        xL = tour[s + L - 1]
        a = tour[s - 1]
        b = tour[s + L]
        d_ax0 = _euclid(xy, a, x0)
        d_xLb = _euclid(xy, xL, b)
        d_ab = _euclid(xy, a, b)
        gap_save = d_ax0 + d_xLb - d_ab
        if gap_save <= 1e-12:
            continue
        best_gain = 1e-12
        best_t = -1
        for kk in range(K):
            t_city = candidates[x0, kk]
            t = pos[t_city]
            if t >= s - 1 and t <= s + L - 1:
                continue
            if t >= n - L:
                continue
            u = tour[t]
            v = tour[t + 1]
            d_uv = _euclid(xy, u, v)
            d_ux0 = _euclid(xy, u, x0)
            d_xLv = _euclid(xy, xL, v)
            insert_cost = d_ux0 + d_xLv - d_uv
            gain = gap_save - insert_cost
            if gain > best_gain:
                best_gain = gain
                best_t = t
        if best_t < 0:
            continue
        t = best_t
        # Stash segment cities then shift the gap closed and reinsert.
        seg0 = tour[s]
        seg1 = tour[s + 1] if L >= 2 else 0
        seg2 = tour[s + 2] if L >= 3 else 0
        if t < s - 1:
            # shift tour[t+1..s-1] right by L positions
            for q in range(s + L - 1, t + L, -1):
                cy = tour[q - L]
                tour[q] = cy
                pos[cy] = q
            tour[t + 1] = seg0
            pos[seg0] = t + 1
            if L >= 2:
                tour[t + 2] = seg1
                pos[seg1] = t + 2
            if L >= 3:
                tour[t + 3] = seg2
                pos[seg2] = t + 3
        else:  # t > s + L - 1
            # shift tour[s+L..t] left by L positions
            for q in range(s, t - L + 1):
                cy = tour[q + L]
                tour[q] = cy
                pos[cy] = q
            tour[t - L + 1] = seg0
            pos[seg0] = t - L + 1
            if L >= 2:
                tour[t - L + 2] = seg1
                pos[seg1] = t - L + 2
            if L >= 3:
                tour[t - L + 3] = seg2
                pos[seg2] = t - L + 3
        n_imp += 1
    return n_imp


@njit(cache=True, fastmath=True, inline='always')
def _step_cost(xy, is_prime, k, a, b):
    """Length of step k (1-indexed) going city a → b, with Santa penalty."""
    dx = xy[b, 0] - xy[a, 0]
    dy = xy[b, 1] - xy[a, 1]
    length = (dx * dx + dy * dy) ** 0.5
    if k % 10 == 0 and not is_prime[a]:
        return length * 1.1
    return length


@njit(cache=True, fastmath=True)
def _swap_delta(tour, xy, is_prime, i, j):
    """Cost delta if we swap tour[i] and tour[j], with 0 < i < j < N."""
    if j == i + 1:
        a = tour[i - 1]
        x = tour[i]
        y = tour[j]
        c = tour[j + 1]
        old = (_step_cost(xy, is_prime, i, a, x)
               + _step_cost(xy, is_prime, i + 1, x, y)
               + _step_cost(xy, is_prime, j + 1, y, c))
        new = (_step_cost(xy, is_prime, i, a, y)
               + _step_cost(xy, is_prime, i + 1, y, x)
               + _step_cost(xy, is_prime, j + 1, x, c))
        return new - old
    ai = tour[i - 1]
    bi = tour[i + 1]
    aj = tour[j - 1]
    bj = tour[j + 1]
    x = tour[i]
    y = tour[j]
    old = (_step_cost(xy, is_prime, i, ai, x)
           + _step_cost(xy, is_prime, i + 1, x, bi)
           + _step_cost(xy, is_prime, j, aj, y)
           + _step_cost(xy, is_prime, j + 1, y, bj))
    new = (_step_cost(xy, is_prime, i, ai, y)
           + _step_cost(xy, is_prime, i + 1, y, bi)
           + _step_cost(xy, is_prime, j, aj, x)
           + _step_cost(xy, is_prime, j + 1, x, bj))
    return new - old


@njit(cache=True, fastmath=True)
def prime_swap_pass(tour, pos, xy, is_prime, candidates):
    """For each penalty position k (k%10==0, origin non-prime), try swapping
    the origin city with a prime city from its k-NN. Accept if total cost drops."""
    n = xy.shape[0]
    K = candidates.shape[1]
    n_imp = 0
    for k in range(10, n, 10):
        i = k - 1
        if i < 1 or i > n - 2:
            continue
        b = tour[i]
        if is_prime[b]:
            continue
        for kk in range(K):
            p = candidates[b, kk]
            if p == 0 or not is_prime[p]:
                continue
            j = pos[p]
            if j < 1 or j > n - 2 or j == i:
                continue
            ii = i if i < j else j
            jj = j if i < j else i
            delta = _swap_delta(tour, xy, is_prime, ii, jj)
            if delta < -1e-12:
                tour[i], tour[j] = tour[j], tour[i]
                pos[tour[i]] = i
                pos[tour[j]] = j
                n_imp += 1
                break
    return n_imp


def run_local(tour, pos, xy, candidates, budget, max_outer=20):
    """Alternate 2-opt and Or-{1,2,3} sweeps until all converge or budget exhausted."""
    total_2opt = 0
    total_or = 0
    for outer in range(max_outer):
        if budget.expired():
            break
        s2 = 0
        while not budget.expired():
            n_imp = two_opt_sweep(tour, pos, xy, candidates)
            s2 += 1
            if n_imp == 0:
                break
        total_2opt += s2
        any_or = 0
        for L in (1, 2, 3):
            if budget.expired():
                break
            sL = 0
            while not budget.expired():
                n_imp = or_seg_sweep(tour, pos, xy, candidates, L)
                sL += 1
                if n_imp == 0:
                    break
            total_or += sL
            if sL > 1:
                any_or += 1
        if s2 == 1 and any_or == 0:
            break
    return total_2opt, total_or


def double_bridge(tour, rng):
    """Martin-Otto-Felten double-bridge 4-opt perturbation. Cuts tour into
    4 segments at 3 random points and reconnects A|C|B|D."""
    n = len(tour) - 1  # tour[0] == tour[n] == START_CITY
    cuts = rng.choice(n - 1, size=3, replace=False) + 1
    cuts.sort()
    i, j, k = int(cuts[0]), int(cuts[1]), int(cuts[2])
    return np.concatenate([tour[:i], tour[j:k], tour[i:j], tour[k:]])


# ---------------------------------------------------------------------------
# Solver entry point
# ---------------------------------------------------------------------------

def solve(xy, is_prime, budget):
    print("  building cKDTree + candidate list ...")
    t0 = time.perf_counter()
    candidates = build_candidates(xy, K_NEIGHBORS)
    print(f"  candidates built in {time.perf_counter() - t0:.2f}s")

    print("  building fast NN tour ...")
    t0 = time.perf_counter()
    tour, fallbacks = fast_nn(xy, candidates, START_CITY)
    print(f"  NN done in {time.perf_counter() - t0:.2f}s ({fallbacks} brute fallbacks), remaining {budget.remaining():.1f}s")

    if budget.remaining() < 1:
        return tour

    n = len(xy)
    pos = np.empty(n, dtype=np.int64)
    pos[tour[:-1]] = np.arange(n, dtype=np.int64)

    print("  running 2-opt + Or-{1,2,3} to local optimum ...")
    s2, sor = run_local(tour, pos, xy, candidates, budget)
    print(f"  local converged: {s2} 2-opt sweeps, {sor} or-opt sweeps, remaining {budget.remaining():.1f}s")

    best_tour = tour.copy()
    best_cost = score_tour(best_tour, xy, is_prime)
    print(f"  cost after local search: {best_cost:.2f}")

    if budget.remaining() < 1:
        return best_tour

    print("  running ILS (double-bridge + local-search) ...")
    rng = np.random.default_rng(0xBEEF)
    iters = 0
    accepts = 0
    while not budget.expired():
        cand = double_bridge(best_tour, rng)
        pos[cand[:-1]] = np.arange(n, dtype=np.int64)
        run_local(cand, pos, xy, candidates, budget)
        if budget.expired():
            # don't waste a score call on a possibly-incomplete optimisation
            break
        new_cost = score_tour(cand, xy, is_prime)
        iters += 1
        if new_cost < best_cost:
            best_cost = new_cost
            best_tour = cand.copy()
            accepts += 1
            print(f"    ILS iter {iters}: NEW BEST {best_cost:.2f}, "
                  f"remaining {budget.remaining():.1f}s")
    print(f"  ILS done: {iters} iters, {accepts} improvements")

    print("  running prime-swap post-pass ...")
    pos[best_tour[:-1]] = np.arange(n, dtype=np.int64)
    total_prime_imp = 0
    for sweep in range(20):
        n_imp = prime_swap_pass(best_tour, pos, xy, is_prime, candidates)
        total_prime_imp += n_imp
        if n_imp == 0:
            break
    new_cost = score_tour(best_tour, xy, is_prime)
    print(f"  prime-swap: {total_prime_imp} swaps applied, cost {best_cost:.2f} -> {new_cost:.2f}")
    if new_cost < best_cost:
        best_cost = new_cost
    return best_tour


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
