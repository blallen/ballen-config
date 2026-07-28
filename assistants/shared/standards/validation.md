---
provenance:
  source_repository: plato
  source_revision: 6bb59d00ac01fd3238c091d90f2aea43872934c9
  source_paths:
    - .cursor/rules/104_data_validation.mdc
    - .cursor/rules/104_pydantic_style_guide.mdc
    - .cursor/rules/lessons_learned.mdc
    - .cursor/rules/lessons_promoted.mdc
  source_roles:
    .cursor/rules/lessons_promoted.mdc: provenance-only
  approved_decision: docs/superpowers/specs/2026-07-27-plato-engineering-standards-migration-design.md
  disposition: adapted
  portability_result: portable-after-adaptation
  review_date: "2026-07-27"
---

# Validation

## Separate the stages

Treat parsing, validation, normalization, and business rules as distinct
operations:

- Parsing establishes that input can be decoded into an expected structural
  form.
- Validation checks types, ranges, required relationships, and invariants.
- Normalization converts accepted variants into one documented canonical form.
- Business rules decide whether otherwise valid data is allowed in the current
  workflow or state.

Keep these stages visible in code and error reporting. A successful parse does
not establish trust, and normalization must not silently repair information
whose meaning is ambiguous.

Use explicit booleans when `None` has different semantics. Keep omission,
explicit null, and a present value distinct: `NotRequired` describes an omitted
mapping key, while a nullable type describes a present key that may be null.
Align nullability across storage, internal models, and external contracts.

## Trust boundaries

Identify trust boundaries before choosing a validation mechanism. External
requests, files, environment values, database records, cached payloads, and
messages may each have different guarantees. Validate at entry, then pass a
typed representation inward so downstream code does not repeat uncertain
checks.

For tabular data, validate required columns, data types, nullability, units, and
cross-column relationships before computation. Report row or field locations
without echoing sensitive values.

## Results and errors

Return structured results when callers need to distinguish multiple failures.
Include a stable code, a safe message, and an optional field or location.
Reserve exceptions for boundaries where continuing without valid data is not a
normal outcome.

Redact credentials, personal data, and confidential values from messages,
logs, traces, and serialized results. Preserve enough context to diagnose the
contract without reproducing the unsafe input.

## Configuration

Use validated configuration at the application boundary. Separate fixed
constants from deployment-dependent settings, define source precedence, reject
unknown settings when appropriate, and fail early with actionable errors.
Keep configuration discoverable and make one declaration the single source for
each setting. Secret retrieval and authentication flows are integration
concerns, not validation policy.
