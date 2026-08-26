# Employer Profiles and Wave Removal Implementation Plan

**Status:** Implemented (2026-08-26)

**Goal:** Split the mixed `work` profile into `fsp` and `wsh`, remove Wave from
live desired state, make `glab` an include, and prune owned managed files that
left the current configure plan.

**Approved design:**
[Employer profiles and Wave removal design](../specs/2026-08-26-employer-profiles-and-wave-removal-design.md)

This file is the execution record for that design. Step-by-step task recipes
were used during implementation and are not kept here.

## What shipped

- `work` is deleted. `fsp` and `wsh` each extend `default` only. There is no
  `work` alias. Daily command is `./bootstrap --profile wsh`.
- Wave is gone from applications, configuration, `skip wave`, live docs, and
  CI. Wave.app is not uninstalled. `terminal/wave/settings.json` is deleted.
- `glab` is an opt-in include (`--include glab`) on `default`. `libmagic` and
  `awscli` are `fsp`-only.
- `zprofile-work` is `wsh`-only. Source and destination stay
  `dotfiles/shell/zprofile.work` → `~/.zprofile.work`.
- Cursor Bedrock overlay and Atlassian MCP are `fsp`-only. Resource ids and
  `settings.work.json` are unchanged.
- `run_configure` validates with `plan`, applies the current spec set, then
  prunes owned `StateStore` records whose ids left that set. Digest mismatch
  leaves the file and the record. Per-spec `apply` does not prune. Empty spec
  sets prune every unprotected owned record.
- GitLab plan/doctor actions run only when `glab` is selected. AWS runs only
  for `fsp`. GitLab failure uses the same WARNING / `not authenticated`
  pattern as GitHub.
- CI runs `./bootstrap plan --profile wsh`.
- `using-gitlab` stays on `default`. The tracked-tree `plato` import guard is
  unchanged. Historical `docs/superpowers/` files other than this plan and
  the design were not rewritten.

## Follow-ups (not this branch)

- `.jj/` being gitignored still hides colocated Jujutsu from tools that only
  inspect git-visible files.
