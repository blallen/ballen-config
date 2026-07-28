---
provenance:
  source_repository: plato
  source_revision: 6bb59d00ac01fd3238c091d90f2aea43872934c9
  source_paths:
    - AGENTS.md
    - .cursor/rules/uv.mdc
    - docs/tooling/uv_workspace_guide.md
  source_roles:
    docs/tooling/uv_workspace_guide.md: evidence-after-correction
  approved_decision: docs/superpowers/specs/2026-07-27-plato-engineering-standards-migration-design.md
  disposition: corrected
  portability_result: portable-after-adaptation
  review_date: "2026-07-27"
  correction_note: "Removed workspace layout and command recipes and corrected stale membership evidence."
---

# Dependency management

## Repository authority

Use the repository-selected package manager and environment model. Project
declarations and the committed lockfile are the authority for supported
dependencies; prose and local environments are evidence, not substitutes.

Use uv only when the repository has selected it. The same policy applies to
other managers: respect their native declaration, resolution, and environment
boundaries rather than mixing tools opportunistically.

## Dependency intent

- Add a runtime dependency only when production code imports or requires it.
- Put test, lint, documentation, and build tools among development dependencies
  in the appropriate group.
- Prefer the narrowest direct dependency that owns the required behavior.
  Transitive availability is not a stable contract.
- Record optional features explicitly so a minimal installation does not pull
  integrations it does not use.
- Remove unused declarations and regenerate the lockfile with the selected
  manager so resolved state remains reproducible.

Review licenses, maintenance posture, platform support, and security exposure
in proportion to the dependency's role. A library at a sensitive boundary
deserves more scrutiny than a local development formatter.

## Lockfiles and workspaces

Commit the lockfile when the repository uses one, and update it intentionally
with the declaration that caused the change. Review both direct and transitive
deltas. Avoid broad lockfile churn unrelated to the requested work.

In a multi-package repository, derive workspace membership from executable
configuration rather than a directory convention or a guide that can become
stale. A shared lockfile is useful only when the selected workspace model
actually includes those packages.

## Environments and verification

Run checks in the repository-managed environment and keep local activation
details out of normative policy. Verify that a clean environment can install
from committed declarations and resolved state. Procedural command recipes,
cache repair, and manager-specific troubleshooting belong in a dedicated
workflow skill.
