---
name: respond-to-github-review
description: Use when executing an approved GitHub review response plan through separately authorized local and remote boundaries
---

# Respond to GitHub Review

## Overview

This skill turns a current provider-neutral response plan into a guarded,
sequential response workflow. It revalidates repository scope, standards,
GitHub identity, head, and thread state before each boundary.

## When to Use

Use when the user has a current response plan and explicitly wants to act on
selected local changes, verification, commits, pushes, or remote replies.

## Quick Reference

1. Authorize selected local edits.
2. Run and inspect focused verification.
3. Authorize the exact change description and commit.
4. Authorize push to the reviewed remote and branch.
5. Preview and authorize exact remote replies or status comments.

## Boundaries

- Delegate local scope to `resolve-change-scope` and use repository-native source
  control; use Jujutsu when `.jj/` is present.
- Never bundle commit, push, and reply into one approval.
- Do not claim completion before focused verification passes.
- Do not claim a change is remote until the expected head contains it.
- Revalidate the provider identity, expected head, and native thread before each
  remote reply.
- Use `publish-github-review` for the fresh reply preview and its digest/head
  gates; do not invent a second publisher.
- Never edit, commit, push, resolve, or reply without the corresponding explicit
  approval.

## Common Mistakes

| Mistake | Correct behavior |
|---|---|
| One approval for edits, commit, push, and reply | Ask at each ordered boundary |
| Declaring a fix complete before tests | Inspect focused verification first |
| Replying against an old head | Revalidate and preview again |
| Using a guessed repository scope | Delegate scope resolution |

## Related Skills

- `prepare-review-response`
- `publish-github-review`
- `resolve-change-scope`
- `discover-project-standards`
- `using-github`
