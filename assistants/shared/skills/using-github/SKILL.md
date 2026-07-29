---
name: using-github
description: >-
  Use when working with GitHub remotes for pull requests, review comments, checks,
  or repository metadata. Prefer read-only inspection, discover providers before
  assuming gh, and require explicit user intent before remote writes.
---

<!-- markdownlint-disable -->

# Using GitHub

Portable GitHub forge workflow. Keep pull-request vocabulary (`PR`, review
comments, checks). Do not route through a shared gitforge skill.

## Repository and remote identity

Derive repository and remote identity from the current checkout:

- Inspect the configured remotes (`git remote -v` or `jj git remote list` when
  applicable).
- Resolve owner/name (and host, for GitHub Enterprise) from the remote URL.
- Prefer dynamic lookup over hard-coded numeric repository IDs.

## Provider discovery

Discover available providers; do not assume one tool surface.

1. Check whether a GitHub-capable MCP or IDE integration is already available.
2. Check whether `gh` is on PATH and authenticated for the target host.
3. Prefer the least surprising available surface; document which one you used.

## Read-only inspection

Prefer read-only inspection before any mutation. Typical read flows:

- List or show pull requests
- Read review comments / conversation
- Inspect checks or workflow runs
- Fetch repository metadata

## CLI fallback

Document CLI fallback with `gh` when no connector is available.

Examples (verify flags against current primary `gh` docs):

```text
gh pr list
gh pr view <number>
gh pr checks <number>
gh api repos/{owner}/{repo}/pulls/<number>
```

When neither a connector nor `gh` is available, stop and tell the user what is
missing. Do not invent ad-hoc HTTP clients or scrape the web UI.

## Provider setup vs workflow

Separate provider setup from workflow guidance.

- Setup (install `gh`, host login, IDE connector enablement) is a user-owned
  precondition.
- This skill covers workflow once a provider works.
- If setup is incomplete, explain the gap and stop.

## Mutation safety

Preview mutations; confirm the canonical remote target.

- Show the exact PR, repository, and host you will write to.
- Prefer dry-run / preview modes when the tool supports them.
- Require explicit user intent before remote writes (create/update PR, post
  review comments, merge, re-run checks, change labels/assignees/reviewers).
- After a write, briefly confirm what changed.

## Forge guard

Confirm the remote is GitHub. If the remote is GitLab (or another forge), name
`using-gitlab` (or the appropriate forge skill) and stop. Do not flatten GitLab
merge-request workflows into GitHub PR commands in place.

## Authentication boundary

Never migrate authentication or MCP configuration.

- Do not copy tokens, rewrite credential helpers, or install MCP servers.
- If auth fails, stop and ask the user to repair auth in their own environment
  (for example `gh auth login` / `gh auth status`).
- Do not retry blindly across transports to bypass auth failures.
