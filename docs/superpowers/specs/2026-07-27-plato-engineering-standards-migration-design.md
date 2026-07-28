# Plato Engineering Standards Migration Detailed Design

## Status

Revised detailed design for Workstream 1 of the
[Plato generic assets migration program](./2026-07-27-plato-generic-assets-migration-design.md).
Implementation remains gated on review of this written specification.

## Context

Plato's root assistant instructions, Cursor rules, review lessons, tooling
configuration, and workflow skills mix four different concerns:

1. concise defaults that should guide every coding assistant;
2. reusable engineering standards that should be consulted when relevant;
3. copyable starting points for new repositories; and
4. Plato package, infrastructure, domain, and development-stage policy.

`ballen-config` already renders one shared engineering instruction into Cursor,
Claude Code, and Codex. This migration extends that source of truth, adds a
focused standards library, and preserves generic Plato tooling as copyable
starter configuration.

The Plato source checkout was clean during the final inventory. The source
revision was `d18efa3f4bf3bff6f07a1019e4f6d6c0f4206387`. Implementation must
capture the then-current clean revision rather than assume this design-time
revision is still current.

## Goals

- Keep the always-on engineering core concise and broadly applicable.
- Make fuller standards focused, authoritative, and independently addressable.
- Preserve repository precedence over global defaults.
- Update the shared Pydantic default from an obsolete minor pin to Pydantic v2.
- Preserve generic Ruff, mypy, pytest, pre-commit, and Markdownlint defaults as
  valid, copyable starter files.
- Provide concise repository-native rule templates as the default baseline and
  a documented `all` mode that also copies the fuller standards.
- Treat copied rules and tooling as repository-owned snapshots.
- Record reviewable source provenance and intentional corrections.
- Preserve independent native delivery to Cursor, Claude Code, and Codex.
- Leave Plato unchanged unless a later explicit override authorizes a source
  update.

## Non-Goals

- Package the fuller standards as progressively loaded native skills.
- Create a typed standards catalog, resolver, `CatalogKind`, or bootstrap
  preflight path for passive documentation.
- Generate, synchronize, upgrade, or reconcile templates after they are copied
  into another repository.
- Add an arbitrary file-selector API; individual assets are already copyable by
  path.
- Create a template engine, repository initializer, or automated merge tool.
- Copy Plato's root or package `pyproject.toml`, Makefile, or dependency-specific
  coverage commands as generic templates.
- Port application-agent architecture or prompt-decomposition guidance.
- Port authentication, trust, sessions, project paths, generated plugin state,
  or internal infrastructure.
- Implement a future uv workflow skill.
- Rewrite or clean up Plato source files.

## Design Decisions

### Three Deliverables

The migration creates three related deliverables:

1. `assistants/shared/instructions/engineering.md` remains the concise,
   always-on core rendered into every native global instruction.
2. `assistants/shared/standards/` becomes the canonical fuller standards
   library.
3. `assistants/shared/standards/templates/` provides copy-once repository rules
   and Python tooling configuration.

The core owns defaults needed in every coding session. Topic documents own
detailed normative guidance. Templates turn those decisions into useful
starting points without introducing an installer or synchronization system.

### Snapshot Ownership

Templates are seeds, not managed projections. After copying:

- the destination repository owns the files;
- repository instructions and configuration take precedence;
- maintainers or coding agents may adapt the files immediately;
- `ballen-config` does not report or repair drift; and
- later synchronization requires a separate design and explicit adoption.

Copy guidance must never overwrite an existing repository file silently. An
agent handling an established repository reads the existing file, migrates
applicable rules, and preserves local decisions.

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
│       ├── python.md
│       ├── pydantic.md
│       ├── validation.md
│       ├── api-design.md
│       ├── testing.md
│       ├── documentation.md
│       ├── source-control.md
│       ├── dependency-management.md
│       └── templates/
│           ├── python/
│           │   ├── README.md
│           │   ├── ruff.toml
│           │   ├── mypy.ini
│           │   ├── pytest.ini
│           │   ├── .pre-commit-config.yaml
│           │   └── .markdownlint.json
│           └── repository-rules/
│               ├── README.md
│               ├── AGENTS.md
│               ├── CLAUDE.md
│               └── .cursor/
│                   └── rules/
│                       └── engineering.mdc
├── cursor/
│   └── user-rules.md
├── claude/
│   └── CLAUDE.md
└── codex/
    └── AGENTS.md
```

The implementation may extend existing documentation and instruction tests. It
does not require a new runtime standards module.

## Python Tooling Starter Bundle

### Contents

The first implementation slice ports five valid configuration files:

| Template | Portable baseline | Required cleanup from Plato |
|---|---|---|
| `ruff.toml` | Python 3.12, 100 columns, formatting, Google docstrings, and reviewed lint policy | Remove Plato paths, first-party packages, temporary migration ignores, and AMI workarounds |
| `mypy.ini` | Python 3.12, typed definitions, strict optional handling, error codes, and checked untyped bodies | Remove vendor overrides, scratch paths, layout assumptions, and migration-tolerance settings; make the Pydantic plugin optional |
| `pytest.ini` | `-ra`, `testpaths`, strict expected failures, and a documented marker pattern | Remove Memray, test-path injection, and dependency-specific warning suppression |
| `.pre-commit-config.yaml` | File-integrity hooks, Ruff, and Markdownlint | Remove Plato paths and `src` project assumptions; document uv-lock and conventional commits as optional |
| `.markdownlint.json` | Reviewed Markdown defaults | Reconfirm disabled line length and multiple-heading choices; no Plato paths are present |

The bundle README identifies required dependencies, adaptation points, optional
sections, and the fact that hook revisions need periodic maintenance.

### Exclusions

Plato has no standalone coverage template. Its coverage behavior is embedded in
path-heavy Make targets, so this migration does not invent a generic
`.coveragerc`.

The root and package `pyproject.toml` files remain evidence, not templates.
Their workspace membership, package metadata, dependencies, entry points, test
plugins, and promotion configuration are repository-specific.

### Use

The files are directly copyable. There is no generator or parameter
substitution. A new repository may copy the whole Python bundle; an established
repository may copy or adapt an individual file by path.

Optional Pydantic, uv-lock, or conventional-commit configuration is enabled
only when the destination repository declares the corresponding dependency or
policy.

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

The existing global renderer remains unchanged unless implementation exposes a
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

## Repository Rules Baseline

### Native Entries

The repository-rules template supplies native entry files for all three
agents:

- `AGENTS.md` for Codex;
- `CLAUDE.md` for Claude Code; and
- `.cursor/rules/engineering.mdc` for Cursor.

They contain the same concise engineering baseline, expressed through each
agent's native repository configuration model. They do not contain
authentication, trust, project paths, generated state, or Plato policy.

Each entry includes a conditional routing sentence: if
`docs/engineering-standards/` exists, read the applicable topic documents
before relevant implementation or review work. The sentence is harmless in the
default mode, where that directory is absent.

### Copy Modes

The repository-rules README documents two modes:

1. **Default** copies only the three concise native entry files.
2. **All** copies the same entry files plus the standards index and eight topic
   documents into `docs/engineering-standards/`.

These are documented copy recipes, not a new command-line interface. The Python
tooling bundle remains a separate opt-in operation, so `all` for rules does not
create or replace project tooling configuration.

There is no arbitrary file selector. Every source file remains directly
copyable when an agent or maintainer needs a narrower migration.

## Fuller Standards Library

### Human Index

`README.md` explains:

- the two-layer model;
- runtime precedence;
- canonical topic filenames;
- which documents are normative;
- the default and `all` repository-rule modes;
- snapshot ownership after copying; and
- how future skills may consume canonical content.

The README is an index, not a second normative authority.

### Documents

| Document | Scope |
|---|---|
| `python.md` | Python style, typing, naming, imports, exceptions, and domain-owned serialization |
| `pydantic.md` | Pydantic model design, fields, configuration, validators, composition, settings, and serialization |
| `validation.md` | Trust boundaries, external data, secrets and redaction, structured validation results, and configuration boundaries |
| `api-design.md` | HTTP semantics, typed request and response contracts, errors, and framework-neutral API design |
| `testing.md` | Test levels, regression workflow, fixtures, mocking, behavioral assertions, snapshots, and opt-in nondeterministic tests |
| `documentation.md` | Google docstrings, README scope, diagrams, configured Markdown linting, and nonduplicated API documentation |
| `source-control.md` | Repository detection, safety, and source-control policy without command recipes |
| `dependency-management.md` | Repository-selected package managers, lockfiles, environments, and conditional uv policy |

The existing inventory resource ID `shared.engineering` remains the stable
identity of the always-on global core.

### Provenance

Each topic document contains a concise metadata block with:

- source path or `authored` origin;
- immutable source revision or approved decision reference;
- retained, adapted, or corrected disposition;
- review date; and
- a short correction note when applicable.

Version-sensitive guidance also names the primary documentation and version
reviewed. Newly authored guidance does not invent a repository path or commit.
Tests check required fields and index links without adding a runtime resolver
or preflight path. Canonical repository-relative filenames are sufficient
identity until a real progressive-loading consumer needs another scheme.

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

Do not claim that `model_post_init` is deprecated. The detailed standard
distinguishes validated external boundaries from trusted internal mapping
shapes and runtime dependency containers. It cross-references `validation.md`
for trust, secret-handling, redaction, and
configuration-boundary policy.

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

Exclude false claims about attribute docstrings being exposed through `help()`
and Plato-specific README templates reserved for the application-agent
workstream.

#### Source Control

Migrate repository detection, the `.jj/` routing rule, preservation of
repository conventions, and safe review boundaries.

Commands, bookmark procedures, workspaces, rebases, and conflict recovery
remain in `jujutsu-workflow`. GitLab operations remain in their later skills
workstream.

#### Dependency Management

Require assistants to discover and use the repository's selected package
manager and lockfile rather than bypass its environment.

For uv-managed repositories, Python commands run through the uv environment
and dependency changes use uv. Exact commands, workspace or package selection,
lockfile recipes, and troubleshooting belong in a later workflow skill.

## Authority and Conflict Resolution

For work in a repository, authority is:

1. repository instructions and executable configuration;
2. the applicable copied or global standards baseline;
3. procedural skills that apply those standards; and
4. source examples, provisional lessons, or legacy patterns.

A repository may override any generic default for its own scope. Executable
Plato configuration is evidence of Plato behavior, not automatically a
universal rule. Approved migration decisions and current primary documentation
resolve source disagreements.

### Required Corrections

The migration records these intentional departures:

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
- uv command recipes remain for a later workflow skill.
- agent construction, MCP, prompt decomposition, eval thresholds, demos, and
  maturity tiers remain in the application-agent workstream.

## Source Disposition

### Root and Cursor Sources

| Plato source | Disposition | Target or treatment |
|---|---|---|
| `AGENTS.md` | Adapt | Always-on core and repository-rule templates; remove Plato development-stage and GitLab policy |
| `CLAUDE.md` | Do not migrate separately | Content duplicate of `AGENTS.md`; generate a native concise template from the same decisions |
| `.cursor/rules/104_python_style_guide.mdc` | Adapt and correct | `python.md` and `documentation.md` |
| `.cursor/rules/104_pydantic_style_guide.mdc` | Adapt and correct | `pydantic.md`; remove Plato configuration paths and correct `model_post_init` |
| `.cursor/rules/104_data_validation.mdc` | Adapt | `validation.md`; exclude named infrastructure and auth |
| `.cursor/rules/104_pythonic_apis.mdc` | Adapt | `api-design.md`; make framework and HATEOAS choices optional |
| `.cursor/rules/104_llm_output.mdc` | Keep in Plato | Interaction tone is not an engineering standard; uv sentence is duplicate |
| `.cursor/rules/test_rules_macro.mdc` | Adapt | `testing.md`; remove Plato paths, commands, and fixed marker policy |
| `.cursor/rules/test_rules_micro.mdc` | Adapt | `testing.md`; keep principles, make libraries optional profiles |
| `.cursor/rules/uv.mdc` | Adapt | `dependency-management.md`; reserve commands for a later uv workflow skill |
| `.cursor/rules/agent_charter_summary.mdc` | Defer | Application-agent architecture workstream |
| `.cursor/rules/agent_prompt_decomposition.mdc` | Defer | PydanticAI reference profile in the application-agent workstream |
| `.cursor/rules/lessons_learned.mdc` | Review as intake | Apply the item-level decisions below; do not copy the ledger |
| `.cursor/rules/lessons_promoted.mdc` | Provenance only | Existing destinations own normative wording |

### Active Lesson Decisions

| Active lesson | Decision |
|---|---|
| Test history-processing control flow separately from model behavior | Adapt into `testing.md` as deterministic versus model-behavior scope |
| Put reusable test-data factories in shared fixtures | Adapt into `testing.md` without prescribing one repository layout |
| Name or document intentionally excluded cases | Adapt into `python.md` and `documentation.md` |
| Document non-obvious performance choices | Adapt into `documentation.md` |
| Extract complex inline conditional assignments | Adapt into `python.md` as readability guidance |
| Use named result types for multi-value returns | Adapt into `python.md`; do not mandate `NamedTuple` universally |
| Do not duplicate public API inventories in READMEs | Adapt into `documentation.md` |
| Expose raw eval scores and separate reviewer dimensions | Defer to the application-agent evaluation profile |
| Call out simplification opportunities during review | Defer as review-skill procedure; the core already prefers simple solutions |
| Track expected versus actual model invocations | Defer to application-agent observability |
| Isolate heavy optional dependencies from unit-test imports | Adapt into `python.md` and `testing.md` |
| Keep `env_prefix` conventions consistent | Adapt into `pydantic.md`, subordinate to validation policy |
| Keep configuration discoverable and single-sourced | Adapt into `validation.md` and `documentation.md` |
| Distinguish not-found from not-ready errors | Adapt into `api-design.md` without fixed framework classes |
| Update downstream handlers when exception contracts change | Adapt into `python.md` |
| Graceful history-summarization fallback | Defer to application-agent architecture |
| MCP lifespan resource construction | Defer to application-agent architecture |
| Prefer explicit booleans when `None` has different semantics | Adapt into `validation.md` |
| Align API/model and database nullability | Adapt into `api-design.md` and `validation.md` |
| Avoid lossy aggregate-only return contracts | Adapt into `api-design.md` as caller-needs guidance |
| Use literal-tagged discriminated unions | Adapt into `pydantic.md` |
| Derive rather than duplicate identity fields | Adapt into `python.md` and `pydantic.md` |
| Use `NotRequired` for omitted `TypedDict` keys | Adapt into `python.md` and `validation.md` |
| Disable generated equality for values without scalar equality | Adapt conditionally into `python.md`; keep NumPy as an example only |
| S3 and presigned-URL lessons | Keep in Plato |

### Tooling Sources

| Plato source | Disposition | Treatment |
|---|---|---|
| `ruff.toml` | Adapt | Generic starter; remove paths, package names, temporary ignores, and AMI workaround |
| `src/plato/mypy.ini` | Adapt | Generic starter; remove vendor, path, layout, and migration-tolerance assumptions |
| `pytest.ini` | Adapt | Generic starter; remove Memray, path injection, and dependency warnings |
| `.pre-commit-config.yaml` | Adapt | Generic starter; remove project paths and make uv and commit policy optional |
| `.markdownlint.json` | Adapt after review | Generic starter with explicit policy notes |
| root `pyproject.toml` and `src/pyproject.toml` | Evidence only | Do not copy package, workspace, dependency, entry-point, or promotion policy |
| `Makefile` and coverage commands | Keep in Plato | Paths, markers, retries, reports, and CI stages are repository-specific |
| `docs/tooling/uv_workspace_guide.md` | Evidence after correction | Use only verified generic policy; do not copy stale workspace membership |

### Other Sources

| Plato source | Disposition | Treatment |
|---|---|---|
| `docs/agent_charter/{README.md,agent_construction_standard.md,agent_service_pattern.md,file_organization.md,models_exceptions.md,tool_design_guidelines.md,mcp.md,capabilities.md,testing.md,evals.md,readme_templates.md,maturity_tiers.md,demo_apps.md}` | Defer | Detailed application-agent architecture workstream |
| `docs/agent_charter/{auth_flow.md,credentials_config.md}` | Hard exclude | Authentication, trust, secret resolution, and internal paths |
| `docs/agent_charter/observability_logfire.md` | Keep in Plato | Vendor and infrastructure profile |
| `docs/agent_charter/todos.md` | Keep in Plato | Historical backlog, not normative guidance |
| `docs/evals/threshold_guidelines.md` | Keep out | Plato-specific model and threshold assumptions |
| `skills/tooling-{discover-standards,review-standards,review-quality,review-types,review-tests,create-tests,fix-bug,review-snapshots,self-review,lint-markdown,commit-msg}/**` | Defer procedures | Later skills own discovery, review, testing, lint, fixes, and commits |
| `skills/tooling-{workflow,s3-download,s3-upload}/**` | Not standards | Skills workstream may separately evaluate scope |
| `skills/jujutsu-workflow/**` | Existing skill baseline | Source-control standard owns only routing and safety policy |
| `skills/using-gitlab/**` and MR skills | Defer | GitLab and merge-request skills workstream |
| `.claude/temp/archive/**` | Keep in Plato | Historical lesson extraction artifacts |
| `.codex/**`, `.claude-plugin/**`, `.cursor-plugin/**`, and generated state | Exclude | Authentication, trust, paths, caches, sessions, and plugin state do not migrate |

## Future Skill Packaging

A later skills design may wrap one or more topic standards for native
progressive loading. It must:

- treat the topic documents as canonical rather than create independently
  edited copies;
- prove that packaged references do not drift from their source; and
- avoid cross-agent installed-path assumptions.

The skills workstream decides whether to use one standards skill, focused topic
skills, or references bundled with workflows. Skill dependencies and runtime
invocation are designed only if a real workflow needs them.

A later uv workflow skill may own project discovery, command selection,
workspace targeting, dependency changes, locking, environment execution, and
troubleshooting. It references `dependency-management.md` rather than
restate its policy. Its name and packaging remain Workstream 2 decisions.

## Validation Strategy

Tests provide three focused checks:

1. Parse every tooling template and smoke-test the global and repository-native
   renderings, including the default and `all` layouts.
2. Verify that the standards index links all eight topic files and that each
   topic contains its required provenance metadata.
3. Scan normative content and templates for stale `Pydantic 2.8` guidance,
   absolute project paths, Plato imports or identifiers, credentials, auth,
   sessions, trust state, generated state, and unfinished placeholders.

External references are not fetched during bootstrap. Secrets examples use
neutral names such as `credential` and `secret_ref` and contain no token-like
sample values.

Final verification includes focused documentation and instruction tests,
repository lint, formatting, typing, policy, and tests, followed by:

```text
rtk ./bootstrap plan
rtk ./bootstrap doctor --profile default
```

## Logical Implementation Commits

Implementation planning preserves three review boundaries:

1. add the generic Python tooling starter bundle and syntax/policy tests;
2. revise the global core and add default/`all` repository-rule templates; and
3. add the eight topic standards, provenance, index, and content validation.

The detailed implementation plan may split a boundary further, but does not
combine the standards, skills, or application-agent workstreams.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Core grows into another handbook | Enforce the 200-word budget |
| Templates appear centrally managed after copying | State snapshot ownership in every template README |
| `all` unexpectedly changes tooling | Keep rules and tooling as separate opt-in bundles |
| Template defaults become stale | Record review context and verify pins during implementation |
| Standards duplicate skills | Keep policy in standards and commands in skills |
| Plato terminology leaks into generic assets | Run portability scans over normative content and templates |
| Cursor appears automatically updated | Preserve the explicit manual global User Rules handoff |
| Plato changes during migration | Require a clean checkout and record the implementation-time revision |

## Success Criteria

The standards migration is complete when:

- the concise core renders once for Cursor, Claude Code, and Codex;
- all three global outputs say Pydantic v2 rather than Pydantic 2.8;
- five generic tooling templates are valid and free of Plato assumptions;
- the default repository baseline contains only three concise native entries;
- the `all` rules mode additionally provides all eight topic standards;
- copied assets are explicitly repository-owned snapshots;
- every topic standard has concise provenance and recorded corrections;
- prohibited Plato state and repository coupling do not migrate;
- Plato remains unchanged; and
- focused and repository-wide validation pass.
