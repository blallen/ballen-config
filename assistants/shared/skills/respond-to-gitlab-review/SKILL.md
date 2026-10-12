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

1. Revalidate repository standards with `discover-project-standards`, then
   authorize selected local edits only.
2. Run and inspect focused verification.
3. Authorize the exact change description and commit.
4. Authorize push to the reviewed remote and branch.
5. Preview and authorize exact remote replies or status comments:
   1. Recapture the MR's current `diff_refs` and every page of its
      `discussions` with `using-gitlab`, and set the identity's
      `base_revision` and `head_revision` to the new `diff_refs.base_sha` and
      `diff_refs.head_sha`.
   2. Refresh the threads with
      `~/.local/share/ballen-config/review-tools/bin/review-plan normalize-threads --provider gitlab`.
   3. Recompile the response plan against the refreshed threads with
      `~/.local/share/ballen-config/review-tools/bin/review-plan compile-response`.
   4. Write a review draft in the ignored workspace with one item for each
      selected response item: `**Type:** reply`, `**Discussion:**` set to its
      discussion ID, and its proposed response as the body.
   5. Compile that draft with
      `~/.local/share/ballen-config/review-tools/bin/review-plan compile-review`.
   6. Preview with
      `~/.local/share/ballen-config/review-tools/bin/publish-gitlab-review preview`.
      Execute only after a separate approval of the exact preview and receipt
      boundary, with
      `~/.local/share/ballen-config/review-tools/bin/publish-gitlab-review execute`,
      and report its receipt.

Arguments, input shapes, and the draft grammar are in
`~/.local/share/ballen-config/review-tools/README.md`.

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
- `discover-project-standards`
- `using-gitlab`
