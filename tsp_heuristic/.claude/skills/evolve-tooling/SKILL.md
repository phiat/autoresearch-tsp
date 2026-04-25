---
name: evolve-tooling
description: Update or extend the loop's own .claude/ tooling — skills, subagents, slash commands, hooks — based on observed friction or new opportunities discovered during experimentation. Use when a recurring chore could be automated, when an existing skill keeps producing the wrong shape of output, when a hook fires too aggressively or not enough, or when a new class of recurring need emerges (e.g. "I keep wanting to compare three runs at once, not two").
---

# evolve-tooling

The loop's tooling (skills, subagents, hooks, slash commands) is itself
fair game for iteration. This skill is the agent's authorised path to
modify `.claude/` based on what it has learned.

## When to use

- A recurring step in the loop is being done by hand and feels mechanical.
- A skill exists but its output template doesn't match what the situation
  actually needs.
- A hook is producing false positives (blocking valid actions) or false
  negatives (missing real failure modes).
- A new pattern is emerging across multiple cycles that deserves its own
  skill or subagent (e.g. "I keep doing the same 3-step prime-aware
  analysis manually" → factor it into a skill).
- The literature or a `paper-researcher` finding suggests a new
  capability the loop should have.
- After a `postmortem` identifies a process bottleneck (not a code one).

## Inputs

A short statement of:
- The friction observed (with examples — at minimum, two cycles where
  it bit), OR the new opportunity.
- Which kind of tooling change you're proposing:
  - **new skill** under `.claude/skills/<name>/SKILL.md`
  - **new subagent** under `.claude/agents/<name>.md`
  - **new slash command** under `.claude/commands/<name>.md`
  - **new or updated hook** under `.claude/hooks/<name>.sh` and
    `.claude/settings.json`
  - **edit to an existing one of the above**

If the proposed change is small (clarify a description, fix a hook
that misfires), do it directly. If it's structurally new (a whole new
subagent), explain the design first and invoke `algo-blueprint`-style
sketching before writing the file.

## Procedure

1. **Diagnose**: write 2-3 sentences naming the friction and citing
   evidence (cycle numbers, commit hashes, log lines). Vague friction
   ("things feel slow") is not enough — find the concrete miss.
2. **Decide on the smallest tool that fixes it.** Order of preference:
   edit existing → new skill → new subagent → new hook. Hooks are
   expensive to debug — only add when the rule must be enforced
   structurally.
3. **Write the change** using the existing files as templates:
   - Skills: frontmatter (`name`, `description`) + body sections like
     "When to use", "Procedure", "Output template", "What you must
     NOT do". See `profile-solver`, `compare-runs` for shape.
   - Subagents: frontmatter (`name`, `description`, `tools`, `model`)
     + system prompt. See `recap-writer`, `paper-researcher`.
   - Slash commands: frontmatter (`description`) + a short prompt
     body that delegates to a subagent or skill. See `recap.md`.
   - Hooks: shell script in `.claude/hooks/`, registered in
     `.claude/settings.json` under `PreToolUse` / `PostToolUse` /
     `Stop` etc. with the right `matcher`. Always exit 0 unless the
     intent is to block (exit 2). Never crash the harness.
4. **Test** if possible: for a hook, run it against a synthetic JSON
   payload (`echo '{"tool_input": {...}}' | bash <hook>`); for a
   skill or subagent, dry-run the procedure against current state
   without committing artifacts.
5. **Document the change inline in the tool's description.** A new
   skill's description must be specific enough that the model decides
   to invoke it without prompting.
6. **Update `program.md`** if the change adds a new capability the
   loop's main instructions need to mention. Append-only — do not
   rewrite older guidance.
7. **Log the change** by committing it to the experiment branch with
   `meta: <one-line description of tooling change>` (the `meta:`
   prefix distinguishes it from `exp:` commits and means recap-writer
   should include it under "Tooling changes" not "Results").

## Output template

```
Friction observed:
  <2-3 sentences with evidence>

Proposed change:
  <type> <name> — <one-line summary>

Why this shape (smallest tool that fixes it):
  <one paragraph>

Files written/edited:
  - <path>
  - <path>

Validation:
  <what you ran to confirm it works>

Commit:
  meta: <short description>
```

## What you must NOT do

- Do not modify the **frozen substrate**: `prepare.py`, the metric,
  the time budget, the dep allow-list, the keep/revert mechanic, the
  `results.tsv` schema. Those are guarantees the experiment loop
  rests on.
- Do not delete existing skills, subagents, hooks, or commands. If
  one is wrong, *edit* it (with an evidence-cited justification). The
  history of the tooling is itself information.
- Do not add a new subagent or hook on a single data point. Wait for
  the same friction to bite at least twice. Premature tool-building
  is just a different flavour of premature abstraction.
- Do not loosen `block-frozen-edits.sh` or `block-dep-install.sh`.
  Those exist precisely to survive moments of agent confusion. Adding
  exceptions to them is a human decision.
- Do not modify this skill file (`evolve-tooling/SKILL.md`) in a way
  that weakens its constraints. Strengthening is fine.

## Anti-patterns to watch for

- **Tooling sprawl**: 12 skills no one invokes. Better: 3 skills, each
  used regularly. If a skill hasn't been invoked in 20 cycles, propose
  removing it (but document why before deletion — see prior rule).
- **Hook fragility**: hooks that depend on exact path conventions or
  shell quoting. Use `$CLAUDE_PROJECT_DIR` and absolute paths. Always
  test with both empty and weird stdin.
- **Subagent bloat**: subagent system prompts that re-explain the
  whole project. They share no context with the parent — necessary
  context only, no rambling.
- **Description drift**: a skill's `description:` frontmatter says
  one thing, the body does another. The model picks tools by
  description; keep them honest.
