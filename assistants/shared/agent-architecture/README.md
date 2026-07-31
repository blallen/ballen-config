# Agent Architecture Reference Library

This library gives engineers and reviewers a shared language for designing,
documenting, and evaluating agent systems. It separates portable architecture
contracts from optional technology profiles and visibly unfinished guidance.

Use it when starting a system, reviewing an existing design, or defining a
handoff between independently owned components. It is a passive documentation
library; adoption happens through repository decisions and executable local
configuration.

## Authority and Adoption

Requirement: A repository adopting this library MUST identify which normative documents and conditional profiles govern its implementation.

Rationale: Explicit adoption prevents readers from guessing whether a portable
contract, optional profile, or unfinished stub controls a design decision.

Scope: Repositories that cite or install this library as architecture guidance.

Exceptions: A design exploration can cite individual documents without adopting
the whole library when it labels the scope and authority of each citation.

Core, orchestration, and delegation documents are normative within the adopted
scope. Reference profiles are conditional on an explicit technology choice.
The README template is informative, and stubs are non-normative drafts.

## Architecture Categories

| Category | Primary responsibility | Typical shape |
| --- | --- | --- |
| Workflow | Execute a predetermined sequence | Deterministic code, jobs, or pipelines |
| Agent | Choose actions within a bounded task | One model-guided loop with explicit tools |
| Orchestrator | Coordinate multiple bounded units | Durable control flow, handoffs, and recovery |

These are responsibility categories rather than maturity levels. A Workflow can
be production-critical, and a single Agent does not become an Orchestrator just
because it calls one specialist.

## Director, Act, and Scene

Agentic orchestration uses the Director/Act/Scene vocabulary to distinguish its
control structure from an ordinary workflow:

- The Director owns the control plane or scheduler.
- An Act is a bounded stage or handoff boundary.
- A Scene is a retryable step or checkpoint.

The vocabulary does not prescribe classes or package APIs. It makes lifecycle,
authority, state, and recovery responsibilities visible in design discussions.

## Library Map

### Core

- [Architecture levels](core/architecture-levels.md)
- [Agent layers](core/agent-layers.md)
- [Models and errors](core/models-and-errors.md)
- [Tools and capabilities](core/tools-and-capabilities.md)
- [Model Context Protocol](core/mcp.md)
- [Evaluation](core/evaluation.md)

### Orchestration

- [Director, Act, and Scene](orchestration/director-act-scene.md)
- [Handoff contracts](orchestration/handoff-contracts.md)
- [Transitions](orchestration/transitions.md)
- [Persistence and resume](orchestration/persistence-and-resume.md)
- [Anti-patterns](orchestration/anti-patterns.md)

### Delegation

- [Agent as tool](delegation/agent-as-tool.md)
- [Dynamic subagents](delegation/dynamic-subagents.md)
- [Isolation matrix](delegation/isolation-matrix.md)

### Conditional Profiles

- [Reference profile index](reference-profiles/README.md)

### Informative and Draft Material

- [Agent component README template](templates/readme-templates.md)
- [Testing stub](stubs/testing.md)
- [Maturity tiers stub](stubs/maturity-tiers.md)

## Reading Order

For a new system, start with Architecture Levels and Agent Layers. Define models,
errors, tools, and evaluation next. Add the orchestration documents only when
coordination is a first-class responsibility, then choose a delegation contract
and any explicitly adopted reference profile.

For an existing-system review, classify each component first. Trace public
inputs and outputs inward through layers, then inspect authority, state,
lifecycle, errors, and evaluation evidence. For coordinated systems, review
Director/Act/Scene ownership, handoffs, persistence, and delegation isolation.

## Related Reference Library

The [mechanistic modeling reference library](../mechanistic-modeling/README.md)
is a sibling contract for structured scientific models and numerical execution.
Agent architecture owns orchestration, delegation, handoffs, and recovery;
mechanistic modeling owns model semantics, evaluation, composition, solving,
and result interpretation.

An agentic workflow may author or carry a versioned model artifact without
making this library authoritative for the artifact's scientific meaning.

## Authority Legend

| Status | Meaning |
| --- | --- |
| Normative | Required architecture contract within an adopted scope |
| Conditional | Normative only after the named profile is explicitly adopted |
| Informative | Copyable or explanatory material without compliance authority |
| Non-normative draft | Preserved outline with unresolved design inputs |

## Repository Instructions and Engineering Standards

Requirement: Repository instructions MUST take precedence when they define a more specific in-scope implementation rule.

Rationale: This library provides portable architecture intent, while a repository
owns its executable configuration, supported versions, and local constraints.

Scope: Conflicts or overlaps between this library and
[repository instructions](../../../AGENTS.md).

Exceptions: A local rule cannot silently weaken a separately required security,
privacy, or organizational control; that conflict needs explicit resolution.

The separate [engineering standards library](../standards/README.md) governs
general implementation practices such as Python, testing, validation,
documentation, dependencies, and source control. This library governs the
architecture-specific boundary between workflows, agents, orchestrators,
delegation, and framework profiles.
