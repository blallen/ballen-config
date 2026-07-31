# MCP Boundaries for Agents

Model Context Protocol (MCP) provides a process and protocol boundary through
which a client can discover and invoke tools. Use it when independent lifecycle,
language neutrality, remote composition, or standardized discovery matters more
than the simplicity of a direct in-process call.

## Direct invocation or MCP

Direct invocation is usually simpler inside one trusted process. MCP is useful
when tools need an independently operated server, multiple client types,
protocol-level discovery, or a boundary that can evolve separately from the
Agent implementation.

### Choose the smallest sufficient boundary

Requirement: A design SHOULD use MCP only when a protocol boundary provides a
named interoperability, lifecycle, or isolation benefit.

Rationale: A server boundary adds deployment, transport, compatibility, and
failure modes that an in-process call does not have.

Scope: Decisions about exposing Agent services or domain tools through MCP.

Exceptions: A platform can standardize on MCP for local composition when its
operational tooling makes that boundary cheaper than bespoke integration.

## Typed request and response contracts

An MCP tool should accept a typed request and response contract that contains
all required input and all observable output. The wrapper translates protocol
data to a stable service entry point and translates the service result back to
the protocol.

### Keep wrappers thin

Requirement: An MCP wrapper MUST validate protocol input, invoke one stable
service contract, and return a structured protocol result.

Rationale: Thin wrappers keep business behavior reusable and prevent protocol
concerns from leaking into the Agent package.

Scope: MCP tools that expose Agent services or domain operations.

Exceptions: A protocol-only introspection tool can implement its small operation
inside the wrapper when no reusable domain behavior exists.

## Lifecycle and registration

Server startup owns transport configuration, resource initialization, tool
registration, and shutdown. Tool modules own request/response translation and
service invocation. Registration should not construct a different hidden Agent
for each call unless request-scoped construction is the declared design.

### Separate registration from behavior

Requirement: MCP server registration MUST be separated from reusable business
logic and Agent service execution.

Rationale: Separation permits unit tests without a server and keeps startup
composition from becoming the only callable API.

Scope: Server startup, tool registration, resource lifecycle, and shutdown.

Exceptions: A minimal single-purpose server can colocate files while preserving
separate functions for registration and behavior.

## Capability discovery and grants

Capability discovery tells a client which tools exist. It does not authorize
every discovered tool for every caller or delegated worker. Exposure,
authorization, and per-run grants are distinct decisions.

### Preserve least capability

Requirement: Capability discovery MUST NOT be treated as an implicit grant of
all discovered effects.

Rationale: Discovery describes an interface surface; authority depends on the
client, run, environment, and effect policy.

Scope: MCP clients, servers, Agent toolsets, and delegated workers.

Exceptions: A fully trusted single-user local server can use one static grant
when that trust boundary is explicit.

## Expected errors and transport faults

Expected domain outcomes belong in the structured response. Transport faults,
server unavailability, invalid protocol messages, and unexpected implementation
failures belong in the protocol error path with safe diagnostics.

### Distinguish domain outcomes from faults

Requirement: MCP tools MUST return expected non-completion as structured domain
results and reserve protocol errors for transport faults or failed contract
execution.

Rationale: Clients need different retry and reporting policy for a valid
negative result than for a broken connection or server.

Scope: Tool invocation, protocol adapters, clients, and orchestration recovery.

Exceptions: A protocol specification can mandate a particular error envelope;
the envelope must still carry a stable distinction between domain and transport
failure.

## Timeout, cancellation, and retry

Clients and servers should propagate deadlines and cancellation where the
transport supports them. Retry policy belongs with the caller that understands
idempotency and whether an interrupted effect may already have completed.

### Make interruption observable

Requirement: An MCP boundary SHOULD expose timeout and cancellation outcomes
without claiming that interrupted work was rolled back unless that guarantee is
real.

Rationale: A disconnected client does not prove the server or downstream effect
stopped.

Scope: Long-running tools, delegated Agent runs, network calls, and write
operations.

Exceptions: A bounded read-only operation can use the transport's default
deadline when that behavior is documented for clients.

## Observability and compatibility

Record stable tool identity, outcome kind, duration, retry attempt, and safe
correlation identifiers. Avoid high-cardinality operation names and unbounded
payload capture. Treat request and response schema changes as compatibility
changes.

### Version observable contracts

Requirement: Breaking changes to MCP request, response, or error semantics MUST
have an explicit compatibility and rollout plan.

Rationale: Independent clients and servers can be upgraded at different times.

Scope: Published tools, shared servers, generated clients, and persisted
requests.

Exceptions: An unreleased single-consumer prototype can change atomically with
its only client.
