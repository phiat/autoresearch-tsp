# Agent Instructions

## Sub-projects

- **`tsp_research/`** — autonomous research loop for the Kaggle Santa
  2018 TSP. Has its own `AGENTS.md`, `program.md`, and a `.claude/`
  with skills, subagents, slash commands, and hooks. If you're
  driving the loop, work from inside `tsp_research/` and read its
  `AGENTS.md` first.
- **`autoresearch/`** — vendored upstream (karpathy/autoresearch),
  its own git repo. Reference only; do not modify.

## Working alongside a live loop session

There is often a separate Claude Code session running the autonomous
loop in `tsp_research/` on branch `tsp/<tag>`. It uses the same
working tree as you. Disrupting its view of git state confuses it.

**Rules when the loop is live:**

- **Do not switch branches** in this working tree. The loop watches
  `git status` / `git log`, and a branch flip out from under it
  triggers "I'm somewhere I didn't expect, let me investigate"
  detours that waste cycles. If you must work on `main`, do it in a
  worktree (`git worktree add`).
- **Do not push to `main` mid-cycle.** The loop occasionally merges
  `main` into its experiment branch; an unfamiliar `main` commit
  arriving from nowhere reads to the loop as a mystery commit it
  needs to investigate. If you have to update `main`, prefer batching
  changes and timing the push between cycles, or pre-announce the
  commit in the loop's session.
- **Do not commit on the loop's branch.** The loop reverts via
  `git reset --hard HEAD~1` for discarded experiments — any commit
  you slip in on top can be wiped. (It's still in the reflog, but
  it's noise.) Stage `meta:` tooling changes on `main` and let the
  loop pick them up via its own merge.
- **If you must intervene**, send a one-line message in the loop's
  session explaining what happened (e.g. *"that commit on main is
  yours — meta: chore, safe to merge or ignore"*). Don't reach into
  the loop's branch from outside.
- **Editing files outside `tsp_research/`** is generally safe; the
  loop only watches git and its own working dir. But edits inside
  `tsp_research/` can show up in the loop's `git status` and look
  like uncommitted experiment changes — avoid unless coordinating.

Lesson learned the hard way during the apr25 session: a switch to
`main` + commit + push, done while the loop was between cycles,
caused the loop to spend a turn investigating an unfamiliar HEAD on
its own branch when it next ran `git status`.

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
