# Plato Agent Architecture Library Design

## Status

Approved detailed design for extracting the generic parts of Plato's
application-agent charter and agentic-workflow documentation into a passive
reference library in `ballen-config`. Implementation remains pending written
specification review and a separate implementation plan.

This design is the detailed application-agent workstream anticipated by the
[Plato generic assets migration program](./2026-07-27-plato-generic-assets-migration-design.md).

## Context

Plato contains two related documentation corpora:

- `docs/agent_charter/` describes application-agent construction, layers,
  tools, models, services, MCP wrappers, evaluation, observability, and related
  practices; and
- `docs/agentic_workflows/` describes the Director/Act/Scene orchestration
  pattern, its contracts, transitions, and anti-patterns.

Both corpora contain durable concepts that are useful outside Plato. They also
contain Plato package paths, QSP examples, internal infrastructure, incomplete
work, framework-specific APIs, and implementation-status claims. Copying either
tree wholesale would preserve the wrong ownership and portability boundaries.

The two corpora form one conceptual program. Agent architecture defines the
units and their contracts; agentic orchestration defines how bounded units are
sequenced, isolated, retried, resumed, and delegated. The portable result should
therefore be one integrated library rather than two independently evolving
copies of the Plato directory structure.

## Goals

- Create one coherent application-agent architecture reference library in
  `ballen-config`.
- Preserve Director/Act/Scene as the primary metaphor for agentic
  orchestration while translating it to generic architecture terms.
- Define Workflow, Agent, and Orchestrator by responsibility rather than tool
  count or implementation size.
- Distinguish orchestration roles from delegation mechanisms such as static
  agents-as-tools and dynamic subagents.
- Make framework-neutral core guidance normative and explain every requirement.
- Keep MCP in the framework-neutral core.
- Isolate PydanticAI, Logfire, and Streamlit guidance in clearly labeled
  reference profiles.
- Preserve useful incomplete testing and maturity material as visible,
  non-normative stubs.
- Record exact source provenance without creating a synchronization dependency
  on Plato.
- Verify that prohibited local, security, and generated state does not enter
  the library.

## Non-Goals

- Modify, delete, redirect, or otherwise clean up any Plato file.
- Keep the new library synchronized automatically with Plato.
- Copy either Plato documentation tree byte for byte.
- Create a skill, template installer, scaffold, plugin, catalog entry, native
  projection, or bootstrap stage.
- Load the library automatically into any coding agent.
- Define Claude Agent SDK, Claude Managed Agents, or Cursor Cloud Agent parity.
- Complete unfinished testing or maturity requirements during extraction.
- Migrate authentication, credentials, trust, sessions, histories, memories,
  machine-specific project paths, permissions, caches, indexes, or generated
  plugin state.
- Promote QSP, AMi, Plato package, infrastructure, deployment, or internal
  issue-tracker conventions as portable guidance.

## Design Decisions

### One integrated passive library

The canonical library will live at
`assistants/shared/agent-architecture/`. It is human-readable reference
documentation with no runtime registration or installation behavior.

Two alternatives were considered and rejected:

1. Two sibling `agent-charter` and `agentic-workflows` libraries would preserve
   source provenance simply, but would duplicate contracts and leave delegation
   and orchestration concepts split across competing entry points.
2. Extending `assistants/shared/standards/` would reuse existing discovery and
   validation, but would incorrectly make application-agent architecture appear
   to be an always-on engineering baseline. Conditional profiles and incomplete
   stubs also do not belong in that authority layer.

### Plato remains unchanged

Plato is a read-only extraction source for this workstream. The implementation
must pin the exact clean Plato revision used for review, read from it, and prove
that the Plato working copy and revision remain unchanged after implementation.

Any later decision to replace, link, synchronize, or remove Plato documentation
requires a separate design and explicit approval.

### Canonical ownership

After extraction, `ballen-config` owns the genericized wording and structure.
Plato continues to own its existing documentation, examples, overlays, and
history. Similar text in the two repositories does not imply synchronization or
shared live ownership.

The [engineering standards](../../../assistants/shared/standards/README.md)
remain authoritative for general engineering rules. The agent architecture
library links to applicable standards rather than restating them.

## Target Architecture

```text
assistants/shared/agent-architecture/
├── README.md
├── core/
│   ├── architecture-levels.md
│   ├── agent-layers.md
│   ├── models-and-errors.md
│   ├── tools-and-capabilities.md
│   ├── mcp.md
│   └── evaluation.md
├── orchestration/
│   ├── director-act-scene.md
│   ├── handoff-contracts.md
│   ├── transitions.md
│   ├── persistence-and-resume.md
│   └── anti-patterns.md
├── delegation/
│   ├── agent-as-tool.md
│   ├── dynamic-subagents.md
│   └── isolation-matrix.md
├── reference-profiles/
│   ├── README.md
│   ├── pydantic-ai/
│   │   ├── README.md
│   │   ├── construction.md
│   │   ├── services-and-dependencies.md
│   │   └── tools-and-capabilities.md
│   ├── logfire.md
│   └── streamlit-demo-apps.md
├── templates/
│   └── readme-templates.md
└── stubs/
    ├── testing.md
    └── maturity-tiers.md
```

The root README is the library's only universal entry point. It states the
audience, authority model, reading order, adoption semantics, and relationship
to engineering standards. Section directories group concepts; they do not
create separate authorities.

The reference-profile README explains conditional adoption and links each
profile. The PydanticAI profile receives a directory because its source material
spans construction, dependency, service, tool, and capability contracts.

## Document Kinds and Authority

Every destination document has one kind and one authority status recorded in
the provenance manifest.

| Kind | Authority | Meaning |
| --- | --- | --- |
| Core | Normative | Framework-neutral application-agent requirement |
| Orchestration | Normative | Framework-neutral Director/Act/Scene contract |
| Delegation | Normative | Framework-neutral invocation and isolation contract |
| Reference profile | Conditional | Normative only when a consumer explicitly adopts the named framework or pattern |
| Template | Informative | Starting point that must be adapted to repository requirements |
| Stub | Non-normative draft | Incomplete extracted material that creates no compliance requirement |

Repository instructions and executable configuration always take precedence.
Adopting a profile does not override a repository's explicit choices.

### Normative language

Core, orchestration, and delegation documents use MUST, SHOULD, and MAY
consistently:

- MUST identifies a required architecture invariant;
- SHOULD identifies the recommended default when a valid exception may exist;
  and
- MAY identifies an optional technique.

Every MUST and SHOULD includes its rationale, scope, and any valid exception.
Requirements must not rely on emphasis alone to communicate authority.

Profiles follow the same convention within their declared adoption boundary.
Templates and stubs do not introduce MUST or SHOULD requirements.

## Core Architecture Model

### Workflow, Agent, and Orchestrator

The architecture categories describe responsibility, not a linear maturity or
size scale.

| Category | Defining responsibility |
| --- | --- |
| Workflow | Code or configuration owns routing. A bounded step may call a model, but the model does not own the workflow's control flow. |
| Agent | A model owns bounded reasoning or selection among explicitly granted tools and capabilities. An agent may have zero, one, or many tools. |
| Orchestrator | A component owns coordination across agents or stages, including sequencing, handoffs, transitions, retry or gating, resume, or capability boundaries. |

An Orchestrator may be deterministic, agentic, or hybrid. Calling one specialist
does not by itself make a parent an Orchestrator. Coordination must be a
first-class responsibility rather than an incidental tool invocation.

The previous Plato Pattern 0 through Pattern 3 labels are source provenance
only. The portable library does not retain numeric shorthand.

### Agent layers

The core preserves logical separation among:

- agent construction and model-facing configuration;
- thin tool adapters;
- deterministic services and domain logic;
- typed boundary models and dependency containers;
- exceptions and explicit failure results; and
- optional MCP, evaluation, and orchestration adapters.

The documents describe responsibilities and import direction without requiring
Plato package paths or a single physical Python layout. PydanticAI-specific
module and API conventions belong in its profile.

### MCP

MCP is part of the framework-neutral core because it is an interoperability and
process-boundary contract rather than an application-agent framework choice.
Core MCP guidance covers typed request and response boundaries, registration
separation, lifecycle ownership, error policy, and resource scoping.

The core does not include MCP endpoints, authentication, OAuth, secret
resolution, provider configuration, local server state, or generated plugin
configuration. FastMCP-specific mechanics must be labeled as examples or placed
in an appropriate profile.

## Director/Act/Scene Orchestration

Director/Act/Scene remains the primary vocabulary because it distinguishes
agentic orchestration boundaries from ordinary procedural workflow steps.

| Boundary | Primary concern | Generic translation |
| --- | --- | --- |
| Director | Sequencing and resume | Workflow control plane or scheduler |
| Act | Capability confinement and typed handoff | Bounded execution stage and handoff boundary |
| Scene | Retry, gating, and redirection | Retryable step or checkpoint |

These are architecture boundaries, not necessarily model-backed agents:

- a Director may be deterministic code, an agent, or a hybrid control plane;
- an Act may contain deterministic work, one agent, or several cooperating
  units; and
- a Scene identifies the smallest independently retryable or gated unit, which
  may be a tool call, an agent run, or deterministic logic.

The shared guidance treats explicit run infrastructure as valid. A Director may
provision a backend, artifact store, database, queue, or other run-scoped
resource and pass it deliberately. The prohibited pattern is ambient capability
inheritance, not intentional shared infrastructure.

### Orchestration contracts

Normative orchestration guidance covers:

- one explicit entry point for each bounded Act;
- typed or structured handoffs;
- status-coupled payload validation;
- explicit dependency and capability grants;
- artifact references instead of implicit workspace discovery;
- separation of routing policy from mechanical transition application;
- auditable transition reasons;
- distinct retry, escalation, forward-progress, and stop intent;
- durable position and handoff state sufficient for supported resume; and
- separation of expected non-completion from setup, configuration,
  persistence, and contract failures.

The four transition intents are conceptual requirements, not a claim that
Plato's current serialized transition type already represents them directly.
Planned Act-level resume behavior remains Plato-only until implemented and
verified.

## Delegation Model

Delegation mechanism is orthogonal to Workflow, Agent, Orchestrator, and
Director/Act/Scene roles.

### Agent as tool

An agent-as-tool is a statically declared specialist exposed through a stable,
typed public contract. The parent supplies explicit input and receives explicit
output. Parent message history, dependencies, tools, and permissions do not
cross the boundary unless the wrapper passes them deliberately.

This pattern favors predictable capabilities, reusable specialists, isolated
instructions, and independent testing.

### Dynamic subagent

A dynamic subagent is selected or constructed at runtime and receives an
explicit lifecycle and capability grant. The generic contract does not assume a
specific PydanticAI package.

The PydanticAI profile may describe the project-pinned dynamic-subagent
implementation after verifying its current primary documentation. In the
reviewed implementation, subagents receive a separate model run, cloned
dependencies, configured toolsets, and explicit parent communication rather
than automatic parent message history. Those details are version-sensitive and
must not leak into the framework-neutral definition.

### Isolation matrix

Every delegation pattern must document:

- system instructions;
- model message history;
- typed task input and output;
- dependencies and deliberately shared resources;
- tools, capabilities, and permissions;
- lifecycle and ownership;
- persistence and resume behavior; and
- error, retry, cancellation, and escalation behavior.

The framework-neutral defaults are:

- no implicit message-history forwarding;
- no ambient dependency or permission inheritance;
- explicit grants for every shared resource or capability;
- typed or structured handoffs; and
- an explicit owner for delegated-task lifecycle and failure handling.

## Reference Profiles

### PydanticAI

The PydanticAI profile contains framework-specific guidance for:

- startup-fixed versus intentionally dynamic construction;
- dependency containers and `RunContext`;
- service entry points and agent factories;
- tool registration and sequential mutation safety;
- structured outputs and model validation;
- capabilities and scoped toolsets; and
- PydanticAI-specific delegation examples.

Model names, provider choices, Plato wrappers, Temporal integration, and Plato
package imports are not portable requirements. Version-sensitive claims require
a dated review against official PydanticAI sources.

### Logfire

The Logfire profile contains opt-in guidance for OpenTelemetry-compatible span
design, low-cardinality naming, exception recording, bounded input and output
capture, scrubbing, and optional instrumentation.

It excludes tokens, secret lookup, local environment files, Plato project
names, internal headers, and infrastructure-specific configuration. Payload
capture and user-identity propagation must be framed as explicit privacy and
security decisions rather than defaults.

### Streamlit demo apps

The Streamlit profile condenses the portable parts of Plato's demo-app guide:

- direct-import prototyping;
- self-contained demo layout;
- input, agent call, and result rendering;
- minimal runnable examples;
- framework-selection criteria; and
- when direct imports or MCP are appropriate.

It excludes Plato agents, SSO, authentication helpers, credentials, AWS,
CodeArtifact, internal GitLab publishing, ALB, TLS, Fargate, and production
deployment instructions.

## Templates and Stubs

### README templates

The reusable README material becomes an informative template reference. It
provides architecture, state, dependency, tool, control-flow, limitation,
testing, and reference sections without Plato exemplars or package paths.

Examples must be marked as runnable or illustrative. A generated or copied
README becomes destination-repository-owned and may be adapted immediately.

### Testing and maturity tiers

The source testing and maturity documents are unfinished. V1 extracts only the
generic material already present and places it under `stubs/`.

Each stub must:

- begin with a prominent non-normative draft notice;
- state which topics remain incomplete;
- contain no MUST or SHOULD requirements;
- avoid invented completion criteria; and
- record its incomplete source status in provenance.

Completing either topic requires a later review and explicit status change.

## Source Disposition

Every Markdown file in the two source directories receives an explicit
disposition.

| Plato source | Destination or disposition |
| --- | --- |
| `docs/agent_charter/README.md` | Core architecture levels and agent layers |
| `docs/agent_charter/agent_construction_standard.md` | PydanticAI construction profile |
| `docs/agent_charter/agent_service_pattern.md` | Core agent layers, agent-as-tool delegation, and PydanticAI services |
| `docs/agent_charter/auth_flow.md` | Excluded |
| `docs/agent_charter/capabilities.md` | Core capability contract and PydanticAI capability profile |
| `docs/agent_charter/credentials_config.md` | Excluded |
| `docs/agent_charter/demo_apps.md` | Condensed Streamlit demo-app profile |
| `docs/agent_charter/evals.md` | Core evaluation guidance; runner details isolated or omitted |
| `docs/agent_charter/file_organization.md` | Core agent layers |
| `docs/agent_charter/maturity_tiers.md` | Non-normative stub |
| `docs/agent_charter/mcp.md` | Framework-neutral MCP core |
| `docs/agent_charter/models_exceptions.md` | Core models and errors plus PydanticAI examples |
| `docs/agent_charter/observability_logfire.md` | Logfire reference profile |
| `docs/agent_charter/readme_templates.md` | Informative README templates |
| `docs/agent_charter/testing.md` | Non-normative stub |
| `docs/agent_charter/todos.md` | Excluded |
| `docs/agent_charter/tool_design_guidelines.md` | Core tools and capabilities plus PydanticAI profile |
| `docs/agentic_workflows/README.md` | Director/Act/Scene overview and translation table |
| `docs/agentic_workflows/contracts.md` | Handoff contracts |
| `docs/agentic_workflows/transitions.md` | Transitions plus persistence and resume |
| `docs/agentic_workflows/anti_patterns.md` | Orchestration anti-patterns |

Selected Plato implementation files may be recorded as verification evidence
when needed to distinguish current behavior from planned documentation. They do
not become generic prose sources merely because they illustrate one
implementation.

## Extraction Boundary

Extraction is concept-based rather than file-copy-based. A source may feed
several destinations, and a destination may consolidate several sources.

Portable concepts include:

- bounded agent, service, tool, model, and orchestration responsibilities;
- typed inputs, outputs, dependencies, handoffs, and failures;
- explicit capability grants and run-scoped shared infrastructure;
- transition, retry, escalation, gating, persistence, and resume contracts;
- evaluation dimensions and judge pitfalls;
- MCP boundaries;
- conditional framework patterns; and
- reusable documentation structure.

The extraction must remove or isolate:

- Plato, QSP, AMi, and named internal-agent concepts;
- Plato imports and repository-relative implementation paths;
- fixed model identifiers and provider-routing fields;
- internal issue identifiers and future-ticket claims;
- authentication, credentials, secret resolution, trust, and corporate SSL;
- AWS, S3, CodeArtifact, internal GitLab, ALB, and deployment topology;
- local home, workspace, session, history, cache, and generated-state paths;
- Temporal and durable-runtime assumptions unless placed in a future profile;
  and
- incomplete requirements that are not visibly labeled as stubs.

If a generic lesson appears only inside a prohibited source such as an
authentication guide, it is not extracted indirectly from that source. A later
independently authored rule may reach the same conclusion using acceptable
evidence.

## Provenance

Implementation adds:

`docs/superpowers/specs/2026-07-31-plato-agent-architecture-provenance.yaml`

The manifest is audit metadata, not a runtime catalog. It records:

- the Plato repository and pinned source revision;
- the design document governing the extraction;
- review date and portability result;
- every source document and its disposition;
- every destination document, kind, authority status, and source roles;
- transformation notes and explicit exclusions; and
- official sources plus review dates for version-sensitive profile claims.

Source paths are repository-relative POSIX paths with no traversal. Provenance
stays outside the canonical Markdown tree. Reader-facing documents do not
contain migration frontmatter or live links to a local Plato checkout.

Every source document must appear exactly once in the source inventory. Every
destination document must have exactly one manifest entry, though that entry
may list several sources.

## Extraction Workflow

Implementation follows this order:

1. Confirm both repositories are clean and pin the exact Plato source revision.
2. Create the destination tree and provenance schema.
3. Record all source dispositions before drafting normative content.
4. Draft the core taxonomy, agent layers, and boundary contracts.
5. Draft Director/Act/Scene orchestration and delegation contracts.
6. Draft reference profiles using the approved core/profile boundaries.
7. Extract README templates and incomplete stubs with their authority labels.
8. Verify version-sensitive profile claims against official primary sources.
9. Trace every destination claim to acceptable source evidence.
10. Run structural, privacy, link, Markdown, and repository verification.
11. Confirm Plato remains unchanged.

No destination is created by copying a complete source file and editing it in
place. Drafting starts from the approved destination outline and incorporates
only reviewed concepts.

## Failure and Ambiguity Handling

Extraction resolves uncertainty conservatively:

- Unsupported or ambiguous claims are omitted or deferred.
- Framework-coupled guidance moves to a profile.
- A claim tied to a specific runtime remains conditional unless independently
  supported as framework-neutral.
- Planned Plato behavior is never presented as implemented evidence.
- Conflicting source guidance remains qualified rather than being silently
  generalized.
- Sensitive or prohibited material is excluded rather than redacted into a
  nearly equivalent operational recipe.
- If a concept cannot be expressed without a local path, credential, trust
  mechanism, or generated-state dependency, it is omitted.
- Missing external primary evidence blocks a version-sensitive profile claim,
  not the rest of the library.

## Validation Strategy

### Structural tests

Add `tests/assistants/test_agent_architecture.py` to verify:

- the expected V1 tree contains only regular files and directories;
- root and profile indexes link every intended document exactly once;
- every local relative link resolves;
- every Markdown document begins with one level-one heading and has no
  migration frontmatter;
- every destination document has one provenance entry;
- every source document has one disposition;
- source paths are relative, normalized, and traversal-free;
- manifest kinds and authority statuses are valid;
- MCP is core;
- PydanticAI, Logfire, and Streamlit are reference profiles;
- testing and maturity tiers are non-normative stubs;
- version-sensitive profiles carry dated primary-source reviews; and
- a bounded denylist of concrete Plato paths, imports, issue identifiers,
  internal endpoints, and prohibited source artifacts is absent.

Tests should validate structure and metadata rather than brittle prose
substrings. Semantic requirements remain review responsibilities.

### Manual semantic review

Reviewers confirm:

- every MUST and SHOULD has rationale, scope, and exceptions;
- Workflow, Agent, and Orchestrator are responsibility categories rather than
  size tiers;
- Director, Act, and Scene retain distinct boundaries;
- delegation mechanisms remain orthogonal to orchestration roles;
- agent-as-tool and dynamic-subagent isolation claims are accurate;
- intentional shared run infrastructure is not mislabeled as ambient coupling;
- profiles do not leak requirements into the framework-neutral core;
- engineering standards are linked rather than duplicated;
- planned behavior is not represented as implemented; and
- stubs contain no accidental normative language.

### Fresh verification

Run, using repository-native commands discovered at implementation time:

- focused agent-architecture tests;
- the full repository test suite;
- configured lint and type checks;
- Markdown lint;
- local-link validation;
- provenance and prohibited-state scans;
- `jj diff` review; and
- clean working-copy checks.

Record the pinned Plato revision and verify its status before and after the
implementation. Verification claims must report actual fresh results rather
than inferred coverage.

## Delivery Sequence

The implementation plan should organize work into four reviewable slices:

1. Library skeleton, taxonomy, provenance manifest, and structural tests.
2. Core architecture plus orchestration and delegation documents.
3. Reference profiles, README templates, and labeled stubs.
4. Full verification, source-completeness review, and documentation cleanup.

The slices belong to one combined program and one canonical library. They may
be separate Jujutsu changes if that improves reviewability, but none modifies
Plato or introduces runtime delivery.

## Deferred Decisions

The following remain deliberately deferred:

- whether to expose the library through one or more skills;
- whether templates should become managed scaffolds;
- whether any subset should receive native agent projections;
- whether Plato should later reference or consume the generic library;
- completed testing and maturity requirements;
- runtime profiles beyond PydanticAI and Logfire;
- a deployment profile for demo applications; and
- automated synchronization or drift detection between repositories.

Each requires a separate design based on a demonstrated consumer need.

## Success Criteria

The V1 implementation is complete when:

- all 21 Markdown source documents have explicit dispositions;
- the approved destination tree is present and internally linked;
- every destination document is traceable through provenance;
- core, orchestration, and delegation requirements are framework-neutral;
- every normative MUST and SHOULD is explained;
- Director/Act/Scene and Workflow/Agent/Orchestrator relationships are clear;
- delegation isolation is explicit across history, dependencies, resources,
  permissions, lifecycle, and failure behavior;
- PydanticAI, Logfire, and Streamlit content remains inside labeled profiles;
- testing and maturity material remains visibly non-normative;
- prohibited authentication, trust, session, local-path, and generated state is
  absent;
- structural tests, repository checks, Markdown lint, and link validation pass;
  and
- Plato remains unchanged at the pinned source revision.
