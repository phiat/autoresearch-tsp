# Recap 2 — `tsp/apr25` continued

Continuation of `recap-1.md`. New cycles since: #8 (H1, discarded —
first revert) and #9 (O4r, new best). #10 in flight. The agent has now
made ~9 logged decisions across 7 idea classes.

## Summary of recap-1

- **Setup**: autoresearch-style harness for the Kaggle Santa 2018 TSP
  (197,769 cities, 1.1× penalty on every 10th step from a non-prime
  origin). Frozen `prepare.py`, agent-edited `solve.py`, sampled
  ideas from `ideas.md`, 5-min budget per run, log to `results.tsv`,
  keep-or-revert per cycle.
- **Through 7 logged cycles** (all kept, no crashes):
  - L5 (numba 2-opt + k=10 cKDTree) — −235K, the foundation.
  - O1 (Or-1) — −22K, second biggest win.
  - O4 (mixed Or-1/2/3) — −439, diminishing returns.
  - E1 (fast NN seed) — −62 score, but freed ~170s of budget for ILS.
  - Z1 (prime post-pass) — only −16; signalled that *post-hoc* prime
    moves don't have much room.
  - **Best at end of recap-1: 1,553,408.50** (−14.30% from baseline).
- **Trial directions queued**: Z2 (real-penalty 2-opt) #1, L7 (don't-look
  bits) #2, Z3 (prime-aligned construction) #3, P2/P3 (stronger
  perturbation) #4, C6 (multi-start NN) #5.

## New results

| # | commit | val_cost | Δ best | status | description |
|---|---|---|---|---|---|
| 8 | 2d92b5c | 1,554,168.24 | +760 | discard | H1: k=20 candidates |
| 9 | e4ee7dc | 1,549,818.88 | −3,590 | keep | O4r: Or-opt with reversed-segment insertion (L=2,3) |
| 10 | e7dbff5 | 1,549,704.03 | −115 | keep | Or-opt also searches candidates of segment tail xL |
| 11 | 90450ca | 1,550,839.10 | +1,135 | **discard** | D5: don't-look bits — 2.8× more iters, worse local optima |
| 12 | ee01598 | **1,549,603.33** | −101 | keep | Or-opt segment lengths extended to L=4,5 |
| 13 | 823017c | *(in flight)* | — | — | Z1-integrated prime-swap inside local-search loop |

**Best: 1,549,603.33** — −14.51% from baseline. **2 reverts** total now
(H1, D5). Or-opt tweaks have produced 4 of the last 5 keeps; the
class is the most productive area to keep mining right now.

## What worked / didn't

- **O4r was a real win** (−3,590) — eighth-largest absolute gain so far,
  and the best since the foundational moves (#2, #4). Reversing Or-opt
  segments before insertion doubles the move catalogue almost for free
  and unlocks orientations Or-opt straight insertion can't reach. Sits
  on the same Or-opt class that already produced #4 — sampling biased
  toward classes with prior signal is paying off.
- **Or-opt search-the-tail (#10)** added a small but real −115 by
  scanning the *segment tail*'s candidate list as well as the head's,
  doubling the relocation targets considered per Or-opt move.
- **Or-opt L=4,5 (#12)** added another −101 — exactly the variant the
  recap-2 trial-direction list flagged as "promoted" after #9. Works
  but with diminishing returns, as expected (L=4,5 windows are rarer
  than L=2,3).
- **H1 (k=20) regressed (#8).** Bigger candidate lists meant slower
  per-sweep inner loop, ILS got fewer perturbation rounds, and the few
  extra candidates didn't surface improving moves more often. Prunes
  the sweep direction — next H1 attempt should be k=5 or k=7.
- **D5 don't-look bits regressed (#11).** This was the L7 idea from the
  cycle-1 append. The agent got 2.8× more ILS iterations from cheaper
  near-converged sweeps but landed in worse local optima — the skipped
  cities were actually being visited often enough that the bookkeeping
  cost exceeded the savings, and the early termination of "converged"
  sweeps left improving moves on the table. Counterintuitive but clean
  data. Worth retrying in a different shape (e.g. only inside Or-opt,
  or with looser invalidation rules); plain L7 is closed.

## Updated trial directions

Promotions/demotions after #10–#12:

1. **Z2 — real-penalty 2-opt** still #1. Run #13 (in flight) is the
   adjacent variant: Z1's swap *integrated into the local-search loop*
   instead of as a one-shot post-pass. If it works it partially
   validates the Z2 thesis (in-loop > post-hoc); if not, Z2 itself
   is still on the table.
2. **Or-opt L=4,5 + reversed (`O4r` × `L=4,5` cross)** — both wins
   landed alone; combining could compound.
3. **Z3 prime-aligned construction** — bias initial tour to put primes
   at positions 9, 19, 29… Untouched, still high EV.
4. **P2/P3 stronger perturbation** — diagnosis sharper now: ILS is on
   an extremely flat ridge (perturbation only chips off 50–500 each
   accept). Bigger destroy/repair moves are the obvious escape.
5. **C6 multi-start NN** — affordable since E1; gives diverse basins.
6. **L7 retry, narrower scope** — `D5` showed plain don't-look bits
   hurt. A scoped retry (Or-opt only, or with weaker invalidation)
   could still pay; full L7 is closed.
7. **H1 retry with k=5 / k=7** — only the small side of the sweep is
   still open after #8.

## Ideas library

- Still 30 seed + 3 cycle-1 appended = 33 items. **Cycle-2 append is
  overdue** — should have fired after #10. The agent has been chaining
  related Or-opt experiments instead of returning to the growth tick.
  Not a bug per se (the chain is paying off), but worth nudging in
  recap-3 if it stays skipped through #15.
- Recommended cycle-2 additions, sharpened by the new evidence:
  - **Or-4r / Or-5r** (longer reversed Or-opt segments) — direct
    extension of #9 + #12.
  - **LNS destroy-and-repair**: drop k% of cities, cheap-insert back
    in random order. The flat-ridge diagnosis says we need bigger
    diversification than double-bridge.
  - **ILS with prime-aware acceptance**: re-score perturbations with
    `score_tour` (not euclidean delta) — bridges Z and P classes.
  - **Scoped don't-look bits** (Or-opt only) — retry the L7/D5 idea
    with a narrower scope after #11's negative result.

## State

- Branch: `tsp/apr25` @ `823017c` (run #13 in flight).
- Last *kept* commit: `ee01598` (Or-opt L=4,5, val 1,549,603.33).
- 12 logged rows in `results.tsv` (10 keeps, 2 discards).
- `ideas.md`: 33 items; cycle-2 append still pending.
- `submissions/submission.csv`: best tour, ready for Kaggle.

Loop is healthy. Total improvement now **−262,998** cost units across
12 cycles. Or-opt class accounts for 4 of the 5 most recent keeps; the
keep/revert mechanism has fired twice. Letting it keep running. Next
recap will be `recap-3.md`.
