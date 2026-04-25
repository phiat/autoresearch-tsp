---
name: permute-ideas
description: Read kept ideas from results.tsv, propose cross-class permutations as new combination experiments. Use any time the log shows ≥3 kept ideas across different classes (per program.md), when stuck on a plateau, or after a paper-researcher run that introduced new building blocks. Most neural-guided-search wins come from combining model + integration + engineering ideas; this skill systematizes that.
---

# permute-ideas

Cross-class combinations of *already-validated* ideas, appended to
`ideas.md` as `C`-class (combination/pipeline) experiments.

In `tsp_neural/`, the highest-EV combinations usually cross **model**
choices (M) with **integration** strategies (I) and **engineering**
(E) — e.g. "K=10-trained ranker + I5 hybrid-fallback + don't-look
bits + numba-distilled inference."

## When to use

- After every 3+ kept ideas across different M/T/R/I/E classes
  (per the `program.md` permute trigger).
- When you're plateauing — single-axis tuning is exhausted but
  combinations haven't been tried.
- After a `paper-researcher` run added new building blocks; permute
  the new entries with established kept ones.
- After `postmortem` flagged "saturated move-set" or "model-induced
  myopia" bottlenecks.

## Inputs

None required. The skill reads:
- `results.tsv` (last 30 rows; filter to `status == keep`)
- `ideas.md` (to find next free `C` numbers and avoid duplicates)
- The latest `recap-*.md` (for non-obvious wins)
- `checkpoints/` (which trained models exist + their training data)

Optionally takes a hint from the parent: e.g. "permute around the K=30
ranker checkpoint" or "focus on inference-speed combinations".

## Procedure

1. **Extract the kept-idea catalogue.** From `results.tsv`, list
   every row with `status == keep` and bucket by class prefix
   (M / T / R / I / E / C). Skip any C-class entries already in the
   catalogue (don't permute permutations).
2. **Generate candidate combinations.** Aim for the 5–8 highest-EV.
   Heuristics for "high-EV" in this loop:
   - **Model × integration**: a different checkpoint × a different
     I-strategy. E.g. (K=30-trained model) × (I5 first-improving
     iteration) — rather than only K=30 × I3 (best-by-score) which
     was the original failed pairing.
   - **Integration × engineering**: I5 + don't-look bits, ILS +
     numba-distilled scoring, hybrid-fallback + batched inference.
   - **Stack on the new best**: every C-class should build on the
     current `val_cost` champion (currently I5 / ILS-style), not
     start from baseline.
   - **Cover the model's blind spots**: if the model learned on K=10
     and you have K=30 data, propose using the model only for the
     K=10 inner ring while a heuristic handles the K=10..K=30 outer.
   - **Avoid pairs already tried.** Cross-check by description.
3. **For each pair, write one focused 1-line `C` entry** with the
   *contributing pieces named*. End with a short *why* (what each
   piece contributes; what failure mode is covered). Tag with the
   next free `C` number.
4. **Append to `ideas.md`** under:

   ```
   ## Appended (permute: <short summary>)

   <one-line intro: e.g. "6 cross-class combinations of recent kept ideas">

   - C5. <pipeline: M2 + I5 + E1> — <why>
   - C6. <combination> — <why>
   - ...
   ```

   **Append-only.** Do not edit existing entries.
5. Output a 4-6 line confirmation: how many combinations added, the
   single most promising one with a one-line rationale, and any
   intentional skips.

## Output template

```
permute-ideas summary:

Catalogue: <N> kept ideas across <M> classes (M, T, R, I, E).
Generated: <K> C-class combinations, appended to ideas.md.

Top pick: C<N>. <pipeline> — expected to <reason>.
Skipped: <intentional skips, if any>.
```

## What you must NOT do

- Do not modify `solve.py`, `prepare.py`, `program.md`,
  `results.tsv`, or any recap. Output is **only** an append to
  `ideas.md`.
- Do not permute *discarded* ideas as if they were kept. Exception:
  if a discard's failure mode was *external* (e.g. "I3 K=30 was OOD
  on a K=10 model — but with the K=30 model it might work"), call
  out the failure mode you're addressing.
- Do not propose combinations requiring new dependencies. Allow-list
  is: numpy, pandas, sympy, scipy, numba, torch.
- Do not generate >8 combinations. Cycle budget is the bottleneck.
- Do not claim novelty without grepping `ideas.md` for substring
  duplicates first.
