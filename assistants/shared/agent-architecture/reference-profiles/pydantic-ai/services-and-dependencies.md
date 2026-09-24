# PydanticAI Services and Dependencies

> **Status:** Conditional reference profile. Apply this document only after a
> repository selects PydanticAI.

PydanticAI passes a typed dependency value through `RunContext`. Repository
services can use that mechanism while keeping framework details out of their
public interfaces.

## Typed Dependency Container

Requirement: An agent with external services or run-scoped state MUST declare a typed dependency container and access it through `RunContext`.

Rationale: One declared shape makes available dependencies reviewable and keeps
tools from reaching into ambient process state.

Scope: Database clients, service clients, repositories, clocks, settings, and
other values used during an agent run.

Exceptions: An agent with no dependencies can use PydanticAI's dependency-free
form rather than declaring an empty container.

## Public Service Boundary

Requirement: A public service function SHOULD accept domain inputs and dependencies while hiding PydanticAI run mechanics from its callers.

Rationale: Callers depend on a stable application contract instead of
framework-specific result wrappers or context construction.

Scope: Entry points called by application code, APIs, jobs, or workflows.

Exceptions: Framework integration tests can call the agent directly when the
framework behavior is the subject under test.

## Intentional Factories

Requirement: A service that needs dynamic construction MUST expose that variation through a named factory with validated inputs.

Rationale: A named factory distinguishes product-driven variation from
accidental per-call reconstruction.

Scope: Runs that vary model, instructions, toolsets, or output schemas by
validated request or project configuration.

Exceptions: Stable agents remain startup-fixed and need no factory.

## Delegated Dependencies

Requirement: A delegated run MUST clone or map its dependency container explicitly instead of assuming parent dependencies are inherited.

Rationale: Explicit mapping prevents a child from receiving authority or
mutable state that its task does not require.

Scope: Agent-as-tool calls and runtime-created PydanticAI child agents.

Exceptions: An immutable dependency value can be shared by reference when the
sharing policy names it and both lifecycles are bounded by the same owner.

## Mutable Resources

Requirement: Services with mutable resources MUST define lifecycle ownership and a sharing policy before more than one run can access them.

Rationale: Concurrent mutation without ownership can corrupt state, leak
transactions, or close a resource while another run still uses it.

Scope: Clients with connection state, file handles, workspaces, caches, and
in-memory mutable stores.

Exceptions: A concurrency-safe pool can be shared when its owner outlives every
run and shutdown waits for active borrowers.

## References

- [PydanticAI dependencies](https://ai.pydantic.dev/dependencies/)
- [PydanticAI agents](https://ai.pydantic.dev/agents/)
- [PydanticAI release history](https://github.com/pydantic/pydantic-ai/releases)
