---
name: prepare-review-response
description: Use when evaluating normalized GitHub or GitLab review threads and preparing a non-mutating response plan
---

# Prepare Review Response

## Overview

This skill evaluates one validated normalized-thread artifact or one selected
provider input and writes an ignored response plan. It keeps provider-neutral
thread identity, limitations, evaluation evidence, proposed changes, proposed
responses, verification, and selected/skipped state together.

## When to Use

Use after a review has produced native threads and before any local edit,
commit, push, reply, or resolution decision.

## Quick Reference

1. Start read-only and select exactly one normalized input path.
2. Discover repository standards and invoke native `receiving-code-review` when
   available.
3. Evaluate technical validity before agreeing with feedback.
4. Retain every thread, including resolved and informational evidence.
5. Write only the ignored response plan, then stop.

## Boundaries

- GitHub and GitLab provider skills are runtime alternatives, not simultaneous
  dependencies of this provider-neutral skill.
- Preserve normalization limitations and missing native evaluation coverage.
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
