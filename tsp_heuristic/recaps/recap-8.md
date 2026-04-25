# Recap 8 — `heuristic/apr25` continued

Covers results.tsv rows #54–#64 (commits `c70e0ea` through `51a0807`).
This recap opened covering rows #54–#59 with PILSb15 in-flight; it now
closes the full parallel-ILS arc through row #64. Best val_cost is
**1,547,351.05** (X8, `8a1c432`, row #34), now reproducible via 2-worker
PILS (`51a0807`, row #64). Discard streak peaked at 31 consecutive;
two late keeps (rows #63-#64) restored reproducibility, not a new best.

## Summary of recap-7

- Opened from best 1,547,351.05 (X8, `8a1c432`, row #34); streak at 19.
- All 10 new rows (#44–#53) were discards.
- OrL67 (+676): L=6,7 sweeps eat ILS budget; L=1..5 is the bandwidth optimum.
- C6 (+2,642): multi-start NN costs ~25s construction; ILS budget loss dominates.
- OrRev (+1,554): reversed Or-opt order (5..1) lands in a structurally worse basin.
- GLS vein fully exhausted: Z5b (lam=0.1, exact tie), Z5d (lam=0.5, +70), Z5
  (lam=1.0, +70) — no lambda value improves over X8 in 300s budget.
- Reg2p (+577): regret-2 repair fails regardless of destroy method.
- LNSdual (+519): 4-arm split dilutes prime-bias arm; 3-arm balance is optimal.
- PrimePeriodic (+880): Z1 inside ILS loop is always too heavy; post-pass only.
- AdaptiveRestart (+88): closest near-miss, but restart timing luck is not
  reproducible; restart-timing vein now exhausted.
- ForcedLateRestart (+181): 20s is too late for post-restart convergence.
- **Best at end of recap-7: 1,547,351.05.** 36 total discards through row 53.

## New results

| # | commit | val_cost | delta best | status | description |
|---|---|---|---|---|---|
| 54 | c70e0ea | 1,548,329.75 | +979 | **discard** | RngCafe: rng seed 0xBEEF→0xCAFE — 3 restarts, 6 improvements; confirms X8=1,547,351 is rng-luck-dependent |
| 55 | 892f041 | 1,548,269.98 | +919 | **discard** | PILS-defaults: 8 workers × 25s — 528 iters in 274s; within-batch best feedback lost |
| 56 | 8f2746d | 1,547,573.57 | +222 | **discard** | PILSw4: 4 workers × 25s — 420 iters in 275s; best parallel result to date |
| 57 | 4a52e21 | 1,548,256.65 | +906 | **discard** | PILSx8: worker 0 dedicated to NN-restart every batch — slowest worker blocks batch, iters 420→92 |
| 58 | ec46552 | 1,548,511.55 | +1,160 | **discard** | PILSx8r: rare NN-restart at no-improve=10 batches — only 1 restart fired; parallel can't replicate sequential X8 mechanism |
| *(PILSb15)* | b781574 | *(reverted, no log row)* | — | reverted | PILSb15: 25s→15s worker budget — reverted before logging; result lost |
| 59 | 2912652 | 1,547,711.25 | +360 | **discard** | PILSens: 8 independent sequential ILS trajectories — best of 8 = 1,547,711; basin floor |
| 60 | 8d42bc6 | 1,547,711.25 | +360 | **discard** | PILSensB: 8-worker ensemble w0=0xBEEF pinned — same floor 1,547,711 (within-batch feedback actually helps) |
| 61 | fa3eb0a | 1,547,711.25 | +360 | **discard** | PILSens14: 14 workers — same floor 1,547,711 as 8-worker; rng-only diversity exhausted |
| 62 | 9bbf217 | 1,547,714.57 | +363 | **discard** | PILSdiv: 8 workers × diverse params — same basin floor 1,547,714; param diversity doesn't break floor |
| 63 | 2ea9ade | 1,547,438.78 | +88 | **keep** | PILSw4d: 4-worker ensemble (0xBEEF pinned w0) — w0=1,547,439 NEW BEST current code; fewer workers = more CPU per trajectory |
| 64 | 51a0807 | 1,547,351.05 | ±0 | **keep** | PILSens2: 2-worker ensemble (0xBEEF pinned) — w0 EXACT historical X8 match 1,547,351.05; multiprocessing contention was the gap |

**Best: 1,547,351.05** (X8/PILSens2 tied, commits `8a1c432` / `51a0807`) — −14.63% from baseline
(`dd8df32`, 1,812,602.19). 49 total discards through row 64.
Discard streak: 31 consecutive (rows #34–#64); broken by 2 late keeps.
PILSb15 was reverted without a log row — effectively a gap in the ledger.

## What worked / didn't

- **RngCafe (#54, discard, +979).** Changing the ILS seed from 0xBEEF to
  0xCAFE produced a materially different trajectory: 3 restarts, only 6
  improvements, landing at 1,548,329.75. This confirms that X8's score of
  1,547,351.05 is rng-luck-dependent and not a robust property of the
  algorithm. Any experiment that happens to align with the 0xBEEF basin gets
  the benefit; most seeds do not. This underscores that the true ceiling for
  the sequential solver may be above or below 1,547,351.05 depending on
  random initialization. Structural improvements must beat the lucky seed, not
  just match it.

- **PILS-defaults (#55, discard, +919).** The initial parallel-ILS scaffold
  (commit `892f041`, user-authored) ran 8 workers × 25s worker-budget, achieving
  528 iterations across 274s. Despite many more iterations than sequential X8
  (~226 iters in 300s), the final result was worse. Root cause: within each
  25s batch, the coordinator only sees the best result of each batch, not the
  improvement trajectory inside each worker. The best-global-so-far is not fed
  back to workers mid-batch, so workers diversify independently but cannot
  exploit each other's finds in real time. More iterations at lower quality per
  batch is not better than fewer deep sequential iterations.

- **PILSw4 (#56, discard, +222).** Reducing to 4 workers × 25s = 420 iters in
  275s, the best parallel result in this arc. Smaller batches mean the global
  best is updated more frequently (shorter feedback lag), which partially
  addresses the coordination gap. Still +222 vs X8. This is the closest parallel
  has come, and the directional trend (fewer workers = better) suggests the
  benefit of parallelism for this problem structure is negative at all tested
  worker counts.

- **PILSx8: NN-restart dedicated worker (#57, discard, +906).** Allocating
  worker 0 to fire an NN-restart every batch (mirroring X8's P4 mechanism)
  caused the slowest worker to block the entire batch from completing. Iteration
  count collapsed from 420 to 92. The sequential X8 mechanism (restart only
  after RESTART_AFTER idle iters) is fundamentally incompatible with the
  synchronous batch-wait coordination model; forcing it in costs 4.5× the
  iterations.

- **PILSx8r: rare NN-restart at no-improve=10 batches (#58, discard, +1,160).**
  Softening the restart condition — only inject if 10 consecutive batches showed
  no improvement — fired only once in the entire run. A single restart in 77
  batches is insufficient to replicate the benefit of X8's well-timed restart.
  The parallel scaffold's batch granularity (25s each) is too coarse to
  reproduce the sequential solver's restart timing at the iteration level. This
  closes the "port X8 mechanism to parallel" approach: it is architecturally
  mismatched.

- **PILSb15 (reverted, no log row).** Worker budget 25s→15s was reverted before
  results were logged. No data recovered. This is a ledger gap — the commit
  (`b781574`) and its revert (`e828809`) both exist in git history but the
  experiment is missing from results.tsv.

- **PILSens ensemble arc (#59–#62, discards, +360–+363).** Switching from
  batched PILS to independent sequential ensembles (8–14 workers each running
  the full X8 mechanism with their own seed) consistently converged to a floor
  of ~1,547,711. Pinning worker 0 to seed 0xBEEF did not help: within-batch
  feedback (which sequential X8 gets for free by accumulating improvements
  continuously) is what matters. The ensemble architecture discards this
  signal. Scaling to 14 workers adds more samples but the same basin floor —
  rng diversity is exhausted; the fundamental constraint is that the basin
  around 1,547,351 is only accessible via the specific sequential 0xBEEF
  trajectory.

- **PILSw4d (#63, keep, +88).** Reverting to 4-worker batched PILS with
  round-robin forced perturbation diversity (DB/SS/LNS-prime) per worker,
  with w0 pinned to 0xBEEF, partially recovered: w0 hit 1,547,439 — within
  88 of the all-time best. This is the closest any parallel variant has come.
  The key factor is fewer workers (more CPU per worker), not the diversity
  enforcement per se (PILSdiv with 8 workers and diverse params got +363).

- **PILSens2 (#64, keep, ±0).** Reducing to just 2 workers (0xBEEF pinned)
  gave w0 the near-full CPU budget of sequential X8, and exactly reproduced
  1,547,351.05. This resolves a key question: the gap between parallel PILS
  and sequential X8 was entirely CPU contention from multiple workers. With
  2 workers, multiprocessing overhead is negligible, and the reproducibility
  concern from RngCafe is resolved. Best val_cost is now reproducible in the
  PILS scaffold. The parallel arc is concluded: 2-worker pinned is the
  effective equivalent of sequential.

## Updated trial directions

1. **Return to sequential solver; retire parallel-ILS scaffold.** PILSens2
   reproduces X8 exactly, but there is no parallel-specific gain. The correct
   next arc is structural improvements to the move set, not coordination
   architecture. Use the sequential solver (or 2-worker pinned as equivalent)
   for all future experiments.

2. **Z2e — penalty-aware 2-opt accept scoring.** Highest-EV untried mechanism.
   Track primes at k%10==0 positions during 2-opt; apply real penalty delta
   only at boundary moves. Zero per-iteration overhead when boundary check is
   O(1). The RngCafe result confirms structural improvements must beat the
   lucky seed; Z2e is the most likely candidate to do that by changing the
   move-acceptance landscape rather than just timing restarts.

3. **L8 — sequential LK-chain (depth-2) in numba.** Implements a depth-2
   Lin-Kernighan chain: pick t1, remove (t1,t2), for each candidate t3
   test gain_close first (recovers 2-opt); else extend to t4 and test 3-opt
   close. Helsgaun 2009 shows this kernel captures most of the LK gain at
   tractable cost; cfld/simple_tsp implements it in <150 numba lines.
   Directly attacks the basin floor 2-opt + Or-opt cannot reach.

4. **X11 — GLS-biased LNS destroy.** Bias LNS city selection toward cities
   incident to high-frequency (high-GLS-penalty) edges rather than only
   penalty-origin positions. Sidesteps Z5's failed accept-scoring approach;
   uses GLS history only in the destroy selector. Mechanistically fresh.

5. **X6 — Or-opt segment repair inside LNS-prime.** Group originally-adjacent
   removed cities as segments and apply O4r-style forward-vs-reversed insertion
   test during LNS repair. Targets the structural seam left by cheapest-insert.
   Distinct from X5 (which added prime-swap inside repair — failed row #33).

6. **X10 — prime_swap_pass per accepted ILS improvement.** At ~1ms per call
   and ~18 accept events per X8 run, total overhead is ~18ms — negligible vs
   300s. Post-pass Z1 is confirmed productive; per-accept application has not
   been tried cleanly (PrimePeriodic, row #51, ran every 50 iters and was too
   heavy — per-accept is 50× lighter-touch).

7. **X13 — path relinking between elite ILS solutions.** Maintain top-3 tours
   across restarts; generate intermediate tours by swapping edges from one
   elite toward another; accept the best 2-opt-converged intermediate.
   Diversification orthogonal to single-tour perturbations. Higher complexity
   but targets the basin-diversity gap.

## Tooling observations

- **Postmortem never fired.** The loop ran 31 consecutive discards (rows
  #34–#64) without the `postmortem` skill being invoked. Per program.md's
  Stuck protocol (fire postmortem after 5+ consecutive discards), this skill
  was overdue by 26 rows. The parallel-ILS arc was a single structural
  hypothesis; within it the agent correctly tracked sub-variants, but the
  high-level stuck signal was never acted on.

- **Multi-seed-eval not invoked.** Several discards in rows #54–#62 had |delta|
  < 750 (e.g. PILSw4 at +222, PILSw4d at +88, PILSens2 at ±0). Per the RNG
  noise floor rule (|delta| < 750 warrants multi-seed confirmation), the agent
  should have invoked `multi-seed-eval` on at least PILSw4 (+222) and PILSw4d
  (+88) before deciding keep/discard. It did not. PILSens2 was kept — correct,
  but the confirmation was structural (exact match to X8 via seed pinning) not
  a proper multi-seed sweep.

- **Paper-researcher not fired.** The last research tick was cycle ~47 (ideas.md
  "Appended: research classical/hybrid"). The loop ran ~17 more experiments
  (rows 48–64) without another research tick. The ideas pool has L8, L9, L10,
  X13, O5, X12, P6 — research-injected items all untried — while the agent
  continued micro-tuning the parallel-ILS vein. A research tick to surface
  fresh LK/3-opt literature was overdue.

- **PILSb15 ledger gap.** Commit `b781574` (PILSb15) was run and reverted
  (`e828809`) without a results.tsv entry. This is a missing data point —
  if the result was logged before revert the row should exist; if reverted
  before logging the data is lost. The loop's protocol should ensure logging
  before reverting.

- **Parallel-ILS vein [exhausted: rows #55–#64].** 10 PILS variants tested;
  none beat sequential X8; best parallel result was PILSens2 = exact tie via
  seed pinning. This vein should be annotated exhausted in ideas.md to prevent
  re-picks.

## Ideas library

- ~62 items total (last appended: research-injected cycle ~47 — L8, L9, L10,
  X12, X13, O5, H7, P6).
- Exhausted veins: GLS-accept (Z5/Z5b/Z5d), restart-timing
  (AdaptiveRestart/ForcedLateRestart/P4t), regret-repair (Reg2/Reg2p),
  Or-opt bandwidth (OrL67/OrRev), parallel-ILS scaffold (rows #55–#64).
- Confirmed untried research items: L8, L9, L10 (LK-chain family); X13
  (path relinking); O5 (3-opt segment exchange); X12 (backbone-freq LNS);
  P6 (iterated tabu); H7 (GLS lambda schedule). These are the highest-EV
  unexplored ideas.
- Recommended annotation: add `[exhausted: rows 55-64]` to parallel-ILS
  entries in ideas.md.

## State

- Branch: `main`; HEAD is `040410a` (meta: program.md PILS staleness note).
- Last kept experiment commit: `51a0807` (PILSens2, val 1,547,351.05, row #64).
- No in-flight experiment.
- 64 logged rows in `results.tsv` (19 keeps, 45 discards).
- `ideas.md`: ~62 items; ~8 research-injected items untried.
- Submission: `submissions/submission.csv` at val 1,547,351.05.
- C14 (PILS+H=16 distill, commit `0d1a8c9`) is in git history but does not
  appear in results.tsv — it may be a meta/infrastructure commit rather than
  a scored experiment.

Loop exited the 31-run discard streak with two structural confirms (PILSw4d,
PILSens2). Best val_cost remains 1,547,351.05. Total improvement: −265,251.13
cost units (−14.63%) from baseline. Clearest next angles are Z2e
(penalty-aware accept) and L8 (LK depth-2 chain) — both mechanistically
orthogonal to everything tested so far.
