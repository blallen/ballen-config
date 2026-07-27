# Plato Generic Assets Migration Program Design

## Status

High-level program design for extracting reusable engineering assets from Plato
into `ballen-config`. Each workstream requires its own detailed design and
approval before implementation.

## Context

Plato contains three different kinds of potentially reusable material:

1. coding standards and coding-assistant instructions;
2. helper, tooling, review, and development-workflow skills; and
3. an application-agent development charter under `docs/agent_charter/`.

Those materials currently mix durable engineering practices with Plato package
paths, domain concepts, GitLab topology, infrastructure, framework choices, and
generated local agent state. Copying the trees wholesale would preserve the
wrong assumptions and create configuration drift.

`ballen-config` already provides the desired cross-agent foundation:

- one reviewed repository source of truth;
- target-aware catalogs for portable assets;
- independent native adapters for Cursor, Claude Code, and Codex;
- copied skill trees in each agent's native skill root; and
- collision, provenance, safety, and drift checks.

The migration extends that architecture. It does not introduce cross-agent
imports, shared live configuration, or synchronization from installed agent
state.

## Goals

- Extract durable, project-agnostic practices from Plato.
- Preserve clear ownership between generic assets and Plato overlays.
- Support Cursor, Claude Code, and Codex independently through each agent's
  native configuration model.
- Keep always-loaded instructions concise.
- Make fuller guidance available for later progressive loading.
- Preserve provenance without creating an ongoing synchronization dependency.
- Deliver the work as three separately designed and reviewable migrations:
  standards, skills, then application-agent architecture.

## Non-Goals

- Copy Plato's configuration trees byte for byte.
- Move or delete the source material from Plato.
- Modify Plato source material as part of the generic migration.
- Keep generic assets automatically synchronized with Plato.
- Migrate authentication, credentials, trust, sessions, memories, project
  paths, caches, indexes, worktrees, permissions, or generated plugin state.
- Install Plato's GitLab CI, CODEOWNERS, package layout, deployment topology,
  test shards, or domain policies as global defaults.
- Automatically modify arbitrary repositories with generated rules or tool
  configuration.
- Load the complete standards library or application-agent charter into every
  prompt.

## Program Invariants

1. `ballen-config` owns the genericized result after promotion.
2. Plato retains repository-specific overlays and historical provenance.
3. Repository instructions override global defaults.
4. No agent reads another agent's installed files as configuration input.
5. Every installed asset is rendered or copied independently to the selected
   agent's native destination.
6. Shared assets contain no absolute project paths, Plato imports, internal
   project identifiers, credentials, or generated local state.
7. A promotion records its source and review status, but does not create a live
   link back to Plato.
8. Optional or framework-specific guidance is progressively loaded rather than
   globally injected.
9. Standards own normative engineering guidance. Skills own procedures and
   reference stable standards identifiers rather than restating the rules.
10. Cross-asset links and shared-skill references resolve through declared
    catalog dependencies or co-packaged relative paths after native delivery.
    External command, plugin, and connector prerequisites use a separate,
    testable runtime contract.
11. Version-sensitive claims are verified against primary sources during
    promotion; conflicts and intentional departures are recorded.
12. The program is extract-only with respect to Plato. A workstream modifies
    Plato only after a separate, explicit override decision; source cleanup or
    backports are follow-up work.

Promotion provenance includes, at minimum, the source repository, relative
path, source revision or change ID, and portability review result. A detailed
design may add structured schema fields or define a validated text convention,
but free-form untestable provenance is insufficient.

## Target Architecture

The illustrative target keeps authored content separate from native delivery:

```text
assistants/
├── shared/
│   ├── instructions/
│   │   └── engineering.md
│   ├── standards/
│   │   ├── README.md
│   │   ├── python.md
│   │   ├── pydantic.md
│   │   ├── validation.md
│   │   ├── api-design.md
│   │   ├── testing.md
│   │   ├── documentation.md
│   │   └── source-control.md
│   ├── skills/
│   │   ├── catalog.yaml
│   │   └── <skill-name>/
│   └── agent-architecture/  # illustrative until delivery is designed
│       ├── README.md
│       ├── directory-structure.md
│       ├── agent-service-pattern.md
│       ├── models-and-errors.md
│       ├── tool-design.md
│       └── framework-overlays/
├── cursor/
├── claude/
└── codex/
```

The detailed workstream designs may refine filenames and subdirectories. In
particular, the application-agent architecture's canonical storage location
depends on whether its first delivery is a skill, scaffold, or both. The
designs must preserve the ownership boundaries shown here.

## Workstream 1: Engineering Standards

### Scope

This workstream owns both coding-assistant operating principles and reusable
coding standards. Plato's root `AGENTS.md` and `CLAUDE.md` belong here, not in
the application-agent charter workstream.

The existing `assistants/shared/instructions/engineering.md`, its three native
renderers, and their tests are the baseline. The migration extends and
reorganizes that authority; it does not create a second global instruction
source.

### Two-Layer Model

The standards use two layers:

1. **Always-on core** in
   `assistants/shared/instructions/engineering.md`.
   It contains concise, broadly applicable defaults such as repository
   precedence, staff-level judgment, the simplest sufficient solution, typed
   Python defaults when Python is applicable, verification expectations, and
   Jujutsu preference when `.jj/` is present. Language and framework clauses
   remain subordinate to repository configuration.
2. **Fuller standards library** under `assistants/shared/standards/`.
   It contains genericized Python, Pydantic, validation, API, testing,
   documentation, and source-control guidance.

Only the concise core is rendered into every agent's global instructions in
this workstream. The fuller library is canonical reference material and is not
automatically loaded into every prompt.

Workstream 1 also defines stable document identifiers, an index, provenance,
and an adapter-independent lookup contract. Later workstreams may choose how to
package those documents, but may not redefine their semantic identity.

If a later skill packages these standards, the canonical documents remain
under `assistants/shared/standards/`. Skill-local references are deterministic
projections with drift tests, never independently edited copies. Implementing
that projection belongs to the skills workstream.

### Native Delivery

- Cursor receives the core through the existing rendered User Rules artifact.
- Claude Code receives the core through its managed global `CLAUDE.md`.
- Codex receives the core through its managed global `AGENTS.md`.
- Agent-specific suffixes retain only native behavior and safety boundaries.

The existing instruction renderer remains the delivery mechanism unless the
detailed standards design establishes a concrete need to change it.

### Explicit Deferrals

- Packaging the fuller standards as one or more progressively loaded skills.
- Deciding whether a standards skill is a dependency of review/test skills.
- Parameterized Ruff, mypy, pytest, pre-commit, Markdownlint, or coverage
  templates.
- Per-repository scaffolding of `AGENTS.md`, `CLAUDE.md`, or Cursor rule files.

Those are follow-up decisions, not prerequisites for the initial standards
migration.

## Workstream 2: Reusable Skills

### Scope

This workstream promotes generic helper, review, source-control, and
development-workflow skills. Each skill is reviewed independently and placed
in the existing shared skill catalog.

The candidate migration tiers are:

1. foundational discovery and source-control skills;
2. standards, quality, type, test, and snapshot review skills;
3. self-review, bug-fix, commit, and development-workflow orchestration;
4. GitLab and merge-request workflows.

Domain context, QSP review, company reporting, and environment-specific
observability guidance remain in Plato.

Document, presentation, and storage utilities are deferred candidates. Their
detailed design must classify them as default-profile, work-profile, deferred,
or dependent on a new opt-in mechanism; calling them optional does not itself
create an installation selector.

The existing `jujutsu-workflow` skill is a promoted, tested baseline, not new
migration work. It provides the reference pattern for later promotions.

### Packaging

Each promoted skill:

- uses the open `SKILL.md` directory structure;
- declares targets, profiles, dependencies, provenance, and portability status;
- is copied independently to Cursor, Claude Code, and Codex native skill roots;
- contains no references to another agent's installed tree;
- discovers repository tools and standards rather than assuming Plato paths;
- owns workflow rather than copying normative standards text;
- detects `.jj/` before using staged diffs, branches, default-branch names, or
  worktree semantics, and uses Jujutsu procedures when applicable;
- declares every required shared-skill and cross-asset reference; and
- uses one common-denominator `SKILL.md` and co-packaged native reference files
  only where agent tool surfaces genuinely differ.

The current installer copies byte-identical skill trees to every selected
native root. It does not render target-specific skill variants. Distinct
entrypoints therefore use distinct qualified skill names unless a later
adapter design explicitly adds per-target rendering.

Catalog skill dependencies validate installation eligibility only. They do not
invoke or progressively load another skill, and they do not model external
commands, plugins, or connectors. Runtime loading and external prerequisites
require separate contracts in the detailed skills design, such as skill
instructions, target restrictions, documented prerequisites, or `doctor`
checks.

### Progressive Standards Loading

The detailed skills design will evaluate whether to package the fuller
standards library as:

1. one shared standards-reference skill invoked by review workflows;
2. focused language or task standards skills; or
3. references bundled only with the skills that need them.

The design must avoid duplicated standards authorities. This decision is
deliberately deferred until the skill dependency graph is reviewed in detail.

Review-derived lessons default to the current repository's local standards
authority. Updating shared `ballen-config` standards requires a separate,
explicit promotion and review. Plato's lesson ledgers remain Plato provenance
and are never installed globally.

## Workstream 3: Application-Agent Architecture

### Scope

This workstream extracts reusable application-agent structure and design
patterns from Plato's `docs/agent_charter/`. It is not a coding-assistant
persona and is not part of the global `AGENTS.md` or `CLAUDE.md` instructions.

The reusable core is expected to be a framework-neutral Python
application-agent pattern covering:

- clear responsibilities for `agent.py`, `tools.py`, `service.py`, `models.py`,
  `constants.py`, and `exceptions.py`;
- optional `mcp.py` and framework integration boundaries;
- thin tools delegating to a service layer;
- typed inputs, outputs, dependencies, and errors without prescribing one
  framework's base classes or envelopes;
- public API and import-direction principles whose exact contracts are chosen
  by the detailed design; and
- application-agent-specific testing and documentation deltas that reference,
  rather than restate, the canonical standards library.

PydanticAI construction, `@agent.instructions`, dynamic instruction
registration, and the source
`.cursor/rules/agent_prompt_decomposition.mdc` belong to the explicit
PydanticAI overlay.

### Extraction Boundary

The generic architecture removes:

- `plato.*` imports and package locations;
- fixed Plato capability rosters and base classes;
- internal authentication, AWS, S3, GitLab, and corporate SSL behavior;
- required Logfire decorators or project names;
- fixed MCP request/response bases;
- unfinished charter backlog items; and
- domain examples presented as universal architecture.

Framework-specific practices, including PydanticAI conventions, belong in
explicit overlays rather than the framework-neutral core.

The detailed design must classify every source under `docs/agent_charter/` as
core, framework overlay, separate skill or template, deferred, or Plato-only.
The incomplete `testing.md` and `maturity_tiers.md` documents and `todos.md`
are deferred by default. `evals.md`, `demo_apps.md`, and
`readme_templates.md` require explicit placement outside or inside the
architecture core.

The extraction evaluates rather than inherits Plato contracts, including:

- mandatory `success` and `error` envelopes;
- the rule that MCP wrappers never raise;
- `AgentBaseError`;
- strict public-API and import-direction rules;
- singleton versus factory construction;
- `@dataclass` dependency containers; and
- sequential mutation-tool requirements.

Rejected or framework-specific contracts remain in a Plato or framework
overlay.

### Delivery

The architecture pack is not globally loaded. Its detailed design will choose
between:

- a progressively loaded agent-architecture skill with reference documents;
- a reusable project scaffold or template; or
- both, with one canonical source and generated projections.

No canonical storage path is final until that delivery choice is made. If
canonical documents live outside a skill or template, projections require
deterministic generation and drift tests. Repository scaffolding requires a
separate ownership and conflict design before adoption.

## Cross-Workstream Ownership

| Concern | Owner |
|---|---|
| Global coding-assistant defaults | Standards |
| Detailed Python/Pydantic/testing guidance | Standards |
| Standard discovery and application workflows | Skills |
| Source-control selection and safety policy | Standards |
| Jujutsu and Git commands and procedures | Skills |
| GitLab/MR operations | Skills |
| Progressive loading of detailed standards | Skills design, using standards sources |
| Application-agent directory and layer pattern | Agent architecture |
| General testing and documentation rules | Standards |
| Application-agent-specific testing/documentation deltas | Agent architecture |
| PydanticAI construction and prompt decomposition | Agent-architecture overlay |
| Repository-local lesson promotion | Current repository |
| Shared standards promotion | Explicit `ballen-config` review workflow |
| Plato package, domain, CI, auth, and infrastructure rules | Plato |
| Native rendering, copying, collision, and drift behavior | `ballen-config` adapters |

## Sequence and Change Management

The default program sequence is:

1. approve and commit this program design;
2. design, implement, and validate standards;
3. design, implement, and validate skills; and
4. design, implement, and validate application-agent architecture.

This sequence is a planning preference, not a total dependency chain.
Standards authority must exist before standards-dependent skill or
agent-architecture content lands. GitLab foundations must exist before MR
workflows. Agent architecture does not depend on unrelated GitLab, MR,
document, presentation, or storage skills and may proceed if those clusters are
deferred.

Each implementation receives a separate Jujutsu bookmark created from the
current `main` after any required predecessor has landed:

- `port-plato-standards`;
- `port-plato-skills`; and
- `port-plato-agent-architecture`.

The standards bookmark begins with this program design. Later workstreams may
refer to the design after it lands on `main`; they do not need to remain stacked
on an unmerged implementation branch.

Each workstream uses logical, independently reviewable commits:

1. detailed design and implementation plan;
2. validation or adapter support, when required;
3. one coherent content or dependency cluster per commit; and
4. documentation and final verification updates.

## Validation Strategy

Every workstream must verify:

- no prohibited project paths, identifiers, imports, credentials, or generated
  state;
- catalog names, source paths, frontmatter, targets, profiles, dependencies,
  and provenance;
- stable standards identifiers and resolution of every cross-asset reference;
- absence of duplicated normative standards inside workflow skills or
  architecture guidance;
- deterministic native rendering or copying for every installable output
  delivered by that workstream;
- whole-agent skip behavior and unmanaged collision preservation;
- focused tests for changed behavior;
- repository lint, formatting, type, policy, and integration checks; and
- `bootstrap plan` and `bootstrap doctor` for the applicable profile.

Content reviews must also:

- apply an explicit authority order of repository requirements, current primary
  documentation, generic standards, and finally source examples;
- record conflicts, corrections, and intentional departures;
- compare the genericized result with its source without preserving known
  source errors or drift; and
- confirm that removed Plato behavior remains covered by Plato's own overlay.

## Deferred Decisions

The program intentionally leaves these decisions to detailed workstream
designs:

- the exact standards document split and wording;
- standards-as-skills packaging and dependency behavior;
- the precise first set and naming of promoted skills;
- GitLab connector versus CLI adaptations for each agent;
- whether executable configuration templates belong in `ballen-config`;
- the framework-neutral versus PydanticAI overlay boundary; and
- the canonical storage and projection model for application-agent
  architecture;
- whether application-agent architecture needs a project scaffold in addition
  to a skill.

## Success Criteria

The program is successful when:

- the generic assets can be understood without Plato context;
- Cursor, Claude Code, and Codex each receive independently valid native
  configuration;
- global instructions remain concise;
- deeper guidance is available without being loaded by default;
- Plato-specific rules and operational state remain in Plato;
- each migration can be reviewed, landed, or deferred independently; and
- future updates have one clear generic authority and one clear Plato overlay.
