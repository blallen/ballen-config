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
- On Python 3.12, do not use `from __future__ import annotations`. Prefer
  `Self` for methods that return the current class, and quote only unavoidable
  forward references caused by definition order or circular imports.
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
- Annotate a module-level binding that is set once at import and never
  reassigned with `Final[T]`, whether it is a value constant, a compiled
  pattern, a sentinel, or a configured singleton. `Final` prevents rebinding but
  does not make the bound object immutable, so pair a value constant with an
  immutable container such as a read-only mapping proxy, a `frozenset`, or a
  tuple. A singleton whose internals legitimately mutate still takes `Final[T]`,
  because the handle is what must not be replaced.
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
- Provide a domain exception hierarchy when callers need to catch failures at
  different granularity, rather than reusing one broad built-in type everywhere.
- Do not use `assert` to enforce a production contract. Assertions can be
  disabled at runtime, so raise the exception the caller should handle.
- When an exception contract changes, update downstream handlers, tests, and
  user-facing error translation in the same change.
- Acquire files, network responses, locks, and similar resource handles with
  context managers or an equivalent lifecycle abstraction.
- Keep cleanup reliable on success, failure, and cancellation. Never depend on
  garbage collection for externally visible cleanup.

## Logging

Use the logging library the repository has selected and keep its setup in one
place rather than configuring handlers per module.

Preserve the stack trace when logging a caught exception. Pass exception
information through the logging call's own mechanism instead of interpolating the
exception into the message, which records the text and discards the traceback.
Log at warning level when the failure is recoverable and at error level with
exception information when it is not. When the handler re-raises, let the
propagated exception carry the traceback rather than logging it twice.

Keep an exception bound to a name only when something outside the logging call
references it.

## Serialization

Place serialization and representation behavior with the domain type that owns
the data. Keep wire formats explicit, stable, and separate from display
representations. Validate data when it crosses a trust boundary rather than
assuming that a successful decode establishes correctness.
