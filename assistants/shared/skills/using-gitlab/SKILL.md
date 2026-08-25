---
name: using-gitlab
description: >-
  Use when working with GitLab remotes for merge requests, discussions, pipelines,
  or project metadata. Prefer read-only inspection, discover providers before
  assuming glab, and require explicit user intent before remote writes.
---

# Using GitLab

Portable GitLab forge workflow. Keep merge-request vocabulary (`MR`, discussions,
pipelines). Do not route through a shared gitforge skill.

## Repository and remote identity

Derive repository and remote identity from the current checkout:

- Inspect remote configuration locally; never run a command that places raw
  remote URLs in output or transcripts.
- Parse remote URLs locally and emit only a sanitized host and namespace/path.
  Explicitly omit URL userinfo, query strings, and fragments; never reproduce
  secret-bearing components.
- Resolve the canonical GitLab project from the sanitized host and
  namespace/path.
- Prefer dynamic lookup over hard-coded project IDs.

## Provider discovery

Discover available providers; do not assume one tool surface.

1. Check whether a GitLab-capable MCP or IDE integration is already available.
2. Check whether `glab` is on PATH and authenticated for the target host.
3. Prefer the least surprising available surface; document which one you used.

## Read-only inspection

Prefer read-only inspection before any mutation. Typical read flows:

- List or show merge requests
- Read discussions / notes
- Inspect pipelines or job status
- Fetch project metadata

## Shared review-plan boundary

Read-only MR review skills may hand a captured GitLab response to the shared
`review-plan` tool after `using-gitlab` has resolved the current MR and diff
refs:

```text
review-plan normalize-threads --provider gitlab --identity IDENTITY.json \
  --input gitlab-discussions.json --output .reviews/threads.json \
  --repo-root REPOSITORY
```

The normalized artifact is provider-neutral and local. Keep transport,
authentication, pagination, and project identity here; keep parsing and plan
contracts in `review-plan`.

For an explicitly approved remote publication, `publish-gitlab-review` owns the
preview, digest, current-diff-ref, expected-head, and receipt gates. It uses
the same `glab` transport boundary and never copies authentication state.

## CLI fallback

Document CLI fallback with `glab` when no connector is available.

Examples (verify flags against current primary `glab` docs):

```text
glab mr list
glab mr view <iid>
glab api "projects/:id/merge_requests/<iid>"
```

When neither a connector nor `glab` is available, stop and tell the user what is
missing. Do not invent ad-hoc HTTP clients or scrape the web UI.

## Provider setup vs workflow

Separate provider setup from workflow guidance.

- Setup (install `glab`, host login, IDE connector enablement) is a user-owned
  precondition.
- This skill covers workflow once a provider works.
- If setup is incomplete, explain the gap and stop.

## Mutation safety

Preview mutations; confirm the canonical remote target.

- Show the exact MR, project path, and host you will write to.
- Use a provider dry-run / preview as non-mutating only after current primary
  documentation establishes it has no unapproved side effect. Otherwise,
  construct a local target/payload preview or obtain explicit approval for all
  potential side effects.
- Require explicit user intent before remote writes (create/update MR, post
  comments, merge, retry pipelines, change labels/assignees).
- After a write, briefly confirm what changed.

## Forge guard

Confirm the remote is GitLab. If the remote is GitHub (or another forge), name
`using-github` (or the appropriate forge skill) and stop. Do not translate
GitHub pull-request workflows into GitLab MR commands in place.

## Authentication boundary

Never migrate authentication or MCP configuration.

- Do not copy tokens, rewrite credential helpers, or install MCP servers.
- If auth fails, stop and ask the user to repair auth in their own environment
  (for example `glab auth login` / `glab auth status`).
- Do not retry blindly across transports to bypass auth failures.
