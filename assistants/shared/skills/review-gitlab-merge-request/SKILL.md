---
name: review-gitlab-merge-request
description: Use when reviewing a GitLab merge request locally before any remote write
---

# Review GitLab Merge Request

## Overview

This skill creates a provider-neutral local review draft from a GitLab merge
request's discussions, notes, current diff refs, and repository standards. It
keeps GitLab's MR, discussion, and text-position vocabulary at the provider
boundary and performs no remote write.

## When to Use

Use when a GitLab merge request needs a local review plan or a response-ready
snapshot. The workflow starts read-only and stops if the GitLab provider or
current MR identity cannot be verified.

## Quick Reference

1. Use `using-gitlab` to resolve the host, project, MR IID, discussions, notes,
   and current `diff_refs` (`base_sha`, `start_sha`, and `head_sha`).
2. Use `discover-project-standards` for the repository and selected paths.
3. Write captured provider JSON only to a proven ignored workspace.
4. Normalize the capture with:

   ```text
   review-plan normalize-threads --provider gitlab --identity IDENTITY.json \
     --input gitlab-discussions.json --output .reviews/threads.json \
     --repo-root REPOSITORY
   ```

5. Validate the normalized artifact, then compile the human-edited Markdown
   review with `review-plan compile-review`.

## Boundaries

- Keep MR vocabulary, native discussion IDs, note IDs, resolution state, and
  GitLab text-position semantics visible in the evidence and limitations.
- Require all three current diff refs before accepting an inline position.
- Preserve selected and unselected review actions in the logical plan.
- Record excluded system notes, pagination assumptions, incomplete positions,
  and stale positions as bounded limitations.
- Do not post discussions, notes, replies, resolve threads, edit files, commit,
  push, or claim a remote change.
- Keep authentication, project paths, and provider setup in `using-gitlab`; do
  not copy credentials or generated provider state.

## Common Mistakes

| Mistake | Correct behavior |
|---|---|
| Treating GitLab discussions as GitHub review comments | Keep native discussion and note IDs. |
| Guessing a text position from a stale diff | Require current `diff_refs` and record stale state. |
| Writing captures into the repository | Prove the destination is ignored first. |
| Treating system notes as reviewer feedback | Exclude them and retain the limitation. |
| Posting while drafting | Stop after the local normalized plan and review draft. |

## Related Skills

- `using-gitlab`
- `discover-project-standards`
- `prepare-review-response`
