---
name: using-uv
description: >-
  Use when working in a Python repository that has selected uv
  (`pyproject.toml`, `uv.lock`, or uv workspaces) for installs, syncs, locks,
  dependency edits, or running project tools via `uv run`.
---

<!-- markdownlint-disable -->

# Using uv

Procedural companion for repositories that selected uv. Dependency *policy*
lives in the bundled projection at
[references/dependency-management.md](references/dependency-management.md) —
read that file when intent, lockfile, or workspace rules are needed. Do not
treat this skill as a second dependency-management standard.

## Preconditions

1. Confirm the repository selected uv: look for `pyproject.toml` with uv-oriented
   configuration, a committed `uv.lock`, and/or a uv workspace layout.
2. If another manager is clearly selected (Poetry, Pipenv, plain pip +
   requirements, etc.), stop and follow that manager — do not invent a uv
   workflow.
3. If uv is required here but `uv` is not available on PATH, stop and tell the
   user to install uv. Do not invent pip/poetry substitute workflows unless the
   repository selected them.

## Core operations

Prefer these shapes; verify flags against current primary uv documentation when
behavior is version-sensitive.

| Intent | Command pattern |
|--------|-----------------|
| Run a project tool / script | `uv run …` (prefer over activating a venv by hand) |
| Add a dependency | `uv add …` (use the appropriate dependency group) |
| Remove a dependency | `uv remove …` |
| Sync the environment to the lockfile | `uv sync` |
| Refresh / rewrite the lockfile | `uv lock` (after intentional declaration changes) |
| Workspace-aware work | Use uv workspace commands implied by the repo’s workspace members |

Recognize workspaces from executable configuration (for example workspace
member tables in `pyproject.toml`), not from directory guesswork.

## Policy handoff

When deciding *whether* to add a dependency, which group it belongs in, whether
to commit lockfile churn, or how workspaces should behave, open
`references/dependency-management.md` in this skill tree and apply it. Keep
local activation trivia and cache repair out of normative answers unless the
user asked for troubleshooting.

## Boundaries

- Do not restate the dependency-management standard inline.
- Do not mix package managers in one change.
- Do not migrate auth, tokens, or secrets as part of environment setup.
