---
name: review-github-pull-request
description: Use when reviewing a GitHub pull request and producing a local, reviewable comment draft
---

# Review GitHub Pull Request

## Overview

Produce a provider-aware but locally stored GitHub pull-request review draft
and logical comment plan. The result is evidence for a later preview; it is not
publication authorization.

## When to Use

Use when a user asks for a GitHub pull-request review, inline findings, review
coverage, or a draft of comments. Use the skill when the review must remain
local and auditable before any publication decision.

## Quick Reference

1. Use `using-github` for repository, pull-request, diff, and existing-review
   reads. Use `discover-project-standards` before evaluating findings.
2. Record the canonical repository, pull-request, base, and current head. Do
   not guess a branch or reuse an old head.
3. Ask for a repository-local destination that is already ignored and
   untracked when no safe workspace is obvious. Prove it before writing.
4. Run the managed tool at
   `~/.local/share/ballen-config/review-tools/bin/review-plan` to compile and
   validate the current Markdown draft and logical plan.
5. Retain selected and skipped items, missing local coverage, validation
   failures, and provider limitations in the artifact.

## Boundaries

- `POST: YES` means selected candidate for a future preview only.
- Never publish, reply, edit, commit, push, or alter ignore rules.
- Never use `/tmp`, the repository root, a tracked path, an unverified ignored
  path, or a symlinked path for review artifacts.
- Never store credentials, headers, raw API responses, provider auth state, or
  complete review transcripts in canonical content.
- Never silently omit malformed comments, unavailable provider data, or missing
  local coverage.
- If the workspace or provider evidence cannot be proven, stop and report the
  specific blocked condition.

## Common Mistakes

| Mistake | Correct response |
| --- | --- |
| Treating `POST: YES` as permission | Keep it as selection and require a later preview. |
| Writing to a convenient directory | Ask for a safe ignored repository-local workspace. |
| Claiming complete coverage | Record exactly which provider or local evidence is missing. |
| Falling back to ad-hoc HTTP | Use `using-github` transport boundaries and stop if unavailable. |
| Dropping invalid Markdown items | Preserve the item with a bounded validation failure. |

## Related Skills

- `using-github`
- `discover-project-standards`
- `publish-github-review`
