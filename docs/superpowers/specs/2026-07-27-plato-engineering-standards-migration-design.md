# Plato Engineering Standards Migration Detailed Design

## Status

Detailed design for Workstream 1 of the
[Plato generic assets migration program](./2026-07-27-plato-generic-assets-migration-design.md).
The design is approved for implementation planning. Implementation remains
gated on review of this written specification.

## Context

Plato's root assistant instructions, Cursor rules, review lessons, tooling
guides, and workflow skills mix four different concerns:

1. concise defaults that should guide every coding assistant;
2. reusable engineering standards that should be consulted when relevant;
3. tool and review procedures that belong in skills; and
4. Plato package, infrastructure, domain, and development-stage policy.

`ballen-config` already renders one shared engineering instruction into Cursor,
Claude Code, and Codex. This migration extends that source of truth and adds a
reference-only standards library without loading the whole library into every
prompt.

The Plato source checkout was clean during the final inventory. The source
revision was `d18efa3f4bf3bff6f07a1019e4f6d6c0f4206387`. Implementation must
capture the then-current clean revision in structured provenance rather than
assuming this design-time revision is still current.

## Goals

- Keep the always-on engineering core concise and broadly applicable.
- Make fuller standards authoritative, focused, and independently addressable.
- Preserve repository precedence over global defaults.
- Update the shared Pydantic default from an obsolete minor pin to Pydantic v2.
- Record structured, testable provenance and intentional source corrections.
- Validate the standards library before bootstrap can perform effects.
- Preserve independent native delivery to Cursor, Claude Code, and Codex.
- Leave procedures, command recipes, and progressive skill loading to the
  skills workstream.
- Leave Plato unchanged unless a later explicit override authorizes a source
  update.

## Non-Goals

- Install or progressively load the fuller standards library in this
  workstream.
- Create a new `CatalogKind` or an `apply-catalog` plan action for standards.
- Add Ruff, mypy, pytest, pre-commit, Markdownlint, or coverage templates.
- Scaffold project-local `AGENTS.md`, `CLAUDE.md`, or Cursor rules.
- Port application-agent architecture or prompt-decomposition guidance.
- Port authentication, trust, sessions, project paths, generated plugin state,
  or internal infrastructure.
- Implement a future uv workflow skill.
- Rewrite or clean up Plato source files.

## Design Decisions

### Two Layers

The migration creates two distinct layers:

1. `assistants/shared/instructions/engineering.md` remains the concise,
   always-on core rendered into every native agent instruction.
2. `assistants/shared/standards/` becomes the canonical, reference-only
   standards library.

The core owns defaults that must be present in every coding session. The fuller
library owns detailed normative guidance that is loaded only when a future
consumer deliberately requests it.

### Topic Library and Standalone Catalog

The fuller library uses focused topic documents plus a standalone typed
catalog. The catalog is loaded during assistant preflight but is not registered
as an installable inventory resource.

This is intentionally different from the existing extension, plugin, and skill
catalogs. Every current inventory catalog produces an installation action.
Treating reference material the same way would falsely claim that the fuller
library had been installed for an agent.

### Version Policy

The core says **Pydantic v2**, not Pydantic 2.8 or the latest current minor.
Repository pins take precedence. Version-sensitive content records the
documentation version against which it was reviewed.

The initial Pydantic guidance is reviewed against Pydantic 2.13.4, the current
stable release at design time. Pydantic 2.14.0a1 is a prerelease and does not
set the baseline. See the
[official Pydantic release history](https://pypi.org/project/pydantic/).

Python 3.12 remains the user's default baseline in this migration. A repository
may select a different supported Python version.

## Target Structure

```text
assistants/
├── shared/
│   ├── instructions/
│   │   └── engineering.md
│   └── standards/
│       ├── README.md
│       ├── catalog.yaml
│       ├── python.md
│       ├── pydantic.md
│       ├── validation.md
│       ├── api-design.md
│       ├── testing.md
│       ├── documentation.md
│       ├── source-control.md
│       └── dependency-management.md
├── cursor/
│   └── user-rules.md
├── claude/
│   └── CLAUDE.md
└── codex/
    └── AGENTS.md

src/ballen_config/assistants/
└── standards.py

tests/assistants/
└── test_standards.py
```

The implementation may extend existing instruction and integration test files,
but it must not create target-specific copies of the fuller standards.

## Always-On Engineering Core

### Required Content

The core is capped at 200 words and contains:

- repository instructions and executable configuration take precedence;
- staff-level judgment and the simplest sufficient solution;
- readability, maintainability, and avoidance of unrelated scope;
- fresh verification before completion claims;
- conditional Python defaults:
  - Python 3.12;
  - type hints;
  - `TypedDict` for controlled mapping shapes;
  - Pydantic v2 for validated models;
  - Google-style docstrings; and
  - pytest fixtures;
- Jujutsu when `.jj/` is present, otherwise the repository's selected
  source-control system.

The core does not include rationale, long examples, framework internals,
repository-specific commands, or detailed test taxonomies.

### Native Rendering

The existing renderer remains unchanged unless implementation exposes a
specific defect.

- Claude Code embeds the core in its managed global `CLAUDE.md`.
- Codex embeds the core in its managed global `AGENTS.md`.
- Cursor renders the core into the existing manual User Rules handoff artifact.

The repository-precedence sentence moves from all three native suffixes into
the core. Native suffixes retain only target-specific behavior and safety
boundaries.

Updating the core from Pydantic 2.8 to Pydantic v2 therefore updates all three
native outputs from one authored source. Cursor's live User Rules still require
the existing manual application step.

## Fuller Standards Library

### Human Index

`README.md` explains:

- the two-layer model;
- runtime precedence;
- how to use stable standard IDs;
- which documents are normative;
- that the library is not yet installed or progressively loadable; and
- how future skills must consume canonical content.

The README is not an independent authority. Tests compare its index with the
machine catalog.

### Documents

| Stable ID | Document | Scope |
|---|---|---|
| `standards.python` | `python.md` | Python style, typing, naming, imports, exceptions, and domain-owned serialization |
| `standards.pydantic` | `pydantic.md` | Pydantic model design, fields, configuration, validators, composition, settings, and serialization |
| `standards.validation` | `validation.md` | Trust boundaries, external data, secrets and redaction, structured validation results, and configuration boundaries |
| `standards.api-design` | `api-design.md` | HTTP semantics, typed request and response contracts, errors, and framework-neutral API design |
| `standards.testing` | `testing.md` | Test levels, regression workflow, fixtures, mocking, behavioral assertions, snapshots, and opt-in nondeterministic tests |
| `standards.documentation` | `documentation.md` | Google docstrings, README scope, diagrams, configured Markdown linting, and nonduplicated API documentation |
| `standards.source-control` | `source-control.md` | Repository detection, safety, and source-control policy without command recipes |
| `standards.dependency-management` | `dependency-management.md` | Repository-selected package managers, lockfiles, environments, and conditional uv policy |

The existing inventory resource ID `shared.engineering` remains the stable
identity of the always-on core.

### Content Boundaries

#### Python

Migrate generic guidance for readable design, explicit typing, safe exception
handling, `None` versus valid falsy values, domain naming, unambiguous model
names, named state constants, identity preservation, and model-owned
serialization.

Exclude Plato imports, Loguru mandates, centralized Plato configuration, and
package-layout requirements.

#### Pydantic

Migrate validated boundary models, `extra="forbid"` as the default application
posture, field documentation, composition, `Literal` and enum choices,
validator selection, serialization, and mechanisms such as
`pydantic.SecretStr`. Cover `pydantic_settings.BaseSettings` only when a
repository declares the separate `pydantic-settings` dependency. See the
[Pydantic migration guide](https://docs.pydantic.dev/latest/migration/).

Do not claim that `model_post_init` is deprecated. The detailed standard must
distinguish validated external boundaries from trusted internal mapping shapes
and runtime dependency containers. It cross-references
`standards.validation` for trust, secret-handling, redaction, and
configuration-boundary policy rather than owning those concerns.

#### Validation

Migrate trust-boundary analysis, typed external data, redaction, structured
validation results, dataframe or tabular validation, and separation between
fixed constants and environment-dependent configuration.

Exclude named secret providers, authentication flows, provider resolution,
and Plato's singleton configuration object.

#### API Design

Migrate standard HTTP method and status semantics, typed request and response
contracts, structured errors, and framework-neutral layering.

FastAPI, a particular async stack, and HATEOAS are optional examples rather
than universal requirements.

#### Testing

Migrate behavior-first tests, regression reproduction before fixes,
deterministic unit and integration tests, repository-defined functional-test
policy, fixtures, patch-at-use, async-aware mocks, meaningful assertions,
exception-message matching, strict expected failures, and reviewed snapshots.
Nondeterministic, external-service, and real-model tests are opt-in by default.

Repository marker names, Plato paths, real-model commands, Syrupy,
dirty-equals, and coverage thresholds are profiles or examples rather than
universal requirements.

#### Documentation

Migrate Google-style docstrings, specific terminology, purpose-focused READMEs,
Mermaid diagrams, configured Markdown linting, and the rule against duplicating
an API inventory in prose.

Exclude false claims about attribute docstrings being exposed through
`help()` and exclude Plato-specific README templates reserved for the
application-agent workstream.

#### Source Control

Migrate repository detection, the `.jj/` routing rule, preservation of
repository conventions, and safe review boundaries.

Commands, bookmark procedures, workspaces, rebases, and conflict recovery
remain in `jujutsu-workflow`. GitLab operations remain in their later skills
workstream.

#### Dependency Management

Require assistants to discover and use the repository's selected package
manager and lockfile rather than bypassing its environment.

For uv-managed repositories, Python commands run through the uv environment
and dependency changes use uv. Exact commands, workspace or package selection,
lockfile recipes, and troubleshooting belong in the candidate uv workflow
skill described below.

## Catalog and Lookup Contract

### Catalog Ownership

`assistants/shared/standards/catalog.yaml` is the machine authority for the
fuller library. It is target-neutral and has no profiles, destinations, or
installation state.

The catalog is not added to `assistants/inventory.yaml` and does not create a
new `CatalogKind.STANDARD`. This avoids an incorrect `install/apply-catalog`
plan action.

### Typed Records

`src/ballen_config/assistants/standards.py` defines strict Pydantic models for:

- the catalog version;
- each standard specification;
- discriminated repository-derived and authored provenance;
- primary-document references; and
- recorded conflicts or departures.

Raw YAML mappings use explicit typed structures at the loading boundary.

Each standard specification contains:

- `id`;
- repository-relative `source`;
- `title`;
- `summary`;
- applicability tags;
- related standard IDs;
- one or more structured provenance records;
- portability review status;
- intentional corrections or departures; and
- primary-source verification records when claims are version-sensitive.

Repository-derived provenance contains:

- `kind: repository`;
- source repository;
- relative source path;
- immutable commit ID;
- optional supplementary change ID;
- disposition: retained, adapted, or corrected; and
- a concise review note.

Authored provenance contains:

- `kind: authored`;
- a stable approved-decision reference;
- a concise rationale;
- the applicable primary-source reference IDs; and
- the portability review note.

Authored provenance does not invent a source repository path or commit.

Primary-source verification contains:

- source title;
- HTTPS URL;
- version or release reviewed when applicable; and
- review date.

### Validation

The loader rejects:

- invalid UTF-8 or duplicate YAML mapping keys before Pydantic validation;
- unsupported catalog versions;
- duplicate IDs or source paths;
- IDs outside the `standards.<topic>` namespace;
- absolute paths and traversal;
- symlinked or nonregular catalog, README, and standard files;
- sources outside `assistants/shared/standards/`;
- missing provenance;
- repository-derived provenance without an immutable source commit ID;
- authored provenance without decision and primary-source evidence;
- unknown dispositions or review statuses;
- unknown related standard IDs;
- orphan normative Markdown documents;
- README/catalog index drift; and
- nondeterministic catalog ordering.

The resolver maps a stable ID to its validated canonical file. Consumers use
IDs, not source paths, as semantic identity.

The YAML parser must preserve duplicate-key detection; calling
`yaml.safe_load()` and validating only the overwritten mapping is
insufficient.

### Preflight

Assistant desired-state loading validates and stores the standards catalog
before profile or skip resolution. Invalid standards fail before commands,
downloads, confirmations, backups, destination creation, or state writes.

The catalog produces no plan row and no native agent destination. A change to a
fuller standard must not alter global rendered instructions.

### Repository Documentation

The root README's coding-agent portability section links to the standards
library and explains:

- its reference-only status;
- preflight validation;
- why it creates no plan action; and
- the distinction between canonical standards and future skill projections.

The existing root documentation contract tests are updated with this section.

## Authority and Conflict Resolution

### Runtime Precedence

For work in a repository:

1. repository instructions and executable configuration;
2. the always-on core and applicable canonical standards;
3. procedural skills that apply those standards;
4. provisional review lessons; and
5. source examples or legacy patterns.

A skill cannot redefine a canonical standard. A repository may override a
global default for its own scope.

### Promotion Authority

When genericizing source material:

1. approved migration boundaries and user decisions;
2. current official primary documentation for version-sensitive behavior;
3. executable Plato configuration as evidence of Plato's actual behavior;
4. canonical generic standards; and
5. Plato prose, examples, and lesson ledgers.

Executable configuration is not automatically a universal standard. A
configuration/prose disagreement is recorded and resolved, not hidden through
precedence.

### Required Corrections

The migration records at least these intentional departures:

- Pydantic 2.8 becomes Pydantic v2 in the core.
- Pydantic guidance is initially reviewed against 2.13.4.
- `model_post_init` remains a supported hook and is not labelled deprecated.
- Loguru-specific imports, configuration, and incorrect exception examples do
  not become generic logging rules.
- Attribute-docstring behavior is described accurately or omitted.
- HATEOAS remains optional.
- Tests of framework behavior without application behavior are rejected as
  test theatre.
- Jujutsu repositories do not use Git staging, branch, or worktree procedures.
- uv command recipes move to the candidate uv workflow skill.
- agent construction, MCP, prompt decomposition, eval thresholds, demos, and
  maturity tiers remain in the application-agent workstream.

## Source Disposition

### Root and Cursor Sources

| Plato source | Disposition | Target or treatment |
|---|---|---|
| `AGENTS.md` | Adapt | Always-on core; remove Plato development-stage and GitLab policy |
| `CLAUDE.md` | Do not migrate separately | Content duplicate of `AGENTS.md` |
| `.cursor/rules/104_python_style_guide.mdc` | Adapt and correct | `standards.python` and `standards.documentation` |
| `.cursor/rules/104_pydantic_style_guide.mdc` | Adapt and correct | `standards.pydantic`; remove Plato configuration paths and correct `model_post_init` |
| `.cursor/rules/104_data_validation.mdc` | Adapt | `standards.validation`; exclude named infrastructure and auth |
| `.cursor/rules/104_pythonic_apis.mdc` | Adapt | `standards.api-design`; make framework and HATEOAS choices optional |
| `.cursor/rules/104_llm_output.mdc` | Keep in Plato | Interaction tone is not an engineering standard; uv sentence is duplicate |
| `.cursor/rules/test_rules_macro.mdc` | Adapt | `standards.testing`; remove Plato paths, commands, and fixed marker policy |
| `.cursor/rules/test_rules_micro.mdc` | Adapt | `standards.testing`; keep principles, make libraries optional profiles |
| `.cursor/rules/uv.mdc` | Adapt | `standards.dependency-management`; reserve commands for a candidate uv workflow skill |
| `.cursor/rules/agent_charter_summary.mdc` | Defer | Application-agent architecture workstream |
| `.cursor/rules/agent_prompt_decomposition.mdc` | Defer | PydanticAI reference profile in the application-agent workstream |
| `.cursor/rules/lessons_learned.mdc` | Review as intake | Apply the item-level decisions below; do not copy the ledger |
| `.cursor/rules/lessons_promoted.mdc` | Provenance only | Existing destinations own normative wording |

### Active Lesson Decisions

| Active lesson | Decision |
|---|---|
| Test history-processing control flow separately from model behavior | Adapt into `standards.testing` as deterministic versus model-behavior scope |
| Put reusable test-data factories in shared fixtures | Adapt into `standards.testing` without prescribing one repository layout |
| Name or document intentionally excluded cases | Adapt into `standards.python` and `standards.documentation` |
| Document non-obvious performance choices | Adapt into `standards.documentation` |
| Extract complex inline conditional assignments | Adapt into `standards.python` as readability guidance |
| Use named result types for multi-value returns | Adapt into `standards.python`; do not mandate `NamedTuple` universally |
| Do not duplicate public API inventories in READMEs | Adapt into `standards.documentation` |
| Expose raw eval scores and separate reviewer dimensions | Defer to the application-agent evaluation profile |
| Call out simplification opportunities during review | Defer as review-skill procedure; the core already prefers simple solutions |
| Track expected versus actual model invocations | Defer to application-agent observability |
| Isolate heavy optional dependencies from unit-test imports | Adapt into `standards.python` and `standards.testing` |
| Keep `env_prefix` conventions consistent | Adapt as a Pydantic mechanism, subordinate to validation policy |
| Keep configuration discoverable and single-sourced | Adapt into `standards.validation` and `standards.documentation` |
| Distinguish not-found from not-ready errors | Adapt into `standards.api-design` without fixed framework classes |
| Update downstream handlers when exception contracts change | Adapt into `standards.python` |
| Graceful history-summarization fallback | Defer to application-agent architecture |
| MCP lifespan resource construction | Defer to application-agent architecture |
| Prefer explicit booleans when `None` has different semantics | Adapt into `standards.validation` |
| Align API/model and database nullability | Adapt into `standards.api-design` and `standards.validation` |
| Avoid lossy aggregate-only return contracts | Adapt into `standards.api-design` as caller-needs guidance |
| Use literal-tagged discriminated unions | Adapt into `standards.pydantic` |
| Derive rather than duplicate identity fields | Adapt into `standards.python` and `standards.pydantic` |
| Use `NotRequired` for omitted `TypedDict` keys | Adapt into `standards.python` and `standards.validation` |
| Disable generated equality for values without scalar equality | Adapt conditionally into `standards.python`; keep NumPy as an example only |
| S3 and presigned-URL lessons | Keep in Plato |

### Other Sources

| Plato source | Disposition | Treatment |
|---|---|---|
| `docs/tooling/uv_workspace_guide.md` | Evidence after correction | Do not copy stale workspace membership; use only verified generic policy |
| `docs/agent_charter/{README.md,agent_construction_standard.md,agent_service_pattern.md,file_organization.md,models_exceptions.md,tool_design_guidelines.md,mcp.md,capabilities.md,testing.md,evals.md,readme_templates.md,maturity_tiers.md,demo_apps.md}` | Defer | Detailed application-agent architecture workstream |
| `docs/agent_charter/{auth_flow.md,credentials_config.md}` | Hard exclude | Authentication, trust, secret resolution, and internal paths |
| `docs/agent_charter/observability_logfire.md` | Keep in Plato | Vendor and infrastructure profile; vendor-neutral observability is newly designed if needed |
| `docs/agent_charter/todos.md` | Keep in Plato | Historical backlog, not normative guidance |
| `docs/evals/threshold_guidelines.md` | Keep out of general standards | Plato-specific agent-evaluation evidence with model and threshold assumptions |
| `ruff.toml`, `pytest.ini`, `.pre-commit-config.yaml`, `.markdownlint.json`, root `pyproject.toml`, `src/pyproject.toml`, and `Makefile` | Executable evidence | Validate source claims without copying every setting into prose |
| `skills/tooling-{discover-standards,review-standards,review-quality,review-types,review-tests,create-tests,fix-bug,review-snapshots,self-review,lint-markdown,commit-msg}/**` | Defer procedures | Later skills own discovery, review, test, lint, bug-fix, and commit procedures |
| `skills/tooling-{workflow,s3-download,s3-upload}/**` | Not a standards source | Skills workstream may separately evaluate scope; internal operations do not become standards |
| `skills/jujutsu-workflow/**` | Existing skill baseline | Source-control standard owns only routing and safety policy |
| `skills/using-gitlab/**` and MR skills | Defer | GitLab and merge-request skills workstream |
| `.claude/temp/archive/**` | Keep in Plato | Historical lesson extraction artifacts |
| `.codex/**`, `.claude-plugin/**`, `.cursor-plugin/**`, and generated state | Exclude | Authentication, trust, paths, caches, sessions, and plugin state do not migrate |

## Future Installable Standards Guide

The skills workstream may later make the reference library progressively
available. That work must preserve this design's authority and identity.

### Packaging Choices

The later design may choose:

- one `engineering-standards` reference skill;
- focused standards skills by topic; or
- standards projections bundled with the workflows that need them.

It may not create independently edited standards copies.

### Required Mechanisms

Before treating standards as installed or invokable, the skills workstream
must provide:

- deterministic projection from canonical catalog IDs;
- a projection manifest mapping each ID to a bundled relative file and digest;
- drift tests between canonical documents and every projection;
- byte-identical delivery to each selected native skill root unless a reviewed
  adapter design establishes target-specific rendering;
- collision, skip, and unmanaged-file preservation;
- no cross-agent installed-path references; and
- explicit external prerequisite checks rather than modelling commands or
  plugins as skill dependencies.

If the later packaging uses skill-to-skill invocation, it additionally
requires catalog dependencies that install the skill set together and
target-by-target proof of runtime invocation and fallback behavior. A workflow
that bundles its required standards references does not require those two
mechanisms.

Adding a standards entry to the general assistant inventory requires a
reference-only resource role and defined plan semantics. Without that role,
the standalone catalog remains the correct authority.

### Candidate uv Workflow Skill

A later skills design may choose the name `using-uv`. That candidate would own:

- uv project discovery;
- command selection;
- workspace and package targeting;
- adding, removing, locking, and syncing dependencies;
- running tools in the managed environment;
- frozen or locked verification;
- troubleshooting; and
- graceful behavior when uv is absent or the repository selects another tool.

The candidate references `standards.dependency-management` and does not
restate its normative policy. Its final name, packaging, targets, and
dependencies remain Workstream 2 decisions.

## Validation Strategy

### Catalog and Resolver

Focused tests cover:

- valid loading and stable-ID resolution;
- invalid UTF-8, duplicate YAML keys, and unsupported catalog versions;
- duplicate IDs and sources;
- malformed or incomplete provenance;
- invalid dispositions and review states;
- absolute paths, traversal, symlinks, nonregular files, and missing files;
- unknown related standard IDs;
- orphan standards documents;
- deterministic ordering; and
- README/catalog drift.

### Core and Native Outputs

Tests enforce:

- the 200-word core budget;
- repository precedence;
- conditional language and framework defaults;
- `Pydantic v2` and absence of `Pydantic 2.8`;
- verification language;
- `.jj/`-conditional Jujutsu;
- the core exactly once in all three native outputs;
- target-specific suffix content only;
- Cursor and Claude RTK embedding versus Codex's RTK include; and
- absence of fuller standards from global outputs.

### Portability and Safety

Policy and content tests reject:

- absolute project paths;
- Plato imports and internal project identifiers in normative content;
- credentials, authentication instructions, sessions, trust, and generated
  state;
- unresolved IDs declared through `related_standard_ids`;
- broken repository-relative links and anchors within the standards library;
- unfinished placeholders; and
- duplicated normative guidance in README or native suffixes.

External HTTPS references are validated as structured primary-source metadata,
not by nondeterministic network checks during bootstrap.

Secrets and settings examples use neutral names such as `credential` and
`secret_ref` rather than policy-triggering credential assignments. They contain
no token-like sample values. If an exact credential-field example becomes
essential, implementation must add a narrow, context-specific policy treatment
with regression tests; it must not add a broad path or content allowlist.

Structured provenance may identify Plato as the source. Provenance fields are
validated separately from normative content so the source name is not
mistaken for leaked project coupling.

### Preflight and Integration

Integration tests prove that an invalid standards catalog fails before effects
for plan, install, configure, doctor, all, and all-agents-skipped paths.

They also prove:

- a fuller-standard edit creates no install or configure action;
- configure renders the core correctly for all agents;
- Cursor's manual handoff remains explicit;
- repeated runs are idempotent; and
- unmanaged destination collision behavior is unchanged.

Final verification includes focused standards and instruction tests, full
repository lint, formatting, typing, policy, and test checks, plus:

```text
rtk ./bootstrap plan
rtk ./bootstrap plan --profile work
rtk ./bootstrap doctor --profile work
```

## Logical Implementation Commits

Implementation planning should preserve these review boundaries:

1. add the typed standards catalog, resolver, and preflight validation;
2. revise the always-on core and native suffixes, with rendering tests;
3. add Python, Pydantic, and validation standards;
4. add API, testing, and documentation standards;
5. add source-control and dependency-management standards;
6. complete portability, integration, and documentation validation.

The detailed implementation plan may split a boundary further but must not
combine unrelated content clusters merely to reduce commit count.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Core grows into another handbook | Enforce the 200-word budget and prohibit detailed examples |
| README becomes a second authority | Make catalog metadata machine-authoritative and test index parity |
| Catalog appears installed when it is not | Keep it outside general inventory and produce no plan action |
| Standards duplicate skills | Keep normative policy in standards and commands in skills |
| Version guidance becomes stale | Use major-version defaults and record reviewed primary sources |
| Plato terminology leaks into normative text | Separate provenance validation from normative portability scans |
| Cursor appears automatically updated | Preserve and document the manual User Rules handoff |
| Source changes during migration | Require a clean source checkout and capture the implementation-time revision |

## Success Criteria

The standards migration is complete when:

- the core is concise, conditional, and rendered once for all three agents;
- Cursor, Claude Code, and Codex say Pydantic v2 rather than Pydantic 2.8;
- every fuller standard has one stable ID and structured provenance;
- all catalog entries resolve deterministically;
- the library is validated but not represented as installed;
- no prohibited Plato state or repository coupling appears in normative text;
- source corrections and departures are recorded;
- future installable standards packaging has an explicit contract;
- Plato remains unchanged; and
- focused and repository-wide validation pass.
