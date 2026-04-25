# Recap 7 — `heuristic/apr25` continued

Covers results.tsv rows #44–#53 (commits `8e6c422` through `f6d5ff9`).
Recap-6 closed at row #43 / commit `f2c74eb` (SShv, 1,547,793.02) after a
9-run discard streak. All 10 new rows are discards. Best val_cost remains
1,547,351.05 (X8, `8a1c432`, row #34). The streak now spans rows 35–53:
19 consecutive discards. No in-flight experiment as of this recap.

## Summary of recap-6

- Opened from best 1,547,351.05 (X8, `8a1c432`, row #34).
- All 7 new rows (#37-#43) were discards — the longest streak observed to
  that point.
- X9 (+542): candidate split K=7/K=4 broke coherence between 2-opt and
  Or-opt, confirming k=4 is architecture-wide optimum.
- Reg2 (+577): regret-2 LNS repair made reinsertion too coherent; random
  insert order is a feature when destroy is structured.
- P5 (+846): stacked double-bridge over-disrupts; single DB is the right
  perturbation magnitude.
- H6 (+745): bandit arm weights never learned signal — 300s budget too
  short for meaningful softmax shift; fixed 1/3 split is as good.
- Z5 (+70) and X8d (+70): GLS lam=1.0 and enlarged restart-LNS frac both
  tied at the +70 noise floor; neither moved the needle.
- SShv (+442): SS-heavy arm mix produced fewer ILS improvements; per-call
  success rate is not proportional to per-budget productivity.
- **Best at end of recap-6: 1,547,351.05** (X8, `8a1c432`). 26 total
  discards through row 43.

## New results

| # | commit | val_cost | delta best | status | description |
|---|---|---|---|---|---|
| 44 | 8e6c422 | 1,548,026.86 | +676 | **discard** | OrL67: Or-opt L=1..7 — extra L=6,7 sweeps eat budget, +676 (L=1..5 optimal) |
| 45 | d6c95c4 | 1,549,993.30 | +2,642 | **discard** | C6: multi-start NN (5 seeds) — 25s lost from ILS budget for marginal seed gain |
| 46 | f921598 | 1,548,904.59 | +1,554 | **discard** | OrRev: reverse Or-opt L order (5,4,3,2,1) — converges to worse basin |
| 47 | acc857f | 1,547,351.05 | +0 | **discard** | Z5b: GLS lam=0.1 — identical trajectory to X8 (penalty bumps below noise floor), tie |
| 48 | 6590315 | 1,547,420.96 | +70 | **discard** | Z5d: GLS lam=0.5 proper aug gain — overhead drops ILS to 191 iters (was 226), kills late-game improvement |
| 49 | a0e7096 | 1,547,928.49 | +577 | **discard** | Reg2p: regret-2 + prime-bias destroy — same as Reg2 (1,547,928.49), regret hurts regardless of destroy method |
| 50 | 5695001 | 1,547,870.26 | +519 | **discard** | LNSdual: 4-arm split (DB/SS/LNS-rand/LNS-prime) — dilutes LNS-prime, +519 |
| 51 | c5630f8 | 1,548,230.63 | +880 | **discard** | PrimePeriodic: Z1 every 50 iters — eats compute, kills late-game basin |
| 52 | 83abe77 | 1,547,438.78 | +88 | **discard** | AdaptiveRestart: RA=20 in last 60s — close miss, forced restart fired but couldn't match X8 rng-luck |
| 53 | f6d5ff9 | 1,547,532.17 | +181 | **discard** | ForcedLateRestart: forced restart at remaining=20s, only 3 post-restart iters, +181 |

**Best: 1,547,351.05** (X8, commit `8a1c432`) — -14.63% from baseline
(`dd8df32`, 1,812,602.19). 36 total discards through row 53.
All 10 new rows are discards; the discard streak now stands at 19 consecutive
(rows 35–53).

## What worked / didn't

- **OrL67: Or-opt L=1..7 (#44, discard, +676).** Adding L=6 and L=7 passes
  extended each VND sweep, consuming wall-clock budget that would have gone
  to ILS iterations. Marginal geometric gain from longer segment relocations
  does not compensate for fewer perturbation cycles. L=1..5 is the bandwidth
  optimum for the 300s budget.

- **C6: multi-start NN 5 seeds (#45, discard, +2,642).** The worst result of
  this batch. Building five NN tours and picking the best cost ~25s of
  construction time, leaving only ~275s for ILS. The seed-tour quality gain
  was far smaller than the ILS budget loss. Basin diversity via construction
  is expensive; X8 LNS-prime smoothing is the cheaper lever for post-restart
  basin quality. This was tried earlier (row 46 in this ledger); confirmed
  failure again.

- **OrRev: reversed Or-opt order 5,4,3,2,1 (#46, discard, +1,554).** Longer
  segments first leads the VND into a different local-optima basin that is
  structurally worse. The canonical short-to-long order (L=1,2,3,4,5) builds
  on small moves as foundation before making larger cluster relocations;
  reversing this sequence disrupts that layering.

- **Z5b: GLS lam=0.1 (#47, discard, exact tie at 1,547,351.05).** The
  smallest GLS penalty weight tried. At lam=0.1 the penalty increments fall
  below the noise floor — the trajectory is indistinguishable from X8 without
  GLS. This confirms GLS signal is either too weak (lam=0.1) or too strong
  (lam=0.5, lam=1.0) to fit the 300s budget; no lambda value has improved
  over X8. The GLS vein is fully exhausted.

- **Z5d: GLS lam=0.5 proper aug gain (#48, discard, +70).** Using the
  augmented tour gain (penalizing high-frequency edges) in the accept step
  dropped ILS to 191 iterations from X8's 226 — the overhead of the
  augmented scoring function consumed budget, and the diversification it
  provided was insufficient to compensate. Confirmed the GLS-as-accept-score
  approach is a dead end for this time budget.

- **Reg2p: regret-2 + prime-bias destroy (#49, discard, +577).** Pairing
  regret-2 repair with prime-biased destroy did not rescue the regret-2
  mechanism. Matched the original Reg2 result exactly (both 1,547,928.49).
  The destroy method does not compensate for regret ordering's coherence
  problem; random-order reinsertion is the invariant, not the destroy method.

- **LNSdual: 4-arm split (#50, discard, +519).** Splitting LNS into
  rand-destroy and prime-destroy arms reduced the prime-bias arm's share from
  1/3 to 1/4 of the budget. Since LNS-prime is the productive arm (confirmed
  in rows 26-30), diluting it with a weaker LNS-rand arm is counterproductive.
  Three-arm balance (DB/SS/LNS-prime) is the right structure.

- **PrimePeriodic: Z1 every 50 ILS iters (#51, discard, +880).** Running
  prime-swap polish inside the ILS loop is the same failure mode as Z1-
  integrated (X5, row 33, +1,543). This is the third confirmation of the
  principle: Z1 overhead during ILS is never free. Reserve prime-swap for
  the terminal post-pass only.

- **AdaptiveRestart: RA=20 in last 60s (#52, discard, +88).** The closest
  near-miss since X8. Lowering RESTART_AFTER to 20 only in the final 60s
  forced a late restart and fired in the right window — but the run did not
  find a basin as good as X8's lucky post-restart ILS. The +88 result shows
  the mechanism is not reliably better than the fixed RA=40 that produced X8.
  Rng-dependent outcome: X8's restart timing was fortuitous, not systematic.

- **ForcedLateRestart: restart at remaining=20s (#53, discard, +181).**
  Harder engineering of the same idea as AdaptiveRestart. Only 3 ILS
  iterations ran after the forced restart — insufficient to converge the new
  basin. Triggering restart with 20s left is too late; 60s (AdaptiveRestart)
  was closer but still not robust. The restart-timing vein is now exhausted:
  too-early (P4t), too-late (ForcedLateRestart), and close-but-not-robust
  (AdaptiveRestart) have all been tried.

## Updated trial directions

1. **Z2e — penalty-aware 2-opt accept scoring**: The highest-EV untried
   mechanism. Track primes at positions k%10==0 during 2-opt; apply real
   penalty delta only at boundary moves, pure-Euclidean elsewhere. The
   LNS-prime wins (rows 27-30) showed penalty-origin targeting is productive;
   Z2e brings that awareness directly into move-acceptance without
   destroy-repair overhead. Zero per-iteration budget cost when the boundary
   check is O(1).

2. **X11 — GLS-biased LNS destroy**: Bias LNS city selection toward cities
   incident to high-penalty edges (GLS-style edge memory) rather than only
   penalty-origin positions. Z5 (global GLS in accept) is exhausted; X11
   sidesteps that by using GLS history only in the destroy selector. Merges
   two proven penalty-aware signals without inner-loop overhead.

3. **X6 — Or-opt segment repair inside LNS-prime**: When reinserting removed
   cities, group originally-adjacent pairs as a segment and apply O4r-style
   forward-vs-reversed insertion test rather than per-city cheapest-insert.
   Targets the structural seam cheapest-insert leaves. Distinct from X5
   (prime-swap inside repair).

4. **X10 — prime_swap_pass per accepted ILS improvement**: Invoke Z1 once
   per ILS accept event rather than only at the terminal post-pass. At ~1ms
   per call and ~18 accept events per run, the total overhead is ~18ms —
   negligible compared to 300s budget. The post-pass application is confirmed
   productive (Z1, row #7); per-event application has never been tried cleanly
   (PrimePeriodic, row 51, ran every 50 iters and was too heavy; per-accept
   is lighter-touch).

5. **L3-restart — best-improvement 2-opt k=10 for first post-restart VND
   only**: Use wider candidate list (k=10) during the single VND pass after
   a restart to find the post-restart basin more reliably, then revert to k=4
   for remaining ILS iterations. Addresses the finding that X8's restart luck
   matters; better post-restart convergence reduces luck dependence.

6. **X13 — path relinking between elite ILS solutions**: Maintain top-3
   kept tours across restarts. Between restarts, generate intermediate tours
   by swapping edges from one elite tour toward another, accept the best
   2-opt-converged intermediate. Diversification orthogonal to single-tour
   perturbations. Higher-complexity implementation but targets the
   basin-diversity gap that C6 construction diversity failed to fill cheaply.

7. **P6 — iterated tabu search on recent edges**: After each accepted ILS
   improvement, forbid removed edges from re-insertion for K moves. Prevents
   thrashing in degenerate neighborhoods and forces structurally different
   next moves without full LNS destroy overhead.

## Ideas library

- 62 items total (confirmed by grep count).
  Last appended: research-sourced additions (L10, X13, P6 visible in tail).
- From the current batch: all 10 ideas tried (#44-#53) are now exhausted.
  The GLS vein (Z5, Z5b, Z5d), regret-repair vein (Reg2, Reg2p), restart-
  timing vein (AdaptiveRestart, ForcedLateRestart), and Or-opt bandwidth
  (OrL67, OrRev) are all closed.
- D5 (position array for O(1) boundary detection) and X11 (GLS-biased LNS
  destroy) are the most promising untried items from the research-append
  batch. Z2e remains the highest-EV item across the full library.
- Recommended next additions:
  - **Z2e-fast variant**: restrict penalty-aware scoring to pairs where one
    endpoint is within 2 positions of a k%10==0 boundary.
  - **X11-lite**: combine D5 pos[] with Z2e enabling both ideas in one commit.
  - **L3-restart**: wider k post-restart only (lighter than full L3 always-on).

## State

- Branch: `main`; HEAD is `35b8dd1` (revert of ForcedLateRestart).
- Last kept experiment commit: `8a1c432` (X8, val 1,547,351.05, row #34).
- In-flight: none. HEAD is a clean revert.
- 53 logged rows in `results.tsv` (17 keeps, 36 discards).
- `ideas.md`: 62 items.
- Submission: `submissions/submission.csv` at val 1,547,351.05.

Loop is in a 19-run discard streak (rows 35–53). Best val_cost has not moved
since row 34 (X8, `8a1c432`). Total improvement is -265,251.13 cost units
(-14.63%) from baseline. The GLS, restart-timing, repair-ordering, arm-weight,
and Or-opt-bandwidth veins are now all confirmed exhausted. The clearest
remaining angles are Z2e (penalty-aware 2-opt accept, never tried cleanly),
X11 (GLS-biased LNS destroy, sidesteps Z5 failure mode), and X6 (segment-
oriented LNS repair). All three are mechanistically distinct from anything
tried in this streak.
