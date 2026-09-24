# Agent Layers and Dependency Direction

An Agent package is easiest to change when stable domain contracts sit below
framework construction and external adapters. The layers below are conceptual;
a small package can combine files while preserving the same boundaries.

## Construction

Construction selects instructions, model configuration, tools, capabilities,
dependency types, and result types. Long-lived applications usually construct
a fixed Agent at startup. A factory is appropriate when those choices are
intentionally different for each request or delegated task.

### Centralize construction

Requirement: Agent construction MUST have one discoverable owner for each
runtime role.

Rationale: Scattered construction produces agents with silently different
instructions, tools, or permissions.

Scope: Startup composition, request-scoped factories, and delegated worker
factories.

Exceptions: Tests can construct reduced agents through explicit fixtures that
name the substituted dependencies or capabilities.

## Models and expected errors

Use validated boundary data to describe inputs, outputs, handoffs, and tool
results. Keep runtime resources such as clients, stores, and clocks in a
separate dependency container. These concerns can use different type mechanisms
because runtime resources are not serialized contracts.

### Separate data from resources

Requirement: Validated boundary data MUST be separated from runtime resources
in public Agent contracts.

Rationale: Mixing them makes serialization, persistence, test substitution, and
resource lifecycle ambiguous.

Scope: Agent inputs, outputs, dependency containers, tool results, and handoff
packages.

Exceptions: A trivial pure function with no live dependency container can use
one validated input object for all of its data.

Expected domain outcomes belong in typed results. Exceptions represent faults
that prevent the contract from being evaluated or returned correctly.

## Tools and capabilities

Tools are Agent-facing operations with typed inputs, documented semantics, and
structured results. Capabilities group or grant reusable behavior such as
delegation, file access, external lookup, or workflow support.

### Keep business logic below tools

Requirement: Tool implementations SHOULD remain thin and delegate reusable
business behavior to services or domain functions.

Rationale: Thin tools keep model-facing descriptions stable while allowing the
same behavior to be tested and reused without an Agent runtime.

Scope: Tools that perform domain work, access external systems, or wrap service
operations.

Exceptions: A self-contained pure transformation can live directly in a tool
when extracting it would add indirection without reuse or test value.

## Service entry points

A service entry point accepts ordinary typed input, supplies dependencies,
executes the Agent, and translates framework results into the package's public
result contract. Callers should not need to know how the Agent framework stores
messages, usage, or run state.

### Hide framework mechanics

Requirement: Public service entry points MUST hide framework-specific run
mechanics from ordinary callers.

Rationale: Stable service boundaries permit framework upgrades, deterministic
tests, and non-Agent reuse without changing every consumer.

Scope: Application code, HTTP handlers, jobs, MCP wrappers, and other packages
that invoke an Agent.

Exceptions: Framework integration tests and framework-specific reference
profiles can call lower-level APIs directly when that dependency is explicit.

## External adapters

Adapters translate external protocols into service input and translate service
results into protocol responses. Examples include an HTTP route, command-line
entry point, queue consumer, or MCP tool wrapper.

### Keep adapters transport-focused

Requirement: External adapters SHOULD validate protocol concerns and delegate
domain execution to a service entry point.

Rationale: Combining transport, Agent execution, and business logic creates
duplicate behavior and inconsistent errors across entry points.

Scope: Every externally reachable invocation path.

Exceptions: A demonstration adapter can call a stable Agent service directly
without adding another application layer.

## Dependency direction

Dependencies point inward toward stable foundations:

```text
external adapter -> service entry point -> agent construction -> tools
                                             |                |
                                             v                v
                                      dependency types -> domain services
                                             |
                                             v
                                  models, errors, constants
```

Startup composition can import role-specific builders to assemble a fixed
runtime graph. The builders do not import back from startup composition.

### Preserve inward imports

Requirement: Domain services, models, and errors MUST NOT import the top-level
Agent construction or external adapters.

Rationale: Inward dependency direction prevents cycles and keeps domain logic
usable without initializing the Agent runtime.

Scope: Package imports and dependency injection relationships.

Exceptions: A startup-only composition module can import builders from several
roles because composition is its sole responsibility.

## Public API

The package root exposes stable request, result, expected-error, and service
entry-point symbols. Construction helpers and framework objects remain private
unless consumers are expected to configure them directly.

### Export only stable contracts

Requirement: A package public API SHOULD expose the smallest stable set of
boundary types and service entry points needed by consumers.

Rationale: Narrow exports prevent internal framework choices from becoming
compatibility promises.

Scope: Package-root exports, generated API references, and consumer imports.

Exceptions: A framework extension package can deliberately expose construction
types when extension is its documented purpose.

## Example package layout

```text
assistant/
├── __init__.py
├── agent.py
├── service.py
├── tools.py
├── models.py
├── errors.py
└── adapters/
    ├── mcp.py
    └── web.py
```

The file names are illustrative. The dependency and ownership boundaries are
the contract.
