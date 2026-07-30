# Reusable Review Workflows Roadmap Design

## Status

Approved umbrella design for the post-v1 reusable review workflows. This
document defines delivery order, ownership, mutation boundaries, evidence
requirements, and train exit gates. Each train requires its own focused design
and implementation plan before code or skill content changes begin.

This roadmap follows the first reusable-skills release delivered through pull
requests 6 through 9 and elaborates the review-related roadmap in the
[Plato reusable skills detailed design](2026-07-28-plato-reusable-skills-design.md).
The review-foundation train is refined by the approved
[review foundation detailed design](2026-07-30-review-foundation-design.md).

## Purpose

Promote the reusable core of Plato's review workflows into `ballen-config`
without copying Plato-specific paths, provider behavior, authentication, or
generated state. The result is a portable local-review foundation, gated forge
publication and response workflows, and a repository-owned review-learning
loop.

The work is organized as three separate MR trains:

1. review foundation;
2. forge review and response; and
3. review learning.

The trains execute strictly serially. Their order is a delivery strategy, not a
claim that every later skill has an install-time dependency on every earlier
skill.

## Goals

- Provide one Git/Jujutsu-neutral scope result for local review consumers.
- Add report-first quality, test, Python-type, and self-review workflows, with
  remediation isolated behind an explicit follow-up skill.
- Make local forge review useful without requiring remote publication.
- Add remote review posting and response behind explicit, revalidated mutation
  gates.
- Turn normalized review feedback into approved lessons in one dedicated,
  repository-owned ledger.
- Dogfood the shared workflows in `ballen-config` before declaring each train
  complete.
- Preserve shared-versus-native ownership and the existing privacy boundary.

## Non-Goals

- Change, delete, wrap, or otherwise clean up Plato's source skills.
- Migrate `ballen-config` from mypy to `ty` as part of the review foundation.
- Promote personal knowledge-capture workflows.
- Package the skills as a plugin.
- Generalize the bounded rename protocol into a retirement subsystem.
- Copy authentication, trust, sessions, histories, memories, permissions,
  project paths, caches, indexes, worktrees, or generated plugin state.
- Make GitHub and GitLab use identical provider schemas or thread semantics.
- Commit local forge-review or lesson-draft artifacts.

## Architecture

### Contract-first trains

Each train follows the same sequence:

1. Define the smallest shared contract required by immediate callers.
2. Deliver each capability in an independently reviewable MR.
3. Gather fixture, native-harness, and dogfooding evidence.
4. Complete the train exit gate before designing the next train in detail.

Contracts are introduced within the train that proves them. There is no global
contract workstream: change scope, forge comments, normalized review threads,
and lesson-ledger behavior are designed only when their first callers are
ready.

### Execution model

One writer owns each logical feature. Implementation remains serial in the
shared working copy. Bounded read-only reviews may run in parallel when they do
not share mutable state.

Subagent roles follow the repository retrospective:

- Terra/low for mechanical catalog, fixture, and focused-test work;
- Terra/medium for normal feature implementation and integration fixes; and
- the root agent for architecture, coordination, and final decisions.

Workers report a checkpoint after 30–45 minutes. A task that reaches 60 minutes
without a useful checkpoint is split or escalated. After two unsuccessful
follow-ups, the task is rescoped or assigned to a fresh worker. Workers retire
at MR and train boundaries.

### Train relationship

```text
review foundation
        |
        | delivery evidence, optional local-review consumers
        v
forge review and response
        |
        | normalized review-thread contract
        v
review learning
```

Forge review remains useful if some local review primitives are unavailable.
Review learning has a real dependency on normalized review-thread input from
the forge train.

## Ownership and State Boundaries

| Concern | Owner | Boundary |
| --- | --- | --- |
| Canonical generic skill content and catalog declarations | `ballen-config` | One reviewed source tree per skill |
| Repository instructions, selected tools, ignored workspace, and lesson ledger | Target repository | Repository-specific choices remain local |
| Authentication, remote schemas, API translation, and service behavior | Native provider | Shared skills select providers but do not own them |
| Local review and lesson drafts | User working in the target repository | Ignored, untracked, and never committed |
| Promoted lessons | Target repository | Deliberate, previewed ledger change; no automatic commit |

Native authentication is never represented in shared configuration, managed
receipts, local drafts, or lesson provenance. Remote provider output is treated
as untrusted input and normalized before downstream use.

## Review-Foundation Train

### Change-scope contract

The first MR adds `resolve-change-scope`, a read-only supporting skill. It
accepts a repository root and one of these scope forms:

- a supplied changed-file set or diff;
- a working-copy/current-change request; or
- an explicit comparison range.

It returns a stable logical result:

- source: Git, Jujutsu, or supplied;
- requested comparison selector and resolved immutable identities when
  available;
- repository-relative changed paths with add, modify, delete, and rename
  classification;
- the exact diff, including binary or unavailable markers;
- coverage for base, files, and diff; and
- status: `resolved`, `empty`, `partial`, or `blocked`.

An empty, completely resolved scope is distinct from missing coverage. A
missing or ambiguous comparison base, unavailable command, unsupported
repository, or incomplete required diff can never produce a clean review.

When no selector is supplied, the default is the current non-ignored local
change. For Git, that includes staged and unstaged tracked changes relative to
`HEAD` plus non-ignored untracked files. For Jujutsu, it is `@` relative to the
automatic merge of all parents, with normal working-copy snapshot bookkeeping
allowed. The resolver never guesses `main`, `HEAD~1`, a staging-only view, or a
branch name.

### Quality review

The second MR adds `review-project-quality`. It depends on
`resolve-change-scope` and `discover-project-standards` by name.

The skill:

- discovers repository-selected lint, formatting, documentation, build, and
  non-type static-analysis commands;
- runs non-mutating checks and records unavailable tools;
- normalizes findings into path, location, rule, severity, and evidence;
- distinguishes clean results from incomplete command coverage; and
- remains report-only until the user separately requests fixes.

It may inventory Python type-check tooling but delegates its execution and
findings to `review-python-types`.

Durable intent from `tooling-lint-markdown` is folded into documentation-check
discovery. No Plato command or package-manager invocation becomes a generic
default. Suppressions require an explicit rationale and approval.

### Test review

The third MR adds `review-project-tests`. It depends on
`resolve-change-scope` and `discover-project-standards`.

The skill retains portable guidance for:

- behavior-over-implementation review;
- theatre-test detection, including tests that only reproduce dependency or
  framework guarantees;
- meaningful assertions;
- fixtures, doubles, and mock verification;
- consolidation and explicit parameterization opportunities;
- test/source coverage gaps when sufficient source scope exists; and
- concise snapshot-review decisions.

It does not prescribe pytest layout, Python file names, Syrupy APIs,
snapshot-update commands, or Plato modes. Normative test policy remains in
`assistants/shared/standards/testing.md`.

### Python type review

The fourth MR adds `review-python-types`. It depends on
`resolve-change-scope` and `discover-project-standards`.

The skill reports:

- missing or weak type contracts;
- implicit controlled mapping shapes;
- appropriate use of `TypedDict`, dataclasses, or validated Pydantic models;
- downstream callers and tests affected by a proposed contract change; and
- the repository-selected verification needed after an approved edit.

The skill is explicitly Python-specific and report-only. It does not prescribe
mypy, `ty`, Pyright, Ruff, strict-mode flags, model configuration, or an
automatic refactoring menu. Normative Python and Pydantic policy remains in the
shared standards library.

`ballen-config` continues to use strict mypy throughout this train. A separate
follow-up may evaluate `ty` by running both checkers, classifying diagnostic and
configuration differences, and changing repository authority only after that
evidence is reviewed.

### Self-review orchestration

The fifth MR adds `conduct-self-review`. It invokes:

- `review-project-standards`;
- `review-project-quality`;
- `review-project-tests`; and
- `review-python-types` when Python changes apply.

The orchestrator resolves scope once and passes the same logical result to
every consumer. It aggregates findings and coverage rather than implementing
another checker. Skipped, unavailable, and inapplicable sections remain visible
and cannot become a clean verdict.

Every self-review attempt that passes artifact preflight writes a Markdown
artifact, including blocked and incomplete results. The default directory is
`.reviews/self-review/`; the caller may instead supply a repository-relative
ignored directory. The destination must be repository-local, ignored,
untracked, and writable. The inline result is a summary and artifact link. If
no safe ignored destination exists, the skill asks for one and writes nothing.
It never changes ignore rules.

The skill records an additive or delegated relationship with native
`verification-before-completion` and code-review skills instead of claiming
their authority.

### Self-review remediation

The sixth MR adds `address-self-review`. It consumes an explicit self-review
artifact and selected finding IDs, requires a complete matching repository
identity, revalidates scope and standards, and applies the smallest sufficient
edits. Explicit invocation authorizes focused edits when the result still
matches; stale, ambiguous, or materially broader work requires a pause.

After editing, the skill runs focused verification and one fresh self-review.
It reports resolved, unresolved, superseded, and blocked findings without
recursively fixing new findings. It does not commit, push, change ignore rules,
or suppress checks without separate approval.

### Foundation exit gate

The train is complete only when:

- catalog, dependency, portability, digest, and native-destination tests pass;
- Git, Jujutsu, and supplied-scope fixtures cover resolved, empty, partial, and
  blocked outcomes;
- blocked or partial scope cannot yield a clean result;
- each completed self-review produces a valid ignored artifact;
- stale review artifacts cannot authorize edits;
- enabled native harnesses prove name-based composition;
- focused and full repository verification passes; and
- `conduct-self-review` and `address-self-review` are dogfooded on bounded real
  `ballen-config` changes.

## Forge Review and Response Train

### Provider-neutral comment plan

The first MR defines the provider-neutral local-review and comment-plan
contract. It owns:

- canonical repository and change identity;
- provider and head revision;
- changed-file and diff references;
- proposed inline and general comments;
- stable deduplication keys;
- intended publication actions;
- per-item validation and outcome state; and
- exact partial-completion reporting.

The contract does not own provider authentication, API payloads, thread
positions, or retry semantics.

### Local draft workspace

Local review is a complete workflow, not merely a staging step for remote
publication. By default, the forge reviewer writes an editable Markdown draft
inside a repository-local workspace that is already ignored.

Before writing, the skill proves that the destination is repository-local,
ignored, and untracked. If no safe ignored destination exists, it asks for one
and writes nothing. It never changes ignore rules automatically. A tracked or
staged review draft is a review finding.

Editing a Markdown draft does not authorize remote publication. The executable
comment plan and the user's publication intent remain separate.

### GitHub review and publication

GitHub is the default first adapter because `ballen-config` provides immediate
dogfooding evidence. The order remains architecturally reversible.

The GitHub work is delivered in three MRs:

1. `review-github-pull-request` in read, analyze, deduplicate, and local-draft
   mode;
2. an explicit publication phase; and
3. `respond-to-github-review`.

The draft reviewer uses `using-github` for provider behavior and standards
discovery for repository rules. It may consume supplied outputs from the
review-foundation skills when a local checkout and complete scope are
available, but remote draft review does not require every local checker.

Immediately before publication, the skill re-fetches and confirms:

- host, repository, and pull request;
- current head revision;
- comment positions and existing threads;
- deduplication keys; and
- the exact payload to post.

The user explicitly approves the current payload. Stale heads, invalid
positions, ambiguity, or duplicate risk block the affected action. Successful
and failed items are reported separately; retries do not silently duplicate
comments.

### GitHub response

`respond-to-github-review` separates:

1. thread retrieval and normalization;
2. feedback evaluation;
3. proposed local changes;
4. approved editing;
5. verification;
6. change description and commit;
7. push; and
8. remote response.

Each mutation boundary requires its own current intent. Feedback evaluation
delegates to native `receiving-code-review` when available and reports missing
coverage when it is not.

### GitLab adapter

After GitHub dogfooding, the train adds:

1. `review-gitlab-merge-request` in local-draft mode;
2. explicit GitLab publication; and
3. `respond-to-gitlab-review`.

The GitLab adapter uses `using-gitlab` and preserves GitLab-native discussion,
position, and partial-failure semantics. It reuses the provider-neutral logical
contracts without translating GitHub payloads into GitLab shapes.

### Forge exit gate

The train is complete only when:

- local review remains fully useful with publication disabled or unavailable;
- local drafts are proven ignored and untracked;
- GitHub dogfooding covers draft creation and an explicitly approved
  publication;
- stale-head, duplicate-comment, invalid-position, and partial-failure fixtures
  pass;
- GitLab behavior is tested through its native adapter contract;
- normalized review threads are available to downstream consumers; and
- no shared source contains credentials, provider-generated state, or
  provider-specific authentication instructions.

## Review-Learning Train

### Repository lesson-ledger contract

The first MR defines one dedicated, tool-neutral, repository-owned lesson
ledger. Repository instructions may declare its location. This umbrella design
does not authorize a fallback path: the focused learning-train design must
select the portable default and creation gate before implementation. Multiple
plausible ledgers are ambiguous and block promotion until the repository
selects one.

The ledger stores concise durable guidance with:

- a descriptive lesson title;
- the durable rule or recommendation;
- enough rationale to apply it correctly;
- minimal source provenance; and
- status when the repository needs to distinguish active and superseded
  guidance.

It does not store full review conversations, authentication, provider payloads,
or transient comment positions. `discover-project-standards` recognizes the
selected ledger as a repository instruction source.

### Lesson extraction

The second MR adds `extract-review-lessons`. It consumes normalized review
threads and the standards-discovery inventory.

It:

- separates reusable guidance from change-specific comments, unanswered
  questions, approvals, nits without durable value, and administration;
- deduplicates candidates against discovered standards and the ledger;
- preserves minimal provenance without copying the source conversation;
- writes proposed lessons into the verified ignored local workspace; and
- requires human selection and editing before promotion.

No reusable lessons is a valid no-op. Missing or incomplete review-thread
coverage is reported separately and cannot be described as a complete
extraction.

### Lesson promotion

The third MR adds `promote-project-lessons`. It converts approved local drafts
into a previewed patch against the dedicated ledger.

Immediately before applying the patch, it:

- re-reads the ledger;
- rechecks exact and semantic duplicates;
- detects concurrent changes;
- confirms the repository-local destination; and
- shows the exact proposed diff.

Promotion requires explicit approval. It modifies only the selected lesson
ledger, never arbitrary instruction files, global agent configuration, or
shared `ballen-config` standards. It runs applicable documentation checks after
the edit and does not commit the change automatically.

### Learning exit gate

The train is complete only when:

- extraction is dogfooded on a real normalized `ballen-config` GitHub review;
- reusable, change-specific, administrative, and duplicate examples are
  classified correctly;
- exact and semantic duplicate handling is tested;
- concurrent ledger changes force re-planning;
- ignored drafts remain untracked;
- an approved fixture lesson is promoted into a ledger;
- standards discovery finds the promoted lesson; and
- the ledger contains no full transcripts, credentials, or provider state.

## Verification Strategy

### Per change

- Run focused tests for the files and contracts changed.
- Run applicable focused lint and type checks.
- Inspect the Jujutsu diff before recording the change.

### Per MR

- Run shared-skill catalog and model tests.
- Run portability, policy, tree-digest, dependency, and native-destination
  checks.
- Run the relevant fixture and content-contract tests.
- Verify the planned native actions without mutating personal native state.

### Per train

- Run the full pytest suite.
- Run strict mypy while it remains repository authority.
- Run pre-commit across the repository.
- Run the repository policy scan.
- Run work-profile bootstrap plan and doctor with matching selections.
- Run enabled-agent invocation smokes.
- Complete the train-specific dogfooding gate before merge.

The first full live verification happens before the train merges. The
post-merge check is a short confirmation smoke.

## Documentation and Delivery

Each train receives a separate focused design and implementation plan. The
implementation plans use descriptive MR and task names rather than temporary
labels. They identify exact Jujutsu bookmarks, files, focused verification, and
train exit commands.

At train start:

1. create and push the intended Jujutsu stack bookmarks;
2. record the writer, current task, and next checkpoint;
3. keep one writer in the shared working copy; and
4. use separate workspaces only for genuinely independent implementation.

Stacked GitHub PRs merge bottom-up. Train-focused designs own the exact remote
preflight, explicit retargeting, rewritten-ancestry recovery, branch deletion,
and bookmark-retirement procedure. The
[review foundation detailed design](2026-07-30-review-foundation-design.md)
defines the first such procedure. No train relies on automatic retargeting or
continues after an unverified base or diff change.

At train completion:

1. complete dogfooding and full verification;
2. merge and confirm local and remote bookmark state;
3. retire workers and remove temporary workspaces; and
4. begin the next train with fresh context.

## Success Criteria

The roadmap is complete when:

- all three trains have approved focused designs and implementation plans;
- the review-foundation skills distinguish complete, empty, partial, blocked,
  skipped, and inapplicable coverage;
- every completed self-review produces an ignored artifact and explicit
  remediation rejects stale results;
- local forge review works without remote publication;
- GitHub and GitLab publication and response honor explicit mutation gates;
- normalized review threads feed the learning workflow;
- approved lessons promote only into one repository-owned ledger;
- every train has current native-harness and dogfooding evidence;
- Plato remains unchanged; and
- excluded authentication, state, paths, and generated content remain outside
  the repository.
