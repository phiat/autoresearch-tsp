---
name: algo-blueprint
description: Given an algorithm name (e.g. "Lin-Kernighan", "guided local search", "double-bridge LNS"), produce a minimal-implementation plan tailored to this codebase's idiom — specific signatures, where to plug into solve.py, expected runtime cost. Use after picking an idea but before writing code, especially for algorithms with multiple variants in the literature.
---

# algo-blueprint

Bridge a paper/algo name → a focused `solve.py` patch plan.

## When to use

- Just picked an idea like "Z2: real-penalty 2-opt" or "P2: LNS
  destroy-repair" but the literature has 3-5 viable formulations and
  you need to pick one before coding.
- About to implement something the agent has only abstract intuition
  about.
- A `paper-researcher` run dropped a new idea into `ideas.md` and you
  want to size the implementation cost before scheduling it.

## Inputs

An algorithm name or short description. If a paper is referenced (URL
or arXiv ID), fetch it for primary-source detail.

## Procedure

1. Identify the **simplest viable variant** for our context (single
   GPU not used; 197K cities; numba available; 5-min budget). Skip
   academic embellishments that don't translate.
2. Map the algorithm's data-structure needs to what already exists in
   `solve.py` (NN tour, `pos` array, `candidates`, `cKDTree`, etc.).
   Reuse where possible.
3. Sketch the integration:
   - Where in `solve()` does it fit (between which existing phases)?
   - What new functions are needed? Give signatures.
   - What numba-jit candidates does it have?
   - What's the gain formula / acceptance criterion?
4. Estimate:
   - Approximate per-iteration cost vs the 2-opt sweep we already
     have.
   - Expected memory overhead.
   - Where the most likely bug is.

## Output template

```
Algorithm: <name>
Variant chosen: <minimal viable form>, citing <source if any>

Integration in solve.py:
  - Add: <function 1 signature>
  - Add: <function 2 signature>
  - Modify solve(): <where the new piece slots in>

Per-iteration cost:  <ballpark, in same units as existing 2-opt sweep>
Memory:              <ballpark>

Most likely bug:     <one sentence>

Risk-adjusted EV:    <high/medium/low>, <one-sentence why>
Recommend:           <implement / get more data first / skip>
```

## What you must NOT do

- Do not actually edit `solve.py`. This is a planning skill — the
  parent session writes the patch.
- Do not propose multi-week refactors. The 5-min budget per cycle
  rewards small, sharp changes.
- Do not bypass the dep allow-list (numpy, pandas, sympy, scipy,
  numba). If the algorithm requires e.g. `networkx`, flag it as
  "needs human dep approval" and stop.
