# Forge Review and Response Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking. When delegating, use Luna with
> extra-high reasoning for every worker and reviewer subagent.

**Goal:** Deliver seven portable skills and one managed Python toolset for
local GitHub and GitLab review, explicitly approved publication, and separately
authorized review-response workflows.

**Architecture:** Shared skills own intent, artifact contracts, and mutation
gates. `using-github` and `using-gitlab` own provider-native terminology and
transport selection. A locked Python 3.12 project under
`assistants/shared/tools/review/` deterministically parses and validates local
artifacts, constructs provider payloads, performs guarded publication, and
emits minimal receipts. Bootstrap installs that source once as a managed tree;
agent-native skill projections all reference the same stable installation.

**Tech Stack:** Python 3.12, Pydantic v2, `uv`, pytest, Markdown/YAML/JSON,
GitHub REST API, GitLab Discussions API, existing `ManagedTreeSpec`, Jujutsu,
and repository pre-commit hooks.

---

## Delivery Contract

### Approved sources

Implement against:

- [forge review and response detailed design](../specs/2026-07-30-forge-review-response-design.md);
- [reusable review workflows roadmap](../specs/2026-07-30-reusable-review-workflows-roadmap-design.md);
- the `ballen-config` planning baseline ending at change
  `optvutnnssktlkqvqvwnykwwxwqrsqmr`, commit
  `6141a587b7b8ed44fb537e3cdae0cf1fc3aec836`; and
- the audited Plato source revision
  `5f78cc607ad100c72f6e173bc22620bcebd6c855`.

Plato is evidence, not an installation source. From the pinned Plato repository
root, read these exact source files when implementing the GitLab adapter:

```text
skills/mr-review/SKILL.md
skills/mr-respond/SKILL.md
skills/using-gitlab/parse_review.py
skills/using-gitlab/post_comments.py
```

Retain the useful parsing, dry-run, diff-reference, inline/general/reply, and
per-item outcome behavior. Remove repository assumptions and the rule that an
old `POST: YES` value can authorize publication.

### Non-negotiable boundaries

- [ ] Start each capability task read-only and use
      `superpowers:writing-skills` for user-facing skill changes.
- [ ] Add failing tests before production code or skill prose.
- [ ] Use `rtk` for every shell command and Jujutsu for all repository state.
- [ ] Never add, edit, or stage an ignore rule for review artifacts.
- [ ] Never persist credentials, request headers, authentication
      configuration, trust, sessions, generated plugin state, raw API
      responses, machine-specific project paths, or complete provider
      transcripts.
- [ ] Treat a selected item as a candidate for preview only.
- [ ] Require a current approved plan digest and expected head for every remote
      write.
- [ ] Require separate authorization for local edits, commit, push, and remote
      reply in response workflows.
- [ ] Stop when the provider identity, target, head, position, thread, or
      deduplication observation no longer matches the approved preview.
- [ ] Record partial outcomes item by item and never retry a confirmed success.
- [ ] Make local review useful when no mutation-capable provider transport is
      available.

### Canonical artifacts

Use strict, frozen Pydantic v2 models with `extra="forbid"`. The normative
contract names are:

```text
review-comment-plan/v1
publication-preview/v1
publication-receipt/v1
normalized-review-threads/v1
review-response-plan/v1
```

The logical review action model must retain:

```python
class ReviewAction(BaseModel):
    """One retained review candidate, including skipped evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action_id: str
    kind: Literal["inline", "general", "reply"]
    selected: bool
    body: str
    path: PurePosixPath | None = None
    line: int | None = None
    side: Literal["LEFT", "RIGHT"] | None = None
    start_line: int | None = None
    start_side: Literal["LEFT", "RIGHT"] | None = None
    thread_id: str | None = None
    deduplication_key: str
    validation_state: Literal["valid", "invalid", "stale", "duplicate"]
    validation_reason: str | None = None
    intended_action: Literal["create-inline", "create-general", "reply"]
    outcome: Literal[
        "pending",
        "posted",
        "failed",
        "blocked",
        "duplicate",
        "skipped",
        "not-attempted",
    ]
```

Add model validators so inline actions require a safe relative path and line,
reply actions require a native thread target, and general actions reject both.
No artifact field may represent publication authorization.

Compute:

- source-draft SHA-256 over the exact current UTF-8 file bytes;
- logical artifact digests over NFC-normalized canonical JSON with sorted keys,
  compact separators, and a final newline;
- deduplication keys over provider identity, action kind, target, normalized
  body, and current logical location; and
- preview digests over the plan digest, observed remote state, expected head,
  and exact ephemeral payloads.

Artifact paths are repository-relative POSIX paths. Absolute repository paths
are runtime-only arguments.

### Markdown grammar

Keep the familiar Plato metadata while making IDs and validation explicit:

```markdown
### R001: Reject unsafe destination

**Type:** inline
**File:** src/ballen_config/configure.py
**Line:** 294
**Side:** RIGHT
**Start line:** 289
**Start side:** RIGHT
**Discussion:** none
**POST:** YES

The destination is validated after mutation. Move this check into preflight.
```

The parser must:

- recognize only level-three action headings outside fenced code blocks;
- require a unique stable action ID;
- accept `inline`, `general`, and `reply`;
- reject duplicate, unknown, or kind-incompatible metadata;
- retain both `POST: YES` and `POST: NO` items;
- preserve body Markdown after metadata;
- normalize metadata keys without rewriting body text; and
- report every malformed item instead of silently dropping it.

Response drafts use the same stable-heading rule with `Thread`,
`Classification`, `Selected action`, `Verification`, and `Response` fields.
Resolved and informational items remain in the generated response plan as
skipped evidence.

### Managed command surface

The final installed paths are:

```text
~/.local/share/ballen-config/review-tools/bin/review-plan
~/.local/share/ballen-config/review-tools/bin/publish-github-review
~/.local/share/ballen-config/review-tools/bin/publish-gitlab-review
```

Each launcher derives its own managed project root. It sets
`UV_PROJECT_ENVIRONMENT` under
`${XDG_CACHE_HOME:-$HOME/.cache}/ballen-config/review-tools` and executes its
locked console entry point with `uv run --frozen --project`. It must not create
a virtual environment inside the managed tree.

Use subprocess argument arrays and standard input. Never use `shell=True`,
interpolate an API payload into a shell command, inspect authentication state,
or echo provider output containing secrets.

`using-github` and `using-gitlab` select the available transport. When `gh` or
`glab` is available, the matching publication command may execute the reviewed
argument arrays. When only a connected provider tool is available, the managed
tool emits and validates the exact request bundle, the provider skill performs
the separately approved write, and `review-plan validate` checks the normalized
receipt. When neither mutation transport is available, dry run and local review
remain complete while publication reports a blocked capability.

Every capability task that changes `ballen_review_tools` runs both its focused
pytest files and:

```text
rtk uv run --project assistants/shared/tools/review --frozen mypy \
  --config-file assistants/shared/tools/review/pyproject.toml \
  -p ballen_review_tools
```

### Stack topology

Land one planning PR, then create this Jujutsu stack:

```text
main
└── forge-review-github-draft
    └── forge-review-github-publish
        └── forge-review-prepare-response
            └── forge-review-github-response
                └── forge-review-gitlab-draft
                    └── forge-review-gitlab-publish
                        └── forge-review-gitlab-response
```

Every capability PR targets `main`. Merge bottom-up with merge commits, fetch
after each merge, and explicitly inspect the next PR base and diff. Do not
publish, retarget, or merge without the user's authorization.

## Task 0: Land the Planning Baseline

**Bookmark:** `forge-review-response-planning`

**Commit and PR title:** `docs: plan forge review and response`

**PR base:** `main`

- [ ] **Step 0.1: Verify the planning-only diff**

```text
rtk jj status
rtk jj diff --from main@origin --name-only
rtk jj diff --from main@origin
```

Expected changed files:

```text
docs/superpowers/plans/2026-07-30-forge-review-response.md
docs/superpowers/specs/2026-07-30-forge-review-response-design.md
docs/superpowers/specs/2026-07-30-reusable-review-workflows-roadmap-design.md
```

- [ ] **Step 0.2: Run the planning gate**

```text
rtk uv run --frozen pre-commit run --files \
  docs/superpowers/plans/2026-07-30-forge-review-response.md \
  docs/superpowers/specs/2026-07-30-forge-review-response-design.md \
  docs/superpowers/specs/2026-07-30-reusable-review-workflows-roadmap-design.md
rtk uv run --frozen pytest -q
rtk uv run --frozen pre-commit run --all-files
```

Expected: all focused hooks, the full test suite, and all repository hooks pass.

- [ ] **Step 0.3: Verify the remote delivery policy read-only**

Inspect repository merge methods, branch protection, required checks, and any
merge queue with read-only `rtk gh` commands. Confirm merge commits remain
available because the stack procedure depends on preserving each head commit.
Stop and revise the merge procedure if current policy cannot preserve that
ancestry.

- [ ] **Step 0.4: Publish and merge the planning PR**

After explicit authorization:

```text
rtk jj describe -m 'docs: plan forge review and response'
rtk jj bookmark create forge-review-response-planning -r @
rtk jj git push --remote origin --bookmark forge-review-response-planning
rtk gh pr create --base main --head forge-review-response-planning \
  --title 'docs: plan forge review and response' \
  --body 'Approved detailed design and executable plan for the seven-change forge review and response train.'
rtk gh pr view forge-review-response-planning \
  --json baseRefName,headRefName,headRefOid,commits,files,statusCheckRollup,reviewDecision
rtk gh pr checks forge-review-response-planning
```

Merge only after checks and review pass:

```text
rtk gh pr merge forge-review-response-planning --merge
rtk jj git fetch
rtk jj new main@origin
rtk jj status
```

Expected: an empty working copy directly above the merged planning baseline.

## Task 1: PR 1 — GitHub Local-Draft Vertical Slice

**Bookmark:** `forge-review-github-draft`

**Commit and PR title:** `feat: add GitHub pull-request review drafting`

**PR base:** `main`

### Required behavior

This change proves one complete, non-mutating slice:

- `review-github-pull-request` reads a PR through `using-github`, discovers
  repository standards, and writes a Markdown draft plus logical plan;
- a safe-workspace preflight proves the destination is inside the repository,
  ignored, untracked, unstaged, unconflicted, and symlink-free;
- `review-plan` deterministically parses all selected and unselected items;
- the managed Python tree is planned, copied, diagnosed, and shared by all
  enabled agents; and
- no remote mutation path exists in this change.

### Files

Create:

```text
assistants/shared/skills/review-github-pull-request/SKILL.md
assistants/shared/tools/review/README.md
assistants/shared/tools/review/bin/review-plan
assistants/shared/tools/review/contracts/review-comment-plan-v1.md
assistants/shared/tools/review/contracts/review-comment-plan.example.json
assistants/shared/tools/review/contracts/review-comment-plan-vectors.json
assistants/shared/tools/review/pyproject.toml
assistants/shared/tools/review/uv.lock
assistants/shared/tools/review/src/ballen_review_tools/__init__.py
assistants/shared/tools/review/src/ballen_review_tools/canonical.py
assistants/shared/tools/review/src/ballen_review_tools/markdown.py
assistants/shared/tools/review/src/ballen_review_tools/models.py
assistants/shared/tools/review/src/ballen_review_tools/plan_cli.py
assistants/shared/tools/review/src/ballen_review_tools/workspace.py
src/ballen_config/assistants/review_tools.py
tests/assistants/review_tools/__init__.py
tests/assistants/review_tools/conftest.py
tests/assistants/review_tools/test_canonical.py
tests/assistants/review_tools/test_markdown.py
tests/assistants/review_tools/test_models.py
tests/assistants/review_tools/test_plan_cli.py
tests/assistants/review_tools/test_workspace.py
tests/assistants/test_review_tools_installation.py
```

Modify:

```text
assistants/shared/skills/catalog.yaml
assistants/shared/skills/using-github/SKILL.md
pyproject.toml
src/ballen_config/assistants/orchestrator.py
tests/assistants/test_integration.py
tests/assistants/test_review_contracts.py
tests/assistants/test_skills.py
```

- [ ] **Step 1.1: Write failing artifact-model and canonical-digest tests**

Add tests that instantiate valid inline, general, and reply actions; reject
unsafe paths and incompatible fields; retain skipped actions; reject extra
keys; and reproduce known canonical vectors.

```python
def test_selected_action_is_candidate_not_authority() -> None:
    """Keep selection in the plan without creating an approval field."""
    action = review_action(selected=True)

    assert action.selected is True
    assert "approved" not in type(action).model_fields
    assert "authorized" not in type(action).model_fields


def test_canonical_digest_matches_checked_in_vector(
    canonical_vector: CanonicalVector,
) -> None:
    """Keep plan digests stable across key and construction order."""
    assert canonical_digest(canonical_vector.payload) == canonical_vector.sha256
```

Run:

```text
rtk uv run --frozen pytest \
  tests/assistants/review_tools/test_models.py \
  tests/assistants/review_tools/test_canonical.py -q
```

Expected: collection fails because `ballen_review_tools` does not exist.

- [ ] **Step 1.2: Implement the locked project and strict logical models**

Add a standalone `pyproject.toml` with:

```toml
[project]
name = "ballen-review-tools"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
dependencies = ["pydantic==2.8.*"]

[project.scripts]
review-plan = "ballen_review_tools.plan_cli:main"

[dependency-groups]
dev = [
  "mypy>=1.11",
  "pytest>=8.3,<9.0",
]

[tool.mypy]
python_version = "3.12"
strict = true
```

Use Hatchling and package `src/ballen_review_tools`. Add
`pythonpath = ["src", "assistants/shared/tools/review/src"]` to the root pytest
configuration so the full repository suite executes tool tests. Generate the
lockfile:

```text
rtk uv lock --project assistants/shared/tools/review
```

Implement the models and canonical functions from the delivery contract.
Expose only reviewed public types from `__init__.py`.

- [ ] **Step 1.3: Write failing Markdown parser tests**

Cover all valid kinds, selected and unselected items, fenced headings, Unicode,
CRLF, missing IDs, duplicate IDs, duplicate metadata, unknown metadata,
malformed line numbers, invalid ranges, and body preservation.

```python
def test_parser_retains_unselected_items(review_markdown: str) -> None:
    """Keep skipped evidence in the logical plan."""
    actions = parse_review_markdown(review_markdown)

    assert [action.action_id for action in actions] == ["R001", "R002"]
    assert [action.selected for action in actions] == [True, False]


def test_heading_inside_fence_does_not_start_action() -> None:
    """Do not split a comment body on fenced example Markdown."""
    actions = parse_review_markdown(FENCED_HEADING_DRAFT)

    assert len(actions) == 1
    assert "### R999" in actions[0].body
```

Run the focused file and confirm it fails on the unimplemented parser.

- [ ] **Step 1.4: Implement deterministic parsing and `review-plan`**

Use a small line-state parser rather than a permissive Markdown AST. Add these
non-mutating subcommands:

```text
review-plan workspace-check --repo-root PATH --destination PATH
review-plan compile-review --draft PATH --identity PATH --output PATH
review-plan validate --artifact PATH
review-plan digest --artifact PATH
```

`compile-review` must validate the workspace before writing, read the current
draft once, preserve all items, and atomically replace only the requested
ignored output. It must never fetch a provider or perform a remote write.

- [ ] **Step 1.5: Write failing safe-workspace tests**

Use temporary Git repositories to prove:

- an ignored, untracked directory inside the repository is accepted;
- a tracked, staged, conflicted, unignored, outside-root, or symlinked target
  is rejected before writing;
- the tool never edits `.gitignore`; and
- persisted JSON contains relative paths but not the temporary absolute root.

The workspace implementation may call `git` with fixed argument arrays. When
the repository cannot provide authoritative ignore and tracking checks, return
a blocked result rather than guessing.

- [ ] **Step 1.6: Implement the managed-tree contribution test-first**

Add tests for no enabled agents, each single agent, all agents, exact source and
destination, expected digest, executable mode preservation, unmanaged
collision, idempotency, backup, drift, and doctor reporting.

Implement:

```python
_SUPPORTED_AGENTS = frozenset({"cursor", "claude-code", "codex"})


def review_tools_contribution(
    *,
    repo_root: Path,
    enabled: frozenset[str],
) -> ConfigurationContribution:
    """Install the shared review tool tree for any supported agent."""
    if not enabled.intersection(_SUPPORTED_AGENTS):
        return ConfigurationContribution()
    source = repo_root / "assistants/shared/tools/review"
    return ConfigurationContribution(
        specs=(
            ManagedTreeSpec(
                id="shared-review-tools",
                source=source,
                destination=Path(
                    ".local/share/ballen-config/review-tools"
                ),
                component="shared",
                expected_source_digest=digest_tree(source),
            ),
        )
    )
```

Merge this contribution beside hooks and skills in
`AssistantOrchestrator.configuration()`. Reuse the existing managed-tree engine
and generic doctor; do not add a second copier or review-tool-specific drift
framework.

The launcher must be executable and use its stable installed location:

```sh
#!/bin/sh
set -eu
tool_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
cache_root=${XDG_CACHE_HOME:-"$HOME/.cache"}
export UV_PROJECT_ENVIRONMENT="$cache_root/ballen-config/review-tools"
exec uv run --frozen --project "$tool_root" review-plan "$@"
```

Set only the launcher executable bit:

```text
rtk chmod 700 assistants/shared/tools/review/bin/review-plan
```

- [ ] **Step 1.7: Write the GitHub local-review skill**

The skill must begin read-only, invoke `using-github`, discover standards,
identify a user-selected safe ignored workspace, describe coverage, and produce
the draft and plan. It must explicitly say that:

- no publication occurs;
- incomplete supplied review artifacts are reported as missing coverage;
- `POST: YES` is selection for preview only; and
- no ignore rule is created or changed.

Add this exact catalog relationship:

```yaml
  - name: review-github-pull-request
    source: assistants/shared/skills/review-github-pull-request
    targets: [cursor, claude-code, codex]
    profiles: [default]
    dependencies: [using-github, discover-project-standards]
    provenance: >-
      Authored for ballen-config under the approved forge review and response
      design; Plato review workflows at commit
      5f78cc607ad100c72f6e173bc22620bcebd6c855 informed the local draft.
    portability_status: reviewed-generic
```

Update `using-github` with provider-read ownership, GitHub vocabulary, and the
stable `review-plan` path. It must not claim ownership of the shared artifact
contract.

- [ ] **Step 1.8: Make the focused slice pass**

```text
rtk uv run --project assistants/shared/tools/review --frozen pytest \
  tests/assistants/review_tools -q
rtk uv run --frozen pytest \
  tests/assistants/review_tools \
  tests/assistants/test_review_tools_installation.py \
  tests/assistants/test_review_contracts.py \
  tests/assistants/test_skills.py \
  tests/assistants/test_integration.py -q
rtk uv run --frozen pre-commit run --files \
  assistants/shared/skills/review-github-pull-request/SKILL.md \
  assistants/shared/skills/using-github/SKILL.md \
  assistants/shared/skills/catalog.yaml \
  assistants/shared/tools/review/README.md \
  assistants/shared/tools/review/contracts/review-comment-plan-v1.md
```

Expected: nested locked-environment tests and root integration tests pass; the
catalog installs the new skill for all three agents; the managed tree converges
without generated files inside it.

- [ ] **Step 1.9: Commit and open the PR**

```text
rtk jj status
rtk jj diff --summary
rtk jj describe -m 'feat: add GitHub pull-request review drafting'
rtk jj bookmark create forge-review-github-draft -r @
rtk jj new
```

After authorization, push the bookmark and create the PR against `main`. Its
description must state that the change has no remote mutation path and must
include the focused command results.

## Task 2: PR 2 — GitHub Publication

**Bookmark:** `forge-review-github-publish`

**Commit and PR title:** `feat: add GitHub review publication`

**PR base:** `main`

### Required behavior

`publish-github-review` consumes an existing draft and logical plan. Its default
mode performs read-only remote preflight and emits the exact current preview.
Execution requires `--execute`, the approved logical plan digest, and expected
head. It re-fetches the PR and comments, invalidates stale or duplicate actions,
posts only still-valid actions, and emits a minimal itemized receipt.

The provider layer keeps these GitHub actions distinct:

- compatible inline comments batched into a pull-request review;
- top-level conversation comments posted through the issue-comments endpoint;
  and
- replies posted through the review-comment reply endpoint.

### Files

Create:

```text
assistants/shared/skills/publish-github-review/SKILL.md
assistants/shared/tools/review/bin/publish-github-review
assistants/shared/tools/review/contracts/publication-preview-v1.md
assistants/shared/tools/review/contracts/publication-preview.example.json
assistants/shared/tools/review/contracts/publication-receipt-v1.md
assistants/shared/tools/review/contracts/publication-receipt.example.json
assistants/shared/tools/review/contracts/publication-vectors.json
assistants/shared/tools/review/src/ballen_review_tools/github_cli.py
assistants/shared/tools/review/src/ballen_review_tools/providers/__init__.py
assistants/shared/tools/review/src/ballen_review_tools/providers/base.py
assistants/shared/tools/review/src/ballen_review_tools/providers/github.py
tests/assistants/review_tools/test_github.py
tests/assistants/review_tools/test_publication.py
tests/assistants/review_tools/test_receipts.py
```

Modify:

```text
assistants/shared/skills/catalog.yaml
assistants/shared/skills/using-github/SKILL.md
assistants/shared/tools/review/README.md
assistants/shared/tools/review/pyproject.toml
assistants/shared/tools/review/uv.lock
assistants/shared/tools/review/src/ballen_review_tools/models.py
tests/assistants/test_review_contracts.py
tests/assistants/test_skills.py
```

- [ ] **Step 2.1: Reconfirm the current GitHub contract**

Read the current official endpoints before fixing payload tests:

- <https://docs.github.com/en/rest/pulls/reviews>
- <https://docs.github.com/en/rest/pulls/comments>
- <https://docs.github.com/en/rest/issues/comments>

Record the API version used by the provider module. Confirm current support for
`commit_id`, `line`, `side`, `start_line`, and `start_side`, and confirm the
reply endpoint and review event values. Do not use the retiring `position`
field for new comments.

- [ ] **Step 2.2: Write failing transport and payload tests**

Define a narrow injected runner:

```python
class GitHubReviewCommentPayload(TypedDict):
    """Exact GitHub pull-request review comment payload."""

    path: str
    line: int
    side: Literal["LEFT", "RIGHT"]
    body: str
    start_line: NotRequired[int]
    start_side: NotRequired[Literal["LEFT", "RIGHT"]]


class CommandRunner(Protocol):
    """Run one reviewed argument vector without a shell."""

    def run(
        self,
        argv: Sequence[str],
        *,
        input_text: str | None = None,
    ) -> CompletedCommand:
        """Return bounded stdout, stderr, and status."""
```

Tests must assert exact argument arrays and JSON sent on standard input:

```python
def test_github_review_payload_uses_current_line_fields(
    github_provider: GitHubProvider,
) -> None:
    """Build a commit-pinned multi-line review comment."""
    payload = github_provider.review_payload(
        plan=INLINE_RANGE_PLAN,
        observed_head=HEAD_SHA,
    )

    assert payload["comments"] == [
        {
            "path": "src/example.py",
            "line": 20,
            "side": "RIGHT",
            "start_line": 18,
            "start_side": "RIGHT",
            "body": "Guard the empty case.",
        }
    ]
    assert payload["commit_id"] == HEAD_SHA
    assert "position" not in payload["comments"][0]
```

Cover exact GET argument vectors for PR identity, review comments, conversation
comments, and replies. Confirm the runner is never invoked through a shell.

Run:

```text
rtk uv run --frozen pytest \
  tests/assistants/review_tools/test_github.py -q
```

Expected: tests fail because the provider and transport protocol do not exist.

- [ ] **Step 2.3: Implement read-only preflight and preview**

Add `PublicationPreview` and `PublicationItemPreview` models. Preview must bind:

- current canonical provider/change identity;
- logical plan digest;
- expected and observed head;
- current review, comment, and thread observation digest;
- each deduplication result; and
- the exact payload for each valid selected action.

The command surface is:

```text
publish-github-review preview \
  --plan PATH \
  --output PATH

publish-github-review execute \
  --plan PATH \
  --approved-plan-digest SHA256 \
  --expected-head SHA \
  --receipt PATH
```

`preview` is the default when no subcommand is supplied. It may issue GET
requests but the provider API must expose no mutation method on that path.

- [ ] **Step 2.4: Write failing approval, stale-state, and deduplication tests**

Cover:

- missing execution mode;
- missing or malformed approved digest;
- approved digest different from the current plan;
- expected head different from current remote head;
- changed repository or pull-request identity;
- invalid line or range on the current diff;
- exact duplicate inline, general, and reply comments;
- same body at a different current location;
- secondary-rate-limit and validation errors; and
- no selected actions.

```python
def test_execute_rejects_changed_head_before_any_write(
    runner: RecordingRunner,
) -> None:
    """Invalidate approval when remote head moves after preview."""
    result = execute_github_publication(
        plan=VALID_PLAN,
        approved_plan_digest=PLAN_DIGEST,
        expected_head=OLD_HEAD,
        runner=runner.with_current_head(NEW_HEAD),
    )

    assert result.status == "blocked"
    assert runner.mutation_calls == []
```

- [ ] **Step 2.5: Implement guarded execution and minimal receipts**

Execution order is fixed:

1. load and strictly validate the current plan;
2. recompute and compare the approved plan digest;
3. fetch canonical PR identity and current head;
4. compare expected and observed head;
5. fetch current comments and review threads;
6. recompute deduplication and position validity;
7. construct the exact current preview;
8. post eligible actions in deterministic action-ID order;
9. stop automatic reposting after any ambiguous provider result; and
10. atomically write one receipt with every item's final outcome.

Receipt diagnostics are bounded and redacted. Store only minimal remote IDs or
URLs, never headers, raw bodies, full payloads, or full provider responses.

Batch compatible inline comments into:

```json
{
  "commit_id": "CURRENT_HEAD_SHA",
  "event": "COMMENT",
  "comments": []
}
```

Post general comments and replies separately so one type cannot be silently
translated into another. When a batch request fails ambiguously, mark every
unconfirmed batch item `failed` and require a new preflight; never guess which
items succeeded.

- [ ] **Step 2.6: Prove partial retry cannot duplicate success**

Simulate one successful general comment followed by one failed reply. On the
next invocation, return that successful comment in remote observations and
assert:

```python
assert retry_receipt.items["R001"].outcome == "duplicate"
assert retry_receipt.items["R002"].outcome == "posted"
assert runner.posted_action_ids == ["R002"]
```

Also validate the checked-in preview and receipt examples and vectors through
`review-plan validate`.

- [ ] **Step 2.7: Add the publication launcher and skill**

Add this console script:

```toml
publish-github-review = "ballen_review_tools.github_cli:main"
```

Regenerate `uv.lock`, create the executable launcher using the Task 1 pattern,
and set mode `0700`.

The skill must:

- refuse to discover or rewrite findings;
- recompile the current draft before preview;
- show exact eligible, blocked, duplicate, and skipped actions;
- obtain approval for the current preview;
- pass only the approved plan digest and expected head into execution; and
- summarize receipt outcomes without claiming failed items posted.

It delegates transport selection to `using-github`. If `gh` is unavailable but
a connected mutation tool exists, it uses the managed preview as the exact
request bundle, obtains the same current approval, performs the provider call,
and validates the normalized receipt. If no mutation transport exists, it
stops as blocked without weakening local review.

Add this catalog relationship:

```yaml
  - name: publish-github-review
    source: assistants/shared/skills/publish-github-review
    targets: [cursor, claude-code, codex]
    profiles: [default]
    dependencies: [using-github, review-github-pull-request]
    provenance: >-
      Authored for ballen-config under the approved forge review and response
      design; Plato posting helpers at commit
      5f78cc607ad100c72f6e173bc22620bcebd6c855 informed the guarded publisher.
    portability_status: reviewed-generic
```

- [ ] **Step 2.8: Run focused verification and commit**

```text
rtk uv run --project assistants/shared/tools/review --frozen pytest \
  tests/assistants/review_tools -q
rtk uv run --frozen pytest \
  tests/assistants/review_tools \
  tests/assistants/test_review_contracts.py \
  tests/assistants/test_skills.py -q
rtk uv run --frozen pre-commit run --files \
  assistants/shared/skills/publish-github-review/SKILL.md \
  assistants/shared/skills/using-github/SKILL.md \
  assistants/shared/tools/review/contracts/publication-preview-v1.md \
  assistants/shared/tools/review/contracts/publication-receipt-v1.md
rtk jj status
rtk jj diff --summary
rtk jj describe -m 'feat: add GitHub review publication'
rtk jj bookmark create forge-review-github-publish -r @
rtk jj new
```

After authorization, push and open the PR against `main`. Use dry-run evidence
only in this PR; a live write remains part of the explicit train dogfood gate.

## Task 3: PR 3 — Provider-Neutral Response Preparation

**Bookmark:** `forge-review-prepare-response`

**Commit and PR title:** `feat: add provider-neutral review response planning`

**PR base:** `main`

### Required behavior

`prepare-review-response` consumes validated normalized threads or retrieves
provider-native threads through one selected provider skill, evaluates the
feedback, and writes a normalized thread set plus response plan. It may propose
local changes and exact replies, but it has no edit, commit, push, reply,
resolution, or other mutation path.

`using-github`, `using-gitlab`, and a supplied normalized artifact are runtime
alternatives. They are not simultaneous catalog dependencies.

### Files

Create:

```text
assistants/shared/skills/prepare-review-response/SKILL.md
assistants/shared/tools/review/contracts/normalized-review-threads-v1.md
assistants/shared/tools/review/contracts/normalized-review-threads.example.json
assistants/shared/tools/review/contracts/review-response-plan-v1.md
assistants/shared/tools/review/contracts/review-response-plan.example.json
assistants/shared/tools/review/contracts/response-vectors.json
tests/assistants/review_tools/test_response_plans.py
```

Modify:

```text
assistants/shared/skills/catalog.yaml
assistants/shared/tools/review/README.md
assistants/shared/tools/review/src/ballen_review_tools/markdown.py
assistants/shared/tools/review/src/ballen_review_tools/models.py
assistants/shared/tools/review/src/ballen_review_tools/plan_cli.py
tests/assistants/test_review_contracts.py
tests/assistants/test_skills.py
```

- [ ] **Step 3.1: Write failing normalized-thread model tests**

The model must preserve provider/change identity, native thread and comment
IDs, state, logical location, author, chronology, required text, current head,
and normalization limitations.

```python
def test_resolved_and_informational_threads_remain_visible() -> None:
    """Keep skipped evidence instead of dropping completed feedback."""
    response = compile_response_plan(NORMALIZED_THREADS)

    assert [item.thread_id for item in response.items] == ["T001", "T002"]
    assert response.items[1].classification == "informational"
    assert response.items[1].selected_action == "skip"
```

Reject absolute file paths, unknown classifications, missing native IDs,
unbounded diagnostics, and a response plan whose target or head differs from
its normalized source.

- [ ] **Step 3.2: Implement contracts and non-mutating CLI support**

Add:

```text
review-plan validate-threads --threads PATH
review-plan compile-response \
  --threads PATH \
  --draft PATH \
  --output PATH
```

`compile-response` validates the ignored workspace before writing. The response
plan records:

- `actionable`, `question`, `discussion`, `resolved`, or `informational`;
- evaluation and evidence;
- proposed local changes;
- proposed response;
- focused verification required;
- selected action; and
- current native provider target.

The tool must not run source-control or provider mutation commands. Add tests
whose recording runners fail if any mutation-capable dependency is constructed.

- [ ] **Step 3.3: Write the provider-neutral skill**

The skill must:

1. start read-only;
2. select exactly one validated provider input path;
3. preserve normalization limitations;
4. invoke native `receiving-code-review` when available;
5. record missing native evaluation coverage when unavailable;
6. evaluate technical validity before agreeing with feedback;
7. retain every thread and selected/skipped state; and
8. stop after writing the ignored response plan.

Add this catalog relationship:

```yaml
  - name: prepare-review-response
    source: assistants/shared/skills/prepare-review-response
    targets: [cursor, claude-code, codex]
    profiles: [default]
    dependencies: [discover-project-standards]
    provenance: >-
      Authored for ballen-config under the approved forge review and response
      design; Plato response workflows at commit
      5f78cc607ad100c72f6e173bc22620bcebd6c855 informed the evaluation flow.
    portability_status: reviewed-generic
```

Add a catalog test proving neither provider skill is a hard dependency.

- [ ] **Step 3.4: Verify read-only behavior and commit**

```text
rtk uv run --project assistants/shared/tools/review --frozen pytest \
  tests/assistants/review_tools/test_response_plans.py -q
rtk uv run --frozen pytest \
  tests/assistants/review_tools \
  tests/assistants/test_review_contracts.py \
  tests/assistants/test_skills.py -q
rtk uv run --frozen pre-commit run --files \
  assistants/shared/skills/prepare-review-response/SKILL.md \
  assistants/shared/tools/review/contracts/normalized-review-threads-v1.md \
  assistants/shared/tools/review/contracts/review-response-plan-v1.md
rtk jj status
rtk jj diff --summary
rtk jj describe -m 'feat: add provider-neutral review response planning'
rtk jj bookmark create forge-review-prepare-response -r @
rtk jj new
```

After authorization, push and open the PR against `main`.

## Task 4: PR 4 — GitHub Review Response

**Bookmark:** `forge-review-github-response`

**Commit and PR title:** `feat: add GitHub review response workflow`

**PR base:** `main`

### Required behavior

`respond-to-github-review` consumes a current response plan and independently
gates selected local edits, verification, commit, push, and exact remote
replies. It must revalidate local scope, repository standards, GitHub identity,
head, and thread state before each relevant boundary.

### Files

Create:

```text
assistants/shared/skills/respond-to-github-review/SKILL.md
tests/assistants/review_tools/test_github_threads.py
```

Modify:

```text
assistants/shared/skills/catalog.yaml
assistants/shared/skills/using-github/SKILL.md
assistants/shared/tools/review/src/ballen_review_tools/plan_cli.py
assistants/shared/tools/review/src/ballen_review_tools/providers/github.py
tests/assistants/test_review_contracts.py
tests/assistants/test_skills.py
```

- [ ] **Step 4.1: Write failing GitHub thread-normalization tests**

Use fixtures for open, resolved, outdated, and missing review threads. Preserve
native review-thread and comment IDs, current head, chronology, side/range, and
any GraphQL or REST coverage limitation.

Add:

```text
review-plan normalize-threads \
  --provider github \
  --identity PATH \
  --input PATH \
  --output PATH
```

Normalization is read-only and writes only to a preflighted ignored workspace.

- [ ] **Step 4.2: Write structural gate tests before the skill**

Assert the skill presents these five boundaries in this order:

1. authorize selected local edits;
2. run and inspect focused verification;
3. authorize the exact change description and commit;
4. authorize push to the reviewed remote/branch; and
5. preview and authorize exact remote replies or status comments.

Also assert it:

- delegates local scope to `resolve-change-scope`;
- follows repository-native source control and uses Jujutsu when `.jj/` exists;
- never bundles commit, push, and reply into one approval;
- does not claim completion before focused verification passes; and
- does not claim a change is remote until the expected head contains it.

- [ ] **Step 4.3: Write the responder skill and catalog entry**

Use this exact dependency graph:

```yaml
  - name: respond-to-github-review
    source: assistants/shared/skills/respond-to-github-review
    targets: [cursor, claude-code, codex]
    profiles: [default]
    dependencies: [prepare-review-response, publish-github-review, resolve-change-scope, discover-project-standards]
    provenance: >-
      Authored for ballen-config under the approved forge review and response
      design; Plato response workflows at commit
      5f78cc607ad100c72f6e173bc22620bcebd6c855 informed the guarded sequence.
    portability_status: reviewed-generic
```

Remote replies use the already guarded GitHub publication command with an
action subset derived from the revalidated response plan. They still require a
fresh preview, approved plan digest, and expected head.

- [ ] **Step 4.4: Run focused verification and controlled dry dogfood**

```text
rtk uv run --project assistants/shared/tools/review --frozen pytest \
  tests/assistants/review_tools/test_github_threads.py \
  tests/assistants/review_tools/test_response_plans.py \
  tests/assistants/review_tools/test_github.py -q
rtk uv run --frozen pytest \
  tests/assistants/test_review_contracts.py \
  tests/assistants/test_skills.py -q
rtk uv run --frozen pre-commit run --files \
  assistants/shared/skills/respond-to-github-review/SKILL.md \
  assistants/shared/skills/using-github/SKILL.md
```

Against this PR, create an ignored response-plan fixture from its actual GitHub
threads and run through every preview boundary without authorizing edits,
commit, push, or reply. Verify `rtk jj status` does not show the artifact.

- [ ] **Step 4.5: Commit and open the PR**

```text
rtk jj status
rtk jj diff --summary
rtk jj describe -m 'feat: add GitHub review response workflow'
rtk jj bookmark create forge-review-github-response -r @
rtk jj new
```

After authorization, push and open the PR against `main`. A live controlled
response is deferred to the train-level gate.

## Task 5: PR 5 — GitLab Local-Draft Adapter

**Bookmark:** `forge-review-gitlab-draft`

**Commit and PR title:** `feat: add GitLab merge-request review drafting`

**PR base:** `main`

### Required behavior

`review-gitlab-merge-request` is a native local-review adapter. It reuses the
safe workspace, Markdown, logical plan, digest, and outcome contracts while
preserving merge-request vocabulary, GitLab discussions, diff references, and
text-position semantics. It depends on `using-gitlab`, never on a GitHub skill.
This change remains read-only.

### Files

Create:

```text
assistants/shared/skills/review-gitlab-merge-request/SKILL.md
assistants/shared/tools/review/src/ballen_review_tools/providers/gitlab.py
tests/assistants/review_tools/test_gitlab_threads.py
```

Modify:

```text
assistants/shared/skills/catalog.yaml
assistants/shared/skills/using-gitlab/SKILL.md
assistants/shared/tools/review/README.md
assistants/shared/tools/review/src/ballen_review_tools/plan_cli.py
tests/assistants/test_review_contracts.py
tests/assistants/test_skills.py
```

- [ ] **Step 5.1: Re-read audited Plato behavior**

At the pinned Plato revision, extract:

- the accepted Markdown action kinds and metadata;
- how `base_sha`, `head_sha`, and `start_sha` are read;
- inline discussion, general note, and discussion-reply distinctions;
- dry-run evidence;
- action-specific success/failure reporting; and
- existing test vectors.

Write a short implementation note in the PR description mapping each retained
behavior to a new test. Do not copy Plato paths, project IDs, authentication
assumptions, or the approved-only parser mode.

- [ ] **Step 5.2: Write failing GitLab normalization tests**

Fixtures must cover:

- current MR identity and all three diff SHAs;
- open and resolved discussions;
- outdated positions;
- system notes excluded with a recorded limitation;
- full discussion and note IDs;
- old-path, new-path, old-line, and new-line positions;
- missing or incomplete `diff_refs`; and
- pagination assembled in stable chronology.

```python
def test_gitlab_normalization_preserves_native_discussion_identity() -> None:
    """Keep GitLab IDs and state without inventing GitHub threads."""
    threads = normalize_gitlab_threads(
        raw_discussions=GITLAB_DISCUSSIONS,
        identity=GITLAB_IDENTITY,
        revisions=GITLAB_DIFF_REFS,
    )

    assert threads.items[0].thread_id == "discussion-012345"
    assert threads.items[0].state == "open"
    assert threads.items[0].comments[0].comment_id == 987
    assert threads.items[0].location.new_line == 42
```

Run and confirm failure because the adapter does not exist.

- [ ] **Step 5.3: Implement the read-only GitLab adapter**

Add provider-neutral return types and:

```text
review-plan normalize-threads \
  --provider gitlab \
  --identity PATH \
  --input PATH \
  --output PATH
```

The adapter accepts captured provider JSON from `using-gitlab`, validates MR
identity and `diff_refs`, and emits the shared normalized-thread contract. It
must not force GitLab discussion state into GitHub review-state names.

`review-plan compile-review` already accepts `provider: gitlab`; extend tests to
prove the same logical draft can represent GitLab inline discussions, general
notes, and replies without storing a provider payload.

- [ ] **Step 5.4: Write the local GitLab skill and provider boundary**

The skill:

- starts read-only;
- uses merge-request and discussion terminology;
- retrieves the MR, changes, discussions, and current diff refs through
  `using-gitlab`;
- discovers repository standards;
- writes only to a proven ignored workspace;
- reports pagination or normalization limitations;
- compiles all selected and unselected actions; and
- performs no remote write.

Add:

```yaml
  - name: review-gitlab-merge-request
    source: assistants/shared/skills/review-gitlab-merge-request
    targets: [cursor, claude-code, codex]
    profiles: [default]
    dependencies: [using-gitlab, discover-project-standards]
    provenance: >-
      Genericized from Plato merge-request review behavior at commit
      5f78cc607ad100c72f6e173bc22620bcebd6c855 under the approved forge
      review and response design.
    portability_status: reviewed-generic
```

Update `using-gitlab` with read ownership and the stable `review-plan` path. It
must keep transport and authentication inherited from the current environment.

- [ ] **Step 5.5: Prove there is no GitHub dependency**

Add catalog and prose tests asserting:

```python
assert catalog.by_name("review-gitlab-merge-request").dependencies == (
    "using-gitlab",
    "discover-project-standards",
)
assert "publish-github-review" not in projected_dependency_closure
assert "review-github-pull-request" not in projected_dependency_closure
```

Run:

```text
rtk uv run --project assistants/shared/tools/review --frozen pytest \
  tests/assistants/review_tools/test_gitlab_threads.py \
  tests/assistants/review_tools/test_markdown.py -q
rtk uv run --frozen pytest \
  tests/assistants/test_review_contracts.py \
  tests/assistants/test_skills.py -q
rtk uv run --frozen pre-commit run --files \
  assistants/shared/skills/review-gitlab-merge-request/SKILL.md \
  assistants/shared/skills/using-gitlab/SKILL.md
```

- [ ] **Step 5.6: Commit and open the PR**

```text
rtk jj status
rtk jj diff --summary
rtk jj describe -m 'feat: add GitLab merge-request review drafting'
rtk jj bookmark create forge-review-gitlab-draft -r @
rtk jj new
```

After authorization, push and open the PR against `main`.

## Task 6: PR 6 — GitLab Publication

**Bookmark:** `forge-review-gitlab-publish`

**Commit and PR title:** `feat: add GitLab review publication`

**PR base:** `main`

### Required behavior

`publish-gitlab-review` ports and hardens the useful Plato publication helpers.
Preview fetches current MR state, diff refs, discussions, and notes without
mutation. Execute requires explicit mode, an approved current plan digest, and
the expected head. It posts native discussions, notes, or replies and writes a
minimal itemized receipt.

### Files

Create:

```text
assistants/shared/skills/publish-gitlab-review/SKILL.md
assistants/shared/tools/review/bin/publish-gitlab-review
assistants/shared/tools/review/src/ballen_review_tools/gitlab_cli.py
tests/assistants/review_tools/test_gitlab.py
tests/assistants/review_tools/test_gitlab_publication.py
```

Modify:

```text
assistants/shared/skills/catalog.yaml
assistants/shared/skills/using-gitlab/SKILL.md
assistants/shared/tools/review/README.md
assistants/shared/tools/review/pyproject.toml
assistants/shared/tools/review/uv.lock
assistants/shared/tools/review/src/ballen_review_tools/providers/gitlab.py
tests/assistants/test_review_contracts.py
tests/assistants/test_skills.py
```

- [ ] **Step 6.1: Reconfirm the current GitLab API**

Read the current official contracts before fixing payload tests:

- <https://docs.gitlab.com/api/discussions/>
- <https://docs.gitlab.com/api/notes/>
- <https://docs.gitlab.com/api/merge_requests/>

Confirm current text-position fields, URL encoding for namespaced project IDs,
discussion replies, pagination, and the source of
`base_sha`/`head_sha`/`start_sha`. Record the API assumptions in provider
docstrings and tests.

- [ ] **Step 6.2: Write failing GitLab payload tests**

Represent exact provider payload mappings with `TypedDict`, not untyped
`dict[str, Any]`. Assert a new-line text position contains:

```python
assert payload["position"] == {
    "position_type": "text",
    "base_sha": BASE_SHA,
    "head_sha": HEAD_SHA,
    "start_sha": START_SHA,
    "new_path": "src/example.py",
    "new_line": 42,
}
```

Add old-line and renamed-file vectors. Reject incomplete diff refs, invalid line
sides, ambiguous discussions, and stale head before any POST.

Assert exact `glab api` argument arrays and JSON standard input for:

```text
POST /projects/:id/merge_requests/:iid/discussions
POST /projects/:id/merge_requests/:iid/notes
POST /projects/:id/merge_requests/:iid/discussions/:discussion_id/notes
```

No request may use shell interpolation or parse authentication output.

- [ ] **Step 6.3: Implement preview and execute modes**

Expose:

```text
publish-gitlab-review preview \
  --plan PATH \
  --output PATH

publish-gitlab-review execute \
  --plan PATH \
  --approved-plan-digest SHA256 \
  --expected-head SHA \
  --receipt PATH
```

Reuse the shared preview and receipt models. The GitLab provider must separately
construct:

- an inline discussion with a current text position;
- a general MR note; and
- a reply to an existing full discussion ID.

Do not generate a GitHub-shaped intermediate payload.

- [ ] **Step 6.4: Port parser/poster outcomes without old authority**

Write regression fixtures derived from Plato's parser and poster tests. Prove:

- `POST: YES` and `POST: NO` are both parsed;
- only the current preview's selected, valid, nonduplicate actions are eligible;
- execution cannot occur from the Markdown selection alone;
- every action receives one final outcome;
- successful actions retain minimal native IDs;
- failed actions retain bounded diagnostics;
- remaining actions become `not-attempted` after an ambiguous stop; and
- retry re-fetches discussions and does not repeat confirmed successes.

```python
def test_gitlab_retry_skips_confirmed_discussion(
    runner: RecordingRunner,
) -> None:
    """Resume a partial publication without duplicate discussions."""
    receipt = execute_gitlab_publication(
        plan=PARTIALLY_POSTED_PLAN,
        approved_plan_digest=PLAN_DIGEST,
        expected_head=HEAD_SHA,
        runner=runner.with_existing_discussion("R001"),
    )

    assert receipt.items["R001"].outcome == "duplicate"
    assert runner.posted_action_ids == ["R002"]
```

- [ ] **Step 6.5: Add the launcher, skill, and catalog entry**

Add:

```toml
publish-gitlab-review = "ballen_review_tools.gitlab_cli:main"
```

Regenerate the lock, add the Task 1 launcher pattern, and set mode `0700`.

The skill mirrors the approved publication boundary while using GitLab-native
terms and current diff refs.

It delegates transport selection to `using-gitlab`. A connected provider tool
may execute the exact validated request bundle when `glab` is unavailable; the
skill then validates the normalized receipt. Without either mutation transport,
it stops as blocked and retains the local draft and preview.

Add this catalog relationship:

```yaml
  - name: publish-gitlab-review
    source: assistants/shared/skills/publish-gitlab-review
    targets: [cursor, claude-code, codex]
    profiles: [default]
    dependencies: [using-gitlab, review-gitlab-merge-request]
    provenance: >-
      Genericized from Plato review parsing and posting helpers at commit
      5f78cc607ad100c72f6e173bc22620bcebd6c855 under the approved forge
      review and response design.
    portability_status: reviewed-generic
```

- [ ] **Step 6.6: Run focused verification and commit**

```text
rtk uv run --project assistants/shared/tools/review --frozen pytest \
  tests/assistants/review_tools/test_gitlab.py \
  tests/assistants/review_tools/test_gitlab_publication.py \
  tests/assistants/review_tools/test_receipts.py -q
rtk uv run --frozen pytest \
  tests/assistants/review_tools \
  tests/assistants/test_review_contracts.py \
  tests/assistants/test_skills.py -q
rtk uv run --frozen pre-commit run --files \
  assistants/shared/skills/publish-gitlab-review/SKILL.md \
  assistants/shared/skills/using-gitlab/SKILL.md
rtk jj status
rtk jj diff --summary
rtk jj describe -m 'feat: add GitLab review publication'
rtk jj bookmark create forge-review-gitlab-publish -r @
rtk jj new
```

After authorization, push and open the PR against `main`. Live GitLab mutation
remains optional and requires a separately approved safe target.

## Task 7: PR 7 — GitLab Review Response

**Bookmark:** `forge-review-gitlab-response`

**Commit and PR title:** `feat: add GitLab review response workflow`

**PR base:** `main`

### Required behavior

`respond-to-gitlab-review` applies the same five independent local and remote
gates as the GitHub responder while preserving GitLab discussion IDs, current
diff refs, resolution state, positions, and partial-failure evidence. It does
not silently resolve discussions or retry confirmed replies.

### Files

Create:

```text
assistants/shared/skills/respond-to-gitlab-review/SKILL.md
tests/assistants/review_tools/test_gitlab_response.py
```

Modify:

```text
assistants/shared/skills/catalog.yaml
assistants/shared/skills/using-gitlab/SKILL.md
assistants/shared/tools/review/src/ballen_review_tools/providers/gitlab.py
tests/assistants/test_review_contracts.py
tests/assistants/test_skills.py
```

- [ ] **Step 7.1: Write failing response and retry tests**

Cover:

- selected edits against a current open discussion;
- resolved, outdated, and missing discussions;
- a changed MR head after local verification;
- reply deduplication by discussion ID and normalized body;
- one successful reply followed by one failed reply;
- retry after that partial outcome; and
- no automatic discussion-resolution call.

```python
def test_changed_diff_refs_invalidate_reply_preview() -> None:
    """Require a fresh response preview after the MR changes."""
    result = preflight_gitlab_response(
        response_plan=RESPONSE_PLAN,
        observed_diff_refs=NEW_DIFF_REFS,
    )

    assert result.status == "blocked"
    assert "head" in result.reason
```

- [ ] **Step 7.2: Write structural gate tests and the skill**

Assert the same five ordered gates as Task 4. Add GitLab-specific requirements:

- re-fetch current MR identity, diff refs, and selected discussions;
- preserve complete discussion IDs;
- run selected local edits through `resolve-change-scope`;
- re-run focused verification after edits;
- use project-native source control and Jujutsu when present;
- preview exact replies through `publish-gitlab-review`;
- never infer remote resolution from a local reply; and
- report every receipt outcome separately.

Add:

```yaml
  - name: respond-to-gitlab-review
    source: assistants/shared/skills/respond-to-gitlab-review
    targets: [cursor, claude-code, codex]
    profiles: [default]
    dependencies: [prepare-review-response, publish-gitlab-review, resolve-change-scope, discover-project-standards]
    provenance: >-
      Genericized from Plato merge-request response behavior at commit
      5f78cc607ad100c72f6e173bc22620bcebd6c855 under the approved forge
      review and response design.
    portability_status: reviewed-generic
```

- [ ] **Step 7.3: Complete focused verification**

```text
rtk uv run --project assistants/shared/tools/review --frozen pytest \
  tests/assistants/review_tools/test_gitlab_response.py \
  tests/assistants/review_tools/test_gitlab_publication.py \
  tests/assistants/review_tools/test_response_plans.py -q
rtk uv run --frozen pytest \
  tests/assistants/test_review_contracts.py \
  tests/assistants/test_skills.py -q
rtk uv run --frozen pre-commit run --files \
  assistants/shared/skills/respond-to-gitlab-review/SKILL.md \
  assistants/shared/skills/using-gitlab/SKILL.md
```

- [ ] **Step 7.4: Update train documentation**

Update the forge detailed design and roadmap with:

- all seven capability PR links;
- final command and stable installation paths;
- GitHub dogfood evidence location;
- GitLab contract-test evidence and whether live write was intentionally
  skipped; and
- a stable statement that implementation is tracked by the linked PRs and
  GitHub merge state is authoritative.

Do not commit receipts, review drafts, normalized threads, response plans, or
full provider transcripts as documentation.

- [ ] **Step 7.5: Commit and open the PR**

```text
rtk jj status
rtk jj diff --summary
rtk jj describe -m 'feat: add GitLab review response workflow'
rtk jj bookmark create forge-review-gitlab-response -r @
rtk jj new
```

After authorization, push and open the final capability PR against `main`.

## Task 8: Train-Level Verification and Dogfooding

- [ ] **Step 8.1: Verify the final artifact and dependency graph**

Assert the final direct dependencies:

```text
review-github-pull-request
  -> using-github
  -> discover-project-standards

publish-github-review
  -> using-github
  -> review-github-pull-request

prepare-review-response
  -> discover-project-standards

respond-to-github-review
  -> prepare-review-response
  -> publish-github-review
  -> resolve-change-scope
  -> discover-project-standards

review-gitlab-merge-request
  -> using-gitlab
  -> discover-project-standards

publish-gitlab-review
  -> using-gitlab
  -> review-gitlab-merge-request

respond-to-gitlab-review
  -> prepare-review-response
  -> publish-gitlab-review
  -> resolve-change-scope
  -> discover-project-standards
```

Run:

```text
rtk uv run --frozen pytest \
  tests/assistants/test_models.py \
  tests/assistants/test_skills.py \
  tests/assistants/test_review_contracts.py \
  tests/assistants/test_review_tools_installation.py \
  tests/assistants/test_integration.py -q
```

Expected: all seven skills project to Cursor, Claude Code, and Codex; all
dependency closures validate; GitLab closures contain no GitHub skill; and all
agent projections reference the same managed tool location.

- [ ] **Step 8.2: Verify the locked managed tool in isolation**

```text
rtk uv lock --check --project assistants/shared/tools/review
rtk uv run --project assistants/shared/tools/review --frozen pytest \
  tests/assistants/review_tools -q
rtk uv run --project assistants/shared/tools/review --frozen mypy \
  --config-file assistants/shared/tools/review/pyproject.toml \
  -p ballen_review_tools
rtk sh -n assistants/shared/tools/review/bin/review-plan
rtk sh -n assistants/shared/tools/review/bin/publish-github-review
rtk sh -n assistants/shared/tools/review/bin/publish-gitlab-review
```

Expected: the lock is current, all unit and CLI fixtures pass, strict typing
passes, and launchers have valid shell syntax. Inspect the managed source tree
afterward and confirm no `.venv`, cache, receipt, preview, or provider output
was created inside it.

- [ ] **Step 8.3: Run bootstrap planning and doctor checks**

```text
rtk ./bootstrap plan --profile default
rtk ./bootstrap doctor --profile default
rtk ./bootstrap plan --profile work
rtk ./bootstrap doctor --profile work
```

Expected:

- one `shared-review-tools` managed tree is planned when any supported agent is
  enabled;
- all-agent skip plans no review-tool action;
- the source and installed digest, executable bits, collision, and drift checks
  use the existing managed-tree engine;
- no plan or doctor output exposes credentials or native provider state; and
- repeat planning is deterministic.

- [ ] **Step 8.4: Exercise every artifact fixture class**

The fixture matrix must include:

```text
valid inline, general, and reply actions
selected and unselected Markdown
malformed and duplicate metadata
safe, unsafe, tracked, staged, conflicted, and unignored workspaces
current and stale provider heads
valid and invalid GitHub single-line and range locations
valid and invalid GitLab diff references and text positions
open, resolved, outdated, unknown, and missing threads
exact duplicates and same-body/different-location comments
authentication, permission, validation, and rate-limit failures
complete, blocked, partial, and retry publication receipts
```

Every provider fixture asserts exact argument arrays and JSON input. No fixture
requires credentials or performs a live write.

- [ ] **Step 8.5: Dogfood a real ignored GitHub draft**

Choose a bounded open `ballen-config` PR and a repository-local directory that
is already ignored. Do not modify ignore rules. Then:

1. run `review-github-pull-request` read-only;
2. run `review-plan workspace-check`;
3. inspect the Markdown draft and logical plan;
4. toggle at least one selected and one skipped item;
5. recompile and validate the plan; and
6. run `publish-github-review preview`.

Confirm:

- the preview binds the current PR identity, head, observations, plan digest,
  and exact payload;
- no remote comment was created;
- the draft, plan, preview, and later receipt remain ignored and untracked; and
- a second compile of unchanged input has the same logical plan digest.

Use `rtk jj status` and `rtk git check-ignore` as evidence. Do not paste full
review text or provider output into the repository.

- [ ] **Step 8.6: Publish one controlled GitHub review**

This step requires separate user authorization after the exact current preview
is shown. Pass the approved plan digest and expected head literally to:

```text
~/.local/share/ballen-config/review-tools/bin/publish-github-review execute \
  --plan REVIEW_PLAN_PATH \
  --approved-plan-digest APPROVED_SHA256 \
  --expected-head EXPECTED_HEAD_SHA \
  --receipt RECEIPT_PATH
```

Before execution, replace each uppercase token with the inspected value; do not
use an old preview. After execution:

- inspect the remote comments read-only;
- compare them with item-level receipt outcomes;
- rerun preview and prove successful actions classify as duplicates; and
- confirm no failed or blocked action is reported as posted.

If the target head or preview changes, return to preview and request new
authorization.

- [ ] **Step 8.7: Prepare and apply one controlled GitHub response**

Use actual review feedback on the bounded PR:

1. normalize current GitHub threads;
2. run `prepare-review-response`;
3. inspect the ignored response plan;
4. request authorization for selected local edits only;
5. run focused verification;
6. request authorization for the exact commit description;
7. request authorization for push;
8. re-fetch the remote head and threads;
9. show exact reply preview; and
10. request authorization for remote replies.

At every declined gate, stop that mutation and preserve the read-only evidence.
A response may claim a fix only after the focused verification passes and the
referenced change is present on the expected remote head.

- [ ] **Step 8.8: Prove retry behavior after simulated partial failure**

Use the provider recording transport, not an intentionally ambiguous live
failure. Replay the same approved logical actions with one recorded success and
one recorded failure. Re-fetch observations, preview again, and assert the
success is duplicate while only the unsuccessful action remains eligible.

- [ ] **Step 8.9: Verify GitLab natively**

Run all GitLab adapter and publication fixtures and inspect exact native
payloads. A live GitLab write is optional. If no separately approved safe
target exists, record `live write intentionally skipped; contract and transport
tests passed` in the PR evidence. Do not substitute a GitHub payload or claim
live GitLab evidence.

- [ ] **Step 8.10: Run the fresh repository gate**

```text
rtk uv run --frozen pytest -q
rtk uv run --frozen mypy
rtk uv run --frozen --no-sync python -m ballen_config.policy
rtk uv run --frozen pre-commit run --all-files
rtk zsh -n bootstrap
rtk ./bootstrap plan --profile work
rtk ./bootstrap doctor --profile work
rtk jj status
rtk jj diff --summary
```

Expected: every command passes, only the final logical stack change is in the
working copy, and no local review artifact appears in Jujutsu.

- [ ] **Step 8.11: Audit the complete stack for prohibited state**

```text
rtk jj diff --from main@origin --name-only
rtk rg -n \
  '/Users/|[P]rojects/plato|[c]redential|[t]oken|[t]rust|[s]ession|[T]ODO|[T]BD|[F]IXME|<placeholde[r]>' \
  assistants/shared/skills \
  assistants/shared/tools/review \
  src/ballen_config/assistants \
  tests/assistants
```

Interpret matches in context. Provenance may name Plato and safety prose may
name prohibited concepts; canonical code and examples must contain no local
absolute paths, secrets, authentication configuration, generated provider
state, complete transcripts, or committed review workspaces.

- [ ] **Step 8.12: Review every PR as an independent slice**

For each bookmark, inspect parent, changed paths, tests, catalog delta, managed
tool delta, provider boundary, PR base, and dogfood evidence. Confirm contracts
arrive with the first capability that exercises them and no PR depends on
unreviewed code from a later slice.

## Task 9: Merge the Stack Bottom-Up

Initial ancestry:

```text
main
└── forge-review-github-draft
    └── forge-review-github-publish
        └── forge-review-prepare-response
            └── forge-review-github-response
                └── forge-review-gitlab-draft
                    └── forge-review-gitlab-publish
                        └── forge-review-gitlab-response
```

- [ ] **Step 9.1: Inspect and merge only the bottom eligible PR**

For the current bottom PR, read base, head, head SHA, commits, files, required
checks, review decision, and unresolved conversations:

```text
rtk gh pr view PR_NUMBER \
  --json baseRefName,headRefName,headRefOid,commits,files,statusCheckRollup,reviewDecision
rtk gh pr checks PR_NUMBER
```

Replace `PR_NUMBER` with the exact inspected number. Merge only after checks,
approvals, conversations, and diff are current:

```text
rtk gh pr merge PR_NUMBER --merge
```

If current branch policy requires a merge queue, use the verified queue path
only when it preserves the approved merge-commit history. Stop if it does not.

- [ ] **Step 9.2: Fetch and validate remote main after every merge**

```text
rtk jj git fetch
rtk jj log -r main@origin --no-graph
```

Confirm the expected merge commit and files are present. Inspect the next PR's
base and diff. Retarget with `rtk gh pr edit` only when needed and only with
explicit authorization. Wait for checks to rerun before the next merge.

- [ ] **Step 9.3: Repeat through the final GitLab response PR**

Never merge out of order. Before the final merge, confirm the linked design and
roadmap describe the seven delivered capabilities, stable command paths, and
actual GitHub/GitLab evidence without embedding local artifacts.

- [ ] **Step 9.4: Run bounded post-merge smoke verification**

```text
rtk jj git fetch
rtk jj new main@origin
rtk uv run --frozen pytest \
  tests/assistants/review_tools \
  tests/assistants/test_review_contracts.py \
  tests/assistants/test_review_tools_installation.py \
  tests/assistants/test_skills.py -q
rtk ./bootstrap plan --profile work
rtk ./bootstrap doctor --profile work
rtk jj status
```

Expected: the focused suite passes on remote `main`, plan and doctor agree, the
working copy is empty, and all seven skills plus the three managed commands are
discoverable through their canonical names and stable paths.

## Plan-Length Justification

This plan is intentionally kept as one document even though it exceeds the
usual 1,200-line planning target. The seven PRs are serial slices of one
artifact digest, managed tool tree, provider boundary, and approval model.
Splitting the plan would duplicate global invariants and make stale-head,
deduplication, partial-retry, dogfood, and bottom-up merge gates easier to apply
inconsistently. Each implementation task remains independently reviewable and
committable.
