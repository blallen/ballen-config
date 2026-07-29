# Plato Reusable Skills Detailed Design

## Status

Detailed design. Engine scope is a bounded rename protocol plus the coarse
mutation lock its ownership proof requires; an earlier revision generalized this
into a retirement subsystem and has been reduced. Ready for an implementation
plan.

This document defines Workstream 2 of the
[Plato generic assets migration program](2026-07-27-plato-generic-assets-migration-design.md).
It supersedes the personal-plugin revision reviewed on 2026-07-28. Plugin
packaging is removed from this workstream and deferred; see
[Deferred plugin packaging](#deferred-plugin-packaging).

The product direction, the seven-skill first-release scope, the skill names, and
the roadmap recorded here are approved. Per-skill portability results are not:
each skill's `portability_status` and provenance are proposed values that its own
slice records after review. Implementation remains gated on a separate executable
plan.

## Context

Plato contains several reusable engineering workflow skills, while
`ballen-config` already owns portable engineering standards and a promoted
`jujutsu-workflow` skill delivered through the shared-skill catalog.

That existing mechanism already provides every delivery and installation
capability this workstream needs. A skill declares its targets, profiles,
dependencies, provenance, and portability status in
`assistants/shared/skills/catalog.yaml`. `SkillCatalog` validates unknown
dependencies, cycles, and dependency target and profile coverage. `configure`
copies each canonical tree byte for byte into every selected harness's native
skill root, records a digest-backed managed receipt, detects unmanaged
collisions, preserves drift, and converges idempotently. Whole-harness skip
already removes a target from selection.

It cannot rename a skill. The engine has no path for removing a managed record
that leaves the catalog, and making such a removal safe also requires serializing
the tree and receipt mutation it depends on. Those two additions are the engine
work this workstream contributes; see
[the rename protocol](#jujutsu-workflow-rename-protocol).

An earlier revision of this design delivered five of these skills as a personal
plugin named `ballen-workflows`, with three native manifests, two root
marketplace files, a tagged marketplace release, a repository plugin contract
schema, external attestations for existing third-party plugins, versioned
plugin receipts, and a bespoke migration action. Review established that the
plugin carried no plugin-native payload: no commands, no hooks, and no MCP
server. It offered no optional grouping, because the plugin was required with
no per-skill selector, and no distribution benefit, because publishing to a
public marketplace was an explicit non-goal. Against that, it added a
publish-before-install release loop for every skill edit, private-repository
authentication that the design did not handle, and Codex plugin-update behavior
that was unproven at design time. The packaging is therefore removed, and these
skills ship as shared skills.

The first release contains:

| Skill | Origin | Treatment |
|---|---|---|
| `discover-project-standards` | Plato | Genericize and promote |
| `review-project-standards` | Plato | Genericize with a declared discovery dependency |
| `using-gitlab` | Plato | Rewrite for portability and explicit mutation safety |
| `using-github` | New | Author as the GitHub counterpart to `using-gitlab` |
| `using-jujutsu` | Promoted standalone skill | Rename in place |
| `using-uv` | New | Create as a procedural companion to the standards library |
| `writing-executive-communications` | Plato | Genericize and promote |

Because delivery is now a directory and a catalog entry, the release includes
every roadmap item whose only barrier was delivery friction. `using-github` and
`writing-executive-communications` qualify: the first is better written
alongside `using-gitlab` than after it, and the second has no dependency,
contract, or remote mutation at all.

Everything still on the roadmap is gated by design work that packaging never
affected. The project-review primitives need a Git/Jujutsu-neutral change-scope
contract; `conduct-self-review` needs those primitives plus a recorded
relationship with native review skills; forge review needs its comment-plan
contract; and the review-learning skills consume forge review's output. A
generic forge router stays deferred until two provider skills demonstrate
repeated routing logic.

## Goals

- Deliver seven reviewed, portable workflow skills from one authored tree in
  `ballen-config`.
- Keep the existing `SkillSpec` delivery model intact, and deliver every skill
  through it. The only schema addition is the rename declaration required to make
  cleanup safe.
- Install every first-release skill for Cursor, Claude Code, and Codex in the
  `default` profile, subject only to the existing whole-harness skip.
- Preserve native plugins, connectors, and command-line tools as authoritative
  capability providers.
- Keep normative engineering guidance in the standards library and procedures
  in skills.
- Rename `jujutsu-workflow` to `using-jujutsu` without deleting unmanaged or
  modified content.
- Add the bounded rename protocol the engine currently lacks, together with the
  coarse mutation lock its ownership proof depends on.
- Preserve source provenance and a clear roadmap for later generic skills.

## Non-Goals

- Copy Plato's complete skill tree.
- Package these skills as a plugin, or add native manifests, marketplaces,
  plugin versions, release tags, or plugin receipts.
- Copy or migrate authentication, credentials, trust, sessions, memories,
  permissions, project paths, MCP state, caches, indexes, worktrees, external
  or native plugin receipts, or generated plugin state. This excludes
  `ballen-config`'s own managed records, which this design deliberately reads
  and, under the proof rules below, removes.
- Reimplement GitHub, GitLab, or other remote-service connectors.
- Make GitHub and GitLab workflows artificially identical.
- Add a generic `using-gitforge` router over the provider skills; see
  [why the forge skills stay parallel](#why-the-forge-skills-stay-parallel).
- Move normative dependency, testing, typing, documentation, or source-control
  policy out of `assistants/shared/standards/`.
- Make one harness read another harness's installed files.
- Add a capability or workflow-authority vocabulary to the catalog before a
  skill needs one.
- Clean up, rewrite, or backport changes to Plato.
- Add merge-request review, response, or review-learning workflows to the first
  release.
- Add `conduct-self-review` before its quality, test, type, and change-scope
  contracts exist.
- Build a general retirement subsystem: successor-free retirement, adoption of
  unmanaged content, per-target results, or a reusable executable-action
  hierarchy. This workstream needs one safe rename; see
  [deferred generic retirement](#deferred-generic-retirement).

## Design Invariants

1. `ballen-config` owns each genericized skill after promotion.
2. The repository contains one canonical tree per skill and one catalog entry
   per skill. No per-target skill variants are rendered.
3. Repository instructions and repository-selected tools override personal
   defaults.
4. The standards library owns rules; skills own procedures and reference
   standards rather than duplicating them.
5. Native plugins, connectors, and command-line tools own operational
   capabilities, authentication, remote schemas, and service behavior.
6. A skill may select and safely use an available provider, but it may not
   claim a provider's capability as its own workflow logic.
7. Exact skill-name collisions with unmanaged content fail closed before
   mutation.
8. A declared catalog dependency is an install-time contract. A cross-skill
   content reference names the required skill; a co-installed relative path is
   a concrete hint, not the mechanism, and no harness-native invocation syntax
   is assumed.
9. Remote writes require explicit user intent and target confirmation.
10. Structural validation covers the complete canonical source even when one
    harness is skipped. Installation and doctor checks cover only enabled
    harnesses.
11. Only state proven to be managed by `ballen-config` may be replaced or
    removed. Matching bytes without an exact managed receipt never authorize
    deletion.
12. A rename is declared, never inferred. Absence from a resolved selection is
    not evidence of a rename, because profile, include, and skip resolution all
    produce the same absence.
13. Ambiguous or drifted legacy ownership blocks the run and installs no
    replacement. No completed run leaves two skills claiming one procedure on a
    target it converged; an interrupted run leaves either a recognized state the
    next run resolves before other work or a blocked state it reports.
14. Tree and receipt mutation is serialized as one unit against concurrent runs;
    a crash can still separate them, so that state is classified rather than
    assumed away. A destructive mutation
    is planned, applied, and reported like any other action, never performed as a
    side effect of inspection.

## Architecture

### Canonical source layout

```text
assistants/
└── shared/
    ├── standards/
    │   └── dependency-management.md
    └── skills/
        ├── catalog.yaml
        ├── discover-project-standards/
        │   └── SKILL.md
        ├── review-project-standards/
        │   └── SKILL.md
        ├── using-github/
        │   └── SKILL.md
        ├── using-gitlab/
        │   └── SKILL.md
        ├── using-jujutsu/
        │   ├── SKILL.md
        │   └── reference.md
        ├── using-uv/
        │   ├── SKILL.md
        │   └── references/
        │       └── dependency-management.md
        └── writing-executive-communications/
            └── SKILL.md
```

`digest_tree` and the managed-tree copy both walk `rglob("*")`, so the nested
`using-uv/references/` directory needs no installer change.

### Catalog entries

The seven-skill scope is approved. The entries below are the proposed shape, not
a reviewed result: each slice sets its own `provenance` and `portability_status`
after that skill's content is written and its portability review is performed.
No entry may claim `reviewed-generic` before that review happens, and provenance
follows the existing convention of naming the source and letting commit history
carry the rest rather than asserting a review date.

Every entry uses the current `SkillSpec` schema unchanged:

```yaml
skills:
  - name: discover-project-standards
    source: assistants/shared/skills/discover-project-standards
    targets: [cursor, claude-code, codex]
    profiles: [default]
    dependencies: []
    provenance: Genericized from plato/skills/tooling-discover-standards at commit f3b91eead0eff7d0c9cada3bc8e689f7610fba55; commit history records the promotion.
    portability_status: reviewed-generic

  - name: review-project-standards
    source: assistants/shared/skills/review-project-standards
    targets: [cursor, claude-code, codex]
    profiles: [default]
    dependencies: [discover-project-standards]
    provenance: Genericized from plato/skills/tooling-review-standards at commit f3b91eead0eff7d0c9cada3bc8e689f7610fba55; commit history records the promotion.
    portability_status: reviewed-generic

  - name: using-github
    source: assistants/shared/skills/using-github
    targets: [cursor, claude-code, codex]
    profiles: [default]
    dependencies: []
    provenance: Authored for ballen-config as the GitHub counterpart to using-gitlab, verified against current primary GitHub CLI documentation.
    portability_status: reviewed-generic

  - name: using-gitlab
    source: assistants/shared/skills/using-gitlab
    targets: [cursor, claude-code, codex]
    profiles: [default]
    dependencies: []
    provenance: Rewritten for portability from plato/skills/using-gitlab at commit f3b91eead0eff7d0c9cada3bc8e689f7610fba55; commit history records the promotion.
    portability_status: reviewed-generic

  - name: using-jujutsu
    source: assistants/shared/skills/using-jujutsu
    targets: [cursor, claude-code, codex]
    profiles: [default]
    dependencies: []
    provenance: Renamed from the promoted jujutsu-workflow skill added in commit 2d057f673971232e2327924c1a5f846ff9ace48e, itself promoted from plato/skills/jujutsu-workflow at commit f3b91eead0eff7d0c9cada3bc8e689f7610fba55; commit history records both.
    portability_status: reviewed-generic

  - name: using-uv
    source: assistants/shared/skills/using-uv
    targets: [cursor, claude-code, codex]
    profiles: [default]
    dependencies: []
    provenance: Authored for ballen-config against current primary uv documentation.
    portability_status: reviewed-generic

  - name: writing-executive-communications
    source: assistants/shared/skills/writing-executive-communications
    targets: [cursor, claude-code, codex]
    profiles: [default]
    dependencies: []
    provenance: Genericized from plato/skills/reports-consultant-style at commit f3b91eead0eff7d0c9cada3bc8e689f7610fba55; commit history records the promotion.
    portability_status: reviewed-generic

renames:
  - from: jujutsu-workflow
    to: using-jujutsu
```

### Rename declarations

`renames` is the one schema addition: a tuple of frozen entries carrying `from`
and `to`. Both are required, so a rename without a successor is unrepresentable.
Validation rejects a `from` that still appears in `skills`, a `to` that does not,
and duplicate `from` values.

The declaration exists because a rename cannot be safely inferred from local
state. `_eligible_targets` drops a skill whose profiles do not intersect the
active profiles, so a skill excluded by the current profile is indistinguishable
from one that was renamed. Keying cleanup on resolved desired state would retire
every `work`-profile skill during a `--profile default` run. All seven current
entries are `[default]`, but `work` inherits from `default` and the roadmap
contemplates work-only skills, so an explicit declaration is the safe form.
Candidacy is therefore computed from the complete parsed catalog, before profile,
include, target, or skip resolution.

The declaration carries **intent only**. It deliberately does not restate
historical target coverage or an expected legacy digest, because both already
exist in per-machine state and a second copy in the repository could disagree
with reality without any principled way to resolve the conflict. See
[ownership proof](#ownership-proof) for the evidence the protocol actually uses.

Declarations are permanent. They are never removed on the strength of one
machine's converged state, because `renames` lives in the repository and is
shared across machines while receipts are per-machine, and because a harness
skipped today may be enabled tomorrow. A declaration leaves the catalog only by
an explicit human decision that every machine has converged, which no automated
check can establish.

A managed record whose name is absent from `skills` but undeclared in `renames`
is never cleaned. It is reported so the operator can either declare the rename or
restore the entry.

Retirement without a successor is deliberately not modeled. No skill in this
workstream needs it, and requiring `to` keeps the mechanism a rename protocol
rather than a general retirement subsystem. See
[deferred generic retirement](#deferred-generic-retirement) for the conditions
that would justify revisiting this.

Required external commands are documented in each `SKILL.md`, together with the
skill's behavior when the command is absent. They are deliberately not modeled
as catalog fields: every first-release requirement resolves to a single
executable name, and the program design already classifies external commands as
documented prerequisites with graceful fallback rather than skill dependencies.

### Standards pair composition

`review-project-standards` depends on `discover-project-standards`. The catalog
dependency guarantees co-installation: `SkillCatalog` requires the consumer's
targets and profiles to be a subset of the dependency's, and skill
configuration re-checks that coverage against the targets actually selected
after profile resolution and skip.

The reference is by name. `review-project-standards` instructs the agent to
follow the `discover-project-standards` skill, and notes that it installs as a
sibling directory under the same skills root. The relative path
`../discover-project-standards/SKILL.md` is a concrete hint about where that
content lives, not the mechanism the instruction depends on.

That distinction matters because cross-skill sibling access is not documented
behavior. The published skill documentation describes supporting resources
bundled *within* a skill; it does not establish that a harness will resolve a
path into a neighbouring skill's directory. A name-based instruction degrades
usefully when path traversal fails, because native skill invocation, an agent
locating the skill by name under its own skills root, and a direct path read all
satisfy it.

#### Release gate

The composition is proven, not assumed. Before the standards pair is approved,
an opt-in smoke confirms on each enabled target that invoking
`review-project-standards` results in discovery being consulted before review
output. The gate covers the standards-pair slice only. A failure narrows to the
weakest reference form that the failing harness does support, and it never
blocks the other five skills, duplicates the discovery procedure, or reopens
this design.

Discovery remains a separate skill rather than being folded into review because
the roadmap's quality, test, type, and self-review workflows all consume the
same primitive.

## Ownership Boundaries

### Personal skills

The promoted skills own:

- read-only versus mutating workflow boundaries;
- provider selection and portable command fallbacks;
- interpretation of repository-local instructions;
- safe procedural sequences; and
- normalized review or discovery outputs.

### Native providers

Native or third-party plugins, connectors, and installed command-line tools
own:

- GitHub and GitLab API capabilities;
- authentication and credential storage;
- harness-specific tool schemas;
- installation and upgrade state for external providers; and
- remote service behavior.

A skill may explain how to discover and use an available provider. It must not
copy that provider, inspect its generated cache as authority, or claim its
capability as personal workflow logic.

### Standards library

`assistants/shared/standards/` owns normative engineering guidance. Workflow
skills discover, load, and apply those standards without restating them.

For example, `using-uv` owns the decision procedure for choosing `uv run`,
`uv add`, `uv remove`, `uv sync`, lock, and workspace operations. Dependency
policy, Python version policy, and repository precedence remain standards.

### Progressive standards loading

This workstream bundles standards references only with the skill that consumes
them. It does not create a shared standards-reference skill or a family of
focused standards skills.

- `discover-project-standards` and `review-project-standards` inspect
  human-written standards in the target repository. They do not treat the
  `ballen-config` standards library as an implicit project standard.
- `using-uv` receives an exact copy of
  `assistants/shared/standards/dependency-management.md` at
  `using-uv/references/dependency-management.md`. The canonical document is 46
  lines, so the copy is cheap and the skill needs no path outside its own
  installed tree.

Bundled references are generated projections, not independently edited
authorities. A test asserts byte equality with the canonical source, and a
canonical change requires regenerating the projection in the same change. A
standalone standards-reference skill remains deferred until more than one
consumer needs the same runtime-loading behavior.

## First-Release Skill Contracts

### `discover-project-standards`

Source: `plato/skills/tooling-discover-standards/SKILL.md`.

The skill is already mostly generic. Promotion reviews and adapts:

- all supported repository instruction filenames and precedence;
- repository-local tool configuration and standards discovery;
- references to old command-style sibling names;
- behavior when no applicable standards are found; and
- a stable logical result for downstream consumers.

Its result identifies ordered instruction sources, applicable standards,
repository-selected tools, conflicts, and unavailable sources. It does not copy
a repository's instructions into persistent personal state.

### `review-project-standards`

Source: `plato/skills/tooling-review-standards/SKILL.md`.

This skill and `discover-project-standards` are a coupled pair. The review skill
follows discovery by name before reviewing code, as described in
[standards pair composition](#standards-pair-composition), and its release is
gated on proving that composition. It does not contain a duplicated discovery
fallback.

Review is read-only by default. Findings identify the relevant standard,
evidence, file and location when applicable, and severity. The skill
distinguishes:

- no applicable standards;
- incomplete discovery;
- clean review against discovered standards; and
- actionable findings.

### `using-gitlab`

Source: `plato/skills/using-gitlab/SKILL.md`.

This is a substantial genericization, not a rename. The skill:

- derives repository and remote identity from the current checkout;
- removes fixed project IDs, internal hosts, and Plato-specific examples;
- discovers available GitLab providers instead of assuming one tool surface;
- prefers read-only inspection;
- uses `glab` as the documented command fallback and states its behavior when
  neither a connector nor `glab` is available;
- separates provider setup from workflow guidance;
- previews mutations and confirms the canonical remote target;
- requires explicit user intent before remote writes;
- confirms the resolved remote is actually GitLab before proceeding, and names
  `using-github` when it is not; and
- never migrates authentication or MCP configuration.

The skill owns safe GitLab procedure. A connector or `glab` owns API and
authentication capability.

### `using-github`

This is new content, authored as the counterpart to `using-gitlab`. It is
written in the same release so that provider discovery, preview, and
mutation-intent patterns are shared while both are being drafted, rather than
retrofitted onto a skill that has already settled into GitLab-shaped
assumptions. The skill:

- derives repository and remote identity from the current checkout;
- discovers available GitHub providers instead of assuming one tool surface;
- prefers read-only inspection;
- uses `gh` as the documented command fallback and states its behavior when
  neither a connector nor `gh` is available;
- separates provider setup from workflow guidance;
- previews mutations and confirms the canonical remote target;
- requires explicit user intent before remote writes;
- confirms the resolved remote is actually GitHub before proceeding, and names
  `using-gitlab` when it is not; and
- never migrates authentication or MCP configuration.

Pull-request review threads, checks, and merge semantics differ from GitLab's
merge requests. The skill keeps those differences visible rather than flattening
them into shared vocabulary: structural parity is the goal, artificial identity
is not.

#### Why the forge skills stay parallel

The two contracts share every structural bullet and differ only in the provider
command, which invites a generic `using-gitforge` skill that routes to one of
them. That router is rejected rather than deferred.

The shared bullets are a safety protocol, not shared content: identity from the
checkout, provider discovery, read-only preference, documented fallback, preview,
target confirmation, explicit mutation intent, and no credential migration. What
differs is the domain vocabulary. A router shares the dispatch, which is the part
worth least, and leaves the protocol duplicated anyway.

Routing is also the most aggressive possible use of the least proven mechanism
here. Cross-skill reference is unproven enough to need a
[release gate](#release-gate) for one pair, and a router needs two hops of it.
It degrades badly where the standards pair degrades well: `review-project-standards`
still owns a review procedure if its reference fails, whereas a router that
cannot route has no content of its own. The forge is usually named by the
request, and the reciprocal guard bullets above resolve the remaining ambiguity
for the cost of one sentence each.

Parity is therefore maintained by drafting both skills in adjacent slices and
reviewing them against each other, not by a shared tree. The mechanical version
of that sharing is already scoped where its risk earns it: the roadmap's
non-user-facing [`forge-comment-plan`](#forge-review) contract owns canonical
target and head-SHA confirmation, batch validation, preview-before-apply,
stale-head detection, and duplicate protection for the mutation-heavy review
workflows, with provider skills owning API translation. Revisit a shared tree
when that contract lands and there are six forge consumers rather than two, or if
forge detection itself becomes a recurring burden.

### `using-jujutsu`

Sources:

- current promoted `assistants/shared/skills/jujutsu-workflow/`; and
- original Plato provenance under `plato/skills/jujutsu-workflow/`.

The content is a rename. It retains portable Jujutsu repository detection,
status, diff, revision, change-description, bookmark, and remote-operation
procedures. Durable commit-message guidance from Plato's `tooling-commit-msg`
folds into this skill rather than becoming a separate top-level skill.

The skill uses `jj` as its documented command, respects repository
instructions, and keeps remote mutation boundaries explicit. Renaming the
canonical directory and catalog entry changes its installed identity, which
requires the cleanup described below.

### `using-uv`

This is new procedural content. It:

- recognizes `pyproject.toml`, `uv.lock`, and uv workspaces;
- selects `uv run` for project tools;
- distinguishes dependency add, remove, sync, lock, and workspace operations;
- preserves repository-selected Python and dependency policy;
- loads its co-packaged copy of `dependency-management.md` when detailed policy
  is needed;
- explains behavior when uv is absent or another manager is selected; and
- verifies version-sensitive commands against current primary uv documentation
  during implementation.

The skill does not become a second dependency-management standard.

### `writing-executive-communications`

Source: `plato/skills/reports-consultant-style/SKILL.md`.

The source is already project-neutral: 181 lines of communication structure with
no Plato paths, imports, domain examples, or provider assumptions. Promotion is
close to byte-for-byte and reviews:

- the skill name and description, which currently frame the guidance around
  producing presentations;
- the worked examples, so they illustrate structure without implying a
  rendering tool or a remote provider; and
- the option-presentation template, which currently labels alternatives
  `Option A` and `Option B`. Promoted guidance names options descriptively,
  consistent with this repository's own convention against placeholder labels.

The skill owns evidence-aware communication structure: leading with the answer,
MECE decomposition, situation-complication-resolution framing, quantified
claims, explicit confidence levels, and the executive-summary format. It owns no
document format, presentation renderer, or storage destination.

## `jujutsu-workflow` Rename Protocol

### Provenance

The standalone generic skill entered `ballen-config` in commit
`2d057f673971232e2327924c1a5f846ff9ace48e`. The reviewed Plato source snapshot
is change ID `xwypuztloxzpntzpsuzuttsryqporyqs`, commit ID
`f3b91eead0eff7d0c9cada3bc8e689f7610fba55`, source path
`skills/jujutsu-workflow/`. The pinned legacy tree digest is
`e7ca3f2e0a0f3f79dff90cc8fd718d74fecf18234d9b57dfeb0245480af1a8ec`, already
asserted by `tests/assistants/test_skills.py`.

### Why new engine behavior is required

The engine has no removal path. `StateStore` only upserts managed records and
exposes no delete operation. `ConfigurationEngine.plan` acts solely on the
specs it is given, and skill configuration builds those specs only from
currently eligible catalog entries. Because a managed resource ID derives from
the skill name, renaming produces a new record and orphans the old one.

Renaming the catalog entry alone would therefore leave the installed
`jujutsu-workflow` tree and its receipt in place beside the new
`using-jujutsu`, in every harness, indefinitely. That is a duplicate workflow
authority, and it is the one real problem the superseded plugin design
identified.

Making that removal safe requires one further change. Neither state mutation nor
the tree-and-receipt pair it describes is serialized, so a destructive mutation
can lose a concurrent update or leave a receipt disagreeing with the tree it
describes. That is specified below and lands as its own slice.

Nothing beyond those two changes — a removal path and the lock — is added. There
is no general retirement framework, no reusable executable-action hierarchy, and
no per-target result model; see
[deferred generic retirement](#deferred-generic-retirement). The scope is one
declared rename, expressed as a single
`SkillRenameAction` with a planning half and an applying half, symmetric with
every other engine action.

### The rename protocol

Planning resolves the declared rename, classifies each enabled target, and emits
a redacted `PlanAction` per resolved operation. Applying executes only what that
frozen plan contains, in this order:

1. acquire the coarse mutation lock;
2. classify legacy state on every enabled target, accepting only the three states
   below;
3. preflight successor feasibility on every enabled target, so an install that
   cannot succeed is known before anything is mutated;
4. on any other classification, or any infeasible successor, change nothing and
   fail clearly;
5. install `using-jujutsu` where it is absent, and verify its receipt;
6. where legacy state remains, back up the tree, then compare-and-remove its
   exact receipt; and
7. on a later run, resume only the resumable interrupted states below.

Exactly three legacy states are accepted, and step 2 requires each enabled target
to be in one of them:

| Accepted state | Legacy tree | Legacy receipt | Steps that apply |
|---|---|---|---|
| Clean | Absent | Absent | 5 only; nothing to clean |
| Exact live legacy | Present at its recorded digest | Exact | 5, then 6 in full |
| Exact stale receipt | Absent | Exact | 5, then 6's compare-and-remove without a backup |

A clean target is the normal case on a new machine or a harness enabled after the
rename, so requiring live legacy state everywhere would fail those targets for no
reason. An exact stale receipt is the interrupted-cleanup state from a previous
run. Every other combination is a blocking classification; see
[classification](#classification).

Steps 3 and 5 both span all enabled targets deliberately. Because blocking is
all-or-nothing, discovering at step 5 that the successor cannot install on the
third target, after step 6 already cleaned the first, would be exactly the
half-converged outcome the protocol exists to prevent. Feasibility is therefore
established for every target before any target is mutated.

Steps 5 and 6 are ordered, not merely sequential: cleanup never runs before the
successor is proven on that target, and step 2's classification is revalidated
under the lock immediately before step 6.

Cleanup is never a side effect of inspection. `plan` and `doctor` stay read-only:
they classify and report, and only `configure` mutates.

#### Transaction scope

`StateStore.write` is atomic for the file, using a same-directory temporary,
`fsync`, and `replace`. Nothing larger is. `record_managed` and `record_install`
each perform `load`, then build a new mapping, then `write`, with no lock across
the three steps, so two concurrent runs can lose one another's updates.

Serializing only those three steps would not be enough, because the unit that
must stay consistent is the tree together with its receipt, and those are mutated
in separate places. `ConfigurationEngine.apply` revalidates with `digest_tree`,
then `_backup` moves the destination aside with `shutil.move`, then the tree is
published, and only then does `_record` call `record_managed`. Two concurrent
runs can interleave anywhere across that span and leave a receipt describing a
tree that was moved, or a tree with no receipt.

The lock bounds concurrency, not crashes. It prevents two runs from interleaving
across that span, but it cannot make a tree publish and a receipt write atomic
with respect to process death, because they are separate files with no shared
journal. A crash between them is therefore a state the design must classify
rather than exclude; see
[an unprovable replacement destination](#an-unprovable-replacement-destination-blocks-and-reports).

The lock is therefore one coarse exclusive advisory lock in `state_root`,
acquired before apply-time digest validation and held through backup, publish or
removal, and the receipt write or compare-and-remove. It covers **every** state
mutator, because a cleanup-only lock would still lose to a concurrent
`record_managed`. Compare-and-remove reads, compares against the frozen expected
value, and writes without releasing it. A run that cannot acquire the lock
reports contention and mutates nothing rather than proceeding optimistically.

A generation counter with retry is the alternative, and is rejected for this
workstream: `BootstrapState.version` already means schema version, so overloading
or shadowing it invites confusion, and retry loops need their own tests for no
benefit at single-machine concurrency.

#### Ownership proof

The managed receipt is the sole proof source, and this is a deliberate choice
rather than an omission.

`ManagedRecord` carries `resource_id`, `destination`, `source_digest`, and
`destination_digest`, and records are keyed by `resource_id`, which is
`f"shared-skill-{name}-{target.value}"`. Two consequences follow. Historical
target coverage is derivable by enumerating stored keys for the old name, across
every target rather than only the enabled ones. The expected legacy digest is
`destination_digest` on that record.

An exact receipt therefore establishes that `ballen-config` wrote this
destination, and that the bytes there still match what it wrote. That is the same
proof every existing ownership, drift, and repair decision already relies on.

It does not defend against a forged or corrupted state file, which is outside the
threat model: `state.json` is mode 0600 under the user's own home, validated
against symlinked components and non-regular files on every access, and is already
the trust root for all managed content. A pinned digest in the repository would not
improve this, because a declaration that disagreed with a stored receipt would
leave the classifier with two claims and no principled tie-breaker.

### Classification

Each enabled target is classified before the plan is frozen. Every row below
presumes the candidate is already declared in `renames`.

| Installed tree | Managed receipt | Classification | Planned action |
|---|---|---|---|
| Absent | Absent | Nothing to clean | No action |
| Exact receipt destination at recorded digest | Exact receipt identity and digests | Eligible | Back up, then compare-and-remove receipt |
| Absent | Exact stale receipt | Interrupted cleanup | Compare-and-remove receipt |
| Absent | Mismatched or duplicated | Ambiguous orphaned receipt | Preserve receipt, block replacement, report |
| Present | Absent, mismatched, or duplicated | Unmanaged or ambiguous | Preserve, block replacement, report |
| Present | Exact receipt, destination digest differs | Managed drift | Preserve, block replacement, report |
| Any | Target skipped | Out of scope | Leave path and receipt untouched |

An exact receipt means the resource ID, destination, source digest, and
destination digest all match; records are keyed by `resource_id`, so the key and
that field are the same value. Matching bytes without that receipt never
authorize deletion. A skipped target is resolved from target selection alone and
is never inspected.

The ambiguous-orphaned-receipt row needs implementation attention rather than
only a table entry. `_matching_record` currently raises
`ValueError("managed record mismatch")` when a stored record disagrees with the
expected resource ID or destination, or when two records claim one destination.
Rename planning must classify that condition and report it, because an
unhandled exception there would abort the run with a raised error instead of a
reported classification and a preserved receipt.

#### Blocking the replacement

When any enabled target is classified unmanaged, ambiguous, or drifted, the run
installs no replacement. Deploying `using-jujutsu` beside a `jujutsu-workflow`
tree that `ballen-config` cannot prove it owns would leave two installed skills
describing one procedure, with nothing determining which the agent loads. That is
the duplicate authority this rename exists to remove, so the correct outcome is to
converge no further and report the blocked target.

Blocking is all-or-nothing, matching what the planner already does.
`plan_skill_copies` builds its desired mapping across all requested targets and
then raises `SkillCollisionError` from a scan loop covering all of them, so one
target's collision returns no actions for any target. That behavior is kept: the
run fails closed, converges nothing, and reports the blocked target. The operator
either resolves the legacy state or reruns with the existing whole-harness
`--skip` for that harness, which already provides the isolation a per-target
result model would have provided automatically.

A per-target result refactor is deliberately rejected. It would exist only to
preserve partial progress after a single harness collision, and it would change
every skill install path and its tests to do so.

#### An unprovable replacement destination blocks and reports

Replacement proof is a written receipt, and the planner will not produce one when
the destination already holds content whose digest equals the source digest: the
scan loop skips it and the action loop emits nothing, so no `SkillCopyAction` is
created, no managed-tree spec is derived, and no receipt is written. Step 5 then
cannot be satisfied, so the run blocks and reports rather than cleaning legacy
state it cannot pair with a proven replacement.

Two paths reach this state, and the second is the reason it needs a
classification rather than a footnote.

Hand-authored content is the unlikely path. `plan_skill_copies` requires
`declared_skill_name(source) == name`, so the rename edits the `SKILL.md`
frontmatter and the two trees have different digests; arriving here that way
requires someone to have written the new content under the new name at the new
destination. The same fact keeps the pinned legacy digest a valid discriminator.

A crash during step 5 is the realistic path. `apply` publishes the tree before
`_record` writes the receipt, and the lock cannot make those two atomic against
process death, so a crash in that window leaves an exact `using-jujutsu` tree
with no receipt. The next run finds byte-identical unmanaged content at the
successor destination — the same state, arrived at through the protocol's own
ordering rather than through operator error.

Both are classified as a **blocked unmanaged replacement**: the run installs
nothing, cleans nothing, and reports the destination through doctor. The remedy is
to remove the unreceipted `using-jujutsu` tree and rerun, which is safe precisely
because the content is reproducible from the canonical source. This state is
tested explicitly, from a simulated crash between publish and receipt write.

Auto-adopting such a tree is deliberately rejected, and the crash path does not
change that. Without a receipt there is no way to distinguish our own interrupted
publish from content the operator placed, so adoption would claim ownership on
byte equality alone — the exact inference invariant 11 forbids. The cost of
refusing is one manual deletion after a crash, which is the correct side to err
on.

### Failure and recovery

Rename ordering installs the replacement before removing the legacy state, so a
failure after that point can leave both present. Each outcome below is either
resumable or blocked, never silently inconsistent:

- Failure before the replacement is proven leaves the legacy tree and receipt
  untouched, and nothing to resume.
- Failure while backing up or removing the receipt restores the legacy tree and
  receipt, and retains the replacement.
- A crash after backing up the tree but before receipt removal leaves an absent
  path plus an exact stale receipt.
- A crash between publishing the successor and writing its receipt leaves an
  exact unreceipted `using-jujutsu` tree, which blocks rather than resumes.
- A legacy tree or receipt that changes between planning and cleanup fails
  closed.
- Backups use the existing timestamped private backup area.

The middle bullets above describe transient duplicate authority: the replacement
is installed while legacy content or its receipt still exists. Doctor reports it
as an error until it clears.

Automatic resolution is guaranteed only for the exactly recognized intermediate
states — an absent path with an exact stale receipt, and a restored tree with its
exact receipt. The next `configure` run resolves those before other skill work.
Legacy state that has changed, been duplicated, or drifted correctly fails closed
instead, and stays blocked until the operator resolves it, which may be
indefinitely. That is the intended behavior: an unrecognized state is exactly the
case where automatic mutation is unsafe.

An unreceipted successor tree is recognized but deliberately not auto-resolved,
which is the one place those two categories come apart. It is reported with its
remedy rather than repaired, because repairing it means claiming ownership on byte
equality alone.

Rolling back the replacement is deliberately rejected. Uninstalling content just
proven correct, to restore a tree already proven eligible for removal, adds
mutation and new failure paths — including a failed rollback — to avoid an overlap
that is bounded, detected, and reported. Staging the replacement inactively is
also rejected, because no harness offers an inactive skill state to stage into.

The consequence for invariant 13 is stated plainly: no completed run leaves two
skills claiming one procedure on a target it converged, and an interrupted run
leaves either a recognized state the next run resolves first or a blocked state it
reports. A claim of no overlap at any instant would be false.

### Doctor

Cleanup state is reported through the existing skills check, using the state
vocabulary `doctor.py` already defines. No new state, severity, or
target-qualified finding identifier is introduced:

| Situation | Existing state | Severity |
|---|---|---|
| No leftover legacy skill state | No finding emitted | n/a |
| Harness explicitly skipped | `skipped` | info |
| Unmanaged, ambiguous, or duplicated legacy receipt; rename blocked | `manual` | warning |
| Unreceipted `using-jujutsu` tree at the successor destination; rename blocked | `manual` | warning |
| Receipt-backed content differs from its recorded digest; rename blocked | `drift` | error |
| Replacement installed with legacy tree or receipt still present | `drift` | error |

`manual` is the established state for ownership that requires user resolution,
which is exactly the preserved-legacy case. `drift` covers the interrupted-cleanup
window because it is precisely a divergence between recorded and live state, and
it must be an error so transient duplicate authority cannot survive unnoticed. If
implementation finds that any situation above cannot be expressed in the current
vocabulary, adding a state is a reviewed change to the shared check model, not an
incidental part of this workstream.

Doctor never recommends removing a rename declaration. Local convergence says
nothing about other machines or currently skipped harnesses, so a declaration
outliving its usefulness is the intended, harmless steady state.

Messages remain normalized and redact absolute paths, digests, file contents, and
command output.

## Delivery Slices

Implementation proceeds as independently reviewable vertical slices:

1. Take the coarse mutation lock across apply-time digest validation, backup,
   publish, and every state mutator, with no other behavior change.
2. Add the rename protocol: the `renames` model, classification,
   `SkillRenameAction` with its plan and apply halves, compare-and-remove,
   backup, rollback, and doctor reporting, with no content change.
3. Rename `jujutsu-workflow` to `using-jujutsu` as that protocol's caller,
   including its rename declaration.
4. Add `discover-project-standards` and `review-project-standards` together, and
   satisfy the composition release gate.
5. Add `using-uv` and its generated `dependency-management.md` projection.
6. Promote `writing-executive-communications`.
7. Rewrite and add `using-gitlab`.
8. Add `using-github` immediately afterwards, reusing the provider-discovery
   and mutation-safety pattern reviewed in the previous slice.

The two forge skills stay separate slices so each is reviewed on its own
mutation behavior, even though they are drafted together.

The engine slices form one chain: slice 2 depends on slice 1, because
compare-and-remove must run inside the lock's critical section, and slice 3
depends on slice 2 and transitively on slice 1. Slice 1 is worth landing first
regardless, because it is small and fixes a pre-existing race on its own.

Slices 4 through 8 are five additive content slices covering six skills — the
standards pair stays coupled by design — and none of them depends on the engine
chain or on each other. They land in any order. Every skill in this workstream,
including `using-jujutsu`, can be authored and content-reviewed in parallel with
the engine work; only `using-jujutsu`'s merge waits on the chain.

Every slice uses coherent reviewable checkpoints, leaves no duplicate
authority, updates catalog provenance, and passes plan, configure, doctor,
skip, collision, and idempotency tests.

## Validation Strategy

### Static and model tests

- catalog parsing, unknown-field rejection, and kebab-case skill names;
- rename declarations: rejection of a `from` still present in `skills`, of a `to`
  absent from `skills`, of a missing `to`, and of duplicate `from` values;
- dependency existence, cycles, and target and profile coverage for the
  standards pair;
- canonical tree digests for each new and renamed skill;
- byte equality between the bundled `dependency-management.md` projection and
  its canonical source;
- absence of prohibited project paths, identifiers, credentials, or generated
  state in every promoted tree;
- unmanaged collision preservation;
- whole-harness skip behavior; and
- default and inherited profile resolution.

### Rename protocol tests

Parameterize every classification row across Cursor, Claude Code, and Codex.
Cover exact resource, destination, and digest matching; absent paths with
mismatched or duplicated receipts, asserting a reported classification rather
than a raised `ValueError`; symlinks, special files, and traversal;
time-of-check/time-of-use changes; the step 5 before step 6 ordering; rollback
restoring both tree and receipt while retaining the replacement; resume from each
recognized intermediate state; target skips; doctor status, severity, ordering,
and redaction; and a first rename followed by a zero-action, zero-backup second
run.

Each of the three accepted legacy states needs its own case: a clean target
installs the successor and cleans nothing, an exact live legacy target runs the
full sequence, and an exact stale receipt performs compare-and-remove with no
backup. Successor feasibility needs a case where one target's successor
destination is blocked and no target is mutated at all.

Recovery needs assertions on both sides of the guarantee: the next `configure`
resolves each recognized intermediate state before other skill work, changed or
duplicated legacy state stays blocked across repeated runs and mutates nothing,
and doctor reports `drift` at error severity for as long as a replacement
coexists with legacy content or its receipt.

A simulated crash between publishing the successor and writing its receipt needs
its own case: the next run reports a blocked unmanaged replacement at `manual`
severity, adopts nothing, cleans no legacy state, and mutates nothing across
repeated runs until the unreceipted tree is removed.

### Transaction tests

- every state mutator acquires the lock, asserted by a test that fails if a new
  mutator bypasses it;
- the lock is held across apply-time digest validation, backup, publish, and the
  receipt write, asserted by a test that fails if it is released between them;
- a compare-and-remove observing an unexpected stored value makes no change;
- a concurrent mutation attempt reports contention and mutates nothing rather
  than proceeding; and
- lock acquisition failure never leaves a tree and receipt disagreeing.

### Candidate resolution tests

These guard against deleting a skill nobody renamed:

- a skill present in `skills` but excluded by the active profile is never a
  candidate, asserted with a `work`-profile fixture entry converged under
  `--profile default`;
- the same for exclusion by `--skip` and by target selection;
- a name absent from `skills` with no `renames` entry is reported and never
  cleaned; and
- candidacy is computed from the complete parsed catalog, asserted by a test
  that would fail if resolution moved after profile filtering.

### Blocked-replacement tests

For each ambiguous, orphaned-receipt, and drifted classification, assert that no
replacement is installed, that no receipt is written, that the legacy tree and
receipt are left exactly as found, and that the run reports the blocked target
rather than success.

### Native smokes

Use isolated homes and fixture repositories. Do not use personal native state as
test input. After installing into all three harnesses, invoke each first-release
skill once.

The standards-pair composition smoke is a release gate for its slice: on each
enabled target, invoke `review-project-standards` and confirm from the target's
observable output that discovery is consulted before review findings. Record the
reference form that each harness satisfies, since cross-skill sibling access is
not documented behavior.

The forge guard smoke runs each provider skill against a fixture repository whose
remote belongs to the other forge, and confirms the skill names its counterpart
instead of proceeding. This is what replaces a router, so it is verified rather
than assumed.

### Repository verification

After focused tests, run the repository's complete configured checks:

```text
rtk uv run --frozen pytest -q
rtk uv run --frozen ruff check .
rtk uv run --frozen ruff format --check src tests
rtk uv run --frozen mypy
rtk uv run --frozen python -m ballen_config.policy
rtk zsh -n bootstrap
rtk uv run --frozen pre-commit run --all-files
```

Then run read-only `./bootstrap plan` and `./bootstrap doctor` with identical
profile and skip selections, followed by the native invocation smokes.

## Deferred Plugin Packaging

Packaging some or all of these skills as a plugin is deferred, not rejected.
Revisit it when at least one of the following is true:

- a payload needs a plugin-native capability that a skill tree cannot carry,
  such as a command, hook, or bundled MCP server;
- optional grouped installation becomes a real requirement, meaning a per-skill
  or per-group selector rather than a single required unit; or
- distribution to other people or machines becomes a goal.

Any revival must also resolve what the superseded revision did not: private
repository authentication for a Git-backed marketplace, Codex plugin-update
behavior, and a local edit loop that does not require publishing a release to
test a change.

## Deferred Generic Retirement

A generic retirement mechanism is out of scope, deferred rather than rejected.
This workstream needs exactly one safe rename, so it builds a bounded rename
protocol: `renames` requires a successor, blocking stays all-or-nothing, and
unmanaged content is preserved and reported rather than adopted.

An earlier revision generalized that rename into a retirement subsystem. The
generality, not the rename, is what attracted successor-free retirement,
adoption, per-target results, and a reusable executable-action hierarchy, none of
which had a caller here. Revisit the generalization when at least one of the
following is true:

- a skill genuinely leaves the catalog with no successor, which `renames` cannot
  express by construction;
- a second rename or retirement arrives whose shape the bounded protocol does not
  fit;
- a blocked harness stops being resolvable by whole-harness `--skip`, meaning
  partial convergence across targets becomes a real requirement rather than a
  convenience; or
- unmanaged content at a replacement destination becomes a recurring operator
  burden rather than the near-unreachable case it is today.

Any revival inherits safety work this revision deliberately does not do, and each
item exists only with the feature it guards:

- adoption of byte-identical unmanaged content must revalidate at apply time.
  Planning-time byte equality is not ownership proof, because the destination can
  change before apply. Re-digest source and destination under the mutation lock
  immediately before writing the receipt, require that no conflicting managed
  record claims the destination, and write nothing on mismatch.
- per-target results must propagate dependency failure. If
  `discover-project-standards` is blocked on one target, the dependent
  `review-project-standards` must be blocked on that same target, or a dependent
  skill installs against a missing dependency.
- a broader doctor matrix must still map onto the states `doctor.py` defines.
  Adding a state is a reviewed change to the shared check model, not an
  incidental part of a retirement feature.

The coarse mutation lock is not deferred. It is required by the rename protocol,
it fixes a pre-existing race in every state mutator, and it is a prerequisite for
any of the above rather than part of it.

## Post-v1 Roadmap

Later work is grouped below. The groups are independent unless a dependency is
stated; the order is a planning preference, not a chain.

Everything here is gated by a design contract or an upstream skill, not by
delivery cost. Adding a skill is now a directory, a catalog entry, and a digest
test, so an item stays on this roadmap only while its prerequisite is genuinely
missing. Each group therefore records its dependency and its ownership
boundary, and deliberately stops short of specifying contracts for work that
has not started.

### Project review primitives

First define an internal Git/Jujutsu-neutral change-scope contract for the
comparison base, changed files, and diff. Then add:

- `review-project-quality` for report-first lint and type-check command
  discovery and structured diagnostics;
- `review-project-tests` for repository-aware test-quality review; and
- `review-python-types` for explicitly Python-specific type and model review.

Test and type review may proceed in parallel after the shared change-scope and
quality foundations exist. All three consume
`discover-project-standards`.

### Self-review orchestration

Add `conduct-self-review` only after all three project-review primitives exist.
It:

- invokes the standards, quality, tests, and Python-type reviews that apply;
- resolves current change and comparison base for Git and Jujutsu;
- aggregates inline results;
- distinguishes skipped or unavailable coverage from a clean result; and
- writes a report file only when the user asks.

It records a reviewed additive or delegated relationship with native
`verification-before-completion` and code-review skills rather than silently
claiming their authority.

### Forge review

Add a non-user-facing `forge-comment-plan` contract, followed by:

1. `review-gitlab-merge-request` in read, analyze, deduplicate, and draft mode;
2. a separately reviewed explicit posting phase; and
3. `review-github-pull-request` after the GitLab workflow is proven.

The internal contract owns canonical target and head-SHA confirmation, batch
validation, preview-before-apply, stale-head detection, duplicate protection,
and exact partial-completion reporting. Provider skills own API translation.

### Forge response

Add `respond-to-gitlab-review`, then `respond-to-github-review`. These remain
later, high-risk workflows. They delegate feedback evaluation to the native
`receiving-code-review` authority. Editing, verification, change-description
creation, push, and remote response remain distinct phases with explicit
mutation intent.

### Review learning

Add `extract-review-lessons` over normalized review-thread input. It produces
an approved repository-local draft and depends on standards discovery.

Keep `promote-project-lessons` on the roadmap after a generic writable
repository-local lesson-ledger contract is designed. It must not assume
`.claude/temp`, `.cursor/rules`, or direct promotion into shared
`ballen-config` standards.

### Personal knowledge capture

Rewrite the portable formatting core of `reports-obsidian-note` as
`capturing-obsidian-notes`. Raw text always works. URL, PDF, DOCX, PPTX, and S3
acquisition delegate to available native providers. Preview is the default, and
writing requires an explicit destination.

## Fold and Exclusion Decisions

Fold durable material instead of creating these top-level skills:

- `tooling-lint-markdown` into `review-project-quality`;
- `tooling-create-tests` into the testing standard and `review-project-tests`;
- concise `tooling-review-snapshots` guidance into `review-project-tests`,
  while retaining the large Syrupy manual locally; and
- useful `tooling-commit-msg` guidance into `using-jujutsu` and any future
  `using-git`.

Do not promote:

- `tooling-fix-bug` or `tooling-workflow`, because native Superpowers skills
  already own debugging, TDD, planning, execution, and completion;
- `reports-notion-reference`, `reports-read-pptx`, or `reports-write-pptx`,
  because native providers own their service and file mechanics;
- current Logfire and S3 skills, which remain environment-specific; or
- Plato context, digest, deck, QSP, company, and competitive-intelligence
  skills.

## Security and Privacy

- Promoted skill trees contain no authentication material or secret references.
- Native authentication remains native and is never represented in receipts.
- Plans and doctor findings redact absolute paths, digests, source contents,
  and command output.
- Tree validation rejects traversal, symlinks, special files, and unsafe
  destinations before copy or cleanup.
- Remote-write skills require explicit user intent, canonical target
  confirmation, and a preview where the provider permits it.
- Native caches and generated plugin state are never copied, committed, or
  inspected as authoritative input.

## Success Criteria

The workstream is complete when:

- all seven first-release skills install from one reviewed source into Cursor,
  Claude Code, and Codex through the existing shared-skill catalog;
- the existing `SkillSpec` delivery model remained intact, and the only schema
  addition is the rename declaration;
- every promoted skill records its source in catalog provenance, and no entry
  claims `reviewed-generic` before its portability review is performed;
- the bundled standards reference exactly matches its canonical source;
- the standards-pair composition gate passed on every enabled target, with the
  satisfied reference form recorded;
- native plugins and connectors remain authoritative for capabilities;
- repository instructions and configuration retain precedence;
- remote mutation requires explicit user intent;
- no prohibited operational state is migrated;
- the engine can prune an orphaned managed skill record, and does so only for a
  declared rename with exact receipt and digest proof, through a planned and
  reported action rather than a side effect of inspection;
- no profile, include, target, or skip selection can make a skill that remains in
  the catalog look renamed;
- the lock is held across apply-time digest validation, backup, publish, and
  receipt mutation, so no two concurrent runs can leave a tree and receipt
  disagreeing, and a compare-and-remove cannot lose a concurrent update;
- the tree and receipt writes a crash can still separate are classified, reported
  with a remedy, and never auto-adopted;
- the old `jujutsu-workflow` installation is removed only where that proof
  permits; unmanaged, orphaned-receipt, or drifted content is preserved and
  reported, and the run installs no replacement;
- each resumable interrupted state is resolved before other skill work on the next
  run, every other one — recognized or not — stays blocked and reported, and none
  clears silently;
- plan, configure, doctor, skip, collision, rename, blocked-replacement,
  transaction, rollback, and idempotency behavior are tested; and
- each later roadmap group has a clear dependency and ownership boundary.

## Implementation Boundary

This document authorizes preparation of an implementation plan after design
review. It does not itself authorize skill installation, native-state mutation,
legacy cleanup, or changes to Plato.
