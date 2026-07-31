# Forge Review and Response Detailed Design

## Status

Detailed design and written specification approved on July 30, 2026.
Implementation is governed by the
[forge review and response plan](../plans/2026-07-30-forge-review-response.md).

This document refines the forge review and response train in the
[reusable review workflows roadmap](2026-07-30-reusable-review-workflows-roadmap-design.md).
Its skill boundaries, artifact authority, executable tooling, mutation gates,
delivery order, and exit criteria govern this train.

The review-foundation train was delivered through pull requests 10 through 16.
Its scope, standards, specialist-review, self-review, and remediation contracts
are available inputs to this train without becoming mandatory dependencies for
every remote review.

## Implementation checkpoint

The seven capability changes are implemented as a stacked Jujutsu train. Each
bookmark is an independent MR boundary; the current working copy is empty:

| Capability | Bookmark | Head |
| --- | --- | --- |
| GitHub local draft | `forge-review-github-draft` | `cbdbfeb9` |
| GitHub publication | `forge-review-github-publish` | `567f0759` |
| Response preparation | `forge-review-prepare-response` | `f3c356e8` |
| GitHub response | `forge-review-github-response` | `199cbe5d` |
| GitLab local draft | `forge-review-gitlab-draft` | `c20835c7` |
| GitLab publication | `forge-review-gitlab-publish` | `35102cc6` |
| GitLab response | `forge-review-gitlab-response` | `3ab8ea2d` |

The stable managed source is `assistants/shared/tools/review/`, installed at
`~/.local/share/ballen-config/review-tools/`. Its commands are
`review-plan`, `publish-github-review`, and `publish-gitlab-review`.

Local evidence is complete: the full repository test suite, root mypy, nested
tool mypy, lock validation, launcher syntax, and all pre-commit hooks pass.
GitLab-native contract and transport tests pass. Live GitHub publication or
response and live GitLab writes were intentionally skipped because they require
separate approval of a current safe target; no receipts, drafts, or provider
transcripts are committed.

## Purpose

Promote the reusable behavior in Plato's merge-request review and response
workflows into portable GitHub and GitLab skills. Preserve the deterministic
Markdown parsing and correctly positioned posting provided by Plato's Python
helpers while separating:

1. review analysis from publication;
2. feedback evaluation from remediation;
3. provider-neutral logical contracts from provider-native API payloads; and
4. durable local intent from current authorization to mutate local or remote
   state.

Local review must remain complete and useful when remote publication is
disabled, unavailable, or declined.

## Source Evidence

The design generalizes behavior from:

- `plato/skills/mr-review/SKILL.md`;
- `plato/skills/mr-respond/SKILL.md`;
- `plato/skills/using-gitlab/parse_review.py`;
- `plato/skills/using-gitlab/post_comments.py`; and
- their parser and posting tests.

The source workflows demonstrate useful Markdown review drafts, dry-run
payloads, GitLab diff positioning, general comments, discussion replies, and
per-type posting outcomes. They also combine concerns that this design
separates: GitLab setup, review analysis, persisted `POST: YES` selections,
publication, feedback evaluation, local editing, commits, pushes, and remote
responses.

Implementation must record the exact source revision in each promoted skill's
catalog provenance. This design does not authorize changes to Plato's source
skills or helper scripts.

## Goals

- Provide safe local review drafts for GitHub pull requests and GitLab merge
  requests.
- Define provider-neutral comment-plan, normalized-thread, response-plan, and
  receipt contracts.
- Preserve human-editable Markdown while making parsing and validation
  deterministic.
- Add hardened Python publication tools for GitHub and GitLab.
- Require current, exact approval before every remote publication.
- Separate read-only response preparation from local and remote remediation.
- Preserve GitHub and GitLab native terminology, identities, positions, thread
  behavior, and partial-failure semantics.
- Reuse repository standards and review-foundation outputs when available
  without making remote review depend on every local checker.
- Install one canonical executable toolset for Codex, Claude Code, and Cursor.
- Dogfood the complete GitHub workflow in `ballen-config`.

## Non-Goals

- Change, remove, wrap, or redirect Plato's source skills.
- Copy Plato-specific project IDs, paths, attribution text, setup steps, or
  environment-specific subskills.
- Install or modify `gh`, `glab`, provider applications, MCP servers,
  authentication, credential helpers, tokens, or permissions.
- Persist authentication, trust, sessions, histories, memories, project paths,
  caches, worktrees, or generated plugin state.
- Create one shared Git-forge payload or erase provider-native semantics.
- Require a local checkout for useful remote draft review.
- Publish comments merely because an older draft contains `POST: YES`.
- Automatically edit ignore rules, commit, push, reply, resolve threads, or
  suppress checks.
- Extract or promote review lessons. The review-learning train owns that work.
- Package the skills as a plugin.

## Approved Reslice

The umbrella roadmap originally placed a provider-neutral comment-plan contract
before the first provider workflow and combined response analysis with
remediation. The approved reslice moves one boundary:

- the first GitHub local-draft capability proves the comment-plan contract and
  safe workspace against an immediate consumer; and
- a dedicated provider-neutral `prepare-review-response` capability separates
  thread normalization and feedback evaluation from provider-specific
  remediation.

This preserves the train size while replacing a speculative contract-only
change with a complete read-only vertical slice.

## Architecture

### Ownership layers

The train has five ownership layers:

1. **Canonical shared skills** own workflow, composition, intent gates, and
   user-facing behavior.
2. **Provider-neutral contracts** own logical identities, plans, item states,
   digests, and receipts.
3. **Provider skills** (`using-github` and `using-gitlab`) own provider
   discovery, native terminology, transport selection, and authentication
   boundaries.
4. **Managed review tools** own deterministic parsing, validation, provider
   payload construction, remote-state preflight, posting mechanics, and
   machine-readable outcomes.
5. **Native review capabilities** may evaluate feedback or augment review
   coverage. Shared skills record additive or delegated relationships rather
   than claiming native authority.

No layer may infer authorization from a lower layer's persisted state. A valid
plan is evidence and input, not permission to publish or edit.

### Provider relationship

GitHub is implemented and dogfooded first. GitLab follows as a native adapter to
the same logical contracts.

The providers share:

- repository and change identity concepts;
- logical inline, general, and reply actions;
- stable deduplication keys;
- selection, validation, and outcome states;
- plan digests;
- mutation-gate semantics; and
- receipt requirements.

They do not share:

- API request schemas;
- authentication behavior;
- line-position encodings;
- review-versus-discussion semantics;
- thread resolution behavior;
- retry details; or
- provider-generated identifiers.

GitLab behavior is not implemented by translating GitHub payloads, and GitHub
behavior is not constrained to GitLab's discussion model.

## Artifact Authority

### Safe local workspace

Review drafts, plans, normalized threads, response plans, previews, and receipts
are written only to a user-selected repository-local directory that is already
ignored and untracked.

Before the first write, the skill proves that:

- the destination resolves inside the current repository;
- the destination and proposed file are ignored;
- no destination component escapes through a symlink;
- the proposed file is not tracked, staged, or conflicted; and
- the repository identity matches the current task.

The workflow never adds or edits ignore rules. If no safe destination exists,
it asks the user to select one and writes nothing. A tracked or staged review
artifact is reported as a review finding.

Absolute repository paths are runtime inputs only and are not stored in
canonical content or migrated between machines.

### Human draft and logical plan

The human-editable Markdown draft is the source of proposed text and item
selection. A deterministic parser converts the current draft into a validated
logical plan.

The logical plan records:

- schema version;
- provider, host, repository, and change identity;
- base and head identity required by the provider;
- source-draft digest;
- proposed inline, general, and reply actions;
- logical file and line locations;
- stable deduplication keys;
- selected or skipped state;
- validation state and reason;
- intended provider action; and
- per-item outcome state.

The plan does not persist an exact provider API payload. Provider-specific
payloads are generated ephemerally after remote-state preflight.

`POST: YES`, a selected item, or a valid plan means "candidate for the next
preview." It never means "authorized to publish."

### Publication preview and approval binding

A publication preview binds:

- the logical plan digest;
- the current provider identity;
- the current head revision;
- current comment or thread observations;
- deduplication results; and
- the exact ephemeral payloads that would be sent.

The user approves that current preview. Execution requires both the approved
plan digest and expected head revision. Any mismatch invalidates the approval
and returns to preview.

### Publication receipt

Every attempted publication produces a minimal ignored receipt containing:

- plan and preview digests;
- provider and change identity;
- expected and observed head revisions;
- action ID and deduplication key;
- `posted`, `failed`, `blocked`, `duplicate`, `skipped`, or `not-attempted`
  outcome;
- minimal remote identifier or URL when successful; and
- a bounded diagnostic when unsuccessful.

Receipts do not retain credentials, request headers, complete API responses, or
full provider payloads.

### Normalized review threads

`prepare-review-response` consumes provider-native review threads and produces
a normalized thread set. Each logical thread preserves:

- provider and change identity;
- native thread and comment identifiers;
- open, resolved, outdated, or unknown state;
- logical location when available;
- author and chronology needed for evaluation;
- text required to understand the feedback;
- current head revision; and
- any coverage or normalization limitation.

Full thread text may exist in the ignored local artifact while the response is
being prepared. It never enters canonical `ballen-config` content and is not a
durable lesson artifact.

### Response plan

The response plan classifies each thread as:

- actionable;
- question;
- discussion;
- resolved; or
- informational.

For each retained thread, it records the evaluation, proposed local changes,
proposed response, verification needed, selected action, and current provider
target. Resolved and informational threads remain visible as skipped evidence
instead of disappearing.

The response plan is read-only evidence. It cannot authorize edits, commits,
pushes, replies, or thread resolution.

## Managed Executable Toolset

### Canonical source and installation

The executable source lives in one canonical tree under
`assistants/shared/tools/review/` and is installed as a managed tree at:

`~/.local/share/ballen-config/review-tools/`

The toolset is a locked Python 3.12 `uv` project with Pydantic v2 models,
Google-style docstrings, and pytest fixtures. It includes its lockfile and does
not depend on a checkout-specific path after installation.

The bootstrap:

- plans the tool-tree copy before mutation;
- rejects source or destination symlink escapes;
- preserves reviewed executable modes;
- records the managed-tree digest;
- backs up a previously managed destination before replacement;
- rejects an unmanaged destination collision; and
- reports drift through doctor.

This is a narrow extension of the existing managed shared-hook pattern. It does
not create a general plugin or arbitrary executable-installation subsystem.

### Commands

The toolset exposes three commands:

1. `review-plan`
   - parses review and response Markdown;
   - validates provider-neutral artifact models;
   - retains selected and unselected items;
   - computes source and plan digests;
   - validates receipts; and
   - never performs a remote write.
2. `publish-github-review`
   - fetches current GitHub PR state;
   - validates commit-pinned inline locations and existing comments;
   - constructs GitHub-native previews;
   - posts approved review comments, general comments, or replies; and
   - emits per-item outcomes and a receipt.
3. `publish-gitlab-review`
   - fetches current GitLab MR state and diff references;
   - validates discussion targets and positioned comments;
   - constructs GitLab-native previews;
   - posts approved discussions, notes, or replies; and
   - emits per-item outcomes and a receipt.

The publication commands share validated logical models but implement separate
provider modules and payload models.

### Transport selection

`using-github` and `using-gitlab` remain responsible for selecting an available
provider transport.

When `gh` or `glab` is available, the provider command may execute through that
CLI using argument arrays and standard input rather than shell interpolation.
The tools inherit existing authentication and never inspect, print, install, or
modify credentials.

When a connected provider tool is available but the CLI is not, `review-plan`
still provides deterministic validation and payload evidence. The provider
skill may perform the approved write through the connected tool and then
validate the normalized receipt. If no supported mutation transport exists,
local review remains complete and publication reports a blocked capability.

### Dry run and execution

Dry run may perform read-only provider requests but has no remote mutation. It
prints or writes the exact preview, current head, deduplication observations,
and plan digest.

Mutation requires an explicit execution mode plus:

- approved plan digest;
- expected head revision; and
- canonical provider/change identity.

Execution re-fetches remote state. A changed head, changed target, invalid
position, ambiguous thread, or duplicate invalidates the affected action before
posting.

The command never converts an old `POST: YES` selection directly into a remote
write.

### GitHub mechanics

The GitHub implementation:

- uses the current head commit explicitly;
- prefers `line`, `side`, `start_line`, and `start_side` for inline ranges;
- may batch compatible inline comments into one GitHub review;
- keeps review comments, top-level conversation comments, and replies distinct;
- compares existing review comments and threads before posting;
- preserves GitHub review states without inventing GitLab discussions; and
- reports secondary rate limits and validation failures without automatic
  reposting.

The implementation must verify the current GitHub REST contract during its
delivery change. The design references:

- [REST API endpoints for pull request reviews](https://docs.github.com/en/rest/pulls/reviews)
- [REST API endpoints for pull request review comments](https://docs.github.com/en/rest/pulls/comments)

### GitLab mechanics

The GitLab implementation preserves the useful behavior of Plato's helpers
while replacing repository-specific assumptions. It:

- fetches current `base_sha`, `head_sha`, and `start_sha`;
- constructs GitLab text positions;
- distinguishes inline discussions, general notes, and discussion replies;
- preserves full native discussion IDs;
- validates current MR and diff identity before posting;
- records successes and failures independently; and
- does not silently retry successful actions.

The implementation must verify the current
[GitLab Discussions API](https://docs.gitlab.com/api/discussions/) during its
delivery change.

## User-Facing Skills

### `review-github-pull-request`

Read, analyze, deduplicate, and produce the local Markdown draft and logical
comment plan. It:

- uses `using-github` for provider reads and terminology;
- uses `discover-project-standards` for repository rules;
- may consume supplied review-foundation artifacts when a complete matching
  local scope is available;
- records missing local coverage instead of claiming it ran; and
- performs no remote write.

This capability proves the comment-plan contract, safe workspace, parser, and
managed tool installation against one complete vertical slice.

### `publish-github-review`

Consume the current draft and logical plan, run GitHub preflight, show the exact
preview, obtain approval, publish selected actions, and write a receipt.

It depends on `review-github-pull-request` and `using-github`. It cannot analyze
new findings, edit the source draft, or treat previous selection as approval.

### `prepare-review-response`

Retrieve or consume normalized provider threads, evaluate feedback, and produce
an ignored response plan. It:

- is provider-neutral at the logical contract layer;
- preserves provider identity and normalization limitations;
- delegates feedback evaluation to native `receiving-code-review` when
  available;
- reports missing native coverage when unavailable;
- proposes but does not apply local changes; and
- performs no commit, push, reply, resolution, or other mutation.

Provider-thread collection may be supplied by `using-github`, `using-gitlab`,
or an already validated normalized artifact. Those provider capabilities are
runtime alternatives, not simultaneous hard dependencies.

### `respond-to-github-review`

Consume an approved response plan and revalidate the GitHub PR, local scope,
standards, and selected threads. It separates:

1. authorization for selected local edits;
2. focused verification;
3. authorization for a change description and commit;
4. authorization for push; and
5. authorization for exact remote replies or status comments.

A reply may claim work is complete only when the referenced change is verified
and, when relevant, present on the expected remote head.

### `review-gitlab-merge-request`

Provide the GitLab-native local-draft review adapter. It reuses logical plan and
workspace contracts while preserving merge-request vocabulary, discussions,
diff references, and position semantics.

It depends on `using-gitlab` and `discover-project-standards`, not on a GitHub
skill.

### `publish-gitlab-review`

Revalidate and publish selected GitLab discussions, notes, and replies through
the GitLab publication tool or another approved GitLab transport. It consumes
the shared logical plan without translating a GitHub payload.

### `respond-to-gitlab-review`

Consume an approved response plan and apply the same explicit local mutation
gates as the GitHub responder while preserving GitLab discussion IDs,
resolution state, positions, and partial-failure semantics.

## End-to-End Flows

### Review and publication

1. Resolve canonical provider, repository, change, and current head identity.
2. Fetch metadata, diff, existing comments, and available local evidence.
3. Analyze and deduplicate findings.
4. Write the ignored Markdown draft.
5. Parse and validate the logical plan.
6. Let the user edit findings and select candidate actions.
7. Re-parse the current draft and compute a new plan digest.
8. Run provider preflight and generate the exact preview.
9. Obtain approval for that preview.
10. Re-fetch remote state and compare the approved identity and digest.
11. Post eligible actions independently or in a provider-native atomic group.
12. Write and report the normalized receipt.

Editing the draft or changing the remote head after step 8 returns the workflow
to preview.

### Response preparation and remediation

1. Resolve provider, repository, change, and current head identity.
2. Fetch current provider-native review threads.
3. Normalize threads while preserving provider IDs and limitations.
4. Classify feedback and evaluate technical validity.
5. Produce the ignored response plan.
6. Let the user select, edit, defer, or reject proposed actions.
7. Invoke the provider-specific responder with the selected plan.
8. Revalidate remote threads, local scope, and applicable standards.
9. Obtain approval for selected local edits.
10. Apply edits and run focused verification.
11. Obtain separate approval before commit and before push.
12. Re-fetch remote threads and build exact response payloads.
13. Obtain approval for the current remote response preview.
14. Post replies and write the normalized receipt.

Questions and discussions may produce reply-only actions. Actionable feedback
normally requires a verified change before a completion reply. Resolved and
informational threads are retained as skipped evidence.

## Failure and Retry Semantics

Failures are action-specific unless canonical identity or artifact integrity is
invalid for the entire plan.

The whole operation blocks when:

- provider, repository, or change identity is ambiguous;
- the plan or source-draft digest is invalid;
- the safe local workspace cannot be proven;
- authentication or permission is unavailable for the requested mutation; or
- the execution target differs from the approved preview.

An individual action blocks when:

- its head or position is stale;
- its thread target no longer exists or is ambiguous;
- its deduplication key matches an existing comment;
- its provider payload cannot be validated; or
- a prerequisite local change or verification result is absent.

Partial publication records each success, failure, blocked action, duplicate,
and unattempted action. Retry:

1. consumes the previous receipt;
2. re-fetches all relevant remote state;
3. excludes confirmed successes and duplicates;
4. rebuilds failed or blocked previews against the current head; and
5. requires new approval.

No automatic retry may silently repost a successful action.

## Delivery Sequence

The train uses one planning change followed by seven capability changes:

1. **Focused design and implementation plan**
   - approve this design;
   - write the executable implementation plan;
   - prove the stacked-delivery and dogfooding procedure.
2. **GitHub local-draft vertical slice**
   - add `review-github-pull-request`;
   - add comment-plan and workspace contracts;
   - add the managed review-tool tree and `review-plan`;
   - add parser, model, installer, and doctor tests.
3. **GitHub publication**
   - add `publish-github-review`;
   - add the GitHub publication command;
   - prove preview, digest binding, deduplication, stale-head, and receipt
     behavior.
4. **Provider-neutral response preparation**
   - add `prepare-review-response`;
   - add normalized-thread and response-plan contracts;
   - prove read-only evaluation and native delegation.
5. **GitHub response**
   - add `respond-to-github-review`;
   - prove separate edit, commit, push, and reply gates;
   - dogfood a controlled GitHub response.
6. **GitLab local-draft adapter**
   - add `review-gitlab-merge-request`;
   - prove GitLab-native read and normalization behavior;
   - reuse logical contracts without a GitHub dependency.
7. **GitLab publication**
   - add `publish-gitlab-review`;
   - port and harden Plato's useful parser/poster behavior;
   - prove diff-reference, discussion, reply, and partial-outcome handling.
8. **GitLab response**
   - add `respond-to-gitlab-review`;
   - prove GitLab-native response and retry semantics;
   - complete the train exit gate.

Each capability change is independently reviewable. Contracts are introduced
with the first capability that proves them, not in a separate global contract
workstream.

## Verification Strategy

### Per capability change

- Write failing contract or behavior tests before implementation.
- Run focused Python and skill-model tests.
- Run shared-skill catalog, dependency, portability, and digest tests.
- Run native Codex, Claude Code, and Cursor projection tests.
- Run focused Markdown lint for changed documentation.
- Run repository pre-commit checks before claiming completion.

### Artifact and tool fixtures

Fixtures cover:

- valid inline, general, and reply actions;
- selected and unselected Markdown items;
- malformed or incomplete metadata;
- invalid and stale plan digests;
- safe, unsafe, tracked, and unignored workspaces;
- current and stale heads;
- valid and invalid GitHub line ranges;
- valid and invalid GitLab diff references;
- open, resolved, outdated, and missing threads;
- duplicate comments;
- permission and authentication failures;
- provider validation errors;
- complete, blocked, and partial publication;
- retry after partial publication; and
- receipt validation.

Tests mock provider transports and assert exact argument arrays and payloads.
They never require credentials or live writes.

### Managed-tool verification

- Validate the locked Python 3.12 environment.
- Run tool unit and CLI tests.
- Prove dry run performs no mutation.
- Prove the installed shared tree matches its canonical digest.
- Prove each selected agent's skills reference the same stable managed path.
- Prove mode, digest, collision, backup, idempotency, and doctor behavior.
- Prove no source or installed artifact contains prohibited state.

### Train dogfooding

Before the train merges:

- run the full repository test suite and pre-commit checks;
- run work-profile bootstrap plan and doctor with matching selections;
- create a real ignored GitHub review draft for a bounded `ballen-config` pull
  request;
- publish an explicitly approved controlled review;
- prepare and apply an explicitly approved controlled response;
- rerun after a simulated partial failure and prove no duplicate publication;
- verify all local artifacts remain ignored and untracked; and
- confirm the installed skills and tools operate from Codex, Claude Code, and
  Cursor by canonical name and stable managed path.

GitLab receives native contract and transport tests. A live GitLab write is
optional and requires a separately approved safe target.

The first full live verification occurs before train merge. Post-merge
verification is a bounded smoke check.

## Documentation

The planning and capability changes update:

- the shared skill catalog;
- skill promotion and provenance guidance;
- work-profile bootstrap and doctor documentation;
- the reusable review workflows roadmap;
- user-facing skill navigation; and
- executable review-tool usage and safety guidance.

Documentation distinguishes local selection, validated preview, current
approval, attempted publication, and successful remote outcome.

## Success Criteria

The train is complete when:

- all seven user-facing skills are installed and discoverable for Codex, Claude
  Code, and Cursor;
- local GitHub and GitLab review remains useful without publication;
- every local artifact destination is proven ignored and untracked;
- Markdown parsing and plan validation are deterministic;
- no persisted selection independently authorizes a write;
- GitHub and GitLab publication tools revalidate current remote state;
- stale heads, duplicate comments, invalid positions, and partial failures have
  passing fixtures;
- retries cannot duplicate confirmed successful actions;
- response preparation is read-only and remediation requires explicit,
  separate mutation intent;
- GitHub dogfooding covers draft, publication, preparation, and response;
- GitLab-native behavior passes its adapter contract;
- bootstrap, doctor, catalog, native projection, full tests, and pre-commit
  verification pass; and
- canonical sources contain no credentials, authentication configuration,
  provider-generated state, machine-specific project paths, or full review
  transcripts.
