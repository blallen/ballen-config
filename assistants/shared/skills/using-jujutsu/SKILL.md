---
name: using-jujutsu
description: >-
  Use when working in a repository that contains a `.jj/` directory
  (Jujutsu-managed, including git-colocated), for status, diff, log,
  describe, bookmark, rebase, push, workspace, separate checkout,
  worktree-like, or conflict-resolution tasks.
---

# Using Jujutsu

Use `jj` instead of `git` for source control work unless the user explicitly asks for Git.
This guidance overrides generic Git worktree advice in `jj` repos.
If another workflow or user request says "worktree" or "isolated workspace" in a `jj` repo, translate that to `jj workspace add`, or to a separate clone when repo-global isolation is required.

For another working copy in a `jj` repo, prefer `jj workspace add` over `git worktree`.
If the task needs independent repo-global state for multiple agents or risky history edits, use a separate clone instead of another workspace.

## Defaults

- Prefer `jj status | cat` over `git status`
- Prefer `jj diff` or `jj diff --summary` over `git diff`
- Prefer `jj log | cat` over `git log`
- Prefer `jj show | cat` when inspecting the current change
- Prefer `jj workspace add` over `git worktree add` for another working copy in the same repo
- Prefer a separate clone over another workspace when work must not share bookmarks or history-editing operations
- Follow pager-prone `jj` commands with `| cat` so output renders in the terminal

## Common Commands

- Status: `jj status | cat`
- Diff working copy: `jj diff`
- Diff summary: `jj diff --summary`
- Log: `jj log | cat`
- Show current change: `jj show | cat`
- Describe current change: `jj describe -m "..."`
- Create workspace: `jj workspace add ../my-feature`
- List workspaces: `jj workspace list | cat`
- Start a follow-up working copy: `jj new`
- Squash current change: `jj squash`
- Undo last operation: `jj undo`

## Describe Workflow

When the user asks for a commit message or change description:

1. Inspect the current change with:
   - `jj status | cat`
   - `jj diff --summary`
   - `jj log -n 8 --no-graph -T 'description ++ "\n"' | cat`
2. Match the repository's existing message style.
3. If asked to apply the message, use `jj describe -m "..."`

## Aliases

- If `jj cc` is available in the user's environment, treat it as an optional "clean commit" alias that runs pre-commit checks before committing.
- Do not assume `jj cc` exists everywhere. If it matters, inspect the environment or ask before relying on it.
- If `jj cc` is not available, use standard `jj` commands and any repository-specific verification flow.

## Safety Notes

- Do not switch to `git` unless the user explicitly asks.
- If you are already inside a Git worktree, confirm `jj workspace list | cat` shows that checkout before trusting workspace-local `jj` state.
- Be cautious with `jj bookmark move --allow-backwards`, `jj abandon`, and rebases of pushed work.
- Preserve repository conventions for message style and workflow.

## Additional Reference

- For bookmark workflows, rebasing pushed branches, workspaces, push rejections, and conflict resolution patterns, see [reference.md](reference.md).
