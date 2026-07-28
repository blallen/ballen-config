---
provenance:
  source_repository: plato
  source_revision: 6bb59d00ac01fd3238c091d90f2aea43872934c9
  source_paths:
    - .cursor/rules/104_pythonic_apis.mdc
    - .cursor/rules/lessons_learned.mdc
    - .cursor/rules/lessons_promoted.mdc
  source_roles:
    .cursor/rules/lessons_promoted.mdc: provenance-only
  approved_decision: docs/superpowers/specs/2026-07-27-plato-engineering-standards-migration-design.md
  disposition: corrected
  portability_result: portable-after-adaptation
  review_date: "2026-07-27"
  correction_note: "Removed framework mandates and made optional HTTP affordances context-dependent."
---

# API design

## Contracts first

Design small typed contracts around caller needs. Separate transport schemas
from domain behavior when they evolve for different reasons, and avoid exposing
internal persistence shapes as a public contract. Names should communicate
purpose and stability rather than the framework that implements them.

## HTTP semantics

- Match methods to their semantics: safe reads, creation, replacement, partial
  updates, and deletion should behave consistently with documented HTTP
  expectations.
- Use status codes consistently and distinguish client errors from server
  failures. A successful response must not conceal partial failure.
- Return structured errors with a stable machine-readable code, a safe human
  message, and optional field-level detail. Do not leak internal traces or
  sensitive input.
- Distinguish a not-found resource from a known resource that is not-ready.
  Callers need different recovery behavior for absence and incomplete state.
- Define pagination for collections that may grow. Make ordering deterministic,
  document cursor or offset behavior, and state whether results are snapshot
  consistent.
- Give retried writes an explicit idempotency policy. When idempotency keys are
  supported, define their scope, lifetime, conflict behavior, and response
  replay semantics.

## Compatibility

Treat public request and response shapes as versioned contracts. Prefer
additive evolution, preserve the meaning of existing fields, and publish a
migration path before removing behavior. Distinguish omitted fields from
explicit null values when that difference affects compatibility, and align
nullability with the underlying domain and storage model.

Return non-lossy result contracts when callers may need detail. Do not replace
useful records or failure information with only an aggregate count; derive
summary values from the richer result instead.

Keep transport, application, and domain layers independently testable. A web
framework, asynchronous stack, schema generator, or hypermedia strategy may be
useful, but none is a universal requirement. Choose optional frameworks and
related links only when they improve the concrete API and its consumers.
