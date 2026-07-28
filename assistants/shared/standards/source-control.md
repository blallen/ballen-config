---
provenance:
  source_repository: plato
  source_revision: 6bb59d00ac01fd3238c091d90f2aea43872934c9
  source_paths:
    - AGENTS.md
    - skills/jujutsu-workflow/SKILL.md
    - skills/jujutsu-workflow/reference.md
  approved_decision: docs/superpowers/specs/2026-07-27-plato-engineering-standards-migration-design.md
  disposition: corrected
  portability_result: portable-after-adaptation
  review_date: "2026-07-27"
  correction_note: "Replaced staging, branch, worktree, and rebase assumptions with repository-detected policy."
---

# Source control

## Repository detection

Inspect repository metadata and instructions before choosing a workflow. When
`.jj/` is present, use Jujutsu semantics. Otherwise use the repository-selected
source-control system. A colocated repository may expose more than one
interface; follow the repository's stated authority.

## Preserve the working state

Treat existing changes as user-owned unless their origin and scope are known.
Do not discard, rewrite, or fold unrelated work into the current change. If
required edits overlap uncertain changes, stop and resolve ownership before
continuing.

Keep each recorded change coherent and reviewable. Separate unrelated concerns,
describe the intent rather than the mechanics, and create a new working change
after a logical checkpoint when the selected system supports that model.

## Inspect before recording

Review status, diff content, and relevant history before recording or sharing a
change. Confirm that generated files, credentials, local state, and unrelated
edits are absent. Run verification proportional to the risk and record only
what the evidence supports.

Use repository-native concepts for change identity and remote tracking. Do not
translate staging, branches, or workspaces mechanically between tools when
their models differ.

## Safety

Require explicit approval for destructive actions, history rewriting that
affects shared work, forced remote updates, or deletion of a working copy.
Resolve exact targets with read-only inspection first. Prefer reversible
operations, and report what changed when recovery may matter.

Procedural commands and troubleshooting belong in tool-specific workflow
skills. This standard defines invariants that apply regardless of the selected
source-control implementation.
