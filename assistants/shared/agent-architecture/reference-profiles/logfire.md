# Logfire Observability Profile

> **Status:** Conditional reference profile. Adopt this guidance only when a
> repository selects Logfire for agent observability.

- logfire 4.36.0
- Reviewed on 2026-07-31

This profile applies the core observability and privacy contracts to Logfire.
It covers semantic spans and bounded diagnostics, not infrastructure setup.

## Span Names and Attributes

Requirement: Agent instrumentation SHOULD use low-cardinality span names and place run-specific values in attributes.

Rationale: Stable names preserve useful grouping while high-cardinality names
make traces difficult and expensive to aggregate.

Scope: Agent runs, tool calls, delegated work, transitions, and evaluations.

Exceptions: A bounded enum value can appear in a span name when the repository
uses it consistently and verifies its cardinality.

Useful attributes include architecture category, Director/Act/Scene position,
tool name, outcome category, attempt number, and durable run identifier. Record
only fields needed for diagnosis or evaluation.

## Exception Recording

Requirement: Code that catches an operational exception MUST preserve exception recording and mark the active span with an error outcome before translating the failure.

Rationale: A translated domain error is useful to callers, while the original
exception and status are needed to diagnose the underlying failure.

Scope: Service boundaries, tools, delegated runs, and orchestration loops that
handle an exception instead of letting instrumentation capture it naturally.

Exceptions: Expected domain outcomes represented as typed results are recorded
as outcomes rather than exceptions.

## Bounded Capture

Requirement: Instrumentation MUST use bounded input and output capture with documented size, field, and retention limits.

Rationale: Agent prompts and results can be large or sensitive, and complete
capture is rarely necessary to understand control flow.

Scope: Model requests, model responses, tool arguments, tool results, handoffs,
and evaluation evidence.

Exceptions: A dedicated test environment can temporarily capture a larger
fixture after privacy review when the evidence is synthetic or approved.

## Scrubbing and Privacy

Requirement: An observability change MUST complete scrubbing and privacy review before recording new payload fields.

Rationale: Instrumentation runs across many paths and can silently widen the
audience or retention of data.

Scope: New attributes, events, request capture, response capture, and exported
trace data.

Exceptions: Low-sensitivity counters and bounded enums can use a standing
reviewed policy when they contain no user or payload data.

## Identity and Payload Decisions

Requirement: An integration MUST treat payload capture and user identity propagation as explicit security decisions, never defaults.

Rationale: Diagnostic convenience does not establish a legitimate need to
collect content or connect traces to a person.

Scope: Automatic and manual Logfire instrumentation.

Exceptions: A repository can enable a reviewed field for a defined purpose,
audience, and retention period with an owner responsible for reassessment.

## Framework Instrumentation

Requirement: An integration SHOULD enable optional framework instrumentation only when its emitted fields and volume are understood.

Rationale: Automatic integrations can add useful model and HTTP spans, but they
can also duplicate events or collect more detail than the application needs.

Scope: PydanticAI and other supported framework integrations.

Exceptions: A local development profile can use broader synthetic-data tracing
when it cannot publish or persist that configuration as a production default.

## References

- [Logfire documentation](https://pydantic.dev/docs/logfire/)
- [Logfire changelog](https://github.com/pydantic/logfire/blob/main/CHANGELOG.md)
