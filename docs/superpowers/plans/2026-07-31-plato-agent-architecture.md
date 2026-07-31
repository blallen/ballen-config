# Agent Architecture Reference Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract the portable parts of Plato's `agent_charter` and
`agentic_workflows` documentation into a canonical, passive agent-architecture
reference library in `ballen-config`, without modifying Plato or adding runtime
installation behavior.

**Architecture:** Build one integrated Markdown library under
`assistants/shared/agent-architecture/`. Keep framework-neutral requirements in
core, orchestration, and delegation documents; isolate PydanticAI, Logfire, and
Streamlit guidance in explicitly conditional reference profiles; keep README
material informative; and preserve incomplete testing and maturity material as
visibly non-normative stubs. Record the complete source-to-destination mapping
in an audit-only provenance manifest and enforce the library contract with
focused pytest tests.

**Tech Stack:** Markdown, YAML, Python 3.12, pytest, PyYAML, Ruff, mypy,
pre-commit, Markdownlint, and Jujutsu.

---

## Execution Model

- Execute tasks in order. Later documents depend on terminology and authority
  boundaries established by earlier tasks.
- If using subagent-driven development, use one fresh Luna extra-high worker per
  implementation task and serialize the workers. Use separate Luna extra-high
  workers for the read-only specification and portability reviews in Task 11.
- Keep Plato read-only. Never amend, restore, fold, or otherwise touch its
  working copy, including unrelated user changes.
- Treat Plato revision `0d7699bb0cae3025097718126fcb8e413b6a49e0` as the
  reviewed source snapshot. Stop if any source document or version-evidence
  file differs from that revision.
- Run focused tests and Markdown lint before each logical commit. Run the full
  repository verification set only after the complete library exists.
- Do not add the library to `catalog.yaml`, bootstrap logic, generated agent
  configuration, native agent directories, or the existing engineering
  standards projection.

## File Map

### Files to create

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
docs/superpowers/specs/
└── 2026-07-31-plato-agent-architecture-provenance.yaml
tests/assistants/
└── test_agent_architecture.py
```

The canonical library contains exactly 25 Markdown files. The provenance file
is audit metadata and remains outside the canonical tree.

### Existing files to read, not modify

- `docs/superpowers/specs/2026-07-31-plato-agent-architecture-design.md`
- `docs/superpowers/specs/2026-07-27-plato-engineering-standards-provenance.yaml`
- `tests/assistants/test_standards.py`
- `assistants/shared/standards/documentation.md`
- `assistants/shared/standards/source-control.md`
- `../plato/docs/agent_charter/*.md` at the pinned revision
- `../plato/docs/agentic_workflows/*.md` at the pinned revision
- `../plato/uv.lock` at the pinned revision
- Selected Plato implementation files only when needed to verify a behavioral
  claim; record those files as evidence, never as generic prose authority.

## Library-Wide Contracts

### Authority

Use these exact manifest values:

| Kind | Authority |
| --- | --- |
| `core` | `normative` |
| `orchestration` | `normative` |
| `delegation` | `normative` |
| `reference-profile` | `conditional` |
| `template` | `informative` |
| `stub` | `non-normative-draft` |

The root README is recorded as `core` and `normative`, but it acts as the
adoption and navigation entry point rather than adding standalone rules.

### Normative rule form

Every rule containing `MUST` or `SHOULD` uses one heading and four labeled
paragraphs in this order:

```markdown
### Descriptive rule name

Requirement: A concrete subject MUST or SHOULD perform a concrete action.

Rationale: Explain why the rule exists.

Scope: State where the rule applies.

Exceptions: State valid exceptions, or state that there are no exceptions.
```

Do not use uppercase `MUST` or `SHOULD` outside a `Requirement:` paragraph.
Profiles may use this form only within their declared adoption boundary.
Templates and stubs contain neither word in uppercase.

### Terminology

- Use `Workflow`, `Agent`, and `Orchestrator` as responsibility categories.
  Do not preserve the `P0` through `P3` shorthand.
- Use Director, Act, and Scene as the primary orchestration metaphor.
- Include this translation table verbatim in
  `orchestration/director-act-scene.md`:

  | Agentic term | Generic systems term |
  | --- | --- |
  | Director | Control plane or scheduler |
  | Act | Bounded stage or handoff boundary |
  | Scene | Retryable step or checkpoint |

- Treat architecture category, orchestration layer, and delegation mechanism
  as orthogonal axes.
- A parent Agent invoking one fixed specialist as a tool remains an Agent unless
  coordination policy is itself a first-class responsibility.

### Portability boundary

Reader-facing library files contain no Plato imports, internal ticket IDs,
absolute user paths, local credential paths, internal service names,
authentication flows, trust state, session state, generated plugin state, AWS
deployment instructions, or internal publishing instructions.

## Provenance Schema

Create a YAML mapping with exactly these top-level keys in this order:

1. `source_repository`
2. `source_revision`
3. `approved_decision`
4. `portability_result`
5. `review_date`
6. `source_documents`
7. `documents`

Use these scalar values:

```yaml
source_repository: plato
source_revision: 0d7699bb0cae3025097718126fcb8e413b6a49e0  # pragma: allowlist secret
approved_decision: docs/superpowers/specs/2026-07-31-plato-agent-architecture-design.md
portability_result: portable-after-adaptation
review_date: "2026-07-31"
```

Keys under `documents` and values under `source_documents.destinations` are
relative to `assistants/shared/agent-architecture/`. Quote dates and versions
so PyYAML loads them as strings.

Each `source_documents` value has:

- `disposition`: one of `extracted`, `split`, `profile`, `template`, `stub`, or
  `excluded`;
- `destinations`: a non-empty list for every non-excluded source; and
- `reason`: a non-empty sentence for every excluded source.

Each `documents` value has:

- `kind` and `authority` from the authority table;
- `source_paths`, a non-empty list of source documents except for the root
  README, which may cite both source README files;
- `source_roles`, a mapping from every `source_paths` entry to either `primary`
  or `supporting`;
- `transformation_note`, a non-empty sentence describing the portability edit;
- optional `evidence_paths`, containing repository-relative Plato paths used
  only to verify behavior; and
- optional `version_reviews`, with `product`, `package`, `version`,
  `primary_source`, `release_history`, and `reviewed_on`.

Every manifest path is repository-relative POSIX syntax, has no `..` segment,
and contains no absolute local path.

## Complete Source Disposition

Use this table as the exact 21-file source inventory:

| Source | Disposition | Destinations or exclusion reason |
| --- | --- | --- |
| `docs/agent_charter/README.md` | `split` | `core/architecture-levels.md`, `core/agent-layers.md` |
| `docs/agent_charter/agent_construction_standard.md` | `profile` | `reference-profiles/pydantic-ai/construction.md` |
| `docs/agent_charter/agent_service_pattern.md` | `split` | `core/agent-layers.md`, `delegation/agent-as-tool.md`, `reference-profiles/pydantic-ai/services-and-dependencies.md` |
| `docs/agent_charter/auth_flow.md` | `excluded` | Authentication and internal request flow are outside the portable reference-library scope. |
| `docs/agent_charter/capabilities.md` | `split` | `core/tools-and-capabilities.md`, `reference-profiles/pydantic-ai/tools-and-capabilities.md` |
| `docs/agent_charter/credentials_config.md` | `excluded` | Credential storage and local configuration are explicitly prohibited migration material. |
| `docs/agent_charter/demo_apps.md` | `profile` | `reference-profiles/streamlit-demo-apps.md` |
| `docs/agent_charter/evals.md` | `extracted` | `core/evaluation.md` |
| `docs/agent_charter/file_organization.md` | `extracted` | `core/agent-layers.md` |
| `docs/agent_charter/maturity_tiers.md` | `stub` | `stubs/maturity-tiers.md` |
| `docs/agent_charter/mcp.md` | `extracted` | `core/mcp.md` |
| `docs/agent_charter/models_exceptions.md` | `split` | `core/models-and-errors.md`, `reference-profiles/pydantic-ai/construction.md` |
| `docs/agent_charter/observability_logfire.md` | `profile` | `reference-profiles/logfire.md` |
| `docs/agent_charter/readme_templates.md` | `template` | `templates/readme-templates.md` |
| `docs/agent_charter/testing.md` | `stub` | `stubs/testing.md` |
| `docs/agent_charter/todos.md` | `excluded` | Plato-specific work tracking is not reference documentation. |
| `docs/agent_charter/tool_design_guidelines.md` | `split` | `core/tools-and-capabilities.md`, `reference-profiles/pydantic-ai/tools-and-capabilities.md` |
| `docs/agentic_workflows/README.md` | `extracted` | `orchestration/director-act-scene.md` |
| `docs/agentic_workflows/contracts.md` | `extracted` | `orchestration/handoff-contracts.md` |
| `docs/agentic_workflows/transitions.md` | `split` | `orchestration/transitions.md`, `orchestration/persistence-and-resume.md` |
| `docs/agentic_workflows/anti_patterns.md` | `extracted` | `orchestration/anti-patterns.md` |

The root README and profile index are synthesis documents. Their manifest
entries cite the relevant source README files and use transformation notes to
explain their navigation role.

## Task 0: Reconfirm the read-only source boundary

**Files:**

- Read: `../plato/docs/agent_charter/*.md`
- Read: `../plato/docs/agentic_workflows/*.md`
- Read: `../plato/uv.lock`
- Read: `docs/superpowers/specs/2026-07-31-plato-agent-architecture-design.md`

- [ ] From `ballen-config`, confirm the destination working copy is clean:

  ```bash
  rtk jj status
  ```

  Expected: `The working copy has no changes.` If it is dirty, inspect and
  preserve every unrelated user change before proceeding.

- [ ] Verify that the 21 source documents still match the reviewed Plato
  revision:

  ```bash
  rtk jj --repository ../plato diff --from 0d7699bb0cae3025097718126fcb8e413b6a49e0 --to @ --summary 'root:docs/agent_charter' 'root:docs/agentic_workflows'
  ```

  Expected: no output. If output names any source file, stop and revise the
  extraction design against the new source before implementing.

- [ ] Verify the version-evidence lockfile is unchanged:

  ```bash
  rtk jj --repository ../plato diff --from 0d7699bb0cae3025097718126fcb8e413b6a49e0 --to @ --summary 'root:uv.lock'
  ```

  Expected: no output. If `uv.lock` appears, stop and re-review all
  version-sensitive profile claims.

- [ ] Confirm the pinned source inventory contains exactly 21 Markdown files:

  ```bash
  rtk jj --repository ../plato file list -r 0d7699bb0cae3025097718126fcb8e413b6a49e0 'root:docs/agent_charter' 'root:docs/agentic_workflows'
  ```

  Expected: the 17 `agent_charter` files and four `agentic_workflows` files in
  the complete source-disposition table, with no additional Markdown file.

- [ ] Read source content from the pinned revision with `jj file show -r`, using
  a `root:` fileset whenever `--repository ../plato` is present. Do not copy the
  mutable Plato working tree or create a Plato commit.

## Task 1: Establish the provenance and test harness

**Files:**

- Create: `docs/superpowers/specs/2026-07-31-plato-agent-architecture-provenance.yaml`
- Create: `tests/assistants/test_agent_architecture.py`
- Reference: `docs/superpowers/specs/2026-07-27-plato-engineering-standards-provenance.yaml`
- Reference: `tests/assistants/test_standards.py`

- [ ] Add typed test models using `TypedDict` and `Literal` for
  `SourceRecord`, `VersionReview`, and `DestinationRecord`. Define constants
  for the repository root, library root, provenance path, all 21 source paths,
  and all 25 destination paths.

- [ ] Add `load_provenance() -> dict[str, object]` using `yaml.safe_load`, with
  explicit assertions that the parsed root is a mapping. Add a POSIX-path
  helper that rejects absolute paths, backslashes, empty segments, `.` segments,
  and `..` segments.

- [ ] Add a failing test asserting the seven exact top-level keys and fixed
  scalar values from the provenance schema.

- [ ] Run the focused test and confirm the intended failure:

  ```bash
  rtk uv run --frozen pytest tests/assistants/test_agent_architecture.py -q
  ```

  Expected: failure because the provenance YAML does not exist.

- [ ] Create the provenance YAML. Populate all 21 `source_documents` records
  from the complete source-disposition table and all 25 `documents` records
  from the file map. Use `primary` for the source that supplies a document's
  central contract and `supporting` where a source only contributes examples or
  secondary guidance.

- [ ] Add tests that enforce:

    - the source inventory is exactly the 21 paths in the table;
    - excluded records have `reason` and no `destinations`;
    - non-excluded records have `destinations` and no `reason`;
    - the destination inventory is exactly the 25 Markdown paths in the file map;
    - every source role key exactly matches its destination's `source_paths`;
    - all source, destination, evidence, and decision paths are normalized POSIX
    paths; and
    - kind and authority combinations match the authority table.

- [ ] Run focused tests and Ruff:

  ```bash
  rtk uv run --frozen pytest tests/assistants/test_agent_architecture.py -q
  rtk uv run --frozen ruff check tests/assistants/test_agent_architecture.py
  ```

  Expected: both commands exit zero.

- [ ] Commit the provenance contract:

  ```bash
  rtk jj commit -m "test: define agent architecture provenance contract"
  ```

## Task 2: Write the architecture foundations

**Files:**

- Create: `assistants/shared/agent-architecture/core/architecture-levels.md`
- Create: `assistants/shared/agent-architecture/core/agent-layers.md`
- Modify: `tests/assistants/test_agent_architecture.py`
- Read: `../plato/docs/agent_charter/README.md`
- Read: `../plato/docs/agent_charter/agent_service_pattern.md`
- Read: `../plato/docs/agent_charter/file_organization.md`

- [ ] Add failing tests requiring both files, one H1 per file, no YAML
  frontmatter, no `P0` through `P3` token, and correctly formed normative rule
  sections.

- [ ] Add a semantic test requiring `architecture-levels.md` to name exactly
  the three responsibility categories `Workflow`, `Agent`, and `Orchestrator`,
  and to state that one fixed specialist call does not by itself make an
  Orchestrator.

- [ ] Run the focused test and confirm failure for the two absent documents:

  ```bash
  rtk uv run --frozen pytest tests/assistants/test_agent_architecture.py -q
  ```

- [ ] Write `architecture-levels.md` with these sections:

    - purpose and category-selection principle;
    - Workflow: predetermined control flow with bounded model-assisted steps;
    - Agent: model-mediated decisions and actions inside explicit capabilities;
    - Orchestrator: first-class scheduling, delegation, lifecycle, or handoff
    policy across agents or stages;
    - a comparison table covering control ownership, delegation, state, and
    recovery;
    - the fixed-specialist boundary rule; and
    - upgrade signals for moving from Workflow to Agent or Agent to Orchestrator.

- [ ] Write `agent-layers.md` with these sections:

    - construction and startup-fixed configuration;
    - models and expected errors;
    - tools and capabilities;
    - service entry points;
    - external adapters;
    - dependency direction and public API boundaries; and
    - a compact package-layout example that uses generic names only.

  Require inward dependency direction, keep framework objects behind service
  entry points, and distinguish validated boundary data from runtime resources.

- [ ] Run focused tests and Markdownlint:

  ```bash
  rtk uv run --frozen pytest tests/assistants/test_agent_architecture.py -q
  rtk npx --no-install markdownlint-cli2 --config assistants/shared/standards/templates/python/.markdownlint.json "assistants/shared/agent-architecture/core/*.md"
  ```

  Expected: both commands exit zero.

- [ ] Commit the foundations:

  ```bash
  rtk jj commit -m "docs: add agent architecture foundations"
  ```

## Task 3: Write the remaining framework-neutral core

**Files:**

- Create: `assistants/shared/agent-architecture/core/models-and-errors.md`
- Create: `assistants/shared/agent-architecture/core/tools-and-capabilities.md`
- Create: `assistants/shared/agent-architecture/core/mcp.md`
- Create: `assistants/shared/agent-architecture/core/evaluation.md`
- Modify: `tests/assistants/test_agent_architecture.py`
- Read: `../plato/docs/agent_charter/models_exceptions.md`
- Read: `../plato/docs/agent_charter/capabilities.md`
- Read: `../plato/docs/agent_charter/tool_design_guidelines.md`
- Read: `../plato/docs/agent_charter/mcp.md`
- Read: `../plato/docs/agent_charter/evals.md`

- [ ] Add failing tests requiring all four documents, valid normative sections,
  and the headings listed below. Add a specific MCP test rejecting
  framework-specific API symbols such as `RunContext`, `Agent(`, and
  `MCPServerStdio` from `core/mcp.md`.

- [ ] Run the focused test and confirm failure for the four absent documents.

- [ ] Write `models-and-errors.md` covering:

    - validated input, output, and handoff models at system boundaries;
    - runtime dependency containers as a separate concern;
    - stable machine-readable result variants;
    - expected non-completion versus exceptional faults;
    - partial-failure representation; and
    - where exception translation belongs.

- [ ] Write `tools-and-capabilities.md` covering:

    - thin tool wrappers and explicit side effects;
    - capability grants separated from implementation;
    - read, write, external-message, and destructive effect classes;
    - idempotency, retry safety, timeout, and cancellation behavior;
    - approval boundaries for consequential effects; and
    - deterministic input/output schemas and actionable errors.

- [ ] Write `mcp.md` as a framework-neutral protocol boundary covering:

    - when MCP is preferable to direct in-process invocation;
    - typed request and response contracts;
    - server lifecycle and registration separated from business logic;
    - capability discovery and explicit grants;
    - expected errors versus transport or server faults; and
    - observability, cancellation, timeout, and retry expectations.

  Do not include authentication setup, credentials, internal transports, or
  framework-specific constructors.

- [ ] Write `evaluation.md` covering:

    - task success, structural validity, factual support, safety, latency, and
    cost as distinct dimensions;
    - representative golden sets and controlled variation;
    - deterministic checks before model-based judging;
    - offline, pre-release, and production evaluation modes;
    - judge calibration, leakage, and self-preference risks; and
    - result reporting without importing Plato-specific runners, fixed sample
    counts, or hard-coded thresholds.

- [ ] Run focused tests and Markdownlint:

  ```bash
  rtk uv run --frozen pytest tests/assistants/test_agent_architecture.py -q
  rtk npx --no-install markdownlint-cli2 --config assistants/shared/standards/templates/python/.markdownlint.json "assistants/shared/agent-architecture/core/*.md"
  ```

  Expected: both commands exit zero.

- [ ] Commit the core contracts:

  ```bash
  rtk jj commit -m "docs: add framework-neutral agent contracts"
  ```

## Task 4: Define Director, Act, Scene, and handoff contracts

**Files:**

- Create: `assistants/shared/agent-architecture/orchestration/director-act-scene.md`
- Create: `assistants/shared/agent-architecture/orchestration/handoff-contracts.md`
- Modify: `tests/assistants/test_agent_architecture.py`
- Read: `../plato/docs/agentic_workflows/README.md`
- Read: `../plato/docs/agentic_workflows/contracts.md`

- [ ] Add failing tests requiring both documents, valid normative sections, and
  the exact Director/Act/Scene translation table from the terminology contract.
  Require prose that says these are orchestration responsibilities, not a
  requirement for three independent model agents.

- [ ] Run the focused test and confirm failure for the two absent documents.

- [ ] Write `director-act-scene.md` with:

    - the purpose of the metaphor and the exact translation table;
    - Director ownership of cross-Act scheduling, policy, and terminal outcome;
    - Act ownership of a bounded objective and typed handoff boundary;
    - Scene ownership of one retryable step or checkpoint;
    - a responsibility matrix for state, policy, work, recovery, and persistence;
    - the rule that each role may be deterministic code, one Agent, or several
    cooperating components; and
    - the distinction between this hierarchy and standard linear workflows.

- [ ] Write `handoff-contracts.md` with:

    - explicit Act entry points;
    - typed handoff inputs and outputs;
    - status, payload, artifact references, and continuation metadata;
    - explicit dependency and capability requirements;
    - validation before transition;
    - expected refusal or non-completion outcomes; and
    - ownership of compatibility changes.

- [ ] Run focused tests and orchestration Markdownlint:

  ```bash
  rtk uv run --frozen pytest tests/assistants/test_agent_architecture.py -q
  rtk npx --no-install markdownlint-cli2 --config assistants/shared/standards/templates/python/.markdownlint.json "assistants/shared/agent-architecture/orchestration/*.md"
  ```

  Expected: both commands exit zero.

- [ ] Commit the orchestration foundation:

  ```bash
  rtk jj commit -m "docs: define director act scene orchestration"
  ```

## Task 5: Define transitions, persistence, resume, and anti-patterns

**Files:**

- Create: `assistants/shared/agent-architecture/orchestration/transitions.md`
- Create: `assistants/shared/agent-architecture/orchestration/persistence-and-resume.md`
- Create: `assistants/shared/agent-architecture/orchestration/anti-patterns.md`
- Modify: `tests/assistants/test_agent_architecture.py`
- Read: `../plato/docs/agentic_workflows/transitions.md`
- Read: `../plato/docs/agentic_workflows/anti_patterns.md`

- [ ] Add failing tests requiring all three files and valid normative sections.
  Require `transitions.md` to name the conceptual outcomes `Advance`, `Retry`,
  `Escalate`, and `Stop` without claiming they are Plato code symbols.

- [ ] Run the focused test and confirm failure for the three absent documents.

- [ ] Write `transitions.md` with:

    - transition policy separated from transition mechanism;
    - `Advance`, `Retry`, `Escalate`, and `Stop` as conceptual outcomes;
    - a required reason and next target for every transition decision;
    - terminal-state validation;
    - bounded retry policy and escalation ownership; and
    - prevention of hidden fall-through between Acts or Scenes.

- [ ] Write `persistence-and-resume.md` with:

    - durable workflow position, outcome, and handoff references;
    - checkpoint boundaries aligned to Scene completion;
    - restoration into the same control loop;
    - validation of stale or invalid resume targets;
    - explicit retry context and attempt identity;
    - idempotent replay expectations; and
    - separation of durable state from live dependency objects.

- [ ] Write `anti-patterns.md` as repeated `Symptom`, `Why it fails`, and
  `Remedy` sections for:

    - ambient capabilities;
    - implicit workspace discovery;
    - hidden history sharing;
    - mixed policy and mechanism;
    - untyped handoffs;
    - unbounded retries;
    - persisted live resources; and
    - treating every orchestration layer as a separate model Agent.

- [ ] Run focused tests and orchestration Markdownlint:

  ```bash
  rtk uv run --frozen pytest tests/assistants/test_agent_architecture.py -q
  rtk npx --no-install markdownlint-cli2 --config assistants/shared/standards/templates/python/.markdownlint.json "assistants/shared/agent-architecture/orchestration/*.md"
  ```

  Expected: both commands exit zero.

- [ ] Commit the lifecycle guidance:

  ```bash
  rtk jj commit -m "docs: define orchestration lifecycle guidance"
  ```

## Task 6: Define static and dynamic delegation boundaries

**Files:**

- Create: `assistants/shared/agent-architecture/delegation/agent-as-tool.md`
- Create: `assistants/shared/agent-architecture/delegation/dynamic-subagents.md`
- Create: `assistants/shared/agent-architecture/delegation/isolation-matrix.md`
- Modify: `tests/assistants/test_agent_architecture.py`
- Read: `../plato/docs/agent_charter/agent_service_pattern.md`
- Read: selected installed `subagents-pydantic-ai` implementation only as
  version-specific verification evidence

- [ ] Add failing tests requiring all three files, valid normative sections,
  and an isolation matrix containing these dimensions: instructions, message
  history, input, output, dependencies, shared resources, tools, permissions,
  lifecycle, persistence, cancellation, and errors.

- [ ] Add a semantic test requiring both delegation documents to state that
  context, dependencies, resources, and permissions are not inherited unless
  the caller explicitly grants or maps them.

- [ ] Run the focused test and confirm failure for the three absent documents.

- [ ] Write `agent-as-tool.md` with:

    - a statically declared specialist exposed through a typed tool boundary;
    - explicit input and structured output;
    - no implicit parent message history;
    - explicit dependency, resource, tool, and permission mapping;
    - timeout, cancellation, and error translation;
    - suitability for stable, reviewable capabilities; and
    - the rule that a single specialist call does not automatically create an
    Orchestrator.

- [ ] Write `dynamic-subagents.md` in framework-neutral language with:

    - runtime creation or selection of specialists;
    - independent run and lifecycle identity;
    - deliberate context cloning rather than implicit history sharing;
    - capability grants and resource-sharing policy;
    - concurrency, cancellation, retry, and collection behavior;
    - persistence requirements for resumable workers; and
    - criteria for when dynamic delegation makes coordination a first-class
    Orchestrator responsibility.

- [ ] Write `isolation-matrix.md` with one row for each required dimension and
  columns for static agent-as-tool delegation and dynamic subagents. For every
  cell, state the default isolation boundary and the explicit contract required
  to share or map that dimension. Add a short section showing that delegation
  mechanism and Director/Act/Scene placement are independent choices.

- [ ] Record any inspected third-party package files under `evidence_paths` for
  the relevant destination, but do not copy package-specific class names into
  the framework-neutral delegation documents.

- [ ] Run focused tests and delegation Markdownlint:

  ```bash
  rtk uv run --frozen pytest tests/assistants/test_agent_architecture.py -q
  rtk npx --no-install markdownlint-cli2 --config assistants/shared/standards/templates/python/.markdownlint.json "assistants/shared/agent-architecture/delegation/*.md"
  ```

  Expected: both commands exit zero.

- [ ] Commit the delegation contracts:

  ```bash
  rtk jj commit -m "docs: define agent delegation boundaries"
  ```

## Task 7: Write the PydanticAI reference profile

**Files:**

- Create: `assistants/shared/agent-architecture/reference-profiles/pydantic-ai/README.md`
- Create: `assistants/shared/agent-architecture/reference-profiles/pydantic-ai/construction.md`
- Create: `assistants/shared/agent-architecture/reference-profiles/pydantic-ai/services-and-dependencies.md`
- Create: `assistants/shared/agent-architecture/reference-profiles/pydantic-ai/tools-and-capabilities.md`
- Modify: `docs/superpowers/specs/2026-07-31-plato-agent-architecture-provenance.yaml`
- Modify: `tests/assistants/test_agent_architecture.py`
- Read: `../plato/uv.lock`
- Read: official PydanticAI and `subagents-pydantic-ai` documentation

- [ ] Verify the pinned evidence versions in `../plato/uv.lock`:

  ```bash
  rtk rg -n -A 3 -B 1 'name = "(pydantic-ai-slim|subagents-pydantic-ai)"' ../plato/uv.lock
  ```

  Expected: `pydantic-ai-slim` version `2.18.0` and
  `subagents-pydantic-ai` version `0.2.7`. If either differs, stop and re-review
  the profile against the pinned source revision.

- [ ] Review these official sources read-only and record `2026-07-31` as the
  review date:

    - PydanticAI primary documentation:
    `https://ai.pydantic.dev/install/#slim-install`
    - PydanticAI release history:
    `https://github.com/pydantic/pydantic-ai/releases`
    - `subagents-pydantic-ai` primary documentation:
    `https://github.com/vstorm-co/subagents-pydantic-ai#readme`
    - `subagents-pydantic-ai` release history:
    `https://github.com/vstorm-co/subagents-pydantic-ai/releases`

- [ ] Add exact `version_reviews` records to the relevant provenance entries.
  Use product names `PydanticAI` and `subagents-pydantic-ai`, package names
  `pydantic-ai-slim` and `subagents-pydantic-ai`, and the verified versions.

- [ ] Add failing tests requiring the four files, the exact version-review
  records, the `Conditional reference profile` status phrase in each file, and
  valid profile-scoped normative sections.

- [ ] Run the focused test and confirm failure for the four absent documents.

- [ ] Write the profile README with:

    - an explicit conditional-adoption banner;
    - reviewed package versions and review date;
    - links to the three profile documents;
    - the boundary between framework-neutral core requirements and PydanticAI
      implementation choices; and
    - a statement that repository configuration takes precedence; and
    - a References section linking the reviewed official sources.

- [ ] Write `construction.md` covering:

    - startup-fixed agents versus intentionally dynamic factories;
    - explicit model and provider selection without prescribing a model name;
    - structured result models and validation;
    - construction-time versus run-time configuration;
    - exception translation at the service boundary; and
    - test seams for model and dependency substitution.

- [ ] Write `services-and-dependencies.md` covering:

    - `RunContext` and typed dependency containers;
    - public service functions that hide framework mechanics;
    - factories when dynamic construction is intentional;
    - cloning or mapping dependencies for delegated runs;
    - safe handling of mutable resources; and
    - explicit lifecycle ownership.

- [ ] Write `tools-and-capabilities.md` covering:

    - tool registration and typed tool arguments;
    - sequential execution for shared mutable state;
    - scoped toolsets and capability grants;
    - package-version-reviewed dynamic-subagent behavior;
    - separate child runs without implicit parent history;
    - explicit dependency cloning and resource-sharing policy; and
    - cancellation, retry, and result collection.

  Keep package-specific symbols in this profile, not in core or delegation.

- [ ] Run focused tests and profile Markdownlint:

  ```bash
  rtk uv run --frozen pytest tests/assistants/test_agent_architecture.py -q
  rtk npx --no-install markdownlint-cli2 --config assistants/shared/standards/templates/python/.markdownlint.json "assistants/shared/agent-architecture/reference-profiles/pydantic-ai/*.md"
  ```

  Expected: both commands exit zero.

- [ ] Commit the PydanticAI profile:

  ```bash
  rtk jj commit -m "docs: add pydanticai reference profile"
  ```

## Task 8: Write the Logfire and Streamlit profiles

**Files:**

- Create: `assistants/shared/agent-architecture/reference-profiles/README.md`
- Create: `assistants/shared/agent-architecture/reference-profiles/logfire.md`
- Create: `assistants/shared/agent-architecture/reference-profiles/streamlit-demo-apps.md`
- Modify: `docs/superpowers/specs/2026-07-31-plato-agent-architecture-provenance.yaml`
- Modify: `tests/assistants/test_agent_architecture.py`
- Read: `../plato/docs/agent_charter/observability_logfire.md`
- Read: `../plato/docs/agent_charter/demo_apps.md`
- Read: `../plato/uv.lock`
- Read: official Logfire and Streamlit documentation

- [ ] Verify the pinned evidence versions:

  ```bash
  rtk rg -n -A 3 -B 1 'name = "(logfire|streamlit)"' ../plato/uv.lock
  ```

  Expected: Logfire version `4.36.0` and Streamlit version `1.54.0`.

- [ ] Review these official sources read-only and record `2026-07-31` as the
  review date:

    - Logfire primary documentation: `https://pydantic.dev/docs/logfire/`
    - Logfire changelog:
    `https://github.com/pydantic/logfire/blob/main/CHANGELOG.md`
    - Streamlit primary documentation: `https://docs.streamlit.io/`
    - Streamlit release notes:
    `https://docs.streamlit.io/develop/quick-reference/changelog`

- [ ] Add exact Logfire and Streamlit `version_reviews` records to provenance.
  Add failing tests for both records, all three files, profile banners, profile
  index links, and valid profile-scoped normative sections.

- [ ] Run the focused test and confirm failure for the three absent documents.

- [ ] Write `reference-profiles/README.md` with:

    - the conditional authority model;
    - adoption instructions;
    - one link each to PydanticAI, Logfire, and Streamlit; and
    - a reminder that core contracts still apply when a profile is adopted.

- [ ] Write `logfire.md` with:

    - an explicit conditional-adoption banner and reviewed version;
    - low-cardinality span naming;
    - exception recording and status;
    - bounded input and output capture;
    - scrubbing and privacy review;
    - optional framework instrumentation; and
    - a rule that payload capture and user identity propagation are explicit
      security decisions, never defaults; and
    - a References section linking the reviewed official sources.

  Exclude tokens, secret lookup, environment-file setup, internal headers,
  infrastructure configuration, and Plato project names.

- [ ] Write `streamlit-demo-apps.md` with:

    - an explicit conditional-adoption banner and reviewed version;
    - direct-import prototyping;
    - a self-contained minimal layout for input, invocation, and result rendering;
    - criteria for choosing direct imports versus MCP;
    - clear marking of runnable versus illustrative snippets; and
    - limits that keep the profile about demos rather than production
      deployment; and
    - a References section linking the reviewed official sources.

  Exclude authentication, credentials, internal packages, cloud deployment,
  TLS, load balancers, and publishing instructions.

- [ ] Run focused tests and profile Markdownlint:

  ```bash
  rtk uv run --frozen pytest tests/assistants/test_agent_architecture.py -q
  rtk npx --no-install markdownlint-cli2 --config assistants/shared/standards/templates/python/.markdownlint.json "assistants/shared/agent-architecture/reference-profiles/*.md"
  ```

  Expected: both commands exit zero.

- [ ] Commit the remaining profiles:

  ```bash
  rtk jj commit -m "docs: add logfire and streamlit reference profiles"
  ```

## Task 9: Add README templates and non-normative stubs

**Files:**

- Create: `assistants/shared/agent-architecture/templates/readme-templates.md`
- Create: `assistants/shared/agent-architecture/stubs/testing.md`
- Create: `assistants/shared/agent-architecture/stubs/maturity-tiers.md`
- Modify: `tests/assistants/test_agent_architecture.py`
- Read: `../plato/docs/agent_charter/readme_templates.md`
- Read: `../plato/docs/agent_charter/testing.md`
- Read: `../plato/docs/agent_charter/maturity_tiers.md`

- [ ] Add failing tests requiring the template and two stubs. Require the exact
  banner prefix `> **Status:** Non-normative draft.` in both stubs and reject
  uppercase `MUST` or `SHOULD` from templates and stubs.

- [ ] Require the README template to contain these exact H2 headings:

    - Purpose
    - Architecture
    - Inputs and Outputs
    - Dependencies
    - Tools and Capabilities
    - State and Persistence
    - Control Flow
    - Errors
    - Testing and Evaluation
    - Limitations
    - References

- [ ] Run the focused test and confirm failure for the three absent documents.

- [ ] Write `readme-templates.md` as an informative copy-and-adapt template.
  Include the exact headings above, concise prompts under each heading, and an
  instruction to label every code sample as runnable or illustrative. Do not
  create compliance rules.

- [ ] Write `testing.md` with the exact non-normative banner and only the
  source-supported outline for unit, contract, integration, evaluation, and
  end-to-end layers. Explicitly identify absent acceptance criteria and coverage
  thresholds as unresolved design inputs; do not invent values.

- [ ] Write `maturity-tiers.md` with the exact non-normative banner and the
  labels `Experimental`, `Preview`, and `Production`. Preserve only the
  source-supported intent of each label and explicitly state that promotion
  gates, owners, evidence requirements, and rollback criteria are not yet
  defined. Do not make any tier normative.

- [ ] Run focused tests and Markdownlint:

  ```bash
  rtk uv run --frozen pytest tests/assistants/test_agent_architecture.py -q
  rtk npx --no-install markdownlint-cli2 --config assistants/shared/standards/templates/python/.markdownlint.json "assistants/shared/agent-architecture/templates/*.md" "assistants/shared/agent-architecture/stubs/*.md"
  ```

  Expected: both commands exit zero.

- [ ] Commit the informative material:

  ```bash
  rtk jj commit -m "docs: add agent architecture templates and stubs"
  ```

## Task 10: Add the library entry point and complete structural tests

**Files:**

- Create: `assistants/shared/agent-architecture/README.md`
- Modify: `tests/assistants/test_agent_architecture.py`
- Modify: `docs/superpowers/specs/2026-07-31-plato-agent-architecture-provenance.yaml`

- [ ] Add failing tests for the exact 25-file tree and the root README.

- [ ] Add an index-coverage test over these three index files:

    - `assistants/shared/agent-architecture/README.md`
    - `assistants/shared/agent-architecture/reference-profiles/README.md`
    - `assistants/shared/agent-architecture/reference-profiles/pydantic-ai/README.md`

  Parse relative Markdown links from only those indexes. Require every other
  library document to be linked exactly once across the three indexes. Require
  every local link in every library document to resolve to an existing file.

- [ ] Add a normative-structure test that scans each line containing uppercase
  `MUST` or `SHOULD`, requires the line to begin `Requirement:`, and requires
  `Rationale:`, `Scope:`, and `Exceptions:` before the next heading of equal or
  higher level.

- [ ] Add a portability test over all 25 Markdown files rejecting these concrete
  patterns case-insensitively where appropriate:

    - absolute `/Users/` paths;
    - `~/.aws`, `~/.agents`, `~/.claude`, and `~/.cursor`;
    - `from plato`, `import plato`, and `plato.`;
    - `AGTC-` followed by digits;
    - `X-Amzn-Oidc`;
    - `LocalBackend` and `DesignManifestStore`;
    - CodeArtifact hostnames; and
    - the numeric taxonomy tokens `P0`, `P1`, `P2`, and `P3`.

- [ ] Add a provenance-completeness test requiring every non-excluded source
  destination to exist in `documents`, every manifest document to exist on
  disk, and every on-disk Markdown document to have exactly one manifest entry.

- [ ] Run the focused test and confirm failure because the root README is absent.

- [ ] Write the root README with:

    - purpose and intended readers;
    - authority and adoption rules;
    - the Workflow, Agent, and Orchestrator overview;
    - Director/Act/Scene as the orchestration vocabulary;
    - a library map linking core, orchestration, delegation, profiles, templates,
    and stubs;
    - a reading order for new systems and existing-system reviews;
    - the authority-status legend; and
    - the relationship to repository instructions and the separate engineering
    standards library.

  The root index links all core, orchestration, and delegation documents, the
  reference-profile index, the template, and both stubs. The profile index owns
  links to the three profiles, and the PydanticAI README owns links to its three
  detail documents.

- [ ] Reconcile all provenance entries with final source roles,
  transformation notes, evidence paths, and version reviews. Do not change the
  seven-key schema or source revision.

- [ ] Run focused tests, Ruff, and full library Markdownlint:

  ```bash
  rtk uv run --frozen pytest tests/assistants/test_agent_architecture.py -q
  rtk uv run --frozen ruff check tests/assistants/test_agent_architecture.py
  rtk npx --no-install markdownlint-cli2 --config assistants/shared/standards/templates/python/.markdownlint.json "assistants/shared/agent-architecture/**/*.md"
  ```

  Expected: all commands exit zero; pytest reports only passing tests and
  Markdownlint reports zero errors.

- [ ] Commit the integrated library contract:

  ```bash
  rtk jj commit -m "docs: complete agent architecture reference library"
  ```

## Task 11: Review and verify the completed program

**Files:**

- Review: `assistants/shared/agent-architecture/**/*.md`
- Review: `docs/superpowers/specs/2026-07-31-plato-agent-architecture-provenance.yaml`
- Review: `tests/assistants/test_agent_architecture.py`
- Verify unchanged: `../plato/docs/agent_charter/*.md`
- Verify unchanged: `../plato/docs/agentic_workflows/*.md`
- Verify unchanged: `../plato/uv.lock`

- [ ] Invoke `superpowers:verification-before-completion` before making any
  completion claim.

- [ ] Dispatch two independent read-only Luna extra-high reviewers in parallel:

  1. A specification reviewer maps every approved design requirement and all 21
     source dispositions to the implemented files and provenance records.
  2. A portability reviewer checks authority boundaries, normative-rule
     explanations, framework-neutral core language, profile isolation, stub
     labeling, local links, and prohibited state or project leakage.

  Ask each reviewer to report findings with exact file and line references.

- [ ] Address every confirmed finding inline. Re-run the focused pytest and
  Markdownlint commands after each correction group.

- [ ] Run the complete repository verification set from a fresh process:

  ```bash
  rtk uv run --frozen pytest -q
  rtk uv run --frozen ruff check .
  rtk uv run --frozen mypy
  rtk uv run --frozen pre-commit run --all-files
  rtk npx --no-install markdownlint-cli2 --config assistants/shared/standards/templates/python/.markdownlint.json "assistants/shared/agent-architecture/**/*.md" docs/superpowers/specs/2026-07-31-plato-agent-architecture-design.md
  rtk npx --no-install markdownlint-cli2 --config assistants/shared/standards/templates/python/.markdownlint.json docs/superpowers/plans/2026-07-31-plato-agent-architecture.md
  ```

  Expected: every command exits zero. Record the pytest pass count in the final
  handoff rather than predicting it in this plan.

- [ ] Reconfirm Plato remained untouched at the reviewed source paths:

  ```bash
  rtk jj --repository ../plato diff --from 0d7699bb0cae3025097718126fcb8e413b6a49e0 --to @ --summary 'root:docs/agent_charter' 'root:docs/agentic_workflows' 'root:uv.lock'
  ```

  Expected: no output. Unrelated Plato changes may remain and must not be
  modified.

- [ ] Inspect the ballen-config program diff from the approved design commit:

  ```bash
  rtk jj diff --from ynpzzzrx --to @- --summary
  rtk jj status
  ```

  Expected: the summary contains only this implementation plan, the provenance
  YAML, the 25 Markdown library files, and the focused test file. The working
  copy is empty after the last commit.

- [ ] If review corrections changed files after Task 10, commit them as one
  coherent correction change:

  ```bash
  rtk jj commit -m "docs: polish agent architecture reference library"
  ```

- [ ] Re-run the complete verification set after that commit and report exact
  commands and outcomes. Do not claim completion from an earlier run.

## Completion Criteria

- The passive library contains exactly 25 linked Markdown documents at the
  approved paths.
- Plato's source documents and lockfile still match the pinned reviewed
  revision; no Plato file was changed by this work.
- Every one of the 21 source documents has exactly one explicit disposition.
- Every destination document has exactly one provenance record with kind,
  authority, sources, source roles, and transformation note.
- Core MCP guidance is framework-neutral.
- PydanticAI, Logfire, and Streamlit content is visibly conditional and backed
  by dated version reviews.
- Workflow, Agent, and Orchestrator replace the numeric shorthand.
- Director, Act, and Scene remain the primary orchestration vocabulary and have
  the exact generic translation table.
- Static agent-as-tool and dynamic-subagent mechanisms have explicit isolation
  and sharing contracts independent of orchestration placement.
- Every uppercase `MUST` and `SHOULD` has rationale, scope, and exceptions.
- Testing and maturity documents are visibly non-normative drafts and introduce
  no normative requirements.
- No catalog, installer, generated projection, bootstrap behavior, skill, or
  Plato-side cleanup is included.
- Focused and full verification commands pass from fresh processes.
