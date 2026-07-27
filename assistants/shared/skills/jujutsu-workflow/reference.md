# Jujutsu Workflow Reference

This file holds the heavier `jj` guidance that does not need to load in every session.

## Daily Workflows

### Sync local branch to remote

Use when you want the local bookmark to match the remote exactly:

```bash
jj git fetch
jj bookmark set main -r main@origin
```

To create a fresh working copy on top:

```bash
jj bookmark set main -r main@origin
jj new main
```

### Stay current with main

For unpushed commits:

```bash
jj git fetch
jj rebase -d main@origin
```

### Create and push a bookmark

```bash
jj git fetch
jj rebase -d main@origin
jj bookmark create my-feature
jj git push --bookmark my-feature
```

## Push Rejections

### Bookmark moved on remote

```bash
jj git fetch
jj rebase -d main@origin
jj git push --bookmark my-feature
```

### Non-tracking remote bookmark exists

```bash
jj bookmark track my-feature@origin
jj git push --bookmark my-feature
```

### Bookmark is conflicted

```bash
jj bookmark set my-feature -r <your-commit>
jj git push --bookmark my-feature
```

## Bookmark Management

```bash
jj bookmark create my-feature
jj bookmark create my-feature -r <rev-id>
jj bookmark move my-feature --to @
jj bookmark move my-feature --to <rev-id>
jj bookmark move my-feature --to <rev-id> --allow-backwards
jj bookmark list | cat
jj bookmark track my-feature@origin
```

## Abandoning Duplicate or Orphaned Commits

Use `jj abandon` only when you are confident the revset is correct and no important bookmarks point at it.

```bash
jj log -r '<base-commit>::<tip-commit>' | cat
jj bookmark list | cat
jj abandon '<base-commit>::<tip-commit>'
```

Notes:

- `jj abandon` affects only the selected revset
- Recover with `jj undo` if needed
- Double-check bookmarks before abandoning ranges

## Workspaces

Workspaces are the `jj` equivalent of Git worktrees for separate working copies, but they do not isolate repo-global state such as bookmarks and history-editing operations.

### Create a workspace

```bash
jj workspace add .worktrees/my-feature
jj workspace list | cat
```

Notes:

- If you place a workspace inside the repo under `.worktrees/` or `worktrees/`, confirm that directory is already ignored before using it.
- If you are not sure about the ignore setup, prefer a sibling directory outside the repo instead.

### Work inside a workspace

```bash
cd .worktrees/my-feature
jj status | cat
jj log | cat
```

Notes:

- Bookmark moves, rebases, `jj abandon`, and similar history operations affect the shared repo and are visible from other workspaces.
- If you need fully independent repo state, use a separate clone instead of another workspace.

### Clean up a workspace

```bash
jj workspace forget my-feature
rm -rf .worktrees/my-feature
```

## Rebasing Pushed Work

When commits are already pushed and immutable, duplicate before rebasing:

```bash
jj git fetch
jj log -r 'roots(main@origin..my-feature)' | cat
jj duplicate '<root-commit>::my-feature'
jj rebase -s <duplicated-root-commit> -d main@origin
jj bookmark move my-feature --to <rebased-tip-commit> --allow-backwards
jj git push --bookmark my-feature
```

If conflicts appear, move to the first conflicted commit and resolve from there:

```bash
jj new <first-conflicted-commit>
jj status | cat
jj squash
```

## Optional Aliases

Some environments expose aliases like these in `~/.config/jj/config.toml`:

```toml
[aliases]
c = ["commit"]
p = ["git", "push"]
cc = ["util", "exec", "--", "bash", "-c", "...", ""]
pp = ["util", "exec", "--", "bash", "-c", "...", ""]
```

Practical interpretation:

- `jj c` / `jj p`: quick commit and push aliases
- `jj cc` / `jj pp`: aliases that may run pre-commit checks first
- Never assume these aliases exist unless you can verify them

## Conflict Resolution

### Fast loop

```bash
jj new <commit_id>
jj status | cat
jj squash
jj status | cat
```

### Heuristics

- Resolve parent conflicts first and let the cascade rebase descendants
- Use merge commits or other natural boundaries to break large rebases into phases
- Always run `jj status | cat` before squashing

### Common patterns

- Version conflicts: keep the highest intended version and regenerate lockfiles
- Import path conflicts: prefer current file locations and update imports consistently
- File reorganization conflicts: confirm moved locations before deleting anything
- Immutable commit errors: use the duplicate-then-rebase workflow above

## Quick Reference

| Task | Command |
|------|---------|
| Fetch remote | `jj git fetch` |
| Sync bookmark to remote | `jj bookmark set main -r main@origin` |
| Create fresh working copy | `jj new main` |
| Rebase on main | `jj rebase -d main@origin` |
| Create bookmark | `jj bookmark create my-feature` |
| Move bookmark | `jj bookmark move my-feature --to @` |
| Push bookmark | `jj git push --bookmark my-feature` |
| Abandon range | `jj abandon '<base>::<tip>'` |
| Status | `jj status \| cat` |
| Log | `jj log \| cat` |
| Squash | `jj squash` |
| Undo | `jj undo` |

## Revset Notes

| Syntax | Meaning |
|--------|---------|
| `@` | Current working copy |
| `<commit>::<commit>` | Inclusive range |
| `roots(A..B)` | First commits in a range |
| `main@origin` | Remote tracking bookmark |
