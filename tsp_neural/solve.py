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

import math
import os
import subprocess
import time
import multiprocessing as mp
from pathlib import Path

import numpy as np
import torch
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

K_NEIGHBORS = 10            # baseline 2-opt and NN seed
K_NEIGHBORS_HARVEST = 30    # harvest mode logs the wider pool to cover ranker OOD region
HARVEST = os.environ.get("HARVEST", "0") == "1"
MODE = os.environ.get("MODE", "solve")
RANK = os.environ.get("RANK", "auto")  # "auto" => use ckpt if found; "0" force baseline; "1" require ckpt
CHECKPOINTS_DIR = Path(__file__).parent / "checkpoints"

# Parallel ILS knobs (env-overridable so agents can revert or sweep).
# ILS_WORKERS=1 → sequential ILS (legacy path).
# ILS_WORKERS>1 → batched parallel ILS via multiprocessing fork pool.
ILS_WORKERS = int(os.environ.get("ILS_WORKERS", 8))
ILS_WORKER_BUDGET = float(os.environ.get("ILS_WORKER_BUDGET", 25.0))

# Master rng seed for the ILS loops. Used by the parallel/sequential
# entry points; per-worker seeds are derived from this master.
# Hex or decimal accepted (int(s, 0) parses 0xCAFE, 51966, etc).
# multi-seed-eval skill sweeps this via ILS_SEED=1 / =2 / =3 etc.
ILS_SEED = int(os.environ.get("ILS_SEED", "0"), 0)

# Module-level globals set by parallel_ils_loop before Pool fork — workers
# inherit via COW. Avoids per-call IPC of xy / candidates / weights (which
# would otherwise serialise ~10 MB per task).
_W_XY = None
_W_IS_PRIME = None
_W_IS_PRIME_F32 = None
_W_CANDIDATES = None
_W_RANKED_WEIGHTS = None


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
def or_opt_sweep(tour, pos, xy, candidates):
    """Or-opt single-city relocation sweep. For each city x, try inserting it
    before each of its k-NN candidates; accept first improvement.

    Edges removed: (prev,x), (x,next), (c_prev,c)
    Edges added:   (prev,next), (c_prev,x), (x,c)
    Gain = sum(removed) - sum(added).

    Returns number of accepted moves."""
    n = len(xy)
    K = candidates.shape[1]
    n_imp = 0
    for xi in range(1, n):
        x = tour[xi]
        prev = tour[xi - 1]
        nxt = tour[xi + 1]
        d_prev_x = _euclid(xy, prev, x)
        d_x_next = _euclid(xy, x, nxt)
        d_prev_next = _euclid(xy, prev, nxt)
        rem_gain = d_prev_x + d_x_next - d_prev_next
        if rem_gain <= 1e-12:
            continue
        for kk in range(K):
            c = candidates[x, kk]
            if c == 0 or c == prev or c == nxt:
                continue
            cj = pos[c]
            if cj == 0 or cj == xi:
                continue
            c_prev = tour[cj - 1]
            if c_prev == x:
                continue
            d_cprev_c = _euclid(xy, c_prev, c)
            d_cprev_x = _euclid(xy, c_prev, x)
            d_x_c = _euclid(xy, x, c)
            ins_gain = d_cprev_c - d_cprev_x - d_x_c
            total = rem_gain + ins_gain
            if total > 1e-12:
                if xi < cj:
                    for i in range(xi, cj - 1):
                        tour[i] = tour[i + 1]
                        pos[tour[i]] = i
                    tour[cj - 1] = x
                    pos[x] = cj - 1
                else:
                    for i in range(xi, cj, -1):
                        tour[i] = tour[i - 1]
                        pos[tour[i]] = i
                    tour[cj] = x
                    pos[x] = cj
                n_imp += 1
                break
    return n_imp


def run_or_opt(tour, pos, xy, candidates, budget, max_sweeps=10_000):
    sweeps = 0
    while sweeps < max_sweeps and not budget.expired():
        n_imp = or_opt_sweep(tour, pos, xy, candidates)
        sweeps += 1
        if n_imp == 0:
            break
    return sweeps


@njit(cache=True, fastmath=True)
def or_opt_2_sweep(tour, pos, xy, candidates):
    """Or-opt 2-city segment relocation sweep. For each adjacent pair
    (x1, x2) at positions (xi, xi+1), try inserting the segment forward
    before each of x1's k-NN candidates; accept first improvement.

    Edges removed: (prev,x1), (x2,next), (c_prev,c)  — 3 edges
    Edges added:   (prev,next), (c_prev,x1), (x2,c)  — 3 edges
    Gain = sum(removed) - sum(added) (Euclidean only).

    Forward orientation only — reverse insertion is a separate move type
    (Or-opt-2-rev), deferred. Returns number of accepted moves."""
    n = len(xy)
    K = candidates.shape[1]
    n_imp = 0
    for xi in range(1, n - 1):  # need both xi and xi+1 valid
        x1 = tour[xi]
        x2 = tour[xi + 1]
        prev = tour[xi - 1]
        nxt = tour[xi + 2]
        d_prev_x1 = _euclid(xy, prev, x1)
        d_x2_next = _euclid(xy, x2, nxt)
        d_prev_next = _euclid(xy, prev, nxt)
        rem_gain = d_prev_x1 + d_x2_next - d_prev_next
        if rem_gain <= 1e-12:
            continue
        for kk in range(K):
            c = candidates[x1, kk]
            if c == 0 or c == prev or c == nxt or c == x2:
                continue
            cj = pos[c]
            # Insertion point cj must be outside the segment + neighbors.
            if cj == 0 or cj == xi or cj == xi + 1 or cj == xi + 2:
                continue
            c_prev = tour[cj - 1]
            if c_prev == x1 or c_prev == x2:
                continue
            d_cprev_c = _euclid(xy, c_prev, c)
            d_cprev_x1 = _euclid(xy, c_prev, x1)
            d_x2_c = _euclid(xy, x2, c)
            ins_gain = d_cprev_c - d_cprev_x1 - d_x2_c
            total = rem_gain + ins_gain
            if total > 1e-12:
                if xi < cj:
                    # Shift left by 2: tour[xi..cj-3] = tour[xi+2..cj-1]
                    for i in range(xi, cj - 2):
                        tour[i] = tour[i + 2]
                        pos[tour[i]] = i
                    tour[cj - 2] = x1
                    tour[cj - 1] = x2
                    pos[x1] = cj - 2
                    pos[x2] = cj - 1
                else:  # cj < xi (must be cj < xi here; xi == cj excluded above)
                    # Shift right by 2: tour[cj+2..xi+1] = tour[cj..xi-1]
                    for i in range(xi - 1, cj - 1, -1):
                        tour[i + 2] = tour[i]
                        pos[tour[i + 2]] = i + 2
                    tour[cj] = x1
                    tour[cj + 1] = x2
                    pos[x1] = cj
                    pos[x2] = cj + 1
                n_imp += 1
                break
    return n_imp


def run_or_opt_2(tour, pos, xy, candidates, budget, max_sweeps=10_000):
    sweeps = 0
    while sweeps < max_sweeps and not budget.expired():
        n_imp = or_opt_2_sweep(tour, pos, xy, candidates)
        sweeps += 1
        if n_imp == 0:
            break
    return sweeps


@njit(cache=True, fastmath=True)
def two_opt_sweep_harvest(tour, pos, xy, is_prime_f32, candidates,
                          buf_a, buf_a_next, buf_c, buf_c_next,
                          buf_pos_delta, buf_gain, buf_accepted, count_arr):
    """Same as two_opt_sweep but uses PRIME-AWARE boundary gain for both the
    accept decision and the logged label, so the harvested (features, gain,
    accepted) align with what `score_tour` actually rewards."""
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
                d_c_cnext = _euclid(xy, c, c_next)
                d_a_c = _euclid(xy, a, c)
                d_anext_cnext = _euclid(xy, a_next, c_next)
                if (ai + 1) % 10 == 0 or (cj + 1) % 10 == 0:
                    pf_ai = _prime_factor(ai + 1, is_prime_f32[a])
                    pf_cj_old = _prime_factor(cj + 1, is_prime_f32[c])
                    pf_cj_new = _prime_factor(cj + 1, is_prime_f32[a_next])
                    gain = pf_ai * d_a_anext + pf_cj_old * d_c_cnext \
                           - pf_ai * d_a_c - pf_cj_new * d_anext_cnext
                else:
                    gain = d_a_anext + d_c_cnext - d_a_c - d_anext_cnext
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
                d_c_cnext = _euclid(xy, c, c_next)
                d_a_c = _euclid(xy, a, c)
                d_anext_cnext = _euclid(xy, a_next, c_next)
                if (ai + 1) % 10 == 0 or (cj + 1) % 10 == 0:
                    pf_cj = _prime_factor(cj + 1, is_prime_f32[c])
                    pf_ai_old = _prime_factor(ai + 1, is_prime_f32[a])
                    pf_ai_new = _prime_factor(ai + 1, is_prime_f32[c_next])
                    gain = pf_ai_old * d_a_anext + pf_cj * d_c_cnext \
                           - pf_cj * d_a_c - pf_ai_new * d_anext_cnext
                else:
                    gain = d_a_anext + d_c_cnext - d_a_c - d_anext_cnext
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


@njit(cache=True, fastmath=True, inline='always')
def _mlp_score(x, W1, b1, W2, b2, w3, b3_scalar, h1, h2):
    """Forward pass of a 9 -> H -> H -> 1 MLP with ReLU. Returns scalar."""
    H = W1.shape[0]
    nin = W1.shape[1]
    for j in range(H):
        s = b1[j]
        for i in range(nin):
            s += W1[j, i] * x[i]
        h1[j] = s if s > 0.0 else 0.0
    for j in range(H):
        s = b2[j]
        for i in range(H):
            s += W2[j, i] * h1[i]
        h2[j] = s if s > 0.0 else 0.0
    s = b3_scalar
    for i in range(H):
        s += w3[i] * h2[i]
    return s


@njit(cache=True, fastmath=True, inline='always')
def _prime_factor(p_one_indexed, origin_is_prime):
    """1.1 if step k=p_one_indexed is a 10th step AND origin city is non-prime,
    else 1.0. Mirrors prepare.score_tour's penalty rule exactly at boundary
    edges of a 2-opt swap."""
    if (p_one_indexed % 10) == 0 and origin_is_prime < 0.5:
        return 1.1
    return 1.0


@njit(cache=True, fastmath=True)
def two_opt_sweep_ranked(tour, pos, xy, is_prime_f32, candidates,
                         W1, b1, W2, b2, w3, b3_scalar, mu, sd):
    """2-opt sweep where candidates per ai are visited in descending MLP score
    order; first improving swap is taken (one accept per ai). Cycle-3 was
    'try single best then give up'; this is the I5 variant — iterate by score
    until improving or pool exhausted.

    Z1 (cycle 22): the accept-test uses *prime-aware* gain at the swap's two
    boundary edges (positions ai and cj). Interior 10th-step penalties from
    the reversed segment are not yet accounted for."""
    n = len(xy)
    K = candidates.shape[1]
    H = W1.shape[0]
    nin = W1.shape[1]

    feats = np.empty(nin, dtype=np.float32)
    h1 = np.empty(H, dtype=np.float32)
    h2 = np.empty(H, dtype=np.float32)
    scores = np.empty(K, dtype=np.float32)
    valid = np.empty(K, dtype=np.bool_)
    used = np.empty(K, dtype=np.bool_)

    NEG_INF = np.float32(-1e30)
    n_imp = 0
    n_inf = 0
    for ai in range(1, n):
        a = tour[ai]
        a_next = tour[ai + 1]
        d_a_anext = _euclid(xy, a, a_next)

        # Score all K candidates with current tour state.
        for kk in range(K):
            c = candidates[a, kk]
            if c == 0:
                valid[kk] = False
                scores[kk] = NEG_INF
                continue
            cj = pos[c]
            forward = (cj > ai + 1 and cj < n)
            backward = (cj >= 1 and cj < ai - 1)
            if not (forward or backward):
                valid[kk] = False
                scores[kk] = NEG_INF
                continue
            c_next = tour[cj + 1]
            d_c_cnext = _euclid(xy, c, c_next)
            d_a_c = _euclid(xy, a, c)
            d_anext_cnext = _euclid(xy, a_next, c_next)
            feats[0] = (d_a_anext - mu[0]) / sd[0]
            feats[1] = (d_c_cnext - mu[1]) / sd[1]
            feats[2] = (d_a_c - mu[2]) / sd[2]
            feats[3] = (d_anext_cnext - mu[3]) / sd[3]
            feats[4] = (is_prime_f32[a] - mu[4]) / sd[4]
            feats[5] = (is_prime_f32[a_next] - mu[5]) / sd[5]
            feats[6] = (is_prime_f32[c] - mu[6]) / sd[6]
            feats[7] = (is_prime_f32[c_next] - mu[7]) / sd[7]
            pd = cj - ai
            if pd < 0:
                pd = -pd
            feats[8] = (math.log1p(pd) - mu[8]) / sd[8]
            scores[kk] = _mlp_score(feats, W1, b1, W2, b2, w3, b3_scalar, h1, h2)
            valid[kk] = True
            n_inf += 1

        for kk in range(K):
            used[kk] = False

        accepted = False
        for slot in range(K):
            if accepted:
                break
            best_kk = -1
            best_score = NEG_INF
            for kk in range(K):
                if not used[kk] and valid[kk] and scores[kk] > best_score:
                    best_kk = kk
                    best_score = scores[kk]
            if best_kk < 0 or best_score < 0.0:
                break
            used[best_kk] = True

            c = candidates[a, best_kk]
            cj = pos[c]
            if cj > ai + 1 and cj < n:
                c_next = tour[cj + 1]
                d_c_cnext = _euclid(xy, c, c_next)
                d_a_c = _euclid(xy, a, c)
                d_anext_cnext = _euclid(xy, a_next, c_next)
                pf_ai = _prime_factor(ai + 1, is_prime_f32[a])
                pf_cj_old = _prime_factor(cj + 1, is_prime_f32[c])
                pf_cj_new = _prime_factor(cj + 1, is_prime_f32[a_next])
                gain = pf_ai * d_a_anext + pf_cj_old * d_c_cnext \
                       - pf_ai * d_a_c - pf_cj_new * d_anext_cnext
                if gain > 1e-12:
                    lo, hi = ai + 1, cj
                    while lo < hi:
                        x, y = tour[lo], tour[hi]
                        tour[lo], tour[hi] = y, x
                        pos[y], pos[x] = lo, hi
                        lo += 1
                        hi -= 1
                    n_imp += 1
                    accepted = True
            elif cj >= 1 and cj < ai - 1:
                c_next = tour[cj + 1]
                d_c_cnext = _euclid(xy, c, c_next)
                d_a_c = _euclid(xy, a, c)
                d_anext_cnext = _euclid(xy, a_next, c_next)
                pf_cj = _prime_factor(cj + 1, is_prime_f32[c])
                pf_ai_old = _prime_factor(ai + 1, is_prime_f32[a])
                pf_ai_new = _prime_factor(ai + 1, is_prime_f32[c_next])
                gain = pf_ai_old * d_a_anext + pf_cj * d_c_cnext \
                       - pf_cj * d_a_c - pf_ai_new * d_anext_cnext
                if gain > 1e-12:
                    lo, hi = cj + 1, ai
                    while lo < hi:
                        x, y = tour[lo], tour[hi]
                        tour[lo], tour[hi] = y, x
                        pos[y], pos[x] = lo, hi
                        lo += 1
                        hi -= 1
                    n_imp += 1
                    accepted = True
    return n_imp, n_inf


def run_2opt_ranked(tour, pos, xy, is_prime_f32, candidates,
                    weights, budget, max_sweeps=10_000):
    W1, b1, W2, b2, w3, b3_scalar, mu, sd = weights
    sweeps = 0
    total_inf = 0
    while sweeps < max_sweeps and not budget.expired():
        n_imp, n_inf = two_opt_sweep_ranked(
            tour, pos, xy, is_prime_f32, candidates,
            W1, b1, W2, b2, w3, b3_scalar, mu, sd,
        )
        sweeps += 1
        total_inf += n_inf
        if n_imp == 0:
            break
    return sweeps, total_inf


def load_latest_checkpoint():
    paths = sorted(CHECKPOINTS_DIR.glob("*.pt"), key=lambda p: p.stat().st_mtime)
    if not paths:
        return None, None
    ckpt_path = paths[-1]
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    sd = ckpt["state_dict"]
    W1 = sd["net.0.weight"].numpy().astype(np.float32)
    b1 = sd["net.0.bias"].numpy().astype(np.float32)
    W2 = sd["net.2.weight"].numpy().astype(np.float32)
    b2 = sd["net.2.bias"].numpy().astype(np.float32)
    W3 = sd["net.4.weight"].numpy().astype(np.float32)
    b3 = sd["net.4.bias"].numpy().astype(np.float32)
    w3 = W3[0]
    b3_scalar = float(b3[0])
    mu = np.asarray(ckpt["mu"], dtype=np.float32)
    sd_ = np.asarray(ckpt["sd"], dtype=np.float32)
    return ckpt_path, (W1, b1, W2, b2, w3, b3_scalar, mu, sd_)


def run_2opt_harvest(tour, pos, xy, is_prime_f32, candidates, budget, bufs, max_sweeps=10_000):
    sweeps = 0
    while sweeps < max_sweeps and not budget.expired():
        n_imp = two_opt_sweep_harvest(
            tour, pos, xy, is_prime_f32, candidates,
            bufs["a"], bufs["a_next"], bufs["c"], bufs["c_next"],
            bufs["pos_delta"], bufs["gain"], bufs["accepted"], bufs["count"],
        )
        sweeps += 1
        if n_imp == 0:
            break
    return sweeps


# ---------------------------------------------------------------------------
# Module-level VND used by both the initial converge and the parallel ILS
# worker. Hoisted out of solve()'s inner closure so multiprocessing workers
# can call it.
# ---------------------------------------------------------------------------

def _vnd_local(t, p, xy, is_prime_f32, candidates, ranked_weights, budget,
               max_outer=10):
    """Variable neighborhood descent: rotate learned 2-opt → classical Or-opt-1
    → classical Or-opt-2 until all three find no improvement (or max_outer
    outer rounds — caps the initial converge so ILS restarts fit).

    C18: Or-opt-2 added as a third inner move type. Cycle 19 sequential
    Or-opt-2 alone regressed because it ate budget without ILS restarts; in
    the PILS regime each worker has a focused 25s VND from a perturbed seed,
    so Or-opt-2 finds 2-city segment moves Or-opt-1 misses without starving
    the broader restart loop.

    Returns (total_2opt_sweeps, total_or_sweeps, total_inference_calls).
    `total_or_sweeps` = sum of Or-opt-1 + Or-opt-2 sweeps for backward compat.
    """
    total_2opt_sweeps = 0
    total_or_sweeps = 0
    total_inf = 0
    outer = 0
    while not budget.expired() and outer < max_outer:
        outer += 1
        s2, ninf = run_2opt_ranked(
            t, p, xy, is_prime_f32, candidates, ranked_weights, budget
        )
        total_2opt_sweeps += s2
        total_inf += ninf
        if budget.expired():
            break
        so1 = run_or_opt(t, p, xy, candidates, budget)
        total_or_sweeps += so1
        if budget.expired():
            break
        so2 = run_or_opt_2(t, p, xy, candidates, budget)
        total_or_sweeps += so2
        if so1 <= 1 and so2 <= 1 and outer > 1:
            break  # 2-opt also converged on prev iter; all three done
    return total_2opt_sweeps, total_or_sweeps, total_inf


# ---------------------------------------------------------------------------
# Parallel ILS — multiprocessing fork pool dispatching K perturb-and-improve
# workers per batch. Each worker takes the current best tour, applies one
# 2x double-bridge perturbation (cycle-15 sweet spot), runs VND to a fixed
# per-worker time cap, scores, returns. Parent picks the batch's best and
# updates the shared best if it improves.
#
# Avoids the E1 (cycle 32) staleness pitfall: each worker does a fully
# sequential VND on its own tour state — no precomputed scores to invalidate.
# Parallelism is across independent tours, not within a single sweep.
# ---------------------------------------------------------------------------

def _ils_worker_neural(args):
    """Top-level (must be picklable) worker for multiprocessing.Pool. Runs one
    ILS iteration: perturb_count× double-bridge + VND local search up to
    worker_budget_sec, score, return (val_cost, tour, inference_calls). Reads
    xy / candidates / weights from module globals set by the parent (inherited
    via fork COW)."""
    seed_tour, rng_seed, worker_budget_sec, perturb_count = args
    rng = np.random.default_rng(rng_seed)

    new_tour = seed_tour
    for _ in range(perturb_count):
        new_tour = double_bridge(new_tour, rng)

    n = _W_XY.shape[0]
    pos = np.empty(n, dtype=np.int64)
    pos[new_tour[:-1]] = np.arange(n, dtype=np.int64)

    local_budget = TimeBudget(worker_budget_sec)
    _, _, ninf = _vnd_local(
        new_tour, pos, _W_XY, _W_IS_PRIME_F32, _W_CANDIDATES,
        _W_RANKED_WEIGHTS, local_budget,
    )
    val = score_tour(new_tour, _W_XY, _W_IS_PRIME)
    return val, new_tour, ninf


def parallel_ils_loop(best_tour, best_cost, xy, is_prime, candidates,
                      ranked_weights, budget, workers, worker_budget_sec,
                      initial_converge=False, initial_perturb=1,
                      initial_budget_sec=30.0):
    """Batched parallel ILS for the neural loop. Allocates a fork pool ONCE,
    dispatches `workers` perturb+VND jobs per batch, blocks for the slowest,
    accepts the batch's best if it improves the shared best, repeats until
    `budget.remaining() < worker_budget`.

    If `initial_converge=True` (C19): the first batch dispatches workers from
    `best_tour` (a NN seed) with `initial_perturb`× DB and `initial_budget_sec`
    VND budget. Best of `workers` becomes the initial best; the standard PILS
    loop runs from there. Saves the ~30s sequential converge bottleneck and
    gains 8-way starting-point diversity. `best_cost` is ignored in this mode.

    Returns (best_tour, best_cost, total_inference_calls, batches, accepts).
    """
    global _W_XY, _W_IS_PRIME, _W_IS_PRIME_F32, _W_CANDIDATES, _W_RANKED_WEIGHTS
    _W_XY = xy
    _W_IS_PRIME = is_prime
    _W_IS_PRIME_F32 = is_prime.astype(np.float32)
    _W_CANDIDATES = candidates
    _W_RANKED_WEIGHTS = ranked_weights

    print(f"  running PARALLEL ILS "
          f"(workers={workers}, worker_budget={worker_budget_sec:.0f}s, "
          f"initial_converge={initial_converge}) ...")

    rng = np.random.default_rng(ILS_SEED)
    ctx = mp.get_context("fork")

    batch_num = 0
    total_iters = 0
    total_inf = 0
    accepts = 0

    with ctx.Pool(processes=workers) as pool:
        if initial_converge:
            args_list = [
                (best_tour, int(rng.integers(0, 2**31 - 1)),
                 initial_budget_sec, initial_perturb)
                for _ in range(workers)
            ]
            results = pool.map(_ils_worker_neural, args_list)
            batch_num += 1
            total_iters += len(results)
            for _, _, ninf in results:
                total_inf += ninf
            cand_cost, cand_tour, _ = min(results, key=lambda r: r[0])
            best_cost = cand_cost
            best_tour = cand_tour
            accepts += 1
            print(f"    init batch (best of {workers}, "
                  f"{initial_perturb}xDB, {initial_budget_sec:.0f}s): "
                  f"best_cost={best_cost:.2f}, "
                  f"remaining {budget.remaining():.1f}s")

        while not budget.expired():
            if budget.remaining() < worker_budget_sec + 2.0:
                break

            args_list = [
                (best_tour, int(rng.integers(0, 2**31 - 1)),
                 worker_budget_sec, 2)
                for _ in range(workers)
            ]
            results = pool.map(_ils_worker_neural, args_list)
            batch_num += 1
            total_iters += len(results)
            for _, _, ninf in results:
                total_inf += ninf

            cand_cost, cand_tour, _ = min(results, key=lambda r: r[0])
            if cand_cost < best_cost:
                best_cost = cand_cost
                best_tour = cand_tour
                accepts += 1
                print(f"    batch {batch_num} (best of {workers}): "
                      f"NEW BEST {best_cost:.2f}, "
                      f"remaining {budget.remaining():.1f}s")

    print(f"  ILS done: {batch_num} batches × {workers} workers = "
          f"{total_iters} iters, {accepts} accepted batches")
    return best_tour, best_cost, total_inf, batch_num, accepts


# ---------------------------------------------------------------------------
# Solver entry point
# ---------------------------------------------------------------------------

def double_bridge(tour, rng):
    """Random 4-opt double-bridge perturbation: split into 4 segments at 3 cuts,
    rebuild as S0+S2+S1+S3. Cannot be undone by a single 2-opt move."""
    n_inner = len(tour) - 1
    cuts = np.sort(rng.choice(np.arange(1, n_inner), size=3, replace=False))
    p1, p2, p3 = int(cuts[0]), int(cuts[1]), int(cuts[2])
    return np.concatenate([
        tour[:p1 + 1],
        tour[p2 + 1:p3 + 1],
        tour[p1 + 1:p2 + 1],
        tour[p3 + 1:],
    ])


def solve(xy, is_prime, budget, harvest_bufs=None, ranked_weights=None):
    print("  building candidate list (cKDTree) ...")
    tree = cKDTree(xy)
    k_query = max(K_NEIGHBORS, K_NEIGHBORS_HARVEST) + 1
    _, idx = tree.query(xy, k=k_query)
    candidates_full = idx[:, 1:].astype(np.int32)
    candidates = candidates_full[:, :K_NEIGHBORS]

    print("  building NN tour ...")
    tour = nearest_neighbor(xy, candidates, budget)
    print(f"  NN done, remaining {budget.remaining():.1f}s")

    if budget.remaining() < 1:
        return tour, 0

    n = len(xy)
    pos = np.empty(n, dtype=np.int64)
    pos[tour[:-1]] = np.arange(n, dtype=np.int64)

    inference_calls = 0
    restarts = 0
    if harvest_bufs is not None:
        candidates_h = candidates_full[:, :K_NEIGHBORS_HARVEST]
        is_prime_f32 = is_prime.astype(np.float32)
        print(f"  running 2-opt (HARVEST=1, K={K_NEIGHBORS_HARVEST}, prime-aware labels) ...")
        sweeps = run_2opt_harvest(tour, pos, xy, is_prime_f32, candidates_h, budget, harvest_bufs)
        print(f"  2-opt converged in {sweeps} sweeps, remaining {budget.remaining():.1f}s")
        return tour, inference_calls, restarts
    elif ranked_weights is not None:
        is_prime_f32 = is_prime.astype(np.float32)
        print("  running 2-opt (RANK, I5) + Or-opt (classical) + ILS ...")

        if ILS_WORKERS > 1:
            # C19: skip the sequential initial converge; the first PILS batch
            # runs from the NN tour with 1× DB perturbation and 30s VND budget,
            # 8-way parallel. Best of 8 becomes initial best, freeing the ~30s
            # of single-core wall time the sequential converge consumed.
            best_tour, best_cost, ninf_par, batches, accepts = parallel_ils_loop(
                tour, 0.0, xy, is_prime, candidates, ranked_weights,
                budget,
                workers=ILS_WORKERS, worker_budget_sec=ILS_WORKER_BUDGET,
                initial_converge=True, initial_perturb=1, initial_budget_sec=30.0,
            )
            inference_calls += ninf_par
            # Report restarts as total worker iterations for backward compat
            # with the metrics field.
            restarts = batches * ILS_WORKERS
        else:
            # Sequential ILS legacy path: keep the sequential initial converge.
            s2, sor, ninf = _vnd_local(
                tour, pos, xy, is_prime_f32, candidates, ranked_weights, budget,
                max_outer=10,
            )
            inference_calls += ninf
            best_tour = tour.copy()
            best_cost = score_tour(best_tour, xy, is_prime)
            print(f"  initial converge: 2opt={s2}sw, or-opt={sor}sw, val_cost={best_cost:.2f}, remaining {budget.remaining():.1f}s")
            rng = np.random.default_rng(ILS_SEED)
            while not budget.expired():
                new_tour = best_tour.copy()
                new_tour = double_bridge(new_tour, rng)
                new_tour = double_bridge(new_tour, rng)
                new_pos = np.empty(n, dtype=np.int64)
                new_pos[new_tour[:-1]] = np.arange(n, dtype=np.int64)
                s2, sor, ninf = _vnd_local(
                    new_tour, new_pos, xy, is_prime_f32, candidates,
                    ranked_weights, budget, max_outer=10,
                )
                inference_calls += ninf
                restarts += 1
                new_cost = score_tour(new_tour, xy, is_prime)
                if new_cost < best_cost:
                    print(f"    restart {restarts}: 2opt={s2}sw or-opt={sor}sw val_cost={new_cost:.2f} ↓ ({best_cost - new_cost:+.2f})")
                    best_cost = new_cost
                    best_tour = new_tour.copy()
                elif restarts <= 5 or restarts % 5 == 0:
                    print(f"    restart {restarts}: 2opt={s2}sw or-opt={sor}sw val_cost={new_cost:.2f}")
            print(f"  done: {restarts} restarts, best val_cost={best_cost:.2f}")
        return best_tour, inference_calls, restarts
    else:
        print("  running 2-opt ...")
        sweeps = run_2opt(tour, pos, xy, candidates, budget)
        print(f"  2-opt converged in {sweeps} sweeps, remaining {budget.remaining():.1f}s")
        return tour, inference_calls, restarts


def main():
    if MODE == "train":
        import train
        try:
            tag = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"]
            ).decode().strip()
        except Exception:
            tag = "uncommitted"
        train.train_and_eval(tag=tag)
        return

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

    ranked_weights = None
    ckpt_path = None
    if not HARVEST and RANK in ("auto", "1"):
        ckpt_path, ranked_weights = load_latest_checkpoint()
        if ranked_weights is None:
            if RANK == "1":
                raise RuntimeError("RANK=1 but no checkpoint in checkpoints/")
            print("  no checkpoint found — falling back to baseline 2-opt")
        else:
            print(f"  loaded ranker checkpoint: {ckpt_path.name}")

    tour, inference_calls, restarts = solve(
        xy, is_prime, budget,
        harvest_bufs=harvest_bufs,
        ranked_weights=ranked_weights,
    )
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
    if ranked_weights is not None:
        print(f"checkpoint:       {ckpt_path}")
        print(f"inference_calls:  {inference_calls}")
        print(f"restarts:         {restarts}")
    if HARVEST:
        print(f"moves_logged:     {moves_logged}")
        print(f"moves_path:       {moves_path}")


if __name__ == "__main__":
    main()
