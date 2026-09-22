---
name: publish-github-review
description: Use when publishing an approved GitHub pull-request review preview with explicit head and digest gates
---

# Publish GitHub Review

## Overview

This skill publishes only a current, explicitly approved preview generated from
the current review draft and logical plan. It delegates GitHub identity,
terminology, and transport selection to `using-github` and uses the managed
`~/.local/share/ballen-config/review-tools/bin/publish-github-review` command.

## When to Use

Use after `review-github-pull-request` has produced a current draft and plan,
when the user separately asks to preview or publish those exact findings.

## Quick Reference

1. Re-read the current draft and recompile the logical plan.
2. Run the read-only preview and show eligible, blocked, duplicate, and skipped
   actions with the plan digest and observed head.
3. Obtain approval for that exact preview.
4. Execute only with the approved plan digest and expected head.
5. Summarize the itemized receipt without claiming failed or blocked items
   posted.

## Boundaries

- A preview is evidence, not authorization; `POST: YES` is never sufficient.
- Re-fetch the pull request and comments before execution.
- A changed head, identity, plan digest, or remote observation blocks all writes.
- Batch only compatible inline comments; keep general comments and replies
  provider-native and separate.
- Stop automatic retry after an ambiguous provider result.
- Never store credentials, headers, raw provider responses, complete transcripts,
  or full payloads in receipts.
- Never resolve threads, edit files, commit, push, or alter ignore rules.
- If no approved mutation transport is available, stop as blocked.

## Common Mistakes

| Mistake | Correct behavior |
|---|---|
| Reusing an old `POST: YES` draft | Recompile and preview the current draft |
| Publishing after the PR head changed | Invalidate approval and require a new preview |
| Treating a review reply as a general comment | Use the native review-comment reply endpoint |
| Retrying an ambiguous batch | Mark unconfirmed items failed and require preflight |

## Related Skills

- `review-github-pull-request`
- `using-github`
- `discover-project-standards`
