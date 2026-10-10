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

Run these steps from the repository root. The review-tools README at
`~/.local/share/ballen-config/review-tools/README.md` defines the identity
shape, the draft grammar, and each command's arguments.

1. Use `using-gitlab` to resolve the host, project, MR IID, discussions, notes,
   and current `diff_refs` (`base_sha`, `start_sha`, and `head_sha`).
2. Use `discover-project-standards` for the repository and selected paths.
3. Use an existing ignored workspace such as `.reviews/`, and ask for one when
   none is obvious. Prove it before writing any capture or artifact there:

   ```text
   ~/.local/share/ballen-config/review-tools/bin/review-plan workspace-check \
     --repo-root . --destination .reviews --proposed-file .reviews/threads.json
   ```

4. Write `.reviews/IDENTITY.json` from the current MR: `provider` is `gitlab`,
   `host` is the GitLab host, `repository` is the project path,
   `change_number` is the MR IID, `base_revision` is `diff_refs.base_sha`, and
   `head_revision` is `diff_refs.head_sha`. Normalization rejects any other
   base or head.
5. Save the `diff_refs` and every page of `discussions` as one JSON object in
   `.reviews/gitlab-discussions.json`, then normalize and validate it:

   ```text
   ~/.local/share/ballen-config/review-tools/bin/review-plan normalize-threads \
     --provider gitlab --identity .reviews/IDENTITY.json \
     --input .reviews/gitlab-discussions.json --output .reviews/threads.json \
     --repo-root .
   ~/.local/share/ballen-config/review-tools/bin/review-plan validate \
     --artifact .reviews/threads.json
   ```

6. Check out the MR head: `git fetch origin refs/merge-requests/IID/head`, then
   `git switch --detach HEAD_SHA`, where `HEAD_SHA` is `diff_refs.head_sha`.
   `compile-review` rejects a checkout whose `HEAD` is not `head_revision`.
7. Review `git diff BASE_SHA HEAD_SHA`, where `BASE_SHA` is
   `diff_refs.base_sha`, against the discovered standards and the normalized
   threads. Write the findings as a Markdown draft in `.reviews/review.md`.
8. Compile and validate the draft:

   ```text
   ~/.local/share/ballen-config/review-tools/bin/review-plan compile-review \
     --draft .reviews/review.md --identity .reviews/IDENTITY.json \
     --output .reviews/review-plan.json --repo-root .
   ~/.local/share/ballen-config/review-tools/bin/review-plan validate \
     --artifact .reviews/review-plan.json
   ```

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
