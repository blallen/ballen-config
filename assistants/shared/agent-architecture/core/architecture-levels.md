# Workflow, Agent, and Orchestrator

Use these categories to describe where control decisions live. They are
responsibility boundaries, not maturity scores: a small Workflow can be more
production-ready than a large Orchestrator.

## Classification principle

### Classify by responsibility

Requirement: A system MUST be classified by the most autonomous control
responsibility it owns, not by its number of model calls, tools, or files.

Rationale: Observable responsibilities remain meaningful when implementation
details change.

Scope: Architecture descriptions, design reviews, and README summaries for
systems that use models or delegated workers.

Exceptions: None. Secondary labels can describe implementation techniques but
cannot replace the responsibility category.

## Workflow

A Workflow follows a predetermined control path. Individual steps can use a
model to transform, classify, extract, or draft, but the surrounding program
chooses the order, branching rules, and completion condition.

Typical signals include:

- steps and transitions are known before a run starts;
- retries and fallbacks are encoded by deterministic policy;
- tools are invoked by the workflow or by a tightly bounded model-assisted
  step; and
- no component decides which new specialist should exist or run next.

### Keep deterministic control explicit

Requirement: A Workflow SHOULD keep sequencing, branching, retry limits, and
terminal conditions in inspectable deterministic code or configuration.

Rationale: The category is useful only when operators can identify the control
path independently of model behavior.

Scope: Workflow-level control decisions. A model-assisted step can still make
bounded decisions inside its declared input and output contract.

Exceptions: Exploratory prototypes can begin with a model-described sequence
when the uncertainty is explicit and the prototype is not presented as a
reliable Workflow.

## Agent

An Agent makes model-mediated decisions and takes actions inside an explicit
set of instructions, tools, dependencies, and permissions. Its autonomy is
bounded by the capability surface supplied for the run.

Typical signals include:

- the model chooses among tools or strategies;
- inputs and outputs have stable boundary types;
- side effects are constrained by explicit capabilities; and
- a service entry point owns construction, execution, and error translation.

### Bound agent autonomy

Requirement: An Agent MUST receive an explicit capability boundary and MUST
return a documented result or expected non-completion outcome.

Rationale: Model-directed behavior is reviewable only when both the reachable
effects and the observable outcomes are bounded.

Scope: Every production run of an Agent, including an Agent invoked by a
Workflow, another Agent, or an Orchestrator.

Exceptions: None for consequential effects. A local experiment can use a
smaller result contract when it has no external side effects.

## Orchestrator

An Orchestrator owns first-class coordination policy across Agents, Acts, or
runtime-created workers. It decides what runs, when it runs, what context or
capabilities cross a boundary, and how delegated work is collected, cancelled,
retried, or resumed.

Typical signals include:

- runtime selection or creation of specialists;
- coordination across multiple independently bounded runs;
- typed handoffs between stages;
- lifecycle and cancellation ownership; and
- durable position or recovery policy for multi-stage work.

### Make coordination an explicit contract

Requirement: A system MUST use the Orchestrator category when scheduling,
delegation lifecycle, handoff policy, or cross-agent recovery is a first-class
responsibility of the system.

Rationale: Hiding coordination inside an ordinary Agent obscures permissions,
state ownership, failure handling, and operational cost.

Scope: Systems that coordinate independently bounded Agents or dynamically
selected workers.

Exceptions: A predetermined Workflow can call several fixed Agents without
becoming an Orchestrator when deterministic workflow code retains all
coordination decisions.

## Comparison

| Concern | Workflow | Agent | Orchestrator |
| --- | --- | --- | --- |
| Primary control owner | Deterministic program | Model inside a bounded run | Coordination policy |
| Delegation | Predetermined calls | Optional fixed specialist | First-class scheduling or lifecycle |
| State | Step inputs and outputs | Run context and result | Cross-run position and handoffs |
| Recovery | Encoded branch or retry | Run-level failure contract | Cross-stage retry, resume, or escalation |
| Capability boundary | Per step | Per run | Per Agent, Act, or worker |

## Fixed-specialist boundary

A parent Agent can expose one predeclared specialist through a tool. That fixed
specialist call does not make the parent an Orchestrator when the parent owns no
general scheduling, worker lifecycle, or cross-specialist coordination policy.

### Do not infer orchestration from one tool call

Requirement: An architecture description SHOULD keep the Agent category when a
parent invokes one fixed specialist through a typed tool and has no first-class
coordination responsibility.

Rationale: Delegation mechanism and architecture category are separate axes;
conflating them overstates system complexity.

Scope: Static agent-as-tool delegation with a predeclared specialist.

Exceptions: Use the Orchestrator category when the parent selects among
specialists, controls their lifecycle, coordinates concurrent work, or owns
durable cross-run recovery.

## Upgrade signals

Move from Workflow to Agent when the model must choose actions or strategies
inside an explicit capability boundary. Move from Agent to Orchestrator when
coordination itself becomes a durable, testable responsibility rather than an
incidental tool call.

Do not upgrade a category merely because a system grows more files, adds a
model-assisted step, or calls the same fixed specialist more often.
