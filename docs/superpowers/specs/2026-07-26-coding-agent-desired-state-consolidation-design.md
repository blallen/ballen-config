# Coding-Agent Desired-State Consolidation Design

**Date:** 2026-07-26
**Status:** Draft for written-spec review; conversational design approved
**Stack:** `laptop-bootstrap-agents` → `laptop-bootstrap-review` →
`laptop-bootstrap-agent-consolidation`

## Context

The laptop bootstrap already manages portable configuration for Cursor, Claude
Code, and Codex. Review of the coding-agent branch identified two distinct
classes of follow-up work:

1. remove experimental Piste plugins that should not be part of a new laptop;
2. reduce duplicated plugin declarations while preserving each agent's native
   installation and configuration behavior.

The initial design treated Cursor plugins as a mostly manual concern. Cursor
now has a first-class customization system: its plugins can package rules,
skills, agents, commands, MCP servers, and hooks, while portable Agent Skills
are discovered from standard filesystem locations. The relevant interfaces are
documented in the official [Cursor plugin documentation][cursor-plugins] and
[Cursor Agent Skills documentation][cursor-skills].

This document amends the coding-agent portions of the original
[Laptop Migration Bootstrap Design][original-design]. It does not change the
core package, authentication, SSH, or optional-memory decisions in that design.

[cursor-plugins]: https://cursor.com/docs/plugins.md
[cursor-skills]: https://cursor.com/docs/skills.md
[original-design]: ./2026-07-25-laptop-migration-bootstrap-design.md

## Decision Summary

- Remove the Piste marketplace and the `ami-qsp-tools` and `fieldkit` plugins
  from the Claude Code and Codex desired state.
- Promote the reviewed Plato `jujutsu-workflow` skill as the first portable
  shared skill for Cursor, Claude Code, and Codex.
- Keep `ballen-config` as the only desired-state source. Do not use Cursor's
  third-party auto-import behavior to synchronize from Claude Code or Codex.
- Install and inspect every agent independently through a native adapter.
- Store portable skills once in the repository, then copy them independently
  into each selected agent's native skill directory.
- Replace the duplicated Claude Code and Codex plugin catalogs with one strict,
  target-aware shared catalog that also supports Cursor.
- Preserve target-specific identifiers and installation semantics rather than
  inventing a lowest-common-denominator plugin protocol.
- Remove flattened `item_ids` from the central inventory. The referenced
  catalog is the authoritative item list.
- Continue excluding authentication, secrets, sessions, histories, memories,
  caches, downloaded plugin implementations, and other runtime state.

## Goals

1. Make a replacement laptop reproduce the intentionally selected
   coding-agent capabilities.
2. Avoid declaring the same marketplace and plugin more than once when its
   native identity is genuinely shared.
3. Allow Cursor, Claude Code, and Codex to diverge explicitly where their
   capabilities or identifiers differ.
4. Keep plan, install, configure, and doctor behavior deterministic and
   idempotent.
5. Preserve unrelated local configuration and never infer desired state from
   imported or cached agent state.
6. Make failures actionable without reporting a manual marketplace step as a
   successful automated installation.

## Non-goals

- Synchronizing live configuration between coding agents.
- Mirroring everything currently visible in an agent's Customize or plugin
  interface.
- Copying plugin caches or downloaded marketplace repositories.
- Publishing a private Cursor marketplace.
- Creating one universal runtime adapter for incompatible native CLIs and
  configuration formats.
- Moving repository-specific Plato skills into the generic bootstrap without a
  separate portability review.
- Managing authentication, account connectors, trust decisions, or secrets.

## Branch and Commit Boundaries

### PR2: focused review fixes

`laptop-bootstrap-agents` receives two independent commits:

1. **Remove abandoned experimental plugins**
   - remove the Piste marketplace from the Claude Code and Codex catalogs;
   - remove `ami-qsp-tools@piste` and `fieldkit@piste`;
   - update the current flattened inventory lists and focused tests;
   - leave installed local plugins untouched.
2. **Seed portable shared skills**
   - copy the reviewed, generic `jujutsu-workflow` skill from the Plato source;
   - declare Cursor, Claude Code, and Codex targets;
   - record provenance and `reviewed-generic` status;
   - update focused validation, integration tests, and promotion documentation.

The broad catalog architecture does not enter PR2. That keeps its response to
review comments small and minimizes overlap with PR3.

### PR3: preserve the completed quality review

`laptop-bootstrap-review` is rebased onto the updated PR2. Its production
refactors remain unchanged unless the PR2 changes expose a real defect.
Expected conflicts are limited to tests or documentation that mention the
removed plugins or empty skill catalog.

### Follow-on consolidation branch

`laptop-bootstrap-agent-consolidation` starts from the updated PR3 and contains
separate commits for:

1. target-aware catalog models and validation;
2. central-inventory de-duplication;
3. Claude Code and Codex adapter migration;
4. Cursor plugin planning and local-plugin support;
5. documentation and end-to-end validation.

The exact implementation tasks and file groupings belong in the implementation
plan, but these conceptual boundaries should remain independently reviewable.

## Repository Source of Truth

Shared and target-specific concerns remain deliberately separate:

```text
assistants/
├── shared/
│   ├── instructions/
│   ├── hooks/
│   ├── skills/
│   │   ├── catalog.yaml
│   │   └── <skill-name>/
│   └── plugins/
│       └── catalog.yaml
├── cursor/
├── claude/
└── codex/
```

The shared catalogs express portable desired state. Agent directories retain
settings, instructions, hook adapters, and other formats that are genuinely
native.

A declaration with several targets reduces repository duplication. It never
authorizes an adapter to use another agent's installed files as its source of
truth. Cursor may still discover the Claude Code and Codex compatibility skill
roots independently. Byte-identical copies of a shared skill across those
roots are expected and consistent; only same-name, different-content copies
are drift.

## Independent Agent Management

Every enabled agent is planned, installed, configured, and diagnosed
independently:

| Target | Portable skill destination | Plugin behavior |
| --- | --- | --- |
| Cursor | `~/.cursor/skills/<name>/` | Cursor marketplace action or reviewed local plugin |
| Claude Code | `~/.claude/skills/<name>/` | Native `claude plugin` marketplace and install commands |
| Codex | `~/.agents/skills/<name>/` | Native `codex plugin` marketplace and install commands |

Copies are preferred over cross-tool discovery and repository symlinks. A
copied skill continues working if the checkout moves, and each adapter can
inspect the exact native destination that it owns.

The bootstrap remains correct regardless of Cursor's third-party import
setting. Setup documentation recommends disabling the preference for a cleaner
independently managed view, but it is neither a prerequisite nor a blocking
doctor check. The bootstrap does not write an undocumented Cursor preference.
If the user enables it independently, `doctor` may report duplicate same-name
skills or imported plugin capabilities without treating the preference itself
as drift.

## Portable Skills

`assistants/shared/skills/catalog.yaml` remains the authoritative skill
catalog. Each entry declares:

- globally unique skill name;
- repository-relative canonical source;
- one or more concrete targets;
- applicable profiles;
- dependencies;
- provenance;
- portability status.

`jujutsu-workflow` becomes the first entry and targets all three agents. Its
entire directory, including referenced documents and scripts, is reviewed
before promotion. The promoted copy must not import Plato code, assume a Plato
checkout, contain absolute local paths, or instruct the user to migrate
authentication material.

The adapter copies the same canonical bytes into each selected native
destination. A target-specific variant must use a different qualified name;
the bootstrap never creates divergent, same-name skills.

## Target-Aware Plugin Catalog

### One catalog, explicit targets

`assistants/shared/plugins/catalog.yaml` replaces
`assistants/claude/plugins.yaml` and `assistants/codex/plugins.yaml`.

Marketplace and plugin records carry nonempty target sets. An identifier shared
by multiple agents appears once:

```yaml
marketplaces:
  - name: claude-plugins-official
    source: anthropics/claude-plugins-official
    targets: [claude-code, codex]

plugins:
  - id: superpowers@claude-plugins-official
    marketplace: claude-plugins-official
    targets: [claude-code, codex]
```

When native aliases or identifiers differ, separate records make the difference
visible:

```yaml
marketplaces:
  - name: claude-context-mode
    source: mksglu/claude-context-mode
    targets: [claude-code]
  - name: context-mode
    source: mksglu/claude-context-mode
    targets: [codex]

plugins:
  - id: context-mode@claude-context-mode
    marketplace: claude-context-mode
    targets: [claude-code]
  - id: context-mode@context-mode
    marketplace: context-mode
    targets: [codex]
```

This favors explicit records over YAML anchors, nested target overrides, or
adapter-side renaming.

### Cursor plugin variants

Cursor uses the same desired-state catalog but has distinct installation
variants:

- **Cursor marketplace plugin:** identified by its Cursor marketplace slug.
  Until Cursor documents supported unattended install and inspection
  interfaces, the adapter emits a precise `/add-plugin` or Customize action.
  `doctor` always retains it as a manual checklist item rather than scraping
  Cursor's private databases or cache.
- **Reviewed local plugin:** repository-owned source with a valid
  `.cursor-plugin/plugin.json`, copied atomically into
  `~/.cursor/plugins/local/<name>/`.

Cursor's cache directory is runtime state and is never a source or
destination. The initial Cursor plugin list is selected through a deliberate
read-only audit; imported plugins are not automatically promoted.

The models use a discriminated union for incompatible plugin variants rather
than optional fields that are meaningless for most targets. The implementation
plan will name the concrete Pydantic models, but their conceptual variants are:

- native marketplace plugin for Claude Code or Codex;
- Cursor marketplace plugin;
- reviewed Cursor local plugin.

The catalog can add another explicit variant later if a supported Cursor CLI
installer becomes available.

### Normative catalog shape

The catalog uses `kind` as the plugin discriminator. These are the complete
initial variants:

```yaml
marketplaces:
  - name: claude-plugins-official
    source: anthropics/claude-plugins-official
    targets: [claude-code, codex]
    profiles: [default]

plugins:
  - kind: native-marketplace
    id: superpowers@claude-plugins-official
    marketplace: claude-plugins-official
    targets: [claude-code, codex]
    profiles: [default]
    required: true

  - kind: cursor-marketplace
    id: example-plugin
    targets: [cursor]
    profiles: [default]
    required: false
    scope: user
    verification: manual

  - kind: cursor-local
    id: example-local-plugin
    source: assistants/shared/plugins/local/example-local-plugin
    targets: [cursor]
    profiles: [default]
    required: true
```

Marketplace records contain `name`, `source`, `targets`, and `profiles`.
Marketplace targets are limited to Claude Code and Codex because Cursor
marketplace slugs do not use their native repository-marketplace aliases.

The plugin variants are:

| `kind` | Required variant fields | Allowed targets |
| --- | --- | --- |
| `native-marketplace` | `id`, `marketplace` | Claude Code, Codex |
| `cursor-marketplace` | `id`, `scope: user`, `verification: manual` | Cursor only |
| `cursor-local` | `id`, repository-relative `source` | Cursor only |

Every plugin also has nonempty `targets`, `profiles`, and `required` fields.
Defaults may remain `profiles: [default]` and `required: true`, but serialized
examples and error messages use the same meanings across variants.
For `cursor-marketplace`, `required` controls whether the checklist wording is
required or optional; it does not claim installation, change an exit code, or
create an acknowledgement record.

Duplicate identity is evaluated as `(target, plugin ID)` across all variants,
not separately per `kind`. A marketplace identity is `(target, marketplace
name)`. Before an adapter receives a record, the catalog projector replaces its
target set with exactly one concrete target. Adapters never rename identifiers
or interpret multi-target records.

## Catalog Validation

The entire catalog is validated before native state is inspected or changed.
Validation requires:

- every target is a concrete supported agent;
- all target sets are nonempty;
- marketplace names are unique per target;
- plugin IDs are unique per target;
- a native plugin's targets are a subset of its marketplace's targets;
- plugin profiles are a subset of the referenced marketplace profiles;
- native plugin suffixes match their declared marketplace aliases;
- an installation variant supports every declared target;
- local source roots are repository-relative reviewed directory trees contained
  by the checkout;
- Cursor local plugins contain a valid manifest whose name matches the
  declaration;
- reviewed local Cursor plugins do not declare skills that collide with the
  shared skill catalog for Cursor;
- required dependencies are eligible for every relevant profile and target.

The same identifier may exist in separate records only when their target sets
do not overlap. Error messages identify the target and conflicting record.

## Central Inventory Consolidation

The central inventory indexes catalogs; it does not mirror their contents.
The consolidation branch:

- removes `item_ids` from `CatalogResource`;
- removes every flattened catalog ID list from `assistants/inventory.yaml`;
- replaces the Claude Code and Codex catalog resources with one shared plugin
  catalog resource targeting all three agents;
- keeps the shared skill and Cursor extension catalog resources;
- validates every referenced catalog during inventory loading.

For example:

```yaml
- id: shared.plugins.catalog
  kind: catalog
  owner: shared
  source: assistants/shared/plugins/catalog.yaml
  catalog_kind: plugin
  targets: [cursor, claude-code, codex]
```

Catalog parsing remains an inventory preflight check, but there is no second
list to compare. This removes synchronization work without weakening schema or
source-path validation.

## Desired-State Preflight Boundary

Full validation before native inspection requires an explicit orchestration
boundary. The top-level assistant orchestration loads one immutable desired
state containing:

- the validated central inventory;
- every validated referenced catalog;
- per-profile, per-target catalog projections.

Adapters receive projected model objects rather than catalog paths. They cannot
open or validate a catalog after running a native inspection command.

The same preflight is used by `plan`, `install`, `configure`, and `doctor`
before any runner call or configuration mutation. An invalid shared catalog
therefore produces one stable validation error and zero Cursor, Claude Code, or
Codex commands, backups, state receipts, or destination writes.

## Planning and Application Flow

The runtime flow is:

1. load and strictly validate the central inventory;
2. load and strictly validate every referenced catalog;
3. resolve profiles, includes, and whole-agent skips;
4. filter shared records for one concrete target;
5. inspect only that target's native installed state;
6. produce deterministic automated and manual actions;
7. apply automated actions through the native adapter;
8. report remaining manual actions and drift through `doctor`.

Catalog validation completes before step 5. A validation failure therefore
causes no native inspection side effects and no partial mutation.

Whole-agent skips apply before adapter planning. Skipping Cursor, for example,
suppresses its skill copies, plugins, extensions, instructions, settings, and
manual actions without changing Claude Code or Codex.

## Ownership, Idempotency, and Drift

The bootstrap manages only declared resources:

- matching managed skill or local-plugin content is a no-op;
- changed managed content is backed up and replaced through the existing
  configuration engine;
- an unmanaged destination collision is preserved and reported;
- unrelated skills, plugins, settings, and extension state remain untouched;
- removing a marketplace declaration stops future installation but does not
  uninstall an already installed plugin;
- native marketplace commands run only for missing desired entries;
- Cursor marketplace actions remain visible as manual checklist items on every
  relevant run until a supported inspection interface is designed;
- optional manual actions do not fail the overall install.

The bootstrap never reads an agent's installed state and writes it back into
the repository. A later GUI installation can be audited and deliberately added
to the catalog with coding-agent assistance.

## Failure Semantics

- Invalid inventory or catalog data fails preflight before mutation.
- Malformed native inspection output fails that target rather than assuming
  nothing is installed.
- A required native command failure fails the install stage.
- An optional native command failure is retained for the doctor summary.
- A required Cursor marketplace action is reported as a required manual
  checklist item, not as installed or as an automated stage failure.
- One target's native failure does not corrupt another target's declarations or
  configuration. Successfully applied earlier targets are not rolled back;
  independent idempotency makes the partially completed run safe to resume.
- Authentication prompts and OAuth state remain outside the bootstrap; doctor
  reports only normalized readiness.

## Reviewed Local Plugin Trees

A Cursor local plugin source is a directory tree, not a single regular file.
Its review boundary is:

- the declared root resolves beneath the checkout and is an ordinary directory;
- `.cursor-plugin/plugin.json` is a contained regular file;
- every descendant is an ordinary directory or regular file;
- symlinks, special files, traversal, and descendants that resolve outside the
  root are rejected;
- the manifest is parsed strictly and its `name` equals the catalog `id`;
- a deterministic relative-path and content hash describes the complete tree.

Application builds a fully validated temporary sibling directory, applies
restrictive modes, and atomically renames it into place. An unmanaged existing
destination is preserved as a collision. A managed destination is backed up
before replacement. Failure before the rename leaves the prior destination
unchanged; failure after a successful rename is recorded by the existing
managed-state receipt.

## Testing Strategy

Tests use Pytest fixtures and temporary home directories. They assert
observable plans, files, and native command arguments rather than implementation
call counts.

### Model and catalog tests

- accept a shared marketplace and plugin across Claude Code and Codex;
- accept explicit target-specific aliases;
- accept Cursor marketplace and reviewed-local variants;
- reject empty, shared, or unsupported target sets;
- reject duplicate `(target, marketplace)` and `(target, plugin ID)` pairs;
- reject plugin targets or profiles outside the referenced marketplace;
- reject incompatible installation variants;
- reject unsafe or invalid local plugin sources and manifests;
- reject shared-skill collisions in reviewed local Cursor plugins.

### Resolver and adapter tests

Parameterized fixtures cover Cursor, Claude Code, and Codex:

- profile selection;
- whole-agent skipping;
- shared-record filtering;
- native installed-state de-duplication;
- required and optional action propagation;
- deterministic ordering;
- manual Cursor marketplace actions;
- absence of false installed-state claims when Cursor has no supported
  inspection interface;
- local Cursor plugin copy, collision, drift, backup, unsafe-tree, and
  pre-rename rollback behavior.

### Integration tests

A temporary-home integration test:

1. loads the central inventory and both shared catalogs;
2. plans and configures all three agents;
3. checks the three independent skill destinations;
4. confirms Cursor treats byte-identical skills discovered through
   compatibility roots as consistent rather than drift;
5. checks agent-native plugin actions;
6. reruns the same operation and verifies idempotency;
7. confirms unmanaged files remain unchanged.

A separate invalid-catalog integration test invokes each relevant top-level
stage and asserts:

- zero native runner commands for all three agents;
- zero destination, backup, or state-receipt mutations;
- one stable actionable preflight error.

The focused tests run before the full suite. Final verification includes Ruff,
static type checking, Pytest, repository policy checks, pre-commit, and a
read-only local smoke test that excludes authentication and runtime state.

## Documentation Changes

Implementation updates:

- `README.md` with the repository-source/native-adapter rationale;
- `docs/promoting-shared-skills.md` with the actual `jujutsu-workflow`
  promotion example;
- manual setup documentation for Cursor marketplace actions;
- the original laptop design where its older Cursor plugin wording would
  otherwise conflict with this amendment.

The documentation explicitly states that Cursor's third-party import capability
is intentionally neither configured nor required.

## Rejected Alternatives

### Depend on Cursor's third-party imports

Rejected because Cursor would depend on another agent's installed state,
provenance would be unclear, and bundled MCP servers or duplicate skills could
appear without a direct declaration.

### Keep three complete plugin catalogs

Rejected because identical marketplace sources and plugin IDs would continue
to drift while offering no stronger native isolation. Target filtering provides
the same isolation from one authoritative catalog.

### Normalize every plugin into one universal install command

Rejected because Cursor, Claude Code, and Codex expose different supported
interfaces. The catalog shares desired state; adapters retain native behavior.

### Copy generated plugin caches

Rejected because caches are machine-specific runtime state and can include
mutable downloads or stale paths.

### Automatically import current GUI state

Rejected because visibility in an agent UI does not establish that the item is
portable, intentional, secret-free, or appropriate for a new laptop.

## Success Criteria

The design is complete when:

- PR2 contains only the focused removals and first shared-skill promotion;
- PR3 remains reviewable after rebasing onto PR2;
- the follow-on branch has one target-aware plugin catalog;
- Cursor, Claude Code, and Codex are each planned and applied independently;
- no adapter depends on Cursor cross-tool import;
- setup recommends disabling Cursor cross-tool import but remains correct
  regardless of that preference;
- central inventory catalog lists are no longer duplicated;
- invalid desired state cannot cause partial mutation;
- repeated temporary-home integration runs are idempotent;
- unrelated local files and authentication state remain untouched;
- README and focused docs explain both mechanics and rationale.
