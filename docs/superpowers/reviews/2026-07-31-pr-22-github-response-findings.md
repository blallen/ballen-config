# PR #22 GitHub response review handoff

## Status

- Branch: `forge-review-github-response`
- Source artifact: `20260731T165146Z-2b5cbeea590c.md`
- Result ID: `86d9bf4ba8a8f158baca33668dfd321f9e111977b5d92a88e4f07c34eaca3d48`
- Scope identity: `2b5cbeea590c05f138e72bd35424fd2a09a637f187dbefc456122c875f15d6b5`
- Original verdict: unavailable, with 4 actionable findings and no blockers

This handoff preserves findings from the original self-review. The stack has
since been rewritten, and this document changes the reviewed branch again.
Revalidate every item against the current diff before remediation; paths and
line numbers below describe the original review scope.

## Deferred findings

- [ ] In
  `assistants/shared/tools/review/src/ballen_review_tools/plan_cli.py` (original
  line 237), reject normalization when `--provider` differs from
  `identity.provider`, and cover the failure path.
- [ ] In
  `assistants/shared/tools/review/src/ballen_review_tools/providers/github.py`
  (original lines 334-342), retain orphan and nested replies as missing-thread
  evidence or attach them recursively without dropping native comment IDs.
- [ ] In the same provider (original line 347), represent unavailable GitHub
  resolution and outdated state as unknown or missing instead of asserting
  every normalized thread is open.
- [ ] Replace the limitation-string-only coverage in
  `tests/assistants/review_tools/test_github_threads.py` (original lines 46-56)
  with fixtures proving unavailable state and complete orphan and nested reply
  chronology.

## Verification limitations

The configured hook set included mutating fixers and was not safe for the
original review-only run. No declared safe test command was executed, so the
behavioral review was limited to the immutable diff and nearby context.
