# Agent Component README Template

This is an informative, copy and adapt template. Replace every prompt with
repository-specific facts, delete sections that genuinely do not apply, and
link to executable configuration instead of duplicating it.

Label each code block **Runnable** when it executes as shown or
**Illustrative** when it communicates only a pattern, interface, or flow.

## Purpose

State the component's responsibility, intended users or callers, and the
problem it owns. Name whether it is a Workflow, Agent, or Orchestrator.

## Architecture

Describe the component boundary and its place in the larger system. For an
Orchestrator, map its Director, Acts, and Scenes. Link to a diagram only when it
clarifies relationships that prose cannot show compactly.

## Inputs and Outputs

List each public input and output shape, validation boundary, and compatibility
expectation. Distinguish expected domain outcomes from operational failures.

## Dependencies

Name required services, injected values, and lifecycle owners. Explain which
dependencies are constructed at startup, per run, or per delegated task.

## Tools and Capabilities

List model-visible tools and other capabilities. Summarize purpose, authority,
side effects, recovery behavior, and any concurrency constraints for each one.

## State and Persistence

Describe transient and durable state, ownership, checkpoint boundaries, resume
behavior, retention, and cleanup. Say explicitly when the component is
stateless.

## Control Flow

Explain the normal path, branches, handoffs, retries, cancellation, and terminal
outcomes. Link to transition or delegation contracts where applicable.

## Errors

Describe typed domain outcomes, translated operational errors, retryability,
and the component responsible for reporting or escalation.

## Testing and Evaluation

Summarize deterministic tests, contract checks, integration coverage,
evaluation dimensions, fixtures, and the commands used to verify the component.

## Limitations

Record known exclusions, unsupported modes, scaling assumptions, unresolved
risks, and boundaries that a caller could otherwise misinterpret.

## References

Link to the framework-neutral architecture library, adopted reference profiles,
executable repository configuration, and primary external documentation.
