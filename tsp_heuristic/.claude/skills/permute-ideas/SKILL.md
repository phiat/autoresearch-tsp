---
name: permute-ideas
description: Read kept ideas from results.tsv, propose cross-class permutations as new pipeline experiments. Use any time the log shows ≥3 kept ideas across different classes (per program.md), when stuck on a plateau, or after a paper-researcher run that introduced new building blocks. Most TSP wins come from combining moves; this skill systematizes that.
---

# permute-ideas

Cross-class combinations of *already-validated* ideas, appended to
`ideas.md` as `X`-class (pipeline) experiments. Closes the loop on a
common failure mode: each idea is good in isolation but the agent
never tries them together.

## When to use

- After every 3+ kept ideas across different classes (per the
  `program.md` permute trigger).
- When you're plateauing — single-class tuning is exhausted but
  combinations haven't been tried.
- After a `paper-researcher` run added new building blocks; permute
  the new entries with established kept ones.
- After `postmortem` flagged a "diversification" or "saturated
  move-set" bottleneck.

## Inputs

None required. The skill reads:
- `results.tsv` (last 30 rows; filter to `status == keep`)
- `ideas.md` (to find next free `X` numbers and avoid duplicates)
- The latest `recap-*.md` (for surprise / non-obvious wins)

Optionally takes a hint from the parent: e.g. "focus on prime-aware
combinations" or "permute LNS variants".

## Procedure

1. **Extract the kept-idea catalogue.** From `results.tsv`, list
   every row with `status == keep` and bucket by class prefix
   (C / L / O / P / Z / D / H / X). Skip any X-class entries already
   in the catalogue (don't permute permutations of permutations).
2. **Generate candidate combinations.** Aim for the 5–8 highest-EV
   pairs. Heuristics for "high-EV":
   - **Different acceptance criteria, same move space.** E.g.
     `2-opt(best-improvement)` × `2-opt(first-improvement)`.
   - **Sequential pipeline composition.** E.g. construction(C) →
     local-search(L+O) → polish(Z) → perturbation(P).
   - **One idea inside another.** E.g. Or-opt L=4,5 *as the repair*
     phase of LNSt; prime-aware swaps *inside* the ILS inner loop.
   - **Hyperparam crosses.** E.g. (k=4) × (LNSt 1.5%) — does the
     k-shrink interact with the LNS destroy fraction?
   - **Avoid pairs already tried.** Cross-check the catalogue's
     descriptions for substring overlap.
3. **For each pair, write one focused 1-line `X` entry.** Lead with
   the action ("apply X inside Y", "compose X then Y"), end with a
   short *why* (what each piece contributes; what failure mode is
   covered). Tag with the next free `X` number.
4. **Append to `ideas.md`** under:

   ```
   ## Appended (permute: <short summary>)

   <one-line intro: e.g. "5 cross-class combinations of recent kept ideas">

   - X11. <pipeline> — <why>
   - X12. <combination> — <why>
   - ...
   ```

   **Append-only.** Do not edit existing entries.
5. Output a 4-6 line confirmation: how many combinations added, the
   single most promising one with a one-line rationale, and whether
   any combinations were intentionally skipped (e.g. tried before).

## Output template

```
permute-ideas summary:

Catalogue: <N> kept ideas across <M> classes (C, L, O, P, Z, D, H).
Generated: <K> X-class combinations, appended to ideas.md.

Top pick: X<N>. <pipeline> — expected to <reason>.
Skipped: <intentional skips, if any>.
```

## What you must NOT do

- Do not modify `solve.py`, `prepare.py`, `program.md`, `results.tsv`,
  or any recap. Output is **only** an append to `ideas.md`.
- Do not permute *discarded* ideas. They were tried and didn't work;
  combining failures is unlikely to produce a win. Exception: if a
  discard's failure mode was *external* to the idea itself (e.g. "I3
  K=30 OOD model" → the K=30 *pool* idea isn't fundamentally bad,
  the model was just trained on K=10).
- Do not generate >8 combinations. The cycle budget for trying them
  is the bottleneck; quality over quantity.
- Do not claim a combination is novel without checking the existing
  ideas.md for substring matches. Duplicates pollute the sampling.
