# Pydantic

## Choose the boundary deliberately

Use Pydantic v2 when data crosses an external, serialized, or otherwise
untrusted boundary and runtime validation has value. A boundary model should
make the accepted shape and invariants explicit.

Use `TypedDict`, dataclasses, or ordinary classes for trusted internal mappings
and runtime dependency containers when repeated validation would add ceremony
without reducing risk. Do not turn every in-memory object into a validation
model.

## Model shape

- Default application-owned boundary models to `extra="forbid"` so unknown
  input is rejected deliberately. Relax that rule only for a documented
  compatibility boundary.
- Give non-obvious fields concise field descriptions. Explain domain meaning,
  units, allowed ranges, and jargon rather than restating the type.
- Use `Literal` for a small closed set of wire values and an enum when the
  choices have shared behavior or are reused broadly. Prefer discriminated
  unions when one field selects among distinct model shapes.
- Prefer composition over inheritance for adding groups of fields or behavior.
  Inheritance is appropriate only for a genuine substitutable relationship.
- Represent credentials and comparable sensitive values with `SecretStr` or an
  equivalent secret type, and keep their serialized and logged forms redacted.

## Validation and lifecycle

- Use field validators for one field and model validators for cross-field
  invariants. Prefer after-validation for rules that operate on typed values;
  use before-validation only for intentional raw-input normalization.
- Keep validators deterministic and free of network or filesystem effects.
  Business workflows belong outside the model.
- `model_post_init` is supported as an instance lifecycle hook.
- Use that hook for local initialization that depends on a fully constructed
  instance, not as a substitute for validation or external orchestration.

## Serialization and settings

Define serialization at the model boundary and choose explicit modes, aliases,
and exclusion rules. Test the representation that consumers actually receive.
Avoid persisting redundant derived fields when a property can calculate them
without creating contradictory state.

Use `pydantic-settings` only when the repository declares that separate
dependency and validated environment-backed settings are appropriate. Keep
fixed constants out of environment configuration, document precedence among
configuration sources, and apply a consistent `env_prefix` convention across
related settings classes. Avoid global settings singletons when explicit
dependency injection is clearer.

The [validation standard](validation.md) owns trust-boundary analysis,
normalization, redaction, structured validation results, and configuration
policy.
