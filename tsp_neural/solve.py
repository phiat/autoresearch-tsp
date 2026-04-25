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

K_NEIGHBORS = 10
HARVEST = os.environ.get("HARVEST", "0") == "1"
MODE = os.environ.get("MODE", "solve")
RANK = os.environ.get("RANK", "auto")  # "auto" => use ckpt if found; "0" force baseline; "1" require ckpt
CHECKPOINTS_DIR = Path(__file__).parent / "checkpoints"


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


@njit(cache=True, fastmath=True)
def two_opt_sweep_ranked(tour, pos, xy, is_prime_f32, candidates,
                         W1, b1, W2, b2, w3, b3_scalar, mu, sd):
    """2-opt sweep with MLP-scored candidate order; multiple accepts per ai
    allowed (matches baseline scan depth, just with model ordering).
    After each accept, a_next / d_a_anext refresh; existing scores are kept
    (stale-but-cheap). Already-tried candidates are marked used."""
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

        for slot in range(K):
            best_kk = -1
            best_score = NEG_INF
            for kk in range(K):
                if not used[kk] and valid[kk] and scores[kk] > best_score:
                    best_kk = kk
                    best_score = scores[kk]
            if best_kk < 0:
                break
            used[best_kk] = True
            c = candidates[a, best_kk]
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

def solve(xy, is_prime, budget, harvest_bufs=None, ranked_weights=None):
    print("  building candidate list (cKDTree) ...")
    tree = cKDTree(xy)
    _, idx = tree.query(xy, k=K_NEIGHBORS + 1)
    candidates = idx[:, 1:].astype(np.int32)

    print("  building NN tour ...")
    tour = nearest_neighbor(xy, candidates, budget)
    print(f"  NN done, remaining {budget.remaining():.1f}s")

    if budget.remaining() < 1:
        return tour, 0

    n = len(xy)
    pos = np.empty(n, dtype=np.int64)
    pos[tour[:-1]] = np.arange(n, dtype=np.int64)

    inference_calls = 0
    if harvest_bufs is not None:
        print("  running 2-opt (HARVEST=1, logging candidates) ...")
        sweeps = run_2opt_harvest(tour, pos, xy, candidates, budget, harvest_bufs)
    elif ranked_weights is not None:
        print("  running 2-opt (RANK, MLP-scored candidate order) ...")
        is_prime_f32 = is_prime.astype(np.float32)
        sweeps, inference_calls = run_2opt_ranked(
            tour, pos, xy, is_prime_f32, candidates, ranked_weights, budget,
        )
    else:
        print("  running 2-opt ...")
        sweeps = run_2opt(tour, pos, xy, candidates, budget)
    print(f"  2-opt converged in {sweeps} sweeps, remaining {budget.remaining():.1f}s")

    return tour, inference_calls


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

    tour, inference_calls = solve(
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
    if HARVEST:
        print(f"moves_logged:     {moves_logged}")
        print(f"moves_path:       {moves_path}")


if __name__ == "__main__":
    main()
