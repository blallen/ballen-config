# Delegation Isolation Matrix

Static agent-as-tool delegation and dynamic subagents both create separately
bounded runs. Their defaults are isolation; sharing requires an explicit
contract. Dynamic delegation adds runtime identity and lifecycle decisions.

## Matrix

| Dimension | Static agent as tool | Dynamic subagent |
| --- | --- | --- |
| Instructions | Fixed with the declared specialist; changes through construction | Supplied or selected by a reviewed worker role or factory |
| Message history | Isolated; map selected messages into typed input | Isolated; apply an explicit context-mapping policy |
| Input | Typed tool arguments define the complete task | Typed task plus runtime role or worker-definition input |
| Output | Structured tool result returned to the parent | Structured result collected synchronously or through task identity |
| Dependencies | Construct or map a child dependency container | Factory constructs or maps dependencies per worker role |
| Shared resources | Grant named resources deliberately | Apply a resource-sharing policy per worker or capability |
| Tools | Fixed specialist toolset | Toolsets selected by role, registry, or factory policy |
| Permissions | Explicit child capability set | Explicit capability grants constrained by creation policy |
| Lifecycle | Usually bounded by one tool call | Created, registered, observed, joined, detached, or retired explicitly |
| Persistence | Usually only the parent result | Worker definition, task identity, result, and continuation when durable |
| Cancellation | Parent tool wrapper propagates or records cancellation | Creator retains cancellation ownership or transfers it explicitly |
| Errors | Wrapper translates child faults into the tool contract | Task system records worker faults and collection semantics |

### Default to isolation

Requirement: Delegated runs MUST treat every matrix dimension as isolated until
a named contract maps or shares it.

Rationale: Sharing one dimension does not imply that any other dimension is
safe or necessary to share.

Scope: Fixed specialists, dynamic subagents, nested workers, and background
delegation.

Exceptions: Immutable process-wide utilities with no data, authority, or
lifecycle can be common implementation details outside the delegation contract.

## Choosing a mechanism

Use a static Agent as tool when the specialist roster and contract are stable at
construction time. Use a dynamic subagent when the system needs runtime role
creation, registry selection, background lifecycle, or nested delegation.

### Prefer the simpler reviewed surface

Requirement: A design SHOULD choose static delegation unless runtime creation
or lifecycle policy provides a concrete capability the system needs.

Rationale: Dynamic delegation adds identity, concurrency, cancellation,
persistence, and permission-policy obligations.

Scope: Choosing how a parent delegates model-mediated work.

Exceptions: A platform designed specifically for open-ended runtime composition
can make dynamic delegation its reviewed default.

## Orchestration placement

Delegation mechanism and Director/Act/Scene placement are orthogonal choices. A
Director can call a static specialist; an Act can create dynamic subagents; a
Scene can invoke one fixed Agent tool. The placement describes orchestration
responsibility, while the mechanism describes how a delegated run is created.

### Describe both axes

Requirement: Architecture documentation SHOULD name both the delegation
mechanism and its Director/Act/Scene placement when either affects authority,
state, or recovery.

Rationale: Naming only one axis hides where lifecycle and capability decisions
are owned.

Scope: Designs containing delegated model runs.

Exceptions: A simple Agent with one fixed specialist can document the typed tool
contract without introducing the full orchestration vocabulary.
