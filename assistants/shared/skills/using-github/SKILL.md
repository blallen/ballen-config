---
name: using-github
description: >-
  Use when working with GitHub remotes for pull requests, review comments, checks,
  or repository metadata. Prefer read-only inspection, discover providers before
  assuming gh, and require explicit user intent before remote writes.
---

# Using GitHub

Portable GitHub forge workflow. Keep pull-request vocabulary (`PR`, review
comments, checks). Do not route through a shared gitforge skill.

## Repository and remote identity

Derive repository and remote identity from the current checkout:

- Inspect remote configuration locally; never run a command that places raw
  remote URLs in output or transcripts.
- Parse remote URLs locally and emit only a sanitized host and namespace/path.
  Explicitly omit URL userinfo, query strings, and fragments; never reproduce
  secret-bearing components.
- Resolve owner/name (and host, for GitHub Enterprise) from the sanitized
  remote identity.
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

## Review tool delegation

`review-github-pull-request` and `publish-github-review` own review intent and
approval boundaries. This skill owns GitHub provider identity, terminology,
read transport, and mutation transport selection.

- Use the managed `review-plan` command for deterministic local parsing and
  artifact validation.
- Prefer `gh` with fixed argument arrays when it is available.
- If only a connected provider is available, execute the exact validated
  request bundle after the skill obtains current approval, then validate the
  normalized receipt.
- If no mutation-capable transport is available, keep local review complete and
  report publication as blocked.
- Never put credentials, headers, raw provider responses, or auth state into
  review artifacts.

## Provider setup vs workflow

Separate provider setup from workflow guidance.

- Setup (install `gh`, host login, IDE connector enablement) is a user-owned
  precondition.
- This skill covers workflow once a provider works.
- If setup is incomplete, explain the gap and stop.

## Mutation safety

Preview mutations; confirm the canonical remote target.

- Show the exact PR, repository, and host you will write to.
- Use a provider dry-run / preview as non-mutating only after current primary
  documentation establishes it has no unapproved side effect. Otherwise,
  construct a local target/payload preview or obtain explicit approval for all
  potential side effects.
- `gh pr create --dry-run` may still push Git changes. It is not a safe preview
  unless pushing was explicitly approved. Without push approval, preview title,
  body, head/base, repository, and host locally.
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
