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

K_NEIGHBORS = 4


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
    """One best-improvement pass. For each city a, scans all candidates and applies
    only the single highest-gain move (across both case A and case B)."""
    n = len(xy)
    K = candidates.shape[1]
    n_improvements = 0
    for ai in range(1, n):
        a = tour[ai]
        a_next = tour[ai + 1]
        d_a_anext = _euclid(xy, a, a_next)
        best_gain = 1e-12
        best_kk = -1
        best_case = 0  # 1 = case A (cj > ai+1), 2 = case B (cj < ai-1)
        for kk in range(K):
            c = candidates[a, kk]
            if c == 0:
                continue
            cj = pos[c]
            if cj > ai + 1 and cj < n:
                c_next = tour[cj + 1]
                d_a_c = _euclid(xy, a, c)
                d_c_cnext = _euclid(xy, c, c_next)
                d_anext_cnext = _euclid(xy, a_next, c_next)
                gain = d_a_anext + d_c_cnext - d_a_c - d_anext_cnext
                if gain > best_gain:
                    best_gain = gain
                    best_kk = kk
                    best_case = 1
            elif cj >= 1 and cj < ai - 1:
                c_next = tour[cj + 1]
                d_a_c = _euclid(xy, a, c)
                d_c_cnext = _euclid(xy, c, c_next)
                d_anext_cnext = _euclid(xy, a_next, c_next)
                gain = d_a_anext + d_c_cnext - d_a_c - d_anext_cnext
                if gain > best_gain:
                    best_gain = gain
                    best_kk = kk
                    best_case = 2
        if best_kk < 0:
            continue
        c = candidates[a, best_kk]
        cj = pos[c]
        if best_case == 1:
            lo = ai + 1
            hi = cj
        else:
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
    return n_improvements


def build_candidates(xy, k):
    tree = cKDTree(xy)
    _, idx = tree.query(xy, k=k + 1)
    return idx[:, 1:].astype(np.int32)


@njit(cache=True, fastmath=True)
def or_seg_sweep(tour, pos, xy, candidates, L):
    """Or-opt for arbitrary segment length L. For L>=2, evaluates BOTH forward
    and reversed re-insertion at each candidate target and picks the best."""
    n = len(xy)
    K = candidates.shape[1]
    n_imp = 0
    seg = np.empty(L, dtype=tour.dtype)
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
        best_rev = False
        n_src = 2 if L >= 2 else 1
        for src_idx in range(n_src):
            src = x0 if src_idx == 0 else xL
            for kk in range(K):
                t_city = candidates[src, kk]
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
                gain_fwd = gap_save - (d_ux0 + d_xLv - d_uv)
                if gain_fwd > best_gain:
                    best_gain = gain_fwd
                    best_t = t
                    best_rev = False
                if L >= 2:
                    d_uxL = _euclid(xy, u, xL)
                    d_x0v = _euclid(xy, x0, v)
                    gain_rev = gap_save - (d_uxL + d_x0v - d_uv)
                    if gain_rev > best_gain:
                        best_gain = gain_rev
                        best_t = t
                        best_rev = True
        if best_t < 0:
            continue
        t = best_t
        # Stash segment (in target placement order — reversed if best_rev).
        if best_rev:
            for q in range(L):
                seg[q] = tour[s + L - 1 - q]
        else:
            for q in range(L):
                seg[q] = tour[s + q]
        if t < s - 1:
            for q in range(s + L - 1, t + L, -1):
                cy = tour[q - L]
                tour[q] = cy
                pos[cy] = q
            for q in range(L):
                tour[t + 1 + q] = seg[q]
                pos[seg[q]] = t + 1 + q
        else:
            for q in range(s, t - L + 1):
                cy = tour[q + L]
                tour[q] = cy
                pos[cy] = q
            for q in range(L):
                tour[t - L + 1 + q] = seg[q]
                pos[seg[q]] = t - L + 1 + q
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
        for L in (1, 2, 3, 4, 5):
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


@njit(cache=True, fastmath=True)
def _lns_relink_regret(tour, xy, candidates, removed_set, removed_order):
    """Regret-2 LNS repair: insert cities with largest (second_best - best)
    insertion-cost gap first, so high-preference cities claim their slot
    before others can block it."""
    n = candidates.shape[0]
    K = candidates.shape[1]
    nxt = np.empty(n, dtype=np.int64)
    prv = np.empty(n, dtype=np.int64)
    in_tour = np.empty(n, dtype=np.bool_)
    for i in range(n):
        a = tour[i]
        b = tour[i + 1]
        nxt[a] = b
        prv[b] = a
    for c in range(n):
        in_tour[c] = not removed_set[c]
    for c in range(n):
        if removed_set[c]:
            p = prv[c]
            x = nxt[c]
            nxt[p] = x
            prv[x] = p
    R = removed_order.shape[0]
    start = tour[0]
    regrets = np.empty(R, dtype=np.float64)
    for idx in range(R):
        c = removed_order[idx]
        best_cost = 1e30
        second_best = 1e30
        for kk in range(K):
            u = candidates[c, kk]
            if not in_tour[u]:
                continue
            v = nxt[u]
            d_uc = _euclid(xy, u, c)
            d_cv = _euclid(xy, c, v)
            d_uv = _euclid(xy, u, v)
            cost = d_uc + d_cv - d_uv
            if cost < best_cost:
                second_best = best_cost
                best_cost = cost
            elif cost < second_best:
                second_best = cost
        regrets[idx] = second_best - best_cost
    sort_order = np.argsort(regrets)
    for ii in range(R - 1, -1, -1):
        idx = sort_order[ii]
        c = removed_order[idx]
        best_cost = 1e30
        best_u = -1
        for kk in range(K):
            u = candidates[c, kk]
            if not in_tour[u]:
                continue
            v = nxt[u]
            d_uc = _euclid(xy, u, c)
            d_cv = _euclid(xy, c, v)
            d_uv = _euclid(xy, u, v)
            cost = d_uc + d_cv - d_uv
            if cost < best_cost:
                best_cost = cost
                best_u = u
        if best_u < 0:
            best_u = start
        u = best_u
        v = nxt[u]
        nxt[u] = c
        prv[c] = u
        nxt[c] = v
        prv[v] = c
        in_tour[c] = True
    out = np.empty(n + 1, dtype=tour.dtype)
    out[0] = start
    out[n] = start
    cur = start
    for i in range(1, n):
        cur = nxt[cur]
        out[i] = cur
    return out


@njit(cache=True, fastmath=True)
def _lns_relink(tour, xy, candidates, removed_set, removed_order):
    """Destroy-repair perturbation. Excises cities flagged in removed_set from
    the tour cycle, then reinserts each city in removed_order at its cheapest
    candidate-list position via doubly-linked-list splicing. Returns a new
    (n+1,) tour with the same cycle closure (tour[0] == tour[-1])."""
    n = candidates.shape[0]
    K = candidates.shape[1]
    nxt = np.empty(n, dtype=np.int64)
    prv = np.empty(n, dtype=np.int64)
    in_tour = np.empty(n, dtype=np.bool_)
    for i in range(n):
        a = tour[i]
        b = tour[i + 1]
        nxt[a] = b
        prv[b] = a
    for c in range(n):
        in_tour[c] = not removed_set[c]
    for c in range(n):
        if removed_set[c]:
            p = prv[c]
            x = nxt[c]
            nxt[p] = x
            prv[x] = p
    R = removed_order.shape[0]
    start = tour[0]
    for idx in range(R):
        c = removed_order[idx]
        best_cost = 1e30
        best_u = -1
        for kk in range(K):
            u = candidates[c, kk]
            if not in_tour[u]:
                continue
            v = nxt[u]
            d_uc = _euclid(xy, u, c)
            d_cv = _euclid(xy, c, v)
            d_uv = _euclid(xy, u, v)
            cost = d_uc + d_cv - d_uv
            if cost < best_cost:
                best_cost = cost
                best_u = u
        if best_u < 0:
            best_u = start
        u = best_u
        v = nxt[u]
        nxt[u] = c
        prv[c] = u
        nxt[c] = v
        prv[v] = c
        in_tour[c] = True
    out = np.empty(n + 1, dtype=tour.dtype)
    out[0] = start
    out[n] = start
    cur = start
    for i in range(1, n):
        cur = nxt[cur]
        out[i] = cur
    return out


def lns_perturb(tour, rng, xy, candidates, frac=0.015):
    """Destroy-and-repair LNS perturbation. Removes a random ~frac of cities
    (excluding START_CITY) and reinserts them in random order via cheapest
    insertion against the candidate list."""
    n = candidates.shape[0]
    n_remove = max(2, int(n * frac))
    start_city = int(tour[0])
    mask = np.ones(n, dtype=np.bool_)
    mask[start_city] = False
    pool = np.flatnonzero(mask)
    rem = rng.choice(pool, size=n_remove, replace=False).astype(np.int64)
    removed_set = np.zeros(n, dtype=np.bool_)
    removed_set[rem] = True
    rng.shuffle(rem)
    return _lns_relink(tour, xy, candidates, removed_set, rem)


def lns_perturb_prime(tour, rng, xy, candidates, is_prime, frac=0.010, bias=4.0):
    """LNS variant that biases the destroy-set toward penalty-origin cities
    (non-prime cities currently sitting at tour position k-1 where k%10==0).
    Couples the destroy operator with the Santa metric structure."""
    n = candidates.shape[0]
    n_remove = max(2, int(n * frac))
    start_city = int(tour[0])
    weights = np.ones(n, dtype=np.float64)
    for k in range(10, n + 1, 10):
        origin = tour[k - 1]
        if not is_prime[origin]:
            weights[origin] = bias
    weights[start_city] = 0.0
    weights /= weights.sum()
    rem = rng.choice(n, size=n_remove, replace=False, p=weights).astype(np.int64)
    removed_set = np.zeros(n, dtype=np.bool_)
    removed_set[rem] = True
    rng.shuffle(rem)
    return _lns_relink_regret(tour, xy, candidates, removed_set, rem)


def double_bridge(tour, rng):
    """Martin-Otto-Felten double-bridge 4-opt perturbation. Cuts tour into
    4 segments at 3 random points and reconnects A|C|B|D."""
    n = len(tour) - 1  # tour[0] == tour[n] == START_CITY
    cuts = rng.choice(n - 1, size=3, replace=False) + 1
    cuts.sort()
    i, j, k = int(cuts[0]), int(cuts[1]), int(cuts[2])
    return np.concatenate([tour[:i], tour[j:k], tour[i:j], tour[k:]])


def segment_shift(tour, rng):
    """Cut a random window of ~2-5% of N from the tour and re-insert it at
    another random position. Alternative perturbation operator."""
    n = len(tour) - 1
    w_min = max(2, n // 50)
    w_max = max(w_min + 1, n // 20)
    w = int(rng.integers(w_min, w_max))
    s = int(rng.integers(1, n - w))
    seg = tour[s:s + w]
    rest = np.concatenate([tour[:s], tour[s + w:]])
    # rest length = (n + 1) - w. Insert after position [1, len(rest)-2].
    insert_pos = int(rng.integers(1, len(rest) - 1))
    return np.concatenate([rest[:insert_pos], seg, rest[insert_pos:]])


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

    print("  running ILS (perturb + local-search, random NN restart on stuck) ...")
    rng = np.random.default_rng(0xBEEF)
    iters = 0
    accepts = 0
    restarts = 0
    no_improve = 0
    RESTART_AFTER = 40
    while not budget.expired():
        if no_improve >= RESTART_AFTER:
            seed = int(rng.integers(1, n))
            cand, _ = fast_nn(xy, candidates, seed)
            idx = int(np.where(cand == START_CITY)[0][0])
            cand = np.concatenate([cand[idx:-1], cand[:idx + 1]])
            cand = lns_perturb_prime(cand, rng, xy, candidates, is_prime, frac=0.010, bias=8.0)
            no_improve = 0
            restarts += 1
            print(f"    [iter {iters}] RANDOM RESTART from city {seed} (LNS-prime smoothed)")
        else:
            cand = best_tour
            r = rng.random()
            if r < 1.0 / 3.0:
                cand = double_bridge(cand, rng)
            elif r < 2.0 / 3.0:
                cand = segment_shift(cand, rng)
            else:
                cand = lns_perturb_prime(cand, rng, xy, candidates, is_prime, frac=0.010, bias=8.0)
        pos[cand[:-1]] = np.arange(n, dtype=np.int64)
        run_local(cand, pos, xy, candidates, budget)
        if budget.expired():
            break
        new_cost = score_tour(cand, xy, is_prime)
        iters += 1
        if new_cost < best_cost:
            best_cost = new_cost
            best_tour = cand.copy()
            accepts += 1
            no_improve = 0
            print(f"    ILS iter {iters}: NEW BEST {best_cost:.2f}, "
                  f"remaining {budget.remaining():.1f}s")
        else:
            no_improve += 1
    print(f"  ILS done: {iters} iters, {accepts} improvements, {restarts} restarts")

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
