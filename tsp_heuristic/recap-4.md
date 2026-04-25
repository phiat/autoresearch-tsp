# Recap 4 — `heuristic/apr25` continued

Covers cycles #17–#21 (results.tsv rows 17-21 inclusive). Recap-3 closed
at row #16 / commit `035729e` with the P4 random-restart mechanism as the
headline win. This recap resolves two quick discards followed by three
consecutive wins from tightening the candidate-list k hyperparameter,
setting a new overall best of **1,547,900.81**.

## Summary of recap-3

- Opened from best 1,549,603.33 (Or-opt L=4,5, row #12).
- Z1-integrated prime-swap (#13, +223, discard) — moving prime-swap into
  the inner loop halved ILS iteration count; mirrors the D5 lesson that
  inner-loop overhead is never free.
- L3 best-improvement 2-opt (#14, −627) combined with silent P5 base
  (adaptive perturbation escalation) — largest single gain this recap.
- P3 segment-shift alternated with double-bridge (#15, −25) — thin but
  real; diversifies escape topology.
- P4 random-NN-restart-on-stuck (#16, −455) — the most important new
  capability: after 40 idle ILS iters, re-seed from a random city via
  fast cKDTree NN. Run.log confirmed one restart at iter 84 then 10+
  consecutive new bests. Essentially free thanks to E1 (NN now 4s not 175s).
- **Best at end of recap-3: 1,548,496.21** (row #16, 035729e).
- 3 total reverts through row 16 (H1 k=20, D5 don't-look bits,
  Z1-integrated).

## New results

| # | commit | val_cost | Δ best | status | description |
|---|---|---|---|---|---|
| 17 | 2c1003c | 1,548,884.28 | +388 | **discard** | P4t: RESTART_AFTER=20 — too-frequent restarts dilute local-search depth |
| 18 | 7462c07 | 1,550,420.63 | +1,924 | **discard** | Z3: prime-aligned NN — warps geometry, ILS recovers most but net regression |
| 19 | 29d0256 | 1,548,122.80 | −373 | keep | H1k7: K_NEIGHBORS=7 — faster sweeps, +20 ILS iters, net win |
| 20 | c076566 | 1,548,025.66 | −97 | keep | H1k5: K_NEIGHBORS=5 — deeper local optima despite fewer ILS iters |
| 21 | 5393897 | **1,547,900.81** | −125 | keep | H1k4: K_NEIGHBORS=4 — third k-knob win in a row |

**Best: 1,547,900.81** — −14.59% from baseline (dd8df32, 1,812,602.19).
5 total discards in the run overall (H1/D5/Z1-int/P4t/Z3).
The three k-knob wins total −595 cost units across one direction of the
candidate-list size axis.

## What worked / didn't

- **P4t tighter restart threshold (#17, discard, +388).** Dropping
  RESTART_AFTER from 40 to 20 idle iters caused 5 restarts within budget
  vs. 0 in the H1k4 run. Each restart discards accumulated local-search
  depth to re-seed from NN; when restarts fire too often, the algorithm
  spends most of its budget on shallow post-restart local search rather
  than deep ILS iteration. The 40-iter threshold appears to be near the
  right balance for the current budget. Lesson: the restart mechanism is
  most valuable as a single escape from a deep rut, not as a periodic
  diversification pulse.

- **Z3 prime-aligned NN construction (#18, discard, +1,924).** Reordering
  the NN tour after construction to place primes at positions 9, 19, 29 ...
  imposes a fixed permutation that warps tour geometry. ILS recovers most
  of the cost within 300s, but cannot fully repair a biased starting
  structure. Confirms that the prime penalty is too small a fraction of
  total cost to justify distorting geometric tour structure. Z-class
  construction-phase experiments are effectively closed; Z2 (penalty-aware
  move scoring, not construction bias) remains the only open Z with positive
  EV.

- **H1k7 smaller candidate list (#19, keep, −373).** Shrinking K_NEIGHBORS
  from 10 to 7 makes each 2-opt and Or-opt sweep faster, fitting more ILS
  iterations into budget. The net quality improvement shows the search was
  breadth-limited at k=10: many nearby cities were already being reached
  via the ILS perturbation loop, so reducing per-iter work was a net win.
  First win opening the k-shrink direction.

- **H1k5 even smaller list (#20, keep, −97).** A further reduction from 7
  to 5. Diminishing but real: the search is approaching a point where some
  good moves start to be missed. Still net-positive at this step size.

- **H1k4 (#21, keep, −125).** Third consecutive win from tightening k.
  The run.log for this commit shows 176 ILS iters with 9 improvements and
  0 restarts; the final prime-swap post-pass applied 15 swaps for an
  additional −6.06 cost units. The diminishing-then-recovering pattern
  (−373, −97, −125) suggests the k-shrink vein is not yet exhausted — the
  jump back from −97 to −125 at k=4 may indicate a local plateau at k=5
  that k=4 escapes.

## Updated trial directions

1. **H1k3 — push k to 3**: The k-shrink trend is intact. k=3 is the
   natural next probe; at this level the candidate list is extremely sparse
   but may still provide enough ILS iteration gain to outweigh missed moves.
   Lowest implementation cost, highest information value right now.

2. **Z2 — penalty-aware 2-opt gain formula**: Still the only remaining
   Z-class idea with positive EV. Track modulo-10 positions per move and
   apply real penalty delta only where a prime boundary is crossed; use
   pure euclidean everywhere else. Must not tax the inner loop (Z1-integrated
   and D5 lessons bound the acceptable overhead tightly).

3. **LNS destroy-and-repair**: Remove ~4% of cities at random, repair by
   cheapest insertion. More structural than the P4 NN restart; targets
   tour flat-ridges by destroying contiguous structure. The H1k4 run.log
   shows 0 restarts in 176 ILS iters — P4 never fired — suggesting the
   tour may be in a deep local basin where global re-seeding is not the
   right escape. A targeted destroy-repair may reach further.

4. **Or-opt L=4,5 reversed (O4r x extended lengths)**: Both O4r (reversed
   insertion, L=2,3) and the L=4,5 extension were independent wins.
   Combining them is a low-risk compound experiment with no new mechanisms.

5. **Multi-restart X4 — best-of-N from k=4 random NN seeds**: With NN now
   taking ~8s, running 10-20 NN constructions and keeping the best before
   ILS costs ~80-160s but may deliver a substantially better starting point.
   Most valuable if ILS basin-escape rate remains low.

6. **Scoped don't-look bits (Or-opt only)**: D5 full bits hurt; a version
   restricted to Or-opt (not 2-opt) has not been tested and may recover
   throughput without degrading 2-opt quality.

## Ideas library

- 37 items total: 30 seed + 3 cycle-1 appended (E1, L7, Z4) + 4 cycle-3
  appended (P4t, O4r45, Z2e, LNS).
- Cycle-3 growth tick fired at `008746e`. Next tick due at cycle 25.
- Recommended next additions (cycle-4 append):
  - **H1k3**: probe k=3 to complete the k-shrink sweep.
  - **X4-multi-start**: run 10+ NN constructions before ILS, keep the best.
  - **LNS-prime**: bias destroy-and-repair toward prime-position cities to
    couple the repair idea with the Santa penalty structure.

## State

- Branch: `heuristic/apr25` @ `5393897` (H1k4).
- Last kept experiment commit: `5393897` (val 1,547,900.81).
- In-flight: none. run.log is the completed H1k4 run (176 ILS iters,
  0 restarts, 9 improvements, 15 prime-swap post-pass swaps).
- 21 logged rows in `results.tsv` (16 keeps, 5 discards).
- `ideas.md`: 37 items; cycle-4 growth tick due around row 25.
- Submissions file: `submissions/submission.csv` at val 1,547,900.81.

Loop is healthy. Total improvement **−264,701.38** cost units from baseline
across 21 cycles. The k-knob vein (H1k7/k5/k4, −595 total) is the newest
active seam and has not yet exhausted. Two prior design lessons dominate:
(1) inner-loop overhead is never free — keep local-search moves cheap;
(2) geometric distortion for prime alignment costs more than penalty savings
recover. Best path forward: probe k=3, then pivot to LNS or Z2 depending
on whether the k-shrink vein closes.
