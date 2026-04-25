# Recap 1 — `heuristic/apr25` first session

Snapshot of the autonomous loop on the Kaggle Santa 2018 TSP, branch
`heuristic/apr25`. Captures what was built, what's been tried, what worked,
and what's queued.

## Setup

- **Task**: minimise total tour cost over N=197,769 cities. Cost is
  euclidean step length, with a **1.1× penalty on every 10th step
  whose origin city is not prime** (17,802 primes / 9.00% of cities).
- **Harness mirrors karpathy/autoresearch**:
  - `prepare.py` (frozen) — `load_cities`, sieve-based prime mask,
    `score_tour`, `TimeBudget`. Defines `TIME_BUDGET = 300s`.
  - `solve.py` — agent's playground. Single entry point.
  - `program.md` — agent instructions.
  - `ideas.md` — seeded library of experiment ideas + sample &
    grow protocol.
  - `results.tsv` — append-only ledger of runs (gitignored).
- **Allowed deps**: numpy, pandas, sympy, scipy, numba.
- **Loop mode**: mirror karpathy — separate Claude session in
  `tsp_heuristic/` driving `program.md`. No external scheduler.
- **Hardware**: RTX 4070 16GB, but no GPU work yet — all CPU/numba.

## Loop, in one screen

1. Read state (branch, `results.tsv`, `ideas.md`).
2. Sample an untried idea (random, class-balanced).
3. Edit `solve.py` (one focused change), commit, run with 5-min budget.
4. Grep `val_cost` from `run.log`; log row to `results.tsv`.
5. If improved → keep commit (advance branch). Else → `git reset --hard HEAD~1`.
6. Every 5 logged cycles → append 2-3 fresh ideas to `ideas.md`.
7. Loop forever.

## Results

| # | commit | val_cost | Δ best | description |
|---|---|---|---|---|
| 1 | dd8df32 | 1,812,602.19 | — | NN baseline (start at city 0) |
| 2 | 3366b5a | 1,577,298.71 | −235,304 | L5: numba 2-opt, k=10 cKDTree candidates |
| 3 | 55f4833 | 1,575,748.26 | −1,550   | P1: ILS double-bridge + 2-opt restart |
| 4 | 1649128 | 1,553,925.98 | −21,822  | O1: Or-1 alternated with 2-opt |
| 5 | 705ce3e | 1,553,486.74 | −439     | O4: mixed Or-1/2/3 alternated with 2-opt |
| 6 | 081e0e2 | 1,553,424.33 | −62 | E1: fast cKDTree NN seed (frees ILS budget) |
| 7 | f345bbd | **1,553,408.50** | −16 | Z1: prime-swap post-pass after ILS |
| 8 | 2d92b5c | *(in flight)* | — | H1: candidate list k=20 (vs prior k=10) |

**Best: 1,553,408.50** — −14.30% from baseline. All 7 logged experiments kept
(no reverts, no crashes).

For reference: top public-LB submissions hit ~1,514K. Vanilla 2-opt +
Or-opt typically lands 1.55-1.56M (we're there). The remaining gap is
mostly prime-aware moves and stronger perturbation/diversification.

## What worked

- **Candidate-list 2-opt was the foundation** (#2). 13% drop on its
  own; converges in <1s once k-NN is built. Without it nothing else
  fits in budget on N≈200K.
- **Or-opt complements 2-opt** (#4). Or-1 alone got −22K — by far the
  largest gain after the initial 2-opt jump. Or-opt finds relocate
  moves 2-opt structurally cannot see.
- **Mixed Or-1/2/3 added a tiny bit more** (#5, −439). Diminishing
  returns once Or-1 has been applied.
- **E1 freed lots of budget** (#6). The brute NN took ~175s of 300s;
  cKDTree-walked NN drops it to a few seconds, leaving most of the
  300s for ILS. But the *score* barely moved (−62) — the ILS basin
  is what it is, more iterations don't escape it.
- **Z1 prime-swap post-pass barely moved** (#7, −16). First prime-aware
  move tried; it only nudges *misaligned* steps that already happen to
  have a cheap fix, so the upside is small. The bigger lever is making
  the move-evaluation itself prime-aware (Z2), not patching after the
  fact.

## What surprised

- **ILS double-bridge (#3) was almost a no-op** (−1,550). 160 ILS
  iters, only 9 accepts, none big. Hypothesis: double-bridge isn't
  destructive enough to escape the 2-opt basin on a graph this large,
  and the per-restart re-2-opt is short. Bigger perturbations or
  proper LNS (destroy 5-10% then repair) likely needed.
- **E1's tiny gain despite massive budget unlock**. ILS scaled from
  ~125s to ~290s of compute, ran 232 iters vs 160, and ate ~14
  improvements vs 9 — and still only saved 62. Strong signal that the
  current move-set is the limit, not the time spent on it.

## What's still untried

The library has 33 items; we've sampled 8 (Z1 + H1 in the latest two
cycles). **Notable gaps:**

- **Z2 (real-penalty 2-opt) + Z3 (prime-aligned construction) + Z4
  (post-pass swaps)** — the prime-aware family is still mostly open.
  Z1 underwhelmed but it was the weakest of the four; Z2 in particular
  changes the 2-opt *gain* formula and could redirect ILS into a
  different, prime-friendly basin.
- **Don't-look bits (L7, appended)** — orthogonal speedup that would
  let many more sweeps fit per budget; pairs well with bigger ILS
  perturbations.
- **Construction alternatives** (C2 greedy edge, C3 cheapest insert,
  C5 Hilbert, C6 multi-start NN). E1 made NN cheap, so multi-start
  is now plausible.
- **Remaining hyperparam sweeps (H2-H5)**. H1 (k=20) is in flight; the
  others (Or-opt segment-length set, ILS depth-vs-restarts split,
  double-bridge size, time-budget split) are open.
- **Engineering (D1-D4)**. The cKDTree is rebuilt each run; D1
  cache + D3 jit'd score would help most.
- **Pipelines (X1-X4)** and the LNS-flavoured P2/P3 perturbations.

## Trial directions for the next session

Updated after Z1 and H1-in-flight:

1. **Z2 — real-penalty 2-opt** is now the highest-EV untried lever.
   Z1's tiny gain showed that *post-hoc* prime moves don't have much
   room; Z2 changes what 2-opt optimises *during* the sweep, which
   could redirect ILS into a prime-friendlier basin entirely.
2. **L7 don't-look bits** — turns near-converged sweeps O(1) per
   city, freeing budget for everything else.
3. **Z3 prime-aligned construction** — bias initial tour to put primes
   at positions 9, 19, 29… so the kicker lands on a prime origin
   "for free" before any local search.
4. **P2/P3 stronger perturbation** — segment reverse / shift of
   N/50-N/20 nodes. Targets the diagnosis from #3 (double-bridge
   too gentle).
5. **C6 multi-start NN** — now affordable thanks to E1; gives more
   diverse basins for Or-opt + ILS to refine.
6. **H1 result (in flight)** will tell us whether tightening to k=20
   helps; if yes, try k=15/30 next, if no try k=5/7.

## Ideas library

`ideas.md` has been grown once so far (cycle-1 append: E1, L7, Z4 —
based on runs 1-3). Library has 30 seed + 3 appended = 33 items. Next
growth tick fires after run 10 (currently between #7 and #8).

## Files / state

- Branch: `heuristic/apr25` @ `2d92b5c` (latest commit; run #8 H1 in flight).
- Last *kept* commit: `f345bbd` (Z1 prime post-pass, val 1,553,408.50).
- `submissions/submission.csv` — current best tour, ready for Kaggle.
- `results.tsv` — 7 logged rows + header. Local only.
- `ideas.md` — 33 items, last appended cycle 1.
- `run.log` — overwritten by H1 run; H1 result not yet in `results.tsv`.

The loop is healthy and on a credible trajectory. Z1 was a small-gain
data point that helps inform direction (prefer Z2 over more Z1-like
post-passes). Letting it keep running.
