---
provenance:
  source_repository: plato
  source_revision: 6bb59d00ac01fd3238c091d90f2aea43872934c9
  source_paths:
    - AGENTS.md
    - .cursor/rules/104_python_style_guide.mdc
    - .cursor/rules/lessons_learned.mdc
    - .cursor/rules/lessons_promoted.mdc
  source_roles:
    .cursor/rules/lessons_promoted.mdc: provenance-only
  approved_decision: docs/superpowers/specs/2026-07-27-plato-engineering-standards-migration-design.md
  disposition: corrected
  portability_result: portable-after-adaptation
  review_date: "2026-07-27"
  correction_note: "Removed repository-specific mandates and corrected class-attribute documentation claims."
---

# Python

## Scope and version

Use Python 3.12 unless repository configuration selects another supported
version. Treat executable configuration as authoritative for interpreter,
formatter, linter, and type-checker behavior.

## Types and contracts

- Add type hints to public and internal function signatures where they clarify
  contracts. Prefer precise unions and collection types over broad `Any`.
- Use `TypedDict` for controlled mapping shapes, especially trusted internal
  data that does not need runtime validation. Use a validated model at
  untrusted or serialized boundaries.
- Distinguish omitted mapping keys from keys whose value may be `None`; use
  `NotRequired` when callers may omit a key.
- Use named return types when multiple returned values need semantic names.
- Preserve object identity when callers may depend on a supplied instance.
  Derive duplicated identity fields instead of storing values that can diverge.
- Disable generated equality when a value contains arrays or other objects
  without scalar equality, and document the reason for that choice.

## Structure and naming

- Choose naming that describes the domain concept, not a vendor or incidental
  implementation. Disambiguate generic names such as `model`, `client`, and
  `result` when several meanings coexist.
- Keep imports explicit and organized. Avoid import-time side effects and
  circular dependencies; move shared contracts to the smallest stable module
  that owns them.
- Use immutable values for constants when practical. A name marked `Final`
  prevents rebinding but does not make a mutable value immutable.
- Use named constants or enums for repeated state strings. Check `None`
  explicitly when zero, `False`, or an empty collection is a valid falsy value.
- Prefer readable control flow. Extract dense conditionals into named helpers,
  and use comprehensions only when the transformation remains straightforward.
- Name or document intentionally excluded cases so a narrow implementation is
  not mistaken for accidental incompleteness.
- Isolate heavy optional dependencies behind the feature that needs them.
  Importing a core module must not require an unused optional integration.

## Errors and resources

- Raise explicit exceptions that describe the failed contract. Preserve the
  original cause when translating lower-level failures, and do not catch broad
  exceptions unless the boundary can recover or add meaningful context.
- When an exception contract changes, update downstream handlers, tests, and
  user-facing error translation in the same change.
- Acquire files, network responses, locks, and similar resource handles with
  context managers or an equivalent lifecycle abstraction.
- Keep cleanup reliable on success, failure, and cancellation. Never depend on
  garbage collection for externally visible cleanup.

## Serialization

Place serialization and representation behavior with the domain type that owns
the data. Keep wire formats explicit, stable, and separate from display
representations. Validate data when it crosses a trust boundary rather than
assuming that a successful decode establishes correctness.
