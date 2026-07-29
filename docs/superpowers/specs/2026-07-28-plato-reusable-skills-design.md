# Plato Reusable Skills Detailed Design

## Status

Detailed design for review.

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

It does not provide retirement. The engine has no path for removing a skill that
leaves the catalog, which is the one capability this workstream adds; see
[the rename and orphan cleanup](#jujutsu-workflow-rename-and-orphan-cleanup).

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
- Deliver every skill through the existing `SkillSpec` schema and installer
  unchanged. The only schema addition is the retirement declaration required to
  make cleanup safe.
- Install every first-release skill for Cursor, Claude Code, and Codex in the
  `default` profile, subject only to the existing whole-harness skip.
- Preserve native plugins, connectors, and command-line tools as authoritative
  capability providers.
- Keep normative engineering guidance in the standards library and procedures
  in skills.
- Rename `jujutsu-workflow` to `using-jujutsu` without deleting unmanaged or
  modified content.
- Add the generic orphan cleanup the engine currently lacks, so any skill can
  be renamed or retired safely.
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
12. Retirement is declared, never inferred. Absence from a resolved selection
    is not evidence of retirement, because profile, include, and skip
    resolution all produce the same absence.
13. A target whose legacy ownership is ambiguous or drifted receives no
    replacement, so a run never leaves two skills claiming one procedure.

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

retired:
  - name: jujutsu-workflow
    replaced_by: using-jujutsu
    reason: Renamed for consistency with the using-<tool> convention.
```

### Retirement declarations

`retired` is the one schema addition. It is a tuple of frozen entries carrying a
retired skill `name`, an optional `replaced_by` naming a current skill, and a
`reason`. Validation rejects a `name` that still appears in `skills`, a
`replaced_by` that does not, and duplicate names.

The declaration exists because retirement cannot be safely inferred; see
[classification](#classification) for how it is consumed. Its cost is one small
model and one catalog section, which is the correct trade against deleting a
skill the operator never retired.

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
- requires explicit user intent before remote writes; and
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
- requires explicit user intent before remote writes; and
- never migrates authentication or MCP configuration.

Pull-request review threads, checks, and merge semantics differ from GitLab's
merge requests. The skill keeps those differences visible rather than flattening
them into shared vocabulary: structural parity is the goal, artificial identity
is not. A generic forge router remains deferred until both skills demonstrate
repeated routing logic.

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

## `jujutsu-workflow` Rename and Orphan Cleanup

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

### Generic orphan cleanup

The fix belongs in the engine, not in a skill-specific migration. Add:

1. an atomic compare-and-remove on `StateStore` that deletes a managed record
   only when the stored value exactly equals the expected value from the frozen
   plan; and
2. a converge pass that resolves cleanup candidates from the retirement
   declarations, classifies each per target, and plans the resulting action.

The `jujutsu-workflow` rename is the first caller. No `migration.*` finding
identifiers, per-skill migration action, or bespoke rollback path is introduced,
and every later skill rename or retirement reuses the same behavior.

#### Candidate resolution never reads the resolved selection

A cleanup candidate comes from two independent conditions, both required:

1. the name appears in `retired`; and
2. the name appears nowhere in `skills`, evaluated against the **complete
   parsed catalog**, before profile, include, target, or skip resolution.

Absence from the resolved selection is explicitly not a candidacy signal.
`_eligible_targets` drops a skill whose profiles do not intersect the active
profiles, so a skill excluded by the profile in use is indistinguishable from one
that was retired. Keying cleanup on resolved desired state would retire every
`work`-profile skill during a `--profile default` run, back up its tree, drop its
receipt, and reinstall it on the next `work` run. No current entry triggers this,
because all seven are `[default]`, but `work` inherits from `default` and the
roadmap contemplates work-only skills, so the ordering is load-bearing rather
than theoretical.

A record whose name is absent from `skills` but undeclared in `retired` is never
cleaned. It is reported so the operator can either declare the retirement or
restore the entry.

### Classification

Each enabled target is classified independently before the plan is frozen. Every
row below presumes the candidate is already declared retired.

| Installed tree | Managed receipt | Classification | Planned action |
|---|---|---|---|
| Absent | Absent | Nothing to clean | No action |
| Exact receipt destination at recorded digest | Exact receipt identity and digests | Eligible | Back up, then compare-and-remove receipt |
| Absent | Exact stale receipt | Interrupted cleanup | Compare-and-remove receipt |
| Present | Absent, mismatched, or duplicated | Unmanaged or ambiguous | Preserve, block replacement, report |
| Present | Exact receipt, destination digest differs | Managed drift | Preserve, block replacement, report |
| Any | Target skipped | Out of scope | Leave path and receipt untouched |

An exact receipt means the expected receipt key, resource ID, destination, source
digest, and destination digest all match. Matching bytes without that receipt
never authorize deletion. A skipped target is resolved from target selection
alone and is never inspected.

#### Blocking the replacement

On a target classified unmanaged, ambiguous, or drifted, the run installs no
replacement for that target. Deploying `using-jujutsu` beside a
`jujutsu-workflow` tree that `ballen-config` cannot prove it owns would leave two
installed skills describing one procedure, with nothing determining which the
agent loads. That is the duplicate authority this cleanup exists to remove, so
the correct outcome is to converge no further on that target and report it.

Blocking is per target. Other enabled targets install and clean normally, and
partial completion is an expected result rather than a failure. The replacement
lands on a blocked target only after the operator resolves the legacy state and
reruns.

Ordering per unblocked target is: install the replacement and verify its receipt,
then revalidate the legacy receipt and live digest immediately before cleanup,
then back up, then compare-and-remove. Cleanup never runs before the replacement
is proven.

### Failure and recovery

- Failure before the replacement is proven leaves the legacy tree and receipt
  untouched.
- Failure while backing up or removing the receipt restores the legacy tree and
  receipt.
- A crash after backing up the tree but before receipt removal yields an absent
  path plus an exact stale receipt, which the next run resumes.
- A legacy tree or receipt that changes between planning and cleanup fails
  closed.
- Backups use the existing timestamped private backup area.

### Doctor

Cleanup state is reported through the existing skills check, using the state
vocabulary `doctor.py` already defines. No new state, severity, or
target-qualified finding identifier is introduced:

| Situation | Existing state | Severity |
|---|---|---|
| No orphaned managed skill state | No finding emitted | n/a |
| Harness explicitly skipped | `skipped` | info |
| Unmanaged, ambiguous, or duplicated legacy receipt; replacement blocked | `manual` | warning |
| Receipt-backed content differs from its recorded digest; replacement blocked | `drift` | error |
| Retired declaration whose cleanup has not completed on an enabled target | `missing` | warning |
| Record absent from `skills` with no retirement declaration | `manual` | warning |

`manual` is the established state for ownership that requires user resolution,
which is exactly the preserved-legacy case. If implementation finds that any
situation above cannot be expressed in the current vocabulary, adding a state is
a reviewed change to the shared check model, not an incidental part of this
workstream.

A declared retirement whose cleanup has completed on every enabled target is
reported once so the declaration can be removed, which prevents `retired` from
accumulating entries that no longer describe live state.

Messages remain normalized and redact absolute paths, digests, file contents, and
command output.

## Delivery Slices

Implementation proceeds as independently reviewable vertical slices:

1. Add generic orphan cleanup: the compare-and-remove state operation, the
   converge pass, classification, backup, rollback, and doctor reporting, with
   no content change.
2. Rename `jujutsu-workflow` to `using-jujutsu` as the first caller of that
   cleanup, including its retirement declaration.
3. Add `discover-project-standards` and `review-project-standards` together, and
   satisfy the composition release gate.
4. Add `using-uv` and its generated `dependency-management.md` projection.
5. Promote `writing-executive-communications`. This slice depends only on the
   cleanup foundation and may land at any point after it.
6. Rewrite and add `using-gitlab`.
7. Add `using-github` immediately afterwards, reusing the provider-discovery
   and mutation-safety pattern reviewed in the previous slice.

The two forge skills stay separate slices so each is reviewed on its own
mutation behavior, even though they are drafted together.

Every slice uses coherent reviewable checkpoints, leaves no duplicate
authority, updates catalog provenance, and passes plan, configure, doctor,
skip, collision, and idempotency tests.

## Validation Strategy

### Static and model tests

- catalog parsing, unknown-field rejection, and kebab-case skill names;
- retirement declarations: rejection of a retired name still present in
  `skills`, of a `replaced_by` that is absent from `skills`, and of duplicate
  retired names;
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

### Orphan cleanup tests

Parameterize every classification row across Cursor, Claude Code, and Codex.
Cover exact receipt key, resource, destination, and digest matching; absent
paths with mismatched or duplicated receipts; symlinks, special files, and
traversal; time-of-check/time-of-use changes; ordering of install, verify,
backup, and receipt removal; rollback restoring both tree and receipt; crash
resume; partial target completion and target skips; doctor status, severity,
ordering, and redaction; and a first cleanup followed by a zero-action,
zero-backup second run.

Candidate resolution needs its own cases, because they guard against deleting a
skill nobody retired:

- a skill present in `skills` but excluded by the active profile is never a
  candidate, asserted with a `work`-profile fixture entry converged under
  `--profile default`;
- the same for exclusion by `--skip` and by target selection;
- a name absent from `skills` with no `retired` entry is reported and never
  cleaned;
- a declared retirement whose name is still in `skills` fails catalog
  validation; and
- candidacy is computed from the complete parsed catalog, asserted by a test
  that would fail if resolution moved after profile filtering.

### Blocked-replacement tests

For each ambiguous and drifted classification, assert that no replacement is
installed on that target, that no receipt is written for it, that other enabled
targets still converge, and that the run reports partial completion rather than
success.

### Native smokes

Use isolated homes and fixture repositories. Do not use personal native state as
test input. After installing into all three harnesses, invoke each first-release
skill once.

The standards-pair composition smoke is a release gate for its slice: on each
enabled target, invoke `review-project-standards` and confirm from the target's
observable output that discovery is consulted before review findings. Record the
reference form that each harness satisfies, since cross-skill sibling access is
not documented behavior.

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
- delivering them required no change to `SkillSpec` or the installer, and the
  only schema addition is the retirement declaration;
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
  declared retirement with exact receipt and digest proof;
- no profile, include, target, or skip selection can make a skill that remains in
  the catalog look retired;
- the old `jujutsu-workflow` installation is retired only where that proof
  permits; unmanaged or drifted content is preserved, reported, and receives no
  replacement on that target;
- plan, configure, doctor, skip, collision, cleanup, blocked-replacement,
  rollback, and idempotency behavior are tested; and
- each later roadmap group has a clear dependency and ownership boundary.

## Implementation Boundary

This document authorizes preparation of an implementation plan after design
review. It does not itself authorize skill installation, native-state mutation,
legacy cleanup, or changes to Plato.
