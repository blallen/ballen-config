---
name: using-uv
description: >-
  Use when working in a Python repository that has selected uv
  (`pyproject.toml`, `uv.lock`, or uv workspaces) for installs, syncs, locks,
  dependency edits, or running project tools via `uv run`.
---

# Using uv

Procedural companion for repositories that selected uv. Do not treat this skill
as a second dependency-management standard.

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
| --- | --- |
| Run a project tool / script | `uv run …` (prefer over activating a venv by hand) |
| Add a dependency | `uv add …` (use the appropriate dependency group) |
| Remove a dependency | `uv remove …` |
| Sync the environment | `uv sync` checks and updates the lockfile as needed, then exactly syncs the environment by default |
| Sync with a current lockfile required | `uv sync --locked` disables automatic lock updates and errors if the lockfile is not current |
| Sync without checking lockfile freshness | `uv sync --frozen` uses the existing lockfile without checking freshness |
| Create or refresh the lockfile | `uv lock`; existing locked versions are preferred |
| Intentionally upgrade broadly | `uv lock --upgrade` |
| Workspace-aware work | Use uv workspace commands implied by the repo’s workspace members |

Recognize workspaces from executable configuration (for example workspace
member tables in `pyproject.toml`), not from directory guesswork.

## Policy handoff

For dependency intent, groups, lockfile policy, or workspace policy, read the
installed-tree [dependency-management reference][dependency-management].

## Boundaries

- Do not restate the dependency-management standard inline.
- Do not mix package managers in one change.
- Do not migrate auth, tokens, or secrets as part of environment setup.

[dependency-management]: references/dependency-management.md
