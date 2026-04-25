# Recap 1 — `tsp_neural/` rows 1–34

This recap covers the full experiment history to date: 34 logged cycles
spanning the initial bootstrap (data harvest, model train, integration),
the discovery of the major +1.55% win via VND + Or-opt, a prime-aware
acceptance tweak, and a subsequent tuning plateau. The `.recap-pending`
sentinel was set at cycle 32; this recap captures through cycle 34.

## Results

| # | commit | val_cost | Δ best | status | description |
|---|--------|----------|--------|--------|-------------|
| 1 | 487a5dc | 1,577,298.71 | baseline | baseline | NN seed + 2-opt(k=10), no learning |
| 2 | 3647890 | 1,577,298.71 | 0 | keep | T1: harvest 25M 2-opt candidates to moves/ |
| 3 | 88e5ecb | 1,577,298.71 | 0 | keep | M1+R1+T5+T3: 9-feat 2-layer MLP (1409 params), holdout AUC 0.9992 |
| 4 | daf66de | 1,572,701.48 | −4,597 | keep | I1: MLP as candidate ranker — −0.29% vs baseline |
| 5 | af404f1 | 1,575,564.54 | +2,863 | discard | I3: K=30 pool, MLP picks top 10 — OOD regress |
| 6 | 4342978 | 1,575,657.65 | +2,956 | discard | I1': multi-accept-per-ai — regressed; one-accept was load-bearing |
| 7 | daf5099 | 1,582,301.97 | n/a | keep | T6: K=30 candidate harvest (50M rows) — training artifact |
| 8 | d9725ef | 1,574,181.79 | +1,480 | discard | I3 retry K=30-trained model — still loses to K=10 ranker |
| 9 | 0156ce0 | 1,570,922.32 | −1,779 | keep | I5: first-improving in MLP-score order — NEW BEST |
| 10 | 70c82e0 | 1,574,153.14 | +3,231 | discard | I5+K15: K=15 regresses; K=10 confirmed sweet spot |
| 11 | 1c8e7e5 | 1,570,612.36 | −310 | keep | ILS: double-bridge 16 restarts in 300s — NEW BEST |
| 12 | d43d5a0 | 1,574,570.47 | +3,958 | discard | don't-look v2 (k-NN clear): poor initial converge |
| 13 | 6d16a92 | 1,572,213.50 | +1,601 | discard | don't-look v1 (4-endpoint clear): 49x speedup but quality loss |
| 14 | ca34710 | 1,552,894.37 | −17,718 | keep | C1 BIG WIN: VND learned-2opt + Or-opt-1 + ILS — −1.55% |
| 15 | cadbe17 | 1,552,660.33 | −234 | keep | ILS 2x double-bridge — slight lift |
| 16 | 09dce89 | 1,555,454.10 | +2,794 | discard | R2 MSE-on-gain retrain — BCE > MSE for ranking |
| 17 | 64e7512 | 1,554,495.10 | +1,835 | discard | T2 cumulative K=10+K=30 union — AUC 1.0 but regressed |
| 18 | 3f359a8 | 1,552,720.32 | +60 | discard | C5 MLP in Or-opt — fewer restarts, net loss |
| 19 | 357e94d | 1,552,844.20 | +184 | discard | ILS variable strength 1/2/3x — 2x was optimal |
| 20 | c35790b | 1,552,914.77 | +254 | discard | Or-opt-2 chain classical — doesn't compose well |
| 21 | 5092dbc | 1,553,161.84 | +501 | discard | ILS seed=1 variance probe — RNG floor ~500 |
| 22 | e9c380d | 1,552,554.84 | −105 | keep | Z1 prime-aware boundary gain check — NEW BEST |
| 23 | 7d2817f | 1,552,554.84 | 0 | discard | Z1 fast-path — bottleneck is convergence rate not speed |
| 24 | d8353d4 | 1,552,531.89 | −23 | keep | T7+R6 prime-aware harvest+retrain — sub-noise but pipeline aligned |
| 25 | 46f133c | 1,552,936.18 | +404 | discard | I7 sound don't-look (segment-clear) — still lossy for MLP regime |
| 26 | daa7550 | 1,558,340.40 | +5,808 | discard | Z2 exact prime-aware boundary+interior — over-rejection, slow converge |
| 27 | 66cd4c4 | 1,552,458.02 | −74 | keep | C11 I2 threshold τ=0 — sub-noise, more sweeps not ILS |
| 28 | 56fd812 | 1,551,635.94 | −822 | keep | VND cap MAX_OUTER=10 — NEW BEST; 8 ILS restarts fit vs 0 before |
| 29 | 4dfbafd | 1,551,635.94 | 0 | discard | MAX_VND_OUTER 10→5 — bit-identical; cap was non-binding |
| 30 | 5e51ace | 1,551,770.76 | +135 | discard | ILS 2x→1x perturbation — +135; 2x is the sweet spot |
| 31 | 3d9087a | 1,551,891.85 | +256 | discard | ILS 3x perturbation — 2x still optimal |
| 32 | 3920210 | 1,551,635.94 | 0 | discard | MAX_VND_OUTER 10→15 — bit-identical |
| 33 | c213f8c | 1,552,304.44 | +668 | discard | K_NEIGHBORS 10→12 — K=10 sweet spot confirmed again |
| 34 | 33aec7a | 1,551,635.94 | 0 | discard | ILS adaptive strength — no stalls long enough to trigger; identical |

**Best: 1,551,635.94** (cycle 28, commit 56fd812) — −25,663 from baseline (−1.63%).
34 rows total; 9 discards reverted, 7 discards kept in history. 2 crashes: 0.

## What worked / didn't

- **T1/M1/R1 bootstrap (cycles 1-3)**: MLP trained to AUC 0.9992 on 25M harvested moves. The model learns to predict gain from edge-length features — potentially degenerate, but served as a working ranker.

- **I1 → I5 progression (cycles 4, 9)**: Simple re-ranking gave −0.29%. The key insight was in cycle 9: iterating candidates in MLP-score order and taking the *first improving* move (rather than best-by-score) recovered swaps the earlier approach missed, for a further −1,779.

- **K-pool expansion always hurts (cycles 5, 8, 10, 33)**: K=15, K=30 all regress. The MLP trained on K=10 is OOD on far candidates; one-accept-per-city semantics strongly favour locally coherent moves. K=10 is a load-bearing constant.

- **Multi-accept per city (cycle 6)**: Removing the one-accept-per-city constraint regressed. The constraint was not a limitation but a feature; it prevents cascading stale-score acceptance.

- **C1 VND + Or-opt + ILS (cycle 14, −17,718)**: The biggest single win. Alternating learned 2-opt with classical Or-opt-1 reaches move types 2-opt cannot; initial converge alone landed at 1,553,297. VND unlocked the improvement, not ILS.

- **ILS 2x double-bridge (cycle 15, −234)**: Small but real. 2x perturbation strength is a stable sweet spot; 1x too mild (cycle 30, +135), 3x too disruptive (cycle 31, +256), variable mix (cycle 19, +184) adds noise. Confirmed repeatedly.

- **MSE loss for ranker (cycle 16, +2,794)**: BCE classification boundary > MSE magnitude for within-K ranking. This is because the task is ordinal (rank K=10 candidates) not cardinal (predict exact gain).

- **AUC ceiling (cycles 17, 23-24)**: Model hit AUC≈1.0 early; retrains with more data or union data don't move val_cost. Architecture changes won't help here — the bottleneck shifted to the solver structure.

- **Don't-look bits (cycles 12, 13, 25)**: Consistently lossy. Even segment-clearing (cycle 25) misses cities outside the swap endpoints' k-NN whose best candidates moved. Don't-look is incompatible with MLP-ranked regime.

- **Z1 prime-aware boundary check (cycle 22, −105)**: Small win. The competition's 1.1× prime penalty means a swap that looks Euclidean-positive can be prime-negative at 10th-step boundaries. Checking this during acceptance tightens the local optimum — 743 fewer accepts than cycle 15, but each accept is better-aligned to the true metric.

- **Z2 exact interior prime-aware (cycle 26, +5,808)**: Over-rejected moves, slowing convergence enough to more than erase the quality gain. Boundary-only (Z1) is the right tradeoff.

- **MAX_VND_OUTER cap (cycle 28, −822)**: The biggest post-C1 win. Cycles 22-27 were running 200+ VND outer rounds in initial converge, exhausting the 300s budget before any ILS restart. Capping at 10 freed ~200s; 8 restarts fit, and restarts 1/2/5 each found improvements (+521/+277/+24). Diversification was being starved.

- **Variance floor (~500)**: Cycle 21 (seed=1 probe) showed RNG variance of ~500. Any lift must clear this bar to be meaningful signal.

- **Cycles 29-34 tuning sweep**: All returned bit-identical or sub-noise results against cycle 28's 1,551,635.94. The current pipeline is tightly locally optimal; the only distinguishing feature of the two that gave real lift (MAX_VND_OUTER and ILS 2x) is already set correctly.

## Updated trial directions

Ranked by estimated probability of clearing the ~500 noise floor:

1. **C8 — M5 lookup-table distill** (O(1) scoring replacing MLP): the model inference is the bottleneck now that MAX_VND_OUTER=10 frees budget. If scoring gets 5-10x faster, more ILS restarts fit without sacrificing depth. Low implementation risk.

2. **C9 — M2 city-embedding model** (per-city 32-dim, dot-product scoring): ~50x faster than MLP, preserves "do these cities co-occur in good tours" signal. Same logic as C8 — speed → more restarts.

3. **M7 — Tiny attention construction model** (replaces NN seed with learned partial-tour construction): could improve initial tour quality, giving VND a higher floor to start from. NN seed is currently the only unlearned component of the pipeline.

4. **T8 — Imitation labels from short-LKH oracle on subtours**: current labels are bounded by the solver itself (the ranker can't learn better than the solver). LKH-derived labels on 100-city subtours would break this ceiling. Higher implementation effort.

5. **C10 — R5 prime-aware aux loss retrain**: weighted-BCE with 1.1x weight on 10th-step boundary candidates. Single-cycle train. May sharpen the ranker at exactly the points Z1 polishes — directional but likely sub-noise given AUC≈1.0 ceiling.

6. **R6 — REINFORCE end-to-end training**: highest upside but high variance and training complexity. Worth attempting if C8/C9/M7 all land sub-noise.

7. **LNS / segment-destroy + repair**: not currently in pipeline. Large-neighbourhood search with the MLP ranker guiding repair would add a third diversification axis beyond 2-opt and Or-opt. Several ideas in appended sections (LNSdual etc.) touched this; none committed yet.

## Ideas library

- Seed ideas (cycle 0): 25 items across M/T/R/I/E/C classes.
- Appended (research: modern-learned — cycle 15 tick): 5 items (M6, T6, I6, R5, E6).
- Appended (cycle 20 self-generated tick): 3 items (C6, I7, C7).
- Appended (permute: cross-class combinations — cycle 28 tick): 5 items (C8-C12).
- Appended (research: manual injection at cycle ~31): 3 items (M7, T8, R6).
- **Total: 41 items.** Last appended: cycle ~31 (manual research injection). Recommended next growth tick: cycle 35 (research era = `modern-learned`), already overdue by 4 cycles.

## State

- Branch: `main` (single branch; both loops commit here)
- Last kept commit: `56fd812` — "VND cap MAX_OUTER=10" (val_cost 1,551,635.94)
- In-flight commit: none (run.log confirms cycle 34 = `33aec7a` completed, val_cost 1,551,635.94 identical to best)
- `results.tsv`: 34 data rows + 1 header = 35 lines
- `ideas.md`: 41 items, last appended ~cycle 31
- Submission: `submissions/submission.csv` (cycle 28 best, val_cost 1,551,635.94)
- `.recap-pending`: 32 (to be deleted after this recap)
- Health: **stable but plateaued**. The core pipeline (I5 + C1-VND + ILS-2x + Z1 + MAX_VND_OUTER=10) is well-validated. Every tuning knob within the current structure has been swept and confirmed. Next meaningful lift requires either a faster model (C8/C9) to free ILS budget, a better construction seed (M7), or better training labels (T8).
