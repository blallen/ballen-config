---
name: prepare-review-response
description: Use when evaluating normalized GitHub or GitLab review threads and preparing a non-mutating response plan
---

# Prepare Review Response

## Overview

This skill evaluates one validated normalized-threads file and writes an
ignored response plan. The plan keeps provider-neutral thread identity,
evaluation evidence, proposed changes, proposed responses, verification, and
selected or skipped state together.

## When to Use

Use after a review has produced native threads and before any local edit,
commit, push, reply, or resolution decision.

## Quick Reference

1. Start read-only, select exactly one normalized threads file, and validate
   it:
   `~/.local/share/ballen-config/review-tools/bin/review-plan validate --artifact THREADS`.
2. Discover repository standards and invoke native `receiving-code-review` when
   available.
3. Evaluate technical validity before agreeing with feedback.
4. Write the response draft in the ignored workspace, with a section for every
   thread that is not resolved. Resolved threads without a section are kept as
   `skip` evidence. The `compile-response` section of
   `~/.local/share/ballen-config/review-tools/README.md` defines the draft
   format.
5. Compile the plan, then stop:
   `~/.local/share/ballen-config/review-tools/bin/review-plan compile-response --threads THREADS --draft DRAFT --output PLAN --repo-root REPO`.

## Boundaries

- GitHub and GitLab provider skills are runtime alternatives, not simultaneous
  dependencies of this provider-neutral skill.
- Thread limitations stay in the source threads file, which the plan binds
  through `source_threads_digest`; the response plan does not copy them. Cite a
  limitation in an item's evidence when it affects that evaluation, and report
  missing native evaluation coverage to the user.
- A selected response or proposed change is not authorization to edit or reply.
- Never edit files, commit, push, reply, resolve threads, or publish status.
- Never store credentials, headers, raw provider responses, or full transcripts.

## Common Mistakes

| Mistake | Correct behavior |
|---|---|
| Dropping resolved threads | Retain them as evidence with `skip` |
| Agreeing without technical evaluation | Record evidence and limitations |
| Combining GitHub and GitLab inputs | Select one validated provider source |
| Making a local edit while preparing | Stop after writing the response plan |

## Related Skills

- `receiving-code-review`
- `discover-project-standards`
- `using-github`
- `using-gitlab`
