---
name: publish-gitlab-review
description: Use when an approved GitLab merge-request review plan is ready for a guarded preview or publication
---

# Publish GitLab Review

## Overview

This skill publishes a validated logical review plan through GitLab-native
discussions, top-level MR notes, and discussion replies. Preview and execute
are separate commands, and every mutation is bound to the current MR diff refs,
approved plan digest, and expected head.

## When to Use

Use when a read-only `review-gitlab-merge-request` plan has been inspected and
the user explicitly authorizes a GitLab publication boundary.

## Quick Reference

Preview first:

```text
publish-gitlab-review preview --plan REVIEW_PLAN.json --output PREVIEW.json
```

Inspect the exact MR identity, `base_sha`, `start_sha`, `head_sha`, selected
items, native payloads, duplicates, blocked positions, and remote-state digest.
Execute only after a separate approval:

```text
publish-gitlab-review execute --plan REVIEW_PLAN.json \
  --approved-plan-digest PLAN_SHA256 --expected-head HEAD_SHA \
  --receipt RECEIPT.json
```

## Boundaries

- Delegate GitLab transport and authentication to `using-gitlab`.
- Require a current plan from `review-gitlab-merge-request` and a fresh
  publication preview before execute.
- Treat the approved plan digest and expected head as exact values, not labels.
- Use GitLab-native discussion, note, and reply endpoints; preserve complete
  native discussion IDs in receipts.
- Never resolve or reopen a discussion as a side effect of posting a reply.
- Stop after an ambiguous mutation failure, mark remaining eligible actions
  `not-attempted`, and retry only after re-fetching current discussions.
- Record every selected, skipped, duplicate, blocked, posted, failed, and
  not-attempted action in the minimal publication receipt.
- Do not copy credentials, authentication state, provider transcripts, or
  generated review artifacts into the repository.

## Common Mistakes

| Mistake | Correct behavior |
|---|---|
| Execute from Markdown selection alone | Execute only from the current approved logical plan and preview gates. |
| Reuse old diff refs | Fetch and preview current MR refs again. |
| Treat a reply as resolution | Post a reply only; never infer or perform resolution. |
| Retry every item after a partial result | Re-fetch and skip confirmed duplicates. |
| Call a GitHub publisher for an MR | Use the GitLab-native publisher and `using-gitlab`. |

## Related Skills

- `using-gitlab`
- `review-gitlab-merge-request`
- `prepare-review-response`
