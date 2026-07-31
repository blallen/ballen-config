---
name: respond-to-gitlab-review
description: Use when executing an approved response plan for a GitLab merge-request discussion
---

# Respond to GitLab Review

## Overview

This skill applies a provider-neutral response plan to a GitLab merge request
through separately authorized local and remote gates. It preserves native
discussion IDs, current diff refs, resolution state, positions, and itemized
publication outcomes.

## When to Use

Use when a current `prepare-review-response` plan identifies GitLab discussion
replies or local changes that the user explicitly wants to execute.

## Quick Reference

1. Authorize selected local edits only.
2. Run and inspect focused verification.
3. Authorize the exact change description and commit.
4. Authorize push to the reviewed remote and branch.
5. Preview exact remote replies or status comments through
   `publish-gitlab-review`.

Before the final reply gate, re-fetch the MR identity, complete `diff_refs`,
selected discussions, and current note state. Then approve the exact preview
and receipt boundary separately.

## Boundaries

- Use `using-gitlab` for transport, authentication, project identity, and
  current MR reads.
- Delegate local scope to `resolve-change-scope` and use repository-native
  source control; use Jujutsu when `.jj/` is present.
- Do not claim completion before focused verification passes.
- Do not claim a change is remote until the expected head contains it.
- Never infer remote resolution from a local reply; this workflow never
  resolves or reopens a discussion automatically.
- Preserve complete native discussion IDs and report all receipt outcomes,
  including duplicate, blocked, failed, and not-attempted items.
- Re-preview after a changed head, diff ref, discussion state, or plan digest.
- Never bundle commit, push, and reply into one approval.
- Do not edit, commit, push, resolve, or reply without the corresponding
  explicit approval.

## Common Mistakes

| Mistake | Correct behavior |
|---|---|
| Replying against an old diff ref | Fetch current MR refs and preview again. |
| Treating a reply as resolution | Reply only; leave resolution to a separate explicit action. |
| Combining local changes and remote replies | Keep each approval boundary independent. |
| Repeating a confirmed reply after partial failure | Re-fetch discussions and let the publisher classify duplicates. |
| Using GitHub review endpoints | Use GitLab discussions, notes, and discussion replies. |

## Related Skills

- `prepare-review-response`
- `publish-gitlab-review`
- `resolve-change-scope`
- `using-gitlab`
