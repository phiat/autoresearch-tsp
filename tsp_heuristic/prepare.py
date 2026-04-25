"""
Frozen data + scoring harness for the Santa 2018 Prime Paths TSP.

DO NOT MODIFY THIS FILE. The agent edits `solve.py` only.

Provides:
    - TIME_BUDGET           : wall-clock seconds the solver may run
    - load_cities()         : returns (xy, is_prime) numpy arrays indexed by CityId
    - score_tour(tour)      : ground-truth metric (lower is better)
    - validate_tour(tour)   : sanity check; raises on malformed tours
    - write_submission(...) : Kaggle-format CSV writer

Tour rules (Kaggle Santa 2018):
    - Permutation of all N CityIds, starting and ending at City 0 (North Pole).
    - Cost is sum of euclidean step lengths.
    - Every 10th step (steps 10, 20, 30, ...) is penalised: if the city the
      *previous* step left from is NOT prime, that step is multiplied by 1.1.
"""

import os
import time
import csv
from pathlib import Path

import numpy as np
import pandas as pd
from sympy import isprime

# ---------------------------------------------------------------------------
# Constants (fixed, do not modify)
# ---------------------------------------------------------------------------

TIME_BUDGET = 300            # solver wall-clock budget in seconds (5 min)
HARD_TIMEOUT = 600           # kill threshold for the runner harness
START_CITY = 0               # North Pole

DATA_DIR = Path(__file__).resolve().parent / "data"
CITIES_CSV = DATA_DIR / "cities.csv"
SUBMISSIONS_DIR = Path(__file__).resolve().parent / "submissions"

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_cities():
    """Return (xy, is_prime).

    xy        : float64 array, shape (N, 2)
    is_prime  : bool array,    shape (N,)   -- is_prime[i] iff CityId i is prime
    """
    if not CITIES_CSV.exists():
        raise FileNotFoundError(
            f"Missing {CITIES_CSV}. Unzip the Kaggle "
            "traveling-santa-2018-prime-paths archive into ./data/"
        )
    df = pd.read_csv(CITIES_CSV)
    assert list(df.columns) == ["CityId", "X", "Y"], df.columns
    assert (df["CityId"].values == np.arange(len(df))).all(), "CityIds must be 0..N-1 in order"
    xy = df[["X", "Y"]].to_numpy(dtype=np.float64)
    is_prime = _prime_mask(len(df))
    return xy, is_prime


def _prime_mask(n):
    """Boolean mask of length n, True at prime indices. Cached on disk."""
    cache = DATA_DIR / "is_prime.npy"
    if cache.exists():
        arr = np.load(cache)
        if len(arr) == n:
            return arr.astype(bool)
    # Sieve of Eratosthenes — much faster than per-int sympy.isprime for N~2e5.
    sieve = np.ones(n, dtype=bool)
    sieve[:2] = False
    for i in range(2, int(n ** 0.5) + 1):
        if sieve[i]:
            sieve[i * i :: i] = False
    # Sanity check against sympy on a few random indices.
    rng = np.random.default_rng(0)
    for idx in rng.integers(0, n, size=20):
        assert bool(sieve[idx]) == isprime(int(idx)), f"sieve disagrees at {idx}"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    np.save(cache, sieve)
    return sieve

# ---------------------------------------------------------------------------
# Scoring (DO NOT CHANGE — this is the fixed metric)
# ---------------------------------------------------------------------------

def validate_tour(tour, n_cities):
    """Raise ValueError if tour is not a legal Santa tour."""
    tour = np.asarray(tour, dtype=np.int64)
    if tour.ndim != 1:
        raise ValueError(f"tour must be 1-D, got shape {tour.shape}")
    if len(tour) != n_cities + 1:
        raise ValueError(f"tour length must be {n_cities + 1} (N+1, includes return), got {len(tour)}")
    if tour[0] != START_CITY or tour[-1] != START_CITY:
        raise ValueError(f"tour must start and end at city {START_CITY}; got {tour[0]} .. {tour[-1]}")
    interior = tour[:-1]
    if interior.min() < 0 or interior.max() >= n_cities:
        raise ValueError("tour contains out-of-range CityIds")
    if len(np.unique(interior)) != n_cities:
        raise ValueError("tour does not visit each city exactly once")
    return tour


def score_tour(tour, xy=None, is_prime=None):
    """Compute the Santa 2018 tour cost. Lower is better.

    `tour` is the full permutation including the return to START_CITY
    (length N+1). `xy` and `is_prime` may be passed to avoid reloading.
    """
    if xy is None or is_prime is None:
        xy, is_prime = load_cities()
    tour = validate_tour(tour, len(xy))

    diffs = xy[tour[1:]] - xy[tour[:-1]]                 # (N, 2)
    step = np.sqrt((diffs * diffs).sum(axis=1))          # (N,)

    # Step k (1-indexed) is penalised iff k % 10 == 0 AND the *origin*
    # of that step (tour[k-1]) is not prime. step[i] in 0-indexed terms
    # corresponds to the (i+1)-th step.
    k = np.arange(1, len(step) + 1)
    every_tenth = (k % 10) == 0
    origin = tour[:-1]                                   # tour[k-1] for k=1..N
    not_prime_origin = ~is_prime[origin]
    penalty_mask = every_tenth & not_prime_origin
    step = step * np.where(penalty_mask, 1.1, 1.0)
    return float(step.sum())

# ---------------------------------------------------------------------------
# Submission helpers
# ---------------------------------------------------------------------------

def write_submission(tour, path):
    """Write a Kaggle-format submission CSV (single 'Path' column)."""
    tour = np.asarray(tour, dtype=np.int64).ravel()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Path"])
        for city in tour:
            w.writerow([int(city)])


# ---------------------------------------------------------------------------
# Convenience: timer the agent can use without modifying the budget
# ---------------------------------------------------------------------------

class TimeBudget:
    """Lightweight wall-clock timer pinned to TIME_BUDGET seconds."""

    def __init__(self, seconds=TIME_BUDGET):
        self.seconds = float(seconds)
        self.t0 = time.perf_counter()

    def elapsed(self):
        return time.perf_counter() - self.t0

    def remaining(self):
        return max(0.0, self.seconds - self.elapsed())

    def expired(self):
        return self.elapsed() >= self.seconds


# ---------------------------------------------------------------------------
# Main: smoke test the harness
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"Loading cities from {CITIES_CSV} ...")
    xy, is_prime = load_cities()
    n = len(xy)
    print(f"  N={n} cities, {is_prime.sum()} prime CityIds ({100 * is_prime.mean():.2f}%)")

    # Identity tour: 0, 1, 2, ..., N-1, 0 — useless but legal.
    identity = np.concatenate([np.arange(n, dtype=np.int64), [START_CITY]])
    cost = score_tour(identity, xy, is_prime)
    print(f"  identity tour cost: {cost:,.2f}")
    print(f"  TIME_BUDGET = {TIME_BUDGET}s  HARD_TIMEOUT = {HARD_TIMEOUT}s")
    print("OK")
