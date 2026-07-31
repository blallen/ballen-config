# Ponytail Self-Review Integration Design

## Status

Approved in conversation on July 31, 2026. This design adds one prerequisite
merge request before the forge review and response train.

## Context

The shared plugin catalog already declares Ponytail as a required Claude Code
plugin. Ponytail now provides a native Codex plugin and a `ponytail-review`
skill that reviews the current diff only for unnecessary complexity.

The repository-owned `conduct-self-review` workflow currently aggregates four
common v1 specialist results. Its artifact contract deliberately fixes those
four reviewers and their ordering. Ponytail therefore belongs inside the
existing `review-project-quality` result rather than as a fifth top-level
reviewer that would require a new artifact version.

## Goals

- Declare Ponytail as required desired state for Claude Code and Codex.
- Run one Ponytail simplicity pass as part of project-quality review.
- Keep every specialist on the same immutable change scope and standards
  inventory.
- Preserve the existing self-review artifact v1 contract.
- Review every MR-sized bookmark with an explicit base and target.
- Keep review artifacts ignored, untracked, and local.

## Non-Goals

- Vendoring Ponytail source, hooks, plugin payloads, or generated state.
- Committing authentication, trust decisions, sessions, caches, histories, or
  machine-specific paths.
- Adding Ponytail to Cursor's plugin desired state.
- Running Ponytail's repository-wide audit, debt, gain, or mutation workflows.
- Applying findings during report-only self-review.
- Changing the common review-result or self-review artifact contract version.

## Delivery Boundary

Create `review-foundation-ponytail` from `main`. It is a standalone prerequisite
MR containing the design, implementation plan, desired-state change, review
integration, tests, and any focused documentation updates.

After that MR is locally complete, rebase the existing forge train onto its
bookmark. Because the forge bookmarks have not been pushed, their rewritten
commit identities can be updated without a remote recovery procedure. Refresh
the train checkpoint after the rebase so it never records stale identities.

## Plugin Desired State

Update both the `ponytail` marketplace and `ponytail@ponytail` plugin records in
`assistants/shared/plugins/catalog.yaml` from `targets: [claude-code]` to
`targets: [claude-code, codex]`.

The existing target-aware projection and native adapters remain authoritative:

- Claude Code continues to plan its native marketplace and plugin commands.
- Codex begins planning the same marketplace and plugin through its own native
  adapter.
- Cursor remains unchanged.

The repository stores only stable marketplace and plugin identifiers. Native
tools own installation and regenerated runtime state; user trust remains an
interactive local decision.

## Quality Review Integration

`conduct-self-review` continues to invoke these four top-level specialists in
the existing order:

1. `review-project-standards`;
2. `review-project-quality`;
3. `review-project-tests`; and
4. `review-python-types`.

`review-project-quality` adds one owned Ponytail sub-pass after it establishes
applicability and before final scope revalidation. It invokes
`ponytail-review` exactly once with the same in-memory `ChangeScope`,
`scope_identity`, standards inventory, and changed-path boundary supplied to
the quality specialist. It must use diff review, never repository-wide audit.

The sub-pass remains report-only. It cannot edit code, install a plugin, widen
scope, or authorize remediation.

### Finding normalization

Normalize concrete Ponytail observations into the common v1 finding shape
owned by `review-project-quality`:

| Ponytail tag | Common rule | Default severity |
| --- | --- | --- |
| `delete` | `ponytail/delete` | actionable |
| `stdlib` | `ponytail/stdlib` | actionable |
| `native` | `ponytail/native` | actionable |
| `yagni` | `ponytail/yagni` | actionable |
| `shrink` | `ponytail/shrink` | advisory |

Each accepted observation requires a repository-relative changed path, a tight
line location when available, concrete evidence, and a bounded replacement or
deletion. Reject generic style preferences, findings outside the immutable
scope, and correctness, security, performance, or test-design findings owned
by other specialists.

`Lean already. Ship.` produces a completed Ponytail check with no findings.
The estimated net line reduction is conversational evidence only and is not a
finding, score, or authorization signal.

Normal project-quality deduplication applies before aggregate self-review
deduplication. Ponytail and another quality check may contribute to one finding
only when the common contract's exact semantic-match rule holds.

### Availability and integrity

Ponytail is required when the active host exposes native Claude Code or Codex
plugin support. A missing `ponytail-review` skill produces unavailable quality
coverage and prevents a clean aggregate verdict. Cursor, which has no declared
Ponytail plugin target, records the sub-pass as evidence-backed not applicable.

Malformed or unbounded Ponytail output produces incomplete quality coverage;
it is never interpreted optimistically. Scope drift after the pass blocks the
quality result under the existing revalidation rule.

This already-running migration task began before the Codex plugin could be
loaded. For this one review batch, use the exact published `ponytail-review`
skill contract from Ponytail commit
`16f29800fd2681bdf24f3eb4ccffe38be3baec6b` as bounded reviewer instructions. <!-- pragma: allowlist secret -->
Record a required, completed, changed-scope coverage check named
`ponytail-review-published-contract`; the distinct check name preserves
transition provenance without adding a skip or claiming a native invocation.
Subsequent tasks use the managed native plugin after ordinary bootstrap and
restart.

## Verification

Focused tests prove:

- the production catalog projects Ponytail to both Claude Code and Codex;
- Codex plans the Ponytail marketplace before the Ponytail plugin;
- already installed native entries remain no-ops;
- Cursor projections remain unchanged;
- quality-review instructions require one immutable-scope Ponytail pass;
- every Ponytail tag has the specified normalized rule and severity;
- lean, unavailable, malformed, out-of-scope, and scope-drift outcomes retain
  their correct coverage effects; and
- the self-review v1 example and four-reviewer artifact contract are unchanged.

Run focused plugin, desired-state, skill, and review-contract tests first.
Then run repository mypy, the full test suite, lock validation, and all
pre-commit hooks before claiming the prerequisite MR complete.

## Review Sequence

Preflight `.reviews/self-review/` once per invocation as required by
`conduct-self-review`. Resolve each explicit base and target exactly once and
write one ignored artifact for each MR boundary:

| Target bookmark | Explicit base |
| --- | --- |
| `review-foundation-ponytail` | `main` |
| `forge-review-github-draft` | `review-foundation-ponytail` |
| `forge-review-github-publish` | `forge-review-github-draft` |
| `forge-review-prepare-response` | `forge-review-github-publish` |
| `forge-review-github-response` | `forge-review-prepare-response` |
| `forge-review-gitlab-draft` | `forge-review-github-response` |
| `forge-review-gitlab-publish` | `forge-review-gitlab-draft` |
| `forge-review-gitlab-response` | `forge-review-gitlab-publish` |
| `forge-review-train-checkpoint` | `forge-review-gitlab-response` |

Each review is report-only. Return its verdict, counts, limitations, and exact
ignored artifact path. Do not address findings until the user explicitly
selects an artifact and requests remediation.

## Success Criteria

- Ponytail is declaratively available to Claude Code and Codex without copied
  runtime state.
- Project-quality review accounts for exactly one bounded Ponytail pass.
- Self-review artifact v1 still contains exactly four specialist results.
- The prerequisite and all eight forge bookmarks have verified ignored
  self-review artifacts for their explicit MR scopes.
- The rebased train and checkpoint contain current identities.
- The working copies are clean and no review artifact is committed.
