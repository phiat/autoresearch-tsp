# Agent Instructions

## Sub-projects

- **`tsp_heuristic/`** — classical heuristic-search loop for the Kaggle
  Santa 2018 TSP. Runs on a `heuristic/<tag>` branch in this working tree.
  Has its own `AGENTS.md`, `program.md`, and `.claude/` toolset.
- **`tsp_neural/`** — neural-guided local search loop on the same
  task. Designed to run in a **separate git worktree** on a
  `neural/<tag>` branch so it can run in parallel with
  `tsp_heuristic/` without `HEAD` conflicts. Has its own
  `AGENTS.md`, `program.md`, `.claude/` (with an extra `train-policy`
  skill), and PyTorch in deps.
- **`autoresearch/`** — vendored upstream (karpathy/autoresearch),
  its own git repo. Reference only; do not modify.

When both loops are live, **two Claude Code sessions** are running —
one in this working tree's `tsp_heuristic/`, one in the worktree's
`tsp_neural/`. They share `.git/` (branches are mutually visible) but
never share `HEAD`. See the outer `README.md` for worktree setup.

## Issue tracking

This project uses **bd** (beads) for issue tracking. Run `bd prime` for full workflow context.

## Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work atomically
bd close <id>         # Complete work
bd dolt push          # Push beads data to remote
```

## Non-Interactive Shell Commands

**ALWAYS use non-interactive flags** with file operations to avoid hanging on confirmation prompts.

Shell commands like `cp`, `mv`, and `rm` may be aliased to include `-i` (interactive) mode on some systems, causing the agent to hang indefinitely waiting for y/n input.

**Use these forms instead:**
```bash
# Force overwrite without prompting
cp -f source dest           # NOT: cp source dest
mv -f source dest           # NOT: mv source dest
rm -f file                  # NOT: rm file

# For recursive operations
rm -rf directory            # NOT: rm -r directory
cp -rf source dest          # NOT: cp -r source dest
```

**Other commands that may prompt:**
- `scp` - use `-o BatchMode=yes` for non-interactive
- `ssh` - use `-o BatchMode=yes` to fail instead of prompting
- `apt-get` - use `-y` flag
- `brew` - use `HOMEBREW_NO_AUTO_UPDATE=1` env var

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->

## Running two loops in parallel (worktrees)

When `tsp_heuristic/` and `tsp_neural/` are both live, each runs in its
own **git worktree** (sibling working directories sharing the same
`.git/`), so neither flips the other's `HEAD`. Sessions for the two
loops are completely independent and never see each other's working
tree.

The "Working alongside a live loop session" rules above apply
**per-worktree**. Additionally:

- Don't reach across worktrees with `git checkout` or branch ops.
- `meta:` commits affect both loops; batch them, land on `main`, let
  each loop's agent merge `main` into its branch on its own schedule.
- `compare-runs` across worktrees works (branches mutually visible)
  but the data files (`results.tsv`, `moves/`, `checkpoints/`) are
  per-worktree-local — bring artefacts to one place if you want a
  joint analysis.

See the outer `README.md` "Running both loops in parallel" section for
the worktree setup commands.
