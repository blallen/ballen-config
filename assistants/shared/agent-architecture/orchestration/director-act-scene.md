# Director, Act, and Scene

Director, Act, and Scene name three orchestration responsibilities. They are
not three independent model Agents, nor do they require three processes or
framework objects. Each responsibility can be deterministic code, one Agent,
or several cooperating components as long as its boundary remains explicit.

## Why the pattern exists

- **Capability confinement:** Different stages can be structurally limited to
  different tools, resources, and effects.
- **Resumability:** A long run can restart from a typed position without
  repeating every earlier stage.
- **Gated progress:** A failed check can retry, redirect, or stop the smallest
  relevant unit.
- **Context isolation:** Each stage receives the information it needs instead
  of inheriting the entire run history.

These concerns require different boundaries. Combining them in one ambient
Agent makes sequencing, authority, retry, and recovery difficult to inspect.

## Translation table

| Agentic term | Generic systems term |
| --- | --- |
| Director | Control plane or scheduler |
| Act | Bounded stage or handoff boundary |
| Scene | Retryable step or checkpoint |

The agentic terms remain primary because they emphasize that each level can
contain model-mediated work. The generic terms help readers map the pattern to
other workflow and distributed-systems designs.

## Director

The Director owns cross-Act sequencing, the workflow entry point, durable run
position, and the terminal workflow outcome. It decides which Act is eligible
to run and threads named handoff packages between Acts. It does not own the
domain work inside an Act.

### Keep sequencing in the Director

Requirement: A Director MUST own cross-Act ordering, start-position selection,
and terminal workflow assembly.

Rationale: One sequencing owner makes resume behavior and the final outcome
auditable without inspecting every Act.

Scope: Multi-Act runs, including deterministic, model-assisted, and mixed
implementations.

Exceptions: A single-Act system can omit a separate Director object while its
entry point still owns start and terminal semantics.

## Act

An Act owns one bounded objective, capability set, and typed handoff boundary.
It receives domain input plus explicitly granted infrastructure, runs its
internal Scenes, and returns one terminal envelope to the Director.

### Confine Act capabilities

Requirement: An Act MUST receive only the capabilities and dependencies named
by its entry-point contract.

Rationale: Prompt instructions cannot reliably enforce denial of an ambient
tool or resource that remains reachable in the call graph.

Scope: Every Act entry point and every dependency forwarded across an Act
boundary.

Exceptions: Shared run infrastructure can cross multiple Acts when its purpose
and scope are explicit; restricted domain capabilities still require separate
grants.

## Scene

A Scene is the smallest step that can be retried, gated, or redirected without
restarting its Act. It receives explicit attempt input and returns a typed
outcome to the Act's transition policy.

### Bound retry at the Scene

Requirement: A Scene SHOULD represent one independently checkable unit of work
with an explicit retry boundary.

Rationale: Smaller retry units avoid repeating successful work and make failure
feedback specific.

Scope: Model calls, deterministic transformations, review gates, and external
operations that can be isolated inside an Act.

Exceptions: Tightly coupled atomic operations can share one Scene when partial
completion cannot be retained safely.

## Responsibility matrix

| Concern | Director | Act | Scene |
| --- | --- | --- | --- |
| Primary purpose | Sequence bounded stages | Achieve one bounded objective | Complete one retryable step |
| State owned | Run position and Act results | Act-local progress and handoff | Attempt input and outcome |
| Capability reach | Scheduling and shared run infrastructure | Explicit Act capability set | Explicit subset needed by the step |
| Recovery | Resume, skip, or terminate across Acts | Assemble terminal Act result | Retry, gate, redirect, or escalate |
| Persistence boundary | Cross-Act cursor and results | Terminal envelope | Outcome or checkpoint needed for retry |

## Composition choices

The boundaries describe ownership, not deployment:

- a Director can be a deterministic workflow definition;
- an Act can be one Agent, a fixed Workflow, or a service operation;
- a Scene can be a model call, tool call, deterministic check, or human gate;
  and
- several roles can be implemented in one process without sharing undeclared
  context or capabilities.

### Preserve boundaries when colocated

Requirement: Colocated Director, Act, and Scene implementations MUST preserve
the same typed handoffs, capability grants, and transition ownership as
separately deployed components.

Rationale: Process boundaries do not create the architecture; explicit
contracts do.

Scope: In-process orchestrators and applications that combine several roles in
one package.

Exceptions: None. Colocation can simplify mechanics but not erase ownership.

## Relationship to Workflow, Agent, and Orchestrator

Director/Act/Scene placement is independent of the Workflow, Agent, and
Orchestrator responsibility categories. A deterministic Director can coordinate
Agent Acts. An Agent can implement one Act. A Workflow can implement several
Scenes. The overall system is an Orchestrator when coordination policy is a
first-class responsibility.
