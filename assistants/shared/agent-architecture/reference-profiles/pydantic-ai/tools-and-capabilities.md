# PydanticAI Tools and Capabilities

> **Status:** Conditional reference profile. Apply this document only after a
> repository selects PydanticAI and any delegation extension named below.

PydanticAI tools expose callable actions to a model. The portable capability
contract still governs effects, authority, lifecycle, and errors; this profile
describes the framework-specific registration choices.

## Registration and Arguments

Requirement: Every registered tool MUST present typed tool arguments, a bounded purpose, and a structured return contract.

Rationale: PydanticAI derives model-visible schemas from function signatures,
so precise types and descriptions directly shape tool selection and invocation.

Scope: Constructor-provided tools, decorated tools, and tools assembled through
a toolset.

Exceptions: A text return is acceptable when text itself is the complete domain
result and callers do not need structured fields.

## Shared Mutation

Requirement: Tools that mutate the same non-concurrency-safe resource MUST use sequential execution or an equivalent repository-owned serialization boundary.

Rationale: Parallel model tool calls can race even when each individual tool is
correct in isolation.

Scope: Shared files, mutable workspaces, transactions, and in-memory state.

Exceptions: Independent resources or concurrency-safe services can execute in
parallel when their contract permits it.

## Scoped Authority

Requirement: A run SHOULD assemble scoped toolsets and capability grants for its task instead of exposing every available tool.

Rationale: Least authority reduces accidental side effects and makes delegated
behavior easier to audit.

Scope: Parent agents, static specialists, and runtime-created child agents.

Exceptions: A small single-purpose agent can register its complete fixed tool
set when every tool is necessary for its stated role.

## Reviewed Dynamic Subagents

This guidance was reviewed against subagents-pydantic-ai 0.2.7. That release
includes lifecycle support for delegated tasks, cancellation and steering,
transient-failure retry behavior, and result collection. These are
package-version-reviewed capabilities, not framework-neutral guarantees.

Requirement: Each delegated specialist MUST execute as a separate child run with an explicit task, result contract, and lifecycle owner.

Rationale: A separate run has its own model interaction and failure boundary;
calling it from a parent does not merge the two executions.

Scope: Static subagent tools and runtime-created workers implemented with the
reviewed extension.

Exceptions: A local deterministic helper is an ordinary function or tool, not
a delegated child run.

## Context and Resources

Requirement: A child run MUST receive deliberate dependency cloning or mapping and an explicit resource-sharing policy.

Rationale: The parent message history, dependencies, resources, and permissions do
not become child context merely because the parent initiated the task.

Scope: Every delegated PydanticAI run.

Exceptions: Explicitly selected history or immutable dependencies can be mapped
into child input when the child contract requires them.

## Cancellation, Retry, and Collection

Requirement: A component starting delegated work MUST own Cancellation, Retry policy, and result collection until the work finishes or is deliberately detached.

Rationale: Background work without an owner can outlive its authority, repeat
side effects, or lose failures.

Scope: Concurrent and background child runs.

Exceptions: Deliberately detached durable work can transfer ownership to a
documented scheduler or persisted orchestration record.

Retry policy distinguishes transient failures from validation, authorization,
usage-limit, and cancellation outcomes. It also preserves logical task identity
while recording each attempt separately.

## References

- [PydanticAI tools](https://ai.pydantic.dev/tools/)
- [PydanticAI toolsets](https://ai.pydantic.dev/toolsets/)
- [subagents-pydantic-ai documentation](https://github.com/vstorm-co/subagents-pydantic-ai#readme)
- [subagents-pydantic-ai release history](https://github.com/vstorm-co/subagents-pydantic-ai/releases)
