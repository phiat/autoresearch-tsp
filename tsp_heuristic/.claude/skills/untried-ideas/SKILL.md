---
name: untried-ideas
description: Enumerate ideas in ideas.md that haven't been tested yet (no matching row in results.tsv). Categorizes by class and provenance (seed / cycle-N append / research / permute / manual). Use when the loop is on a long discard streak, when stuck-protocol triggers, or any time you're picking the next experiment and want to avoid micro-tweaking saturated veins.
---

# untried-ideas

Quick reality check: which ideas in `ideas.md` have NOT been tried
yet? Helps the agent route to fresh-mechanism ideas instead of
re-tuning a saturated vein.

## When to use

- After the **stuck protocol** triggers (5+ consecutive discards) —
  pair with `postmortem` to pick the right *kind* of new idea.
- Anytime the next experiment is being chosen and you suspect you've
  been micro-tweaking the same vein.
- Before invoking `paper-researcher` — confirms what's already in
  the pool so research doesn't dup-add.

## Procedure

1. Read `ideas.md`. Parse all idea bullets matching the class-prefix
   pattern (e.g. `- L10.`, `- X13.`, `- C14.`, etc).
2. Read `results.tsv`. Extract the `description` column.
3. For each idea, check if its identifier (e.g. `L10`, `X13`) or
   distinctive substring appears in any row's description. If yes,
   count as tested (regardless of keep/discard).
4. Bucket the untried ideas by:
   - **Class** (C / L / O / P / Z / D / H / X for heuristic;
     M / T / R / I / E / C for neural)
   - **Provenance**: `seed` (original cycle-0 ideas), `growth-cycle-N`,
     `research-<era>`, `permute`, `manual-injection`.
5. Print a structured report:

```
untried-ideas report:

By class (untried count):
  C: 2   L: 1   O: 0   P: 1   Z: 1   D: 1   H: 0   X: 4

By provenance:
  seed:                  3
  growth-cycle-N:        1
  research-classical:    2  (L10, X13, P6)
  research-domain:       0  (all tried)
  permute:               4  (X8c, X9 ... )
  manual-injection:      3

Recommended next pick (highest novelty × lowest collision):
  L10 — Sequential 3-opt LK chain (depth-3) with α-nearness
        [research-classical, src: Lin & Kernighan 1973]
        Untried since manual injection at cycle 47.
```

6. Return that report to the parent session as the skill's output.

## Implementation note

A small parser is fine — `grep "^- [A-Z][0-9]" ideas.md` for ids,
match against `cut -f5 results.tsv` for descriptions. No need for a
big script; an inline `awk`/`python` one-liner works.

## Output

The structured report from step 5, followed by:

```
Recommendation: invoke <next idea id> as the next experiment.
Rationale: <one-line>.
```

## What you must NOT do

- Do not modify `ideas.md` from this skill — it's read-only here.
  (Adding new ideas → `paper-researcher` or growth-tick or
  `permute-ideas`.)
- Do not declare an idea "tried" based on substring overlap alone if
  the description was clearly different — false positives will hide
  good ideas.
- Do not score ideas by expected EV — that's the agent's job. This
  skill just enumerates and bucketizes.
