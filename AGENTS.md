# Agent Instructions

## Sub-projects

- **`tsp_heuristic/`** — classical heuristic-search loop for the Kaggle
  Santa 2018 TSP. Has its own `AGENTS.md`, `program.md`, and `.claude/`
  toolset.
- **`tsp_neural/`** — neural-guided local search loop on the same task.
  Has its own `AGENTS.md`, `program.md`, `.claude/` (with an extra
  `train-policy` skill), and PyTorch in deps.
- **`autoresearch/`** — vendored upstream (karpathy/autoresearch),
  its own git repo. Reference only; do not modify.

Both loops commit to **`main`** from this single working tree. The
file-level isolation comes from their separate subdirs; neither loop's
`solve.py` collides with the other's. The `revert` recipe in each
`justfile` uses `git revert HEAD --no-edit` (creates a revert commit
on top, doesn't rewrite history) so a discard from one loop never
wipes the other's commits. See the outer `README.md` for setup.

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

## Running two loops in parallel

`tsp_heuristic/` and `tsp_neural/` both run in this single working
tree, both on `main`, with two separate Claude Code sessions — one
in each subdir. There are **no per-loop branches and no worktrees**
(an earlier iteration tried that; the file-level isolation from the
subdirs plus the `git revert`–based discard recipe is enough).

Coordination rules:

- Both loops are on `main`. Don't `git checkout` to anything else
  from either session.
- `meta:` commits go on `main` and both agents see them in `git log`
  immediately (no merge step needed since neither is on a branch).
- `compare-runs` across the two paradigms works trivially — both
  trees are visible from a single `git log`. The data files
  (`results.tsv`, `moves/`, `checkpoints/`) are per-subdir-local;
  bring artefacts together if you want a joint analysis.
