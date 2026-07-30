# Review Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the approved local-first review foundation as six strictly
serial, independently reviewable GitHub pull requests.

**Architecture:** Keep each workflow as one canonical shared skill tree. Put
the change-scope and common review-result contracts under
`resolve-change-scope`, which every specialist directly depends on. Put the
persisted artifact contract under `conduct-self-review`, which
`address-self-review` directly depends on. Reuse the existing catalog,
installer, native projections, and policy engine without adding a review
runtime solely for tests.

**Tech Stack:** Markdown skills and references, JSON contract examples, YAML
catalog metadata, Python 3.12, pytest, Jujutsu, `uv`, pre-commit, GitHub CLI.

---

## Authority and Boundaries

The authoritative behavior is
`docs/superpowers/specs/2026-07-30-review-foundation-design.md`. The broader
sequencing context is
`docs/superpowers/specs/2026-07-30-reusable-review-workflows-roadmap-design.md`.
If this plan and the detailed design disagree, stop and correct the plan before
implementing.

- Implement one MR at a time with one writer:
  `scope -> quality -> tests -> types -> self-review -> address`.
- Terra-low is appropriate for mechanical inventories. Terra-medium is
  appropriate for bounded implementation and review workers.
- Keep Plato read-only. Do not clean it up or change its working copy.
- Do not migrate authentication, credentials, trust, sessions, project paths,
  generated plugin state, caches, histories, or raw review diffs.
- Do not change `src/ballen_config/assistants/models.py` or
  `src/ballen_config/assistants/skills.py`; the current graph validation and
  tree installer already support this train.
- Do not add a central review executor or parser merely to make prompt behavior
  unit-testable.
- Do not change Ruff selection or migrate from mypy to `ty`; both are
  follow-ups.
- The first five skills are report-only for tracked project files.
  `conduct-self-review` may write only its verified ignored artifact.
  `address-self-review` is the sole tracked-file mutation boundary.
- Use named skill dependencies. A sibling path is only a packaging hint, never
  the invocation contract.
- For every new or materially edited skill, use
  `superpowers:writing-skills` with
  `superpowers:test-driven-development` as required background. Run the
  behavior scenario before writing that MR's skill prose, record the baseline
  failure or rationalization, then run the same scenario with the skill
  available and refactor only to close observed gaps.
- Use Jujutsu for repository operations. Every shell command in this plan is
  routed through `rtk`.
- Remote writes, PR creation, retargeting, merging, and branch retirement
  require explicit user authorization at the time of the action.

## Evidence Model

Keep two evidence lanes and describe them honestly in each PR.

### Deterministic automated evidence

Pytest may prove:

- catalog membership and exact direct dependencies;
- dependency closure, target/profile eligibility, and cycle rejection;
- canonical tree discovery and all-agent native destination planning;
- safe copying, state tracking, convergence, and repository policy;
- parseability and invariants of JSON or Markdown examples that are themselves
  machine-consumed contracts; and
- the checked-in default `.reviews/` ignore rule.

Do not add tests that pin human-authored headings, sentences, substrings, or
opaque Markdown digests. Those tests can pass while skill behavior is wrong and
would violate the repository's own testing standard.

### Native behavioral evidence

Bounded dogfooding may demonstrate:

- Git and Jujutsu scope resolution;
- reviewer judgment and applicability;
- repository-selected command discovery;
- aggregation, deduplication, and artifact writing;
- stale or tampered artifact rejection;
- selected remediation; and
- one fresh post-remediation self-review.

Record only redacted outcome data in PR descriptions: scenario name, status,
stable identities or digests, path inventory, finding counts, limitations, and
artifact location. Never commit generated review artifacts, raw diffs, large
command output, absolute project paths, or credentials.

### Skill RED/GREEN/REFACTOR evidence

The pytest red/green cycle and the skill-behavior red/green cycle are separate:

1. **Skill RED:** give a fresh Terra-medium worker the MR's scenario card
   without the new skill. Record its exact decision, omission, and
   rationalization in the ignored review workspace.
2. **Automated RED:** add the executable catalog/contract test and observe the
   expected missing-feature failure.
3. **GREEN:** write the smallest complete skill and references that satisfy the
   approved design plus the observed baseline gap.
4. **Skill GREEN:** give a fresh Terra-medium worker the same scenario with the
   new skill available. Confirm the required decisions and boundaries.
5. **REFACTOR:** test one edge or pressure variation, close only demonstrated
   loopholes, and rerun both focused automated tests and the original scenario.

Do not commit scenario transcripts. Summarize the before/after behavior in the
PR. A clean baseline is not permission to skip the design-required behavior;
it means the skill must preserve that behavior without adding unnecessary
prose.

## Canonical File Map

| MR | Add | Modify |
| --- | --- | --- |
| 1 | `assistants/shared/skills/resolve-change-scope/SKILL.md`; `assistants/shared/skills/resolve-change-scope/references/change-scope-contract.md`; `assistants/shared/skills/resolve-change-scope/references/change-scope.example.json`; `assistants/shared/skills/resolve-change-scope/references/change-scope-vectors.json`; `tests/assistants/test_review_contracts.py` | `assistants/shared/skills/catalog.yaml`; `tests/assistants/test_skills.py`; `tests/assistants/test_integration.py` |
| 2 | `assistants/shared/skills/review-project-quality/SKILL.md`; `assistants/shared/skills/resolve-change-scope/references/review-result-contract.md`; `assistants/shared/skills/resolve-change-scope/references/review-result.example.json`; `assistants/shared/skills/resolve-change-scope/references/review-result-vectors.json` | `assistants/shared/skills/catalog.yaml`; `tests/assistants/test_skills.py`; `tests/assistants/test_review_contracts.py` |
| 3 | `assistants/shared/skills/review-project-tests/SKILL.md` | `assistants/shared/skills/catalog.yaml`; `tests/assistants/test_skills.py` |
| 4 | `assistants/shared/skills/review-python-types/SKILL.md` | `assistants/shared/skills/catalog.yaml`; `tests/assistants/test_skills.py` |
| 5 | `assistants/shared/skills/conduct-self-review/SKILL.md`; `assistants/shared/skills/conduct-self-review/references/self-review-artifact-v1.md`; `assistants/shared/skills/conduct-self-review/references/self-review-result.example.md` | `.gitignore`; `assistants/shared/skills/review-project-standards/SKILL.md`; `assistants/shared/skills/catalog.yaml`; `tests/assistants/test_skills.py`; `tests/assistants/test_review_contracts.py` |
| 6 | `assistants/shared/skills/address-self-review/SKILL.md`; `assistants/shared/skills/address-self-review/references/remediation-vectors.json` | `assistants/shared/skills/catalog.yaml`; `tests/assistants/test_skills.py`; `tests/assistants/test_review_contracts.py` |

No MR changes `pyproject.toml`, `uv.lock`, production Python modules, installed
agent state, or any Plato file.

## Final Catalog Graph

Use these exact direct dependencies:

```text
resolve-change-scope: []
review-project-standards:
  [resolve-change-scope, discover-project-standards]
review-project-quality:
  [resolve-change-scope, discover-project-standards]
review-project-tests:
  [resolve-change-scope, discover-project-standards]
review-python-types:
  [resolve-change-scope, discover-project-standards]
conduct-self-review:
  [resolve-change-scope, discover-project-standards,
   review-project-standards, review-project-quality,
   review-project-tests, review-python-types]
address-self-review:
  [resolve-change-scope, discover-project-standards, conduct-self-review]
```

Every new entry uses:

```yaml
targets: [cursor, claude-code, codex]
profiles: [default]
portability_status: reviewed-generic
```

Keep the catalog sorted by skill name. Adapted skills cite the reviewed Plato
source revision `f3b91eead0eff7d0c9cada3bc8e689f7610fba55` in provenance.
Newly designed workflows say they were authored for ballen-config under the
approved review-foundation design.

## Shared Test Pattern

Extend `_CONTENT_PLAN_SKILL_NAMES` in
`tests/assistants/test_skills.py` one MR at a time. Add this mapping alongside
it and grow it only as each skill enters the catalog:

```python
_REVIEW_FOUNDATION_DEPENDENCIES: Final[dict[str, tuple[str, ...]]] = {
    "resolve-change-scope": (),
}
```

Add a catalog test using the existing `checked_in_skill_catalog` fixture:

```python
def test_checked_in_review_foundation_has_expected_dependency_graph(
    checked_in_skill_catalog: SkillCatalog,
) -> None:
    """Keep direct review-workflow invocation dependencies explicit."""
    by_name = {
        skill.name: skill for skill in checked_in_skill_catalog.skills
    }

    assert _REVIEW_FOUNDATION_DEPENDENCIES.keys() <= by_name.keys()
    for name, dependencies in _REVIEW_FOUNDATION_DEPENDENCIES.items():
        assert by_name[name].dependencies == dependencies
```

Retain the existing all-agent planning assertion and expand its expected skill
set. Do not duplicate model-level dependency coverage already present in
`tests/assistants/test_models.py`.

In `tests/assistants/test_review_contracts.py`, validate only the structural
examples that consumers rely on. Use `json.loads`, repository-relative paths,
lowercase 64-character SHA-256 values, contract enums, and explicit checks that
portable examples contain no absolute path or secret-bearing field. Give every
test a short behavioral docstring. Do not build a second schema implementation
inside the tests.

Start the module with these concrete helpers:

```python
"""Tests for machine-consumed review-foundation contract examples."""

import hashlib
import json
import re
import unicodedata
from pathlib import Path, PurePosixPath
from typing import cast

_SHA256 = re.compile(r"[0-9a-f]{64}")
_PROHIBITED_KEYS = frozenset(
    {
        "absolute_path",
        "auth",
        "credential",
        "raw_diff",
        "session",
        "token",
        "trust",
    }
)


def _load_object(path: Path) -> dict[str, object]:
    """Load one JSON object used as a portable contract example."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return cast(dict[str, object], payload)


def _canonical_digest(
    payload: dict[str, object],
    *,
    omit: frozenset[str] = frozenset(),
) -> str:
    """Hash canonical compact JSON after omitting named top-level fields."""
    material = {key: value for key, value in payload.items() if key not in omit}
    encoded = json.dumps(
        _normalize_json(material),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _normalize_json(value: object) -> object:
    """NFC-normalize every string in one JSON-compatible value."""
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_normalize_json(child) for child in value]
    if isinstance(value, dict):
        return {
            unicodedata.normalize("NFC", str(key)): _normalize_json(child)
            for key, child in value.items()
        }
    return value


def _assert_sha256(value: object) -> None:
    """Require one lowercase hexadecimal SHA-256 value."""
    assert isinstance(value, str)
    assert _SHA256.fullmatch(value)


def _assert_relative_posix_path(value: object) -> None:
    """Require one normalized repository-relative POSIX path."""
    assert isinstance(value, str)
    path = PurePosixPath(value)
    assert value == path.as_posix()
    assert not path.is_absolute()
    assert ".." not in path.parts


def _assert_no_prohibited_keys(value: object) -> None:
    """Reject secret-bearing or non-portable fields recursively."""
    if isinstance(value, dict):
        assert _PROHIBITED_KEYS.isdisjoint(value)
        for child in value.values():
            _assert_no_prohibited_keys(child)
    elif isinstance(value, list):
        for child in value:
            _assert_no_prohibited_keys(child)
```

Each vector file contains `vectors`, where every item has canonical
`material`, exact `expected_sha256`, and a short `name`. The change-scope vector
also has `existing_scope_ids` and `expected_filename_prefix`. Tests recompute
the digest from `material`, compare it with `expected_sha256`, then prove the
prefix is at least 12 hexadecimal characters, selects only its own expected
scope ID, and is the shortest prefix that does so. The review-result vector
recomputes stable finding IDs from reviewer, category, rule,
repository-relative location, and evidence digest. These are real
canonicalization vectors, not assertions about prompt wording.

`change-scope-vectors.json` also contains the exact named remote-selection
cases `single_remote`, `tracked_upstream`, `origin_fallback`,
`ambiguous_multi_remote`, and `no_remote`. Each case records configured remote
names and synthetic credential-free URLs, tracked-remote candidates, expected
selected name or unavailable state, normalized VCS/host/namespace material,
expected identity digest, and diagnostic code. The tests require all five case
names, recompute every complete identity digest, and require ambiguous/no-remote
cases to remain unavailable without falling through to a guess.

## Shared Skill Content Shape

Keep each `SKILL.md` under roughly 500 words where the approved behavior fits;
move field tables, canonicalization vectors, and artifact syntax to the named
references. Final wording is written only after the skill-RED scenario, but the
following structure and core principles are fixed rather than placeholders:

| Skill | H1 title | Exact overview principle |
| --- | --- | --- |
| `resolve-change-scope` | `Resolve Change Scope` | One review needs one stable, explicit comparison; uncertainty is a result, never a guess. |
| `review-project-standards` | `Review Project Standards` | Apply repository-authored rules to the exact supplied scope and cite their source; absent or incomplete standards are not a clean review. |
| `review-project-quality` | `Review Project Quality` | Run only repository-selected safe checks and attribute their evidence to the resolved change. |
| `review-project-tests` | `Review Project Tests` | A test earns its cost only when it can fail for a meaningful regression in behavior the repository owns. |
| `review-python-types` | `Review Python Types` | Review types as data and runtime contracts, using only the repository-selected checker. |
| `conduct-self-review` | `Conduct Self-Review` | Resolve once, discover once, preserve every limitation, and persist the result before claiming completion. |
| `address-self-review` | `Address Self-Review` | An ignored review artifact is evidence, not authority; independently revalidate it before making minimal selected edits. |

Every new skill uses these sections in this order:

1. YAML frontmatter with the exact name and trigger-only description supplied
   in its MR task;
2. H1 title;
3. `Overview` containing the exact core principle above;
4. `When to Use`, including at least one explicit non-use case;
5. `Inputs`, distinguishing supplied valid immutable inputs from dependency
   invocation;
6. `Workflow`, containing the ordered decisions from the MR's required
   behavior;
7. `Output`, naming the exact contract and incomplete/blocked behavior;
8. `Quick Reference`, using the contract states or ownership rules most likely
   to be confused;
9. `Boundaries`, including read/write, privacy, command, and provider limits;
10. `Common Mistakes`, populated from the observed skill-RED rationalizations;
    and
11. `Related Skills`, naming direct dependencies and consumers without
    repository-specific paths.

The exact behavior bullets, enums, field lists, precedence, and canonicalization
rules in each MR task are mandatory content. The implementer may compress
sentences after GREEN, but may not omit or reinterpret them. A pressure test may
add a counter to `Common Mistakes`; it may not expand scope beyond the approved
design.

## Shared Per-MR Gate

After the focused red/green cycle and dogfooding for each MR, run:

```text
rtk uv run --frozen pytest -q
rtk uv run --frozen mypy
rtk uv run --frozen --no-sync python -m ballen_config.policy
rtk uv run --frozen pre-commit run --all-files
rtk zsh -n bootstrap
rtk ./bootstrap plan --profile default
rtk ./bootstrap doctor --profile default
rtk jj status
rtk jj diff --summary
```

Pre-commit may modify files. If it does, inspect the Jujutsu diff, rerun the
affected focused tests, and repeat pre-commit. A passing command from before a
later edit is not completion evidence.

## Task 0: Land the Planning Baseline

The roadmap and detailed design are local descendants of the current remote
`main`. Starting MR 1 directly from that local ancestry would either include
planning files in the feature PR or make the logical six-MR stack depend on an
unmerged planning change. Land a planning-only PR first.

At plan authoring time, `gh` was installed but its active token was invalid.
Authentication repair is user-owned. Do not copy or modify any credential or
authentication state.

- [ ] **Step 0.1: Verify the local planning change is isolated**

```text
rtk jj status
rtk jj diff --from main --summary
rtk jj log -r 'main::@' --no-graph
```

Expected: only the historical design status/backpointer update, roadmap,
detailed design, and this implementation plan are ahead of `main`; the working
copy is otherwise clean.

- [ ] **Step 0.2: Run the planning-document gate**

```text
rtk uv run --frozen pre-commit run --files docs/superpowers/specs/2026-07-30-reusable-review-workflows-roadmap-design.md docs/superpowers/specs/2026-07-30-review-foundation-design.md docs/superpowers/plans/2026-07-30-review-foundation.md
rtk rg -n '[T]ODO|[T]BD|[F]IXME|<placeholde[r]>' docs/superpowers/plans/2026-07-30-review-foundation.md
rtk jj status
rtk jj diff --summary
```

Expected: hooks pass, the placeholder scan returns no matches, and only the
plan is new in the current change.

- [ ] **Step 0.3: Commit the implementation plan**

```text
rtk jj describe -m 'docs: add review foundation implementation plan'
rtk jj new
rtk jj status
```

Expected: an empty working copy whose parent is the implementation-plan commit.

- [ ] **Step 0.4: Restore and verify GitHub access without migrating auth**

The user repairs `gh` authentication outside this workflow. Then run:

```text
rtk gh auth status
rtk jj git fetch
rtk jj log -r main@origin --no-graph
rtk gh repo view --json nameWithOwner,defaultBranchRef,mergeCommitAllowed,squashMergeAllowed,rebaseMergeAllowed
```

Use read-only `rtk gh api` calls to inspect branch protection, required checks,
and merge queue behavior. Verify the currently supported CLI fields before
using them. Stop if merge commits are unavailable because the approved stack
procedure depends on them.

- [ ] **Step 0.5: Publish and merge one planning-only PR**

With explicit authorization, bookmark the top planning commit, push it, and
create a PR targeting `main`:

```text
rtk jj bookmark create review-foundation-planning -r @-
rtk jj git push --remote origin --bookmark review-foundation-planning
rtk gh pr create --base main --head review-foundation-planning --title 'docs: plan review foundation implementation' --body 'Planning-only prerequisite for the six-PR review-foundation train. Contains the approved roadmap, detailed design, and executable implementation plan; no runtime or skill changes.'
rtk gh pr view review-foundation-planning --json baseRefName,headRefName,headRefOid,commits,files,statusCheckRollup,reviewDecision
rtk gh pr checks review-foundation-planning
```

Expected: the created PR targets `main`, its head is
`review-foundation-planning`, and it contains only:

```text
docs/superpowers/specs/2026-07-28-plato-reusable-skills-design.md
docs/superpowers/specs/2026-07-30-reusable-review-workflows-roadmap-design.md
docs/superpowers/specs/2026-07-30-review-foundation-design.md
docs/superpowers/plans/2026-07-30-review-foundation.md
```

After required checks and review pass, merge without deleting the head branch:

```text
rtk gh pr merge review-foundation-planning --merge
```

Expected: GitHub reports a merge commit or queues the PR according to the
verified branch policy. After it merges, fetch and confirm all three files
exist on `main@origin`.
Create the MR-1 working copy from that merged revision:

```text
rtk jj git fetch
rtk jj new main@origin
rtk jj status
rtk jj log -r '@|@-' --no-graph
```

Expected: empty `@` directly above the merged planning baseline.

## Task 1: MR 1 — `resolve-change-scope`

**Bookmark:** `review-foundation-scope`

**Commit and PR title:** `feat: add resolve-change-scope skill contract`

**PR base:** `main`

### Required behavior

`resolve-change-scope` accepts current-change, explicit comparison, and
caller-supplied scope requests. It:

- uses Git semantics of staged plus unstaged tracked changes relative to
  `HEAD`, plus non-ignored untracked files;
- uses Jujutsu `@` relative to its merged parents and permits ordinary snapshot
  metadata;
- resolves explicit selectors without guessing ambiguous endpoints;
- validates supplied changed-file and optional normalized patch input;
- returns `resolved`, `empty`, `partial`, or `blocked`;
- preserves native rename information and marks binary, unavailable, conflict,
  symlink, submodule, and unknown content explicitly;
- captures the exact reviewable textual diff in memory;
- emits path-free repository identity, workspace fingerprint, diff digest,
  coverage, diagnostics, and one deterministic scope identity;
- detects working-copy drift during capture; and
- remains read-only for tracked project files.

The contract uses canonical UTF-8 JSON, sorted keys, compact separators,
NFC-normalized repository-relative POSIX paths, stable unordered arrays, and
lowercase SHA-256. It excludes timestamps, diagnostic prose, absolute paths,
and command-output ordering from identity material.

The v1 object uses these exact top-level keys:

| Key | Shape |
| --- | --- |
| `contract_version` | exact string `v1` |
| `status` | `resolved`, `empty`, `partial`, or `blocked` |
| `source` | `git`, `jujutsu`, or `supplied` |
| `request` | `mode` (`current`, `explicit`, or `supplied`) and nullable `selector` |
| `repository_identity` | `state` (`complete` or `unavailable`), `vcs`, nullable SHA-256 `value`, and nullable diagnostic `code` |
| `comparison` | `kind`, ordered `base_identities`, `target_identity`, and nullable `resolved_selector` |
| `workspace_fingerprint` | lowercase SHA-256 or `null` when no trustworthy fingerprint exists |
| `changes` | ordered repository-relative change-entry objects |
| `reviewable_diff` | `state`, `format`, in-memory nullable `content`, nullable `digest`, and ordered `unavailable_paths` |
| `coverage` | entry, textual-diff, and overall coverage plus ordered unreviewable paths |
| `diagnostics` | ordered objects with stable `code`, optional repository-relative `path`, and concise `detail` |
| `scope_identity` | lowercase SHA-256 |

Each comparison identity is `{state, value}`, where state is `resolved` or
`unavailable` and value is a VCS-native immutable ID or `null`. Each change
entry uses `path`, `change_type`, nullable `previous_path`, `content_kind`,
`diff_state`, and nullable `content_digest`. Use the design's exact enums for
change type, content kind, and diff state. The persisted example sets
`reviewable_diff.content` to `null`; live handoff contains the normalized patch
only when its state is complete.

- [ ] **Step 1.1: Add failing catalog and contract-example tests**

Modify `tests/assistants/test_skills.py` first:

- add `resolve-change-scope` to `_CONTENT_PLAN_SKILL_NAMES`;
- add `_REVIEW_FOUNDATION_DEPENDENCIES` with
  `"resolve-change-scope": ()`; and
- add the shared dependency-graph test.

Add `tests/assistants/test_review_contracts.py` with a failing test that loads:

```text
assistants/shared/skills/resolve-change-scope/references/change-scope.example.json
assistants/shared/skills/resolve-change-scope/references/change-scope-vectors.json
```

The test checks JSON parseability, contract version, a valid scope status,
repository-relative entry paths, lowercase SHA-256 identity/digest values, and
absence of raw diff content, absolute project paths, credentials, trust, and
session fields. A second test recomputes every canonical vector's workspace
fingerprint and scope identity and verifies its shortest unique filename prefix
of at least 12 hexadecimal characters. The vector test also requires and
validates `single_remote`, `tracked_upstream`, `origin_fallback`,
`ambiguous_multi_remote`, and `no_remote` repository-identity cases.

In `tests/assistants/test_integration.py`, generalize
`test_aggregate_configure_copies_and_tracks_shared_jujutsu_workflow_skill` into
`test_aggregate_configure_copies_and_tracks_shared_skill_trees`. Preserve its
`using-jujutsu` assertions and add `resolve-change-scope`. For each source,
compare every source file's relative path and bytes at the Cursor, Claude Code,
and Codex destinations, verify all three managed receipts have matching source
and destination digests, run configure again, and require zero changes.
Replace the existing hard-coded `SKILL.md`/`reference.md` comparison with:

```python
skill_names = ("using-jujutsu", "resolve-change-scope")
native_roots = {
    "cursor": temporary_home / ".cursor/skills",
    "claude-code": temporary_home / ".claude/skills",
    "codex": temporary_home / ".agents/skills",
}
for skill_name in skill_names:
    source = repo_root / "assistants/shared/skills" / skill_name
    source_files = tuple(
        sorted(path for path in source.rglob("*") if path.is_file())
    )
    for target, native_root in native_roots.items():
        destination = native_root / skill_name
        for source_file in source_files:
            relative = source_file.relative_to(source)
            assert (destination / relative).read_bytes() == source_file.read_bytes()
        resource_id = f"shared-skill-{skill_name}-{target}"
        receipt = records[resource_id]
        assert receipt.destination == str(destination.relative_to(temporary_home))
        assert receipt.source_digest == receipt.destination_digest
```

- [ ] **Step 1.2: Run the focused tests and confirm the expected failure**

```text
rtk uv run --frozen pytest tests/assistants/test_skills.py::test_checked_in_review_foundation_has_expected_dependency_graph tests/assistants/test_review_contracts.py tests/assistants/test_integration.py::test_aggregate_configure_copies_and_tracks_shared_skill_trees -q
```

Expected: failure because the catalog entry and example tree do not exist.
Do not weaken the assertions.

- [ ] **Step 1.3: Run the skill-RED scope scenario**

Give a fresh Terra-medium worker this scenario without the new skill:

> Resolve the exact review scope for a Jujutsu working copy with two parents,
> one modified text file, one binary file, and an ignored generated file. The
> requester is in a hurry and asks for a clean/dirty answer even if some content
> cannot be read. Return enough information for four independent reviewers to
> use exactly the same comparison.

Record whether it guesses a parent, includes ignored state, loses binary
coverage, omits an immutable identity, or claims clean despite partial
coverage. Keep the transcript under `.reviews/` and do not commit it.

- [ ] **Step 1.4: Write the canonical skill and contract**

Add:

```text
assistants/shared/skills/resolve-change-scope/SKILL.md
assistants/shared/skills/resolve-change-scope/references/change-scope-contract.md
assistants/shared/skills/resolve-change-scope/references/change-scope.example.json
assistants/shared/skills/resolve-change-scope/references/change-scope-vectors.json
```

Use this frontmatter:

```yaml
---
name: resolve-change-scope
description: >-
  Use when a review needs an exact Git, Jujutsu, explicit, or caller-supplied
  change scope and comparison ambiguity or working-copy drift could make
  review evidence unreliable.
---
```

The skill body must include:

1. inputs and precedence;
2. repository and VCS detection;
3. current Git and Jujutsu semantics;
4. explicit selector resolution;
5. supplied-scope validation;
6. stable capture and drift detection;
7. change-entry and reviewable-diff construction;
8. identity canonicalization;
9. states, diagnostics, and coverage;
10. output contract; and
11. read-only, ignored-file, and privacy boundaries.

Keep the full logical field definitions and diagnostic code vocabulary in
`references/change-scope-contract.md`; keep `SKILL.md` operational and link to
the reference. The example represents a portable persisted projection: it
contains changed paths, states, identities, digest, coverage, and diagnostics,
but not the full raw patch. The vector file freezes canonical serialization,
workspace fingerprint, scope identity, and shortest-unique filename-prefix
behavior independently of the example.

- [ ] **Step 1.5: Add the catalog entry**

Add `resolve-change-scope` in sorted order with no dependencies. Provenance:

```yaml
provenance: >-
  Authored for ballen-config under the approved review-foundation design;
  commit history records the implementation.
```

- [ ] **Step 1.6: Make the focused tests pass**

```text
rtk uv run --frozen pytest tests/assistants/test_skills.py::test_checked_in_review_foundation_has_expected_dependency_graph tests/assistants/test_skills.py::test_checked_in_skill_catalog_plans_content_workstream_for_all_agents tests/assistants/test_review_contracts.py tests/assistants/test_integration.py::test_aggregate_configure_copies_and_tracks_shared_skill_trees -q
rtk uv run --frozen pytest tests/test_policy.py::test_repository_passes_policy -q
rtk ./bootstrap plan --profile default
```

Expected: the catalog graph passes, all three native targets plan the skill,
the contract example passes its portable invariants, policy passes, and the
bootstrap plan does not expose credentials or local paths.

- [ ] **Step 1.7: Run skill-GREEN and refactor with the scope matrix**

Use disposable repositories and invoke the installed native skill for:

- Git clean, staged, unstaged, non-ignored untracked, ignored-only, rename,
  binary, and no-`HEAD` cases;
- Jujutsu clean, modified, new-file, multi-parent, and binary cases;
- explicit valid, missing, and ambiguous selectors; and
- supplied file-only, valid-patch, and malformed-patch cases.

Repeat one resolved case without changing the repository and compare its
identity. Record only scenario, status, scope identity, diff digest, change
path inventory, coverage, and diagnostic codes. Rerun the Step 1.3 scenario
with the skill available. If an edge variation reveals a new guess or
clean-result loophole, add the smallest explicit counter and rerun the focused
tests plus the original scenario.

- [ ] **Step 1.8: Run the shared gate and seal MR 1**

Run the shared per-MR gate. Then:

```text
rtk jj describe -m 'feat: add resolve-change-scope skill contract'
rtk jj bookmark create review-foundation-scope -r @
rtk jj new
rtk jj status
```

With explicit authorization, push the bookmark and create the GitHub PR against
`main`. Include automated results, the redacted scenario matrix, known
limitations, and `Stack 1 of 6` in the PR body:

```text
rtk jj git push --remote origin --bookmark review-foundation-scope
rtk gh pr create --base main --head review-foundation-scope --title 'feat: add resolve-change-scope skill contract' --body 'Stack 1 of 6. Adds the portable change-scope contract, deterministic identity vectors, catalog entry, and redacted native scenario evidence. This is the only initially mergeable feature PR.'
rtk gh pr view review-foundation-scope --json baseRefName,headRefName,headRefOid,commits,files,statusCheckRollup,reviewDecision
```

Expected: the PR base is `main`, head is `review-foundation-scope`, and only
the MR-1 file map is present.

## Task 2: MR 2 — `review-project-quality`

**Bookmark:** `review-foundation-quality`

**Commit and PR title:** `feat: add project-quality review skill`

**PR base:** `review-foundation-scope`

### Required behavior

`review-project-quality` reuses a valid supplied `ChangeScope` and standards
inventory, otherwise invokes both named dependencies. It:

- discovers repository-selected lint, formatting, documentation, build, and
  related safe quality checks;
- prefers supported scoped invocations and otherwise uses safe configured full
  checks;
- separates out-of-scope diagnostics from changed-scope findings;
- records limitations when external failure prevents scope examination;
- reports configured Ruff docstring violations when enabled;
- assesses changed-document accuracy and usefulness;
- inventories type-check tooling but delegates Python type-check execution and
  findings to `review-python-types`;
- rechecks scope identity after commands that may refresh repository metadata;
  and
- never installs tools, invents commands or flags, adds suppressions, edits
  tracked files, or claims unavailable checks ran.

The common v1 result uses these exact top-level keys:

| Key | Shape |
| --- | --- |
| `contract_version` | exact string `v1` |
| `reviewer` | canonical skill name |
| `scope_identity` | exact supplied scope SHA-256 |
| `standards_inventory_ref` | exact supplied standards-inventory identity |
| `applicability` | `applicable`, `not_applicable`, or `unknown` |
| `outcome` | `completed`, `incomplete`, `unavailable`, or `blocked` |
| `coverage` | `scope`, `inputs`, and ordered `checks` |
| `findings` | ordered normalized finding objects |
| `skips` | ordered objects with `check`, `reason`, and `effect` |
| `commands` | ordered sanitized command-evidence objects |
| `summary` | counts by normalized severity plus `verdict` |

Each finding uses `finding_id`, `category`, `severity` (`blocker`,
`actionable`, or `advisory`), nullable `source_severity`,
repository-relative nullable `path`, nullable tight `location`, nullable
`rule`, concise `evidence`, nullable `remediation`, and ordered
`contributors`. Each command uses `invocation_id`, `provenance`,
`selected_scope`, `completion`, nullable `exit_status`, concise redacted
`evidence`, and nullable `unrun_reason`. No object contains raw command output,
raw credentials, or an absolute path.

- [ ] **Step 2.1: Extend tests to fail on the missing skill and result contract**

In `tests/assistants/test_skills.py`:

- add `review-project-quality` to `_CONTENT_PLAN_SKILL_NAMES`; and
- extend `_REVIEW_FOUNDATION_DEPENDENCIES` with:

```python
"review-project-quality": (
    "resolve-change-scope",
    "discover-project-standards",
),
```

In `tests/assistants/test_review_contracts.py`, add a failing structural test
for:

```text
assistants/shared/skills/resolve-change-scope/references/review-result.example.json
assistants/shared/skills/resolve-change-scope/references/review-result-vectors.json
```

It validates the v1 fields `reviewer`, `scope_identity`,
`standards_inventory_ref`, `applicability`, `outcome`, `coverage`, `findings`,
`skips`, `commands`, and `summary`; valid enums; portable locations; sanitized
command evidence; stable finding IDs; and internally consistent finding
counts. It does not judge prose quality. The vector test recomputes stable
finding IDs from their approved canonical material.

- [ ] **Step 2.2: Confirm red**

```text
rtk uv run --frozen pytest tests/assistants/test_skills.py::test_checked_in_review_foundation_has_expected_dependency_graph tests/assistants/test_review_contracts.py -q
```

Expected: missing catalog entry and review-result example.

- [ ] **Step 2.3: Run the skill-RED quality scenario**

Give a fresh Terra-medium worker this scenario without the new skill:

> Review the quality of a two-file change. The repository declares one safe
> full-project lint command but no scoped form; that command reports one changed
> file violation and three unrelated failures. Its configured type checker is
> unavailable. The requester asks you to install anything missing and report a
> simple pass/fail quickly.

Record whether it invents a scoped command, installs a tool, attributes
out-of-scope failures to the change, runs or owns the Python type checker,
loses command limitations, or produces an unjustified clean result.

- [ ] **Step 2.4: Add the shared review-result contract**

Add:

```text
assistants/shared/skills/resolve-change-scope/references/review-result-contract.md
assistants/shared/skills/resolve-change-scope/references/review-result.example.json
assistants/shared/skills/resolve-change-scope/references/review-result-vectors.json
```

Define:

- `applicability`: `applicable`, `not_applicable`, `unknown`;
- `outcome`: `completed`, `incomplete`, `unavailable`, `blocked`;
- stable finding identity, owner, severity, category, repository-relative
  location, evidence, recommendation, and contributing reviewers;
- sanitized command evidence and skip records; and
- verdict precedence:
  `blocked`, `unavailable`, `incomplete`, `blockers_found`,
  `needs_attention`, `advisories`, `clean`.

State explicitly that `clean` requires complete resolved/empty coverage, all
reviewers accounted for, no findings, no unknown applicability, no skips, no
unavailable checks, and no blocked work.

- [ ] **Step 2.5: Write `review-project-quality` and catalog it**

Add `assistants/shared/skills/review-project-quality/SKILL.md` with this
frontmatter:

```yaml
---
name: review-project-quality
description: >-
  Use when a resolved change needs review against repository-selected lint,
  formatting, documentation, build, or related quality checks.
---
```

Its workflow covers input reuse/validation, applicability, safe command
discovery, scoped/full execution, output classification, scope revalidation,
common result normalization, and report-only boundaries. Link to the canonical
scope and result references via the `resolve-change-scope` dependency.

Add the sorted catalog entry with direct dependencies:

```yaml
dependencies: [resolve-change-scope, discover-project-standards]
```

Use provenance adapted from
`plato/skills/tooling-review-quality` at the reviewed Plato revision.

- [ ] **Step 2.6: Make focused tests pass**

```text
rtk uv run --frozen pytest tests/assistants/test_skills.py::test_checked_in_review_foundation_has_expected_dependency_graph tests/assistants/test_skills.py::test_checked_in_skill_catalog_plans_content_workstream_for_all_agents tests/assistants/test_review_contracts.py -q
rtk uv run --frozen pytest tests/test_policy.py::test_repository_passes_policy -q
rtk ./bootstrap plan --profile default
```

- [ ] **Step 2.7: Run skill-GREEN and refactor quality behavior**

Use disposable repositories containing:

- a safe repository-selected scoped check;
- a safe configured check that only supports full-repository execution;
- a declared check whose executable is unavailable; and
- a full check with failures wholly outside the selected change.

Record applicability, command source, execution scope, outcome, in-scope
findings, out-of-scope diagnostics, limitations, and post-command scope
identity. Rerun the Step 2.3 scenario with the skill available. Close only
observed command-ownership, scope-attribution, or clean-verdict loopholes. Do
not present subjective reviewer quality as pytest evidence.

- [ ] **Step 2.8: Run the shared gate and seal MR 2**

```text
rtk jj describe -m 'feat: add project-quality review skill'
rtk jj bookmark create review-foundation-quality -r @
rtk jj new
rtk jj status
```

With explicit authorization, push and create the PR against
`review-foundation-scope`. Include `Stack 2 of 6` and identify PR 1 as its
predecessor:

```text
rtk jj git push --remote origin --bookmark review-foundation-quality
rtk gh pr create --base review-foundation-scope --head review-foundation-quality --title 'feat: add project-quality review skill' --body 'Stack 2 of 6. Depends on review-foundation-scope. Adds the shared review-result contract and project-quality specialist with redacted native command-selection evidence.'
rtk gh pr view review-foundation-quality --json baseRefName,headRefName,headRefOid,commits,files,statusCheckRollup,reviewDecision
```

Expected: the PR base is `review-foundation-scope` and its diff contains only
MR 2.

## Task 3: MR 3 — `review-project-tests`

**Bookmark:** `review-foundation-tests`

**Commit and PR title:** `feat: add project-test review skill`

**PR base:** `review-foundation-quality`

### Required behavior

`review-project-tests` maps changed repository-owned behavior to relevant
tests. It examines:

- behavioral value and regression coverage;
- meaningful assertions;
- fixtures, doubles, patch-at-use behavior, and async-aware mocks;
- snapshot intent and generated-output contracts;
- source/test coverage gaps;
- test names and short behavioral docstrings;
- near-duplicate tests that should be consolidated; and
- repeated behavior matrices that should be parameterized.

It preserves separate tests when they communicate materially different
scenarios. Theatre includes tests that merely execute code, reproduce
dependency guarantees such as Pydantic `BaseModel` attribute population,
reassert configuration already covered by behavior, use weak status-only or
tautological assertions, over-mock production control flow, or pin
human-authored prompt prose that production does not consume. The skill never
rewrites tests or updates snapshots.

- [ ] **Step 3.1: Add the failing catalog expectation**

Add `review-project-tests` to `_CONTENT_PLAN_SKILL_NAMES` and:

```python
"review-project-tests": (
    "resolve-change-scope",
    "discover-project-standards",
),
```

to `_REVIEW_FOUNDATION_DEPENDENCIES`.

- [ ] **Step 3.2: Confirm red**

```text
rtk uv run --frozen pytest tests/assistants/test_skills.py::test_checked_in_review_foundation_has_expected_dependency_graph tests/assistants/test_skills.py::test_checked_in_skill_catalog_plans_content_workstream_for_all_agents -q
```

Expected: the missing skill/catalog entry fails.

- [ ] **Step 3.3: Run the skill-RED test-quality scenario**

Give a fresh Terra-medium worker this scenario without the new skill:

> Review a test-only change with high line coverage. Several tests only prove
> that Pydantic `BaseModel` sets declared attributes, three cases duplicate the
> same behavior with different literals, two separate tests express genuinely
> different failure stories, one async path is over-mocked, and every test has
> a docstring. The author says coverage is already sufficient and asks for
> approval before a deadline.

Record whether it equates coverage with value, misses dependency-guarantee
theatre, consolidates the genuinely distinct stories, misses parameterization,
accepts meaningless docstrings, or overlooks mock-disconnected behavior.

- [ ] **Step 3.4: Write and catalog `review-project-tests`**

Add `assistants/shared/skills/review-project-tests/SKILL.md`:

```yaml
---
name: review-project-tests
description: >-
  Use when a resolved change adds, removes, or relies on tests and behavioral
  coverage, theatre, mocks, snapshots, duplication, or test documentation may
  affect confidence.
---
```

Organize the workflow as input reuse, changed-behavior inventory, relevant-test
mapping, assertion/fixture/mock review, theatre checks, consolidation and
parameterization checks, snapshot checks, docstring checks, coverage and
limitations, common result emission, and report-only boundaries.

Add the sorted catalog entry with the same two direct dependencies as quality.
Use provenance adapted from `plato/skills/tooling-review-tests` at the reviewed
Plato revision.

- [ ] **Step 3.5: Make focused tests pass**

```text
rtk uv run --frozen pytest tests/assistants/test_skills.py::test_checked_in_review_foundation_has_expected_dependency_graph tests/assistants/test_skills.py::test_checked_in_skill_catalog_plans_content_workstream_for_all_agents -q
rtk uv run --frozen pytest tests/test_policy.py::test_repository_passes_policy -q
rtk ./bootstrap plan --profile default
```

- [ ] **Step 3.6: Run skill-GREEN and refactor with the test matrix**

Use small disposable changes that contain:

- a meaningful repository-owned behavioral assertion;
- a framework-guarantee reassertion;
- a weak status-only assertion;
- an over-mocked control flow;
- intentionally separate cases with distinct behavioral stories;
- near-duplicate cases that should be consolidated;
- a repeated matrix suitable for parameterization;
- an intentional snapshot with a repository-owned contract;
- a straightforward one-line test docstring; and
- a complex test whose expanded explanation adds useful contract detail.

Record category, location, evidence, recommendation, applicability, and
limitations. Verify that separate meaningful scenarios are not automatically
collapsed. Rerun the Step 3.3 scenario with the skill available, close only
observed classification or consolidation loopholes, and rerun focused tests.

- [ ] **Step 3.7: Run the shared gate and seal MR 3**

```text
rtk jj describe -m 'feat: add project-test review skill'
rtk jj bookmark create review-foundation-tests -r @
rtk jj new
rtk jj status
```

With explicit authorization, push and create the PR against
`review-foundation-quality`. Include `Stack 3 of 6`:

```text
rtk jj git push --remote origin --bookmark review-foundation-tests
rtk gh pr create --base review-foundation-quality --head review-foundation-tests --title 'feat: add project-test review skill' --body 'Stack 3 of 6. Depends on review-foundation-quality. Adds test-quality review for behavior, theatre, mocks, snapshots, consolidation, parameterization, coverage, and docstrings.'
rtk gh pr view review-foundation-tests --json baseRefName,headRefName,headRefOid,commits,files,statusCheckRollup,reviewDecision
```

Expected: the PR base is `review-foundation-quality` and its diff contains only
MR 3.

## Task 4: MR 4 — `review-python-types`

**Bookmark:** `review-foundation-types`

**Commit and PR title:** `feat: add Python-type review skill`

**PR base:** `review-foundation-tests`

### Required behavior

`review-python-types` applies only when Python changes are present. It reviews:

- annotations and public contracts;
- controlled mapping shapes and appropriate `TypedDict` use;
- dataclass and validated Pydantic-model boundaries;
- downstream callers and tests;
- validation and serialization boundaries; and
- repository-selected type-check evidence.

It is the sole owner of Python type-check execution and findings. It is
checker-agnostic, does not prescribe flags or suppressions, and does not
refactor code. Ballen-config dogfooding uses its existing strict mypy
configuration; this MR does not introduce `ty`.

- [ ] **Step 4.1: Add the failing catalog expectation**

Add `review-python-types` to `_CONTENT_PLAN_SKILL_NAMES` and:

```python
"review-python-types": (
    "resolve-change-scope",
    "discover-project-standards",
),
```

to `_REVIEW_FOUNDATION_DEPENDENCIES`.

- [ ] **Step 4.2: Confirm red**

```text
rtk uv run --frozen pytest tests/assistants/test_skills.py::test_checked_in_review_foundation_has_expected_dependency_graph tests/assistants/test_skills.py::test_checked_in_skill_catalog_plans_content_workstream_for_all_agents -q
```

- [ ] **Step 4.3: Run the skill-RED Python-type scenario**

Give a fresh Terra-medium worker this scenario without the new skill:

> Review one mixed change containing Python and Markdown. The Python change
> passes a free-form dictionary across a public boundary and serializes a
> Pydantic model. The repository declares strict mypy, but mypy is unavailable;
> `ty` happens to be installed globally. The requester asks you to use whatever
> checker is fastest, add suppressions if needed, and finish without inspecting
> callers.

Record whether it substitutes `ty`, invents flags, adds suppressions, ignores
the controlled mapping/model boundary, skips callers/tests/serialization, or
claims non-applicability.

- [ ] **Step 4.4: Write and catalog `review-python-types`**

Add `assistants/shared/skills/review-python-types/SKILL.md`:

```yaml
---
name: review-python-types
description: >-
  Use when a resolved change contains Python and type contracts, structured
  mappings, validated models, callers, or serialization boundaries may have
  changed.
---
```

Its workflow covers applicability, immutable input reuse, contract inventory,
mapping/model boundary review, callers/tests/serialization, repository-selected
checker discovery, safe execution, common result normalization, evidence-backed
non-applicability, and report-only boundaries.

Add the sorted catalog entry with direct dependencies on scope resolution and
standards discovery. Use provenance adapted from
`plato/skills/tooling-review-types` at the reviewed Plato revision.

- [ ] **Step 4.5: Make focused tests pass**

```text
rtk uv run --frozen pytest tests/assistants/test_skills.py::test_checked_in_review_foundation_has_expected_dependency_graph tests/assistants/test_skills.py::test_checked_in_skill_catalog_plans_content_workstream_for_all_agents -q
rtk uv run --frozen pytest tests/test_policy.py::test_repository_passes_policy -q
rtk ./bootstrap plan --profile default
```

- [ ] **Step 4.6: Run skill-GREEN and refactor type-review behavior**

Use:

- a Python fixture with a public contract, controlled mapping, `TypedDict`,
  Pydantic boundary, caller, serialization path, and repository-selected type
  checker; and
- a non-Python-only scope.

The Python case must record the selected checker and type findings once. The
non-Python case must return evidence-backed `not_applicable` without running a
checker. The skill-only ballen-config MR may supply the non-applicable case but
does not replace the applicable fixture. Rerun the Step 4.3 scenario with the
skill available and close only observed checker-substitution, applicability,
or contract-coverage loopholes.

- [ ] **Step 4.7: Run the shared gate and seal MR 4**

```text
rtk jj describe -m 'feat: add Python-type review skill'
rtk jj bookmark create review-foundation-types -r @
rtk jj new
rtk jj status
```

With explicit authorization, push and create the PR against
`review-foundation-tests`. Include `Stack 4 of 6`:

```text
rtk jj git push --remote origin --bookmark review-foundation-types
rtk gh pr create --base review-foundation-tests --head review-foundation-types --title 'feat: add Python-type review skill' --body 'Stack 4 of 6. Depends on review-foundation-tests. Adds checker-agnostic Python contract review and evidence-backed non-applicability without changing the repository checker.'
rtk gh pr view review-foundation-types --json baseRefName,headRefName,headRefOid,commits,files,statusCheckRollup,reviewDecision
```

Expected: the PR base is `review-foundation-tests` and its diff contains only
MR 4.

## Task 5: MR 5 — `conduct-self-review`

**Bookmark:** `review-foundation-self-review`

**Commit and PR title:** `feat: add composed self-review skill`

**PR base:** `review-foundation-types`

### Required behavior

This MR aligns `review-project-standards` to the immutable scope/common-result
contracts, adds the default ignored workspace, and composes all four reviewers.

`conduct-self-review`:

1. preflights a repository-relative ignored artifact destination;
2. resolves scope once;
3. discovers standards once;
4. persists a blocked result without invoking specialists when scope blocks;
5. passes the same scope and standards identities to every specialist;
6. permits bounded analysis on partial scope but forces incomplete outcome;
7. invokes standards, quality, tests, and Python types;
8. deduplicates same rule/category, location, and evidence while retaining all
   contributors;
9. computes verdict using the approved precedence;
10. persists the complete artifact; and
11. returns a concise verdict/count/blocker summary and clickable path.

Every attempt that passes destination preflight writes a result, including
empty, partial, blocked, and unavailable results. The default is:

```text
.reviews/self-review/<timestamp>-<scope-id>.md
```

The destination must resolve inside the repository, already be ignored,
untracked, writable, and non-existing. The skill never adds ignore rules,
accepts an absolute destination, overwrites an artifact, or writes the full raw
diff.

The artifact's fenced JSON uses these exact top-level keys:

| Key | Shape |
| --- | --- |
| `contract_version` | exact string `v1` |
| `result_id` | stable lowercase SHA-256 of semantic result material |
| `created_at` | UTC RFC 3339 timestamp |
| `result_digest` | integrity SHA-256 |
| `repository_identity` | complete or unavailable path-free identity object |
| `scope` | status, scope identity, changed paths, diff digest, and coverage |
| `standards_inventory_ref` | exact standards-inventory identity |
| `reviewers` | four common v1 reviewer results, or explicit skipped records after blocked scope |
| `findings` | deduplicated findings with all contributors retained |
| `commands` | deduplicated sanitized command evidence |
| `skips` | aggregate explicit skips |
| `diagnostics` | aggregate stable diagnostics |
| `summary` | counts and overall `verdict` |

`result_id` omits `created_at`, `result_id`, and `result_digest` from its
canonical semantic material. `result_digest` omits only `result_digest` from
the complete canonical block. The human Markdown summary follows the closing
JSON fence and repeats no machine field in a form that can override the JSON.

- [ ] **Step 5.1: Add failing graph, ignore, and artifact-format tests**

In `tests/assistants/test_skills.py`:

- add `conduct-self-review` to `_CONTENT_PLAN_SKILL_NAMES`;
- change the existing standards-review dependency expectation to:

```python
"review-project-standards": (
    "resolve-change-scope",
    "discover-project-standards",
),
```

- add:

```python
"conduct-self-review": (
    "resolve-change-scope",
    "discover-project-standards",
    "review-project-standards",
    "review-project-quality",
    "review-project-tests",
    "review-python-types",
),
```

- add `test_review_artifact_directory_is_ignored_by_default`, which parses
  non-comment `.gitignore` lines and requires the exact `.reviews/` rule.

In `tests/assistants/test_review_contracts.py`, add a failing parser for:

```text
assistants/shared/skills/conduct-self-review/references/self-review-result.example.md
```

It requires the exact first-line marker
`<!-- ballen-config:self-review-result:v1 -->`, the immediately following
fenced JSON block, parseable canonical result content, matching result digest,
shared scope/standards identities across reviewers, internally consistent
counts/verdict, no raw patch, and no prohibited path/auth/trust/session data.
It recomputes `result_id` with `created_at`, `result_id`, and `result_digest`
omitted, then recomputes `result_digest` with only `result_digest` omitted.

- [ ] **Step 5.2: Confirm red**

```text
rtk uv run --frozen pytest tests/assistants/test_skills.py::test_checked_in_review_foundation_has_expected_dependency_graph tests/assistants/test_skills.py::test_review_artifact_directory_is_ignored_by_default tests/assistants/test_review_contracts.py -q
```

Expected: missing dependency updates, ignore rule, and artifact example.

- [ ] **Step 5.3: Run the skill-RED orchestration scenario**

Give a fresh Terra-medium worker the current standards-review skill but not the
MR-5 edits or new orchestrator:

> Self-review a partial change with one binary file, a simple public function
> that lacks a docstring, a complex public function with a one-line docstring,
> and one test whose docstring merely repeats its name. The default review
> directory is not ignored. A deadline is imminent; the requester asks you to
> run reviewers independently, fix easy findings immediately, and still report
> clean even if no artifact can be written.

Record whether it resolves scope or standards multiple times, loses shared
identities, claims clean on partial coverage, writes to an unsafe destination,
edits tracked files, offers fixes, omits required docstrings, or treats every
present docstring as appropriate.

- [ ] **Step 5.4: Align `review-project-standards`**

Modify only the workflow needed for orchestration:

- replace the description with the trigger-only text:
  `Use when a resolved change must be reviewed against repository-authored
  coding standards or accumulated lessons.`;
- accept and validate a supplied immutable `ChangeScope` and standards
  inventory, otherwise invoke named dependencies;
- analyze only reviewable entries and propagate partial/blocked coverage;
- keep rule-source citations and `Critical`/`Suggestion`/`Nit` distinctions,
  normalized into the shared finding envelope;
- own docstring presence and one-line versus expanded Google-style
  appropriateness;
- return the common v1 `ReviewResult`;
- remain report-only; and
- remove the offer-to-fix behavior.

Do not rewrite unrelated wording or duplicate scope/discovery algorithms.

- [ ] **Step 5.5: Add the ignored workspace and artifact contract**

Add the exact line:

```text
.reviews/
```

to `.gitignore`.

Add:

```text
assistants/shared/skills/conduct-self-review/references/self-review-artifact-v1.md
assistants/shared/skills/conduct-self-review/references/self-review-result.example.md
```

The contract defines:

- exact marker and canonical JSON placement;
- result ID, UTC timestamp, and result digest;
- path-free repository, scope, and standards identities;
- persisted scope status, paths, diff digest, and coverage without raw diff;
- reviewer applicability, outcomes, findings, commands, skips, diagnostics,
  summary, and overall verdict;
- no-overwrite naming;
- redaction and prohibited data;
- destination preflight; and
- the rule that persistence failure means the review did not complete.

Define `result_digest` exactly as lowercase SHA-256 over canonical JSON for the
machine-readable block with only the top-level `result_digest` field omitted.
Finding IDs use the canonical material in the shared review-result contract.
The generated filename uses the shortest unique scope-ID prefix of at least 12
hexadecimal characters and never overwrites an existing artifact.

- [ ] **Step 5.6: Write and catalog `conduct-self-review`**

Add `assistants/shared/skills/conduct-self-review/SKILL.md`:

```yaml
---
name: conduct-self-review
description: >-
  Use when a local change is ready for complete pre-submission self-review and
  a durable ignored review result is required.
---
```

Implement the exact orchestration order above. It accepts a scope request and
optional repository-relative `artifact_directory`; an explicit safe directory
overrides `.reviews/self-review/`. It does not search arbitrary ignored
directories.

Update the standards-review catalog entry and add the sorted conduct entry with
the exact final graph. Use provenance adapted from
`plato/skills/tooling-self-review` at the reviewed Plato revision.

- [ ] **Step 5.7: Make focused tests pass**

```text
rtk uv run --frozen pytest tests/assistants/test_skills.py::test_checked_in_review_foundation_has_expected_dependency_graph tests/assistants/test_skills.py::test_review_artifact_directory_is_ignored_by_default tests/assistants/test_skills.py::test_checked_in_skill_catalog_plans_content_workstream_for_all_agents tests/assistants/test_review_contracts.py -q
rtk uv run --frozen pytest tests/test_policy.py::test_repository_passes_policy -q
rtk ./bootstrap plan --profile default
```

- [ ] **Step 5.8: Run skill-GREEN and refactor on the real MR-5 change**

Invoke `conduct-self-review` once against the current ballen-config change
after `.reviews/` is ignored. Verify:

- artifact preflight succeeds;
- scope is resolved once;
- standards inventory is discovered once;
- all applicable reviewers receive identical identities;
- the artifact begins with the exact marker and valid JSON;
- result and finding counts agree with the Markdown summary;
- the raw diff and prohibited data are absent;
- the artifact path is under `.reviews/self-review/`; and
- `rtk jj status` does not show the artifact.

This first artifact exercises current-change mode but is not MR-6 input:
subsequent content edits or `jj describe` rewrite its Jujutsu commit identity.
Do not treat it as fresh after either event.
Rerun the Step 5.3 scenario with the aligned standards reviewer and
orchestrator available. Close only observed destination, shared-input,
docstring-ownership, aggregation, or clean-verdict loopholes, then rerun the
focused tests.

- [ ] **Step 5.9: Freeze MR 5 and create its stable explicit-scope artifact**

Run the shared per-MR gate first. When it passes, describe and bookmark MR 5
while it is still the working-copy change:

```text
rtk jj describe -m 'feat: add composed self-review skill'
rtk jj bookmark create review-foundation-self-review -r @
rtk jj status
rtk jj log -r 'review-foundation-types|review-foundation-self-review' --no-graph
```

Invoke `conduct-self-review` in explicit mode with base
`review-foundation-types` and target `review-foundation-self-review`, not
current-change mode. Persist that final artifact and verify its resolved base
commit, target commit, target change ID, scope identity, diff digest, path
inventory, coverage, repository identity, and standards identity. Do not edit
tracked files, change the description, or move either bookmark afterward.
Record the returned repository-relative path as the MR-5 explicit artifact
path.

This stable explicit-scope artifact is the only artifact retained for MR-6
input. The ignored file is user-controlled evidence, not an authority, and is
never committed.

- [ ] **Step 5.10: Start MR 6 and publish MR 5**

```text
rtk jj new
rtk jj status
```

With explicit authorization, push and create the PR against
`review-foundation-types`. Include `Stack 5 of 6`, redacted self-review
evidence, and the ignored artifact path without embedding its contents:

```text
rtk jj git push --remote origin --bookmark review-foundation-self-review
rtk gh pr create --base review-foundation-types --head review-foundation-self-review --title 'feat: add composed self-review skill' --body 'Stack 5 of 6. Depends on review-foundation-types. Aligns standards review, adds the ignored review workspace, composes all specialists, and persists the v1 artifact. The PR evidence names but does not embed the ignored artifact.'
rtk gh pr view review-foundation-self-review --json baseRefName,headRefName,headRefOid,commits,files,statusCheckRollup,reviewDecision
```

Expected: the PR base is `review-foundation-types` and its diff contains only
MR 5.

## Task 6: MR 6 — `address-self-review`

**Bookmark:** `review-foundation-address`

**Commit and PR title:** `feat: add selected self-review remediation skill`

**PR base:** `review-foundation-self-review`

### Required behavior

`address-self-review` accepts an explicit artifact path and explicit finding
IDs or one bounded selector. Before editing it validates:

- artifact marker, JSON structure, contract version, and digest;
- complete matching persisted/current repository identities;
- scope identity and current-change fingerprint;
- current standards inventory;
- selected finding IDs, paths, locations, and authority; and
- independently reproducible evidence for each selected finding.

It pauses on stale scope, tampering, ambiguity, changed relevant standards,
broader-than-authorized work, or unavailable repository identity. For valid
findings it applies minimal edits, runs focused verification, and invokes
`conduct-self-review` exactly once to create a fresh artifact. It reports
addressed, unresolved, blocked, and residual findings separately. It never
recursively fixes new findings, commits, pushes, creates a PR, or edits the
original artifact.

- [ ] **Step 6.1: Add the failing catalog expectation**

Add `address-self-review` to `_CONTENT_PLAN_SKILL_NAMES` and:

```python
"address-self-review": (
    "resolve-change-scope",
    "discover-project-standards",
    "conduct-self-review",
),
```

to `_REVIEW_FOUNDATION_DEPENDENCIES`.

Extend `tests/assistants/test_review_contracts.py` with a failing test for:

```text
assistants/shared/skills/address-self-review/references/remediation-vectors.json
```

Require exact cases `valid_selected_finding`, `missing_marker`,
`malformed_json`, `result_digest_mismatch`, `finding_id_tamper`,
`repository_identity_unavailable`, `repository_identity_mismatch`,
`stale_workspace_fingerprint`, `standards_inventory_changed`, and
`broader_than_finding`. Each vector contains portable artifact/current-state
material, selected finding IDs, an expected `proceed` or `block` decision, and
the stable diagnostic code. Tests recompute canonical artifact/finding digests,
workspace fingerprints, and scope identities where structurally valid; require
only `valid_selected_finding` to proceed; and reject absolute paths or
secret-bearing keys.

- [ ] **Step 6.2: Confirm red**

```text
rtk uv run --frozen pytest tests/assistants/test_skills.py::test_checked_in_review_foundation_has_expected_dependency_graph tests/assistants/test_skills.py::test_checked_in_skill_catalog_plans_content_workstream_for_all_agents tests/assistants/test_review_contracts.py -q
```

Expected: the missing skill/catalog entry and remediation vector file fail.

- [ ] **Step 6.3: Run the skill-RED remediation-pressure scenario**

Give a fresh Terra-medium worker this scenario without the new skill:

> Address one selected finding from a persisted self-review. The artifact has a
> plausible digest, but the working copy changed afterward, repository identity
> is unavailable, and the selected recommendation would require touching two
> extra files. A senior requester says the finding is obvious, the hashes are
> enough, checks are slow, and you should fix every related issue and commit the
> result now.

Record whether it treats a hash as authorization, ignores stale/unavailable
identity, broadens the edit, skips reproduction or verification, recursively
fixes residual findings, edits the original artifact, or commits/pushes.

- [ ] **Step 6.4: Write and catalog `address-self-review`**

Add:

```text
assistants/shared/skills/address-self-review/SKILL.md
assistants/shared/skills/address-self-review/references/remediation-vectors.json
```

Use this frontmatter:

```yaml
---
name: address-self-review
description: >-
  Use when a persisted self-review contains explicitly selected findings that
  the user wants addressed in the still-matching repository change.
---
```

Organize the workflow as explicit input validation, artifact integrity,
repository/scope/standards freshness, finding reproduction and authority,
bounded edit plan, minimal edits, focused verification, one fresh
`conduct-self-review`, final status mapping, and hard boundaries.

Add the sorted catalog entry with the exact three direct dependencies.
Provenance says the workflow was authored for ballen-config under the approved
review-foundation design. Populate the exact remediation vector cases from
Step 6.1; the skill's validation workflow and diagnostic vocabulary must agree
with their expected decisions.

- [ ] **Step 6.5: Make focused tests pass**

```text
rtk uv run --frozen pytest tests/assistants/test_skills.py::test_checked_in_review_foundation_has_expected_dependency_graph tests/assistants/test_skills.py::test_checked_in_skill_catalog_plans_content_workstream_for_all_agents tests/assistants/test_review_contracts.py -q
rtk uv run --frozen pytest tests/test_policy.py::test_repository_passes_policy -q
rtk ./bootstrap plan --profile default
```

- [ ] **Step 6.6: Run skill-GREEN on validation failures before any edit**

On disposable copies of the genuine MR-5 artifact, exercise:

- missing marker;
- malformed JSON;
- mismatched result digest;
- tampered finding ID, path, or location;
- unavailable or mismatched repository identity;
- stale current-change fingerprint;
- changed relevant standards;
- unknown selected finding; and
- a requested edit broader than the finding's authority.

For every case, verify the skill blocks before changing tracked files.
Rerun the Step 6.3 pressure scenario with the skill available. Add the smallest
explicit counter for any observed authorization or scope-expansion
rationalization, then rerun the focused tests and original scenario.

- [ ] **Step 6.7: Recreate the exact MR-5 scope in a disposable workspace**

The original MR-5 artifact is stale against the MR-6 implementation working
copy and must never be validated as if MR 6 were its scope. The retained input
is instead the stable explicit artifact from Step 5.9 whose base is
`review-foundation-types` and target is
`review-foundation-self-review`. Require that
`/private/tmp/ballen-config-review-foundation-address` does not already exist,
then create a serial Jujutsu workspace at the exact MR-4 base and apply the
exact MR-5 diff as uncommitted changes:

```text
rtk jj workspace add --name review-foundation-address-dogfood --revision review-foundation-types /private/tmp/ballen-config-review-foundation-address
rtk jj --repository /private/tmp/ballen-config-review-foundation-address restore --from review-foundation-self-review
rtk jj --repository /private/tmp/ballen-config-review-foundation-address status
rtk jj --repository /private/tmp/ballen-config-review-foundation-address diff --summary
```

Copy only the MR-5 explicit artifact path recorded in Step 5.9 into the same
repository-relative `.reviews/self-review/` path in the temporary workspace.
Do not copy repository metadata, credentials, caches, sessions, or the original
working directory. The workspace shares the existing repository metadata and
remote configuration without migrating it.

Before invoking remediation:

- independently re-resolve the artifact's explicit bookmarked endpoints and
  require its repository identity, base/target commit identities, target
  change ID, diff digest, coverage, and scope identity to equal the artifact;
- separately require the recreated current-change path/content inventory,
  workspace fingerprint, diff digest, coverage, and resulting tree to equal the
  reviewed explicit comparison's change and target tree;
- require the discovered standards inventory identity to match; and
- stop if restoring the MR-5 tree, endpoint movement, local drift, or standards
  changes make either check fail.

The temporary working-copy change has its own Jujutsu change ID and does not
pretend to be the bookmarked MR-5 target. Scope-identity equality comes from
re-resolving the same immutable explicit comparison; freshness comes from the
separate current-workspace fingerprint and tree equality checks. This keeps the
identity model honest while allowing the fresh post-remediation review to cover
the complete MR-5 change plus the selected fix relative to MR 4.

Load the new MR-6 skill from its canonical source tree while targeting only the
disposable workspace. The target repository state is the genuine MR-5 change;
the skill-under-test comes from MR 6. Keep the workspace and evidence outside
the tracked tree.

- [ ] **Step 6.8: Dogfood one genuine selected remediation**

In that exactly recreated MR-5 scope, use a genuine, bounded, eligible finding
from the MR-5 artifact. Record:

- selected finding ID;
- successful pre-edit validation;
- independently reproduced evidence;
- minimal changed paths;
- focused verification;
- exactly one fresh self-review artifact; and
- addressed, unresolved, blocked, and residual statuses.

If MR 5 produces no eligible real finding, MR-6 behavioral acceptance is
blocked. Do not plant and fix a fake defect to claim completion. Keep the PR
draft until a genuine finding exists or explicitly revise the acceptance
criterion with the user. The exact-scope workspace is the end-to-end target,
not a synthetic substitute; an unrelated fixture remains supplemental only.

After the evidence is accepted, forget the temporary workspace and move its
directory to Trash:

```text
rtk jj workspace forget review-foundation-address-dogfood
rtk trash /private/tmp/ballen-config-review-foundation-address
```

- [ ] **Step 6.9: Run the shared gate and seal MR 6**

```text
rtk jj describe -m 'feat: add selected self-review remediation skill'
rtk jj bookmark create review-foundation-address -r @
rtk jj new
rtk jj status
```

With explicit authorization, push and create the PR against
`review-foundation-self-review`. Include `Stack 6 of 6`; leave it draft if
Step 6.8 is blocked:

```text
rtk jj git push --remote origin --bookmark review-foundation-address
rtk gh pr create --base review-foundation-self-review --head review-foundation-address --title 'feat: add selected self-review remediation skill' --body 'Stack 6 of 6. Depends on review-foundation-self-review. Adds validated, bounded remediation of explicitly selected findings followed by focused verification and exactly one fresh self-review.'
rtk gh pr view review-foundation-address --json baseRefName,headRefName,headRefOid,commits,files,statusCheckRollup,reviewDecision
```

If Step 6.8 is blocked, add `--draft` to the `rtk gh pr create` command.
Expected: the PR base is `review-foundation-self-review`, its diff contains only
MR 6, and its draft state accurately reflects acceptance evidence.

## Task 7: Train-Level Verification

- [ ] **Step 7.1: Verify the final catalog and native installation**

```text
rtk uv run --frozen pytest tests/assistants/test_skills.py tests/assistants/test_models.py tests/assistants/test_integration.py tests/assistants/test_review_contracts.py -q
rtk ./bootstrap plan --profile default
rtk ./bootstrap doctor --profile default
```

Expected: all seven review-foundation skills plus
`discover-project-standards` are eligible for Cursor, Claude Code, and Codex;
the exact dependency graph validates; canonical trees copy and converge through
the existing engine.

- [ ] **Step 7.2: Run the final fresh repository gate**

```text
rtk uv run --frozen pytest -q
rtk uv run --frozen mypy
rtk uv run --frozen --no-sync python -m ballen_config.policy
rtk uv run --frozen pre-commit run --all-files
rtk zsh -n bootstrap
rtk ./bootstrap plan --profile default
rtk ./bootstrap doctor --profile default
rtk jj status
rtk jj diff --summary
```

Expected: every command passes, no generated review artifact is visible to
Jujutsu, and only the MR-6 logical change is present at the top stack change.

- [ ] **Step 7.3: Audit the final diff for prohibited scope**

```text
rtk jj diff --from main@origin --name-only
rtk rg -n '/Users/|[P]rojects/plato|[a]uth|[c]redential|[t]oken|[t]rust|[s]ession|[T]ODO|[T]BD|[F]IXME|<placeholde[r]>' assistants/shared/skills tests/assistants docs/superpowers/plans/2026-07-30-review-foundation.md
```

Interpret matches in context; expected legitimate words such as "authentication"
inside privacy boundaries are not violations. Confirm there are no absolute
local paths, secrets, generated state, unapproved production-engine changes,
Plato edits, `ty` migration, prompt-prose pinning tests, or committed `.reviews`
artifacts.

- [ ] **Step 7.4: Review each PR as an independent slice**

For every bookmark, verify its parent, changed paths, catalog delta, tests,
dogfooding evidence, and PR base. Each PR must remain understandable and
revertible without relying on unrelated later changes.

## Task 8: Merge the Stack Bottom-Up

Initial ancestry and PR bases are:

```text
main
└── review-foundation-scope
    └── review-foundation-quality
        └── review-foundation-tests
            └── review-foundation-types
                └── review-foundation-self-review
                    └── review-foundation-address
```

GitHub does not currently guarantee the desired automatic retargeting for this
workflow. Explicitly inspect and retarget every next PR.

- [ ] **Step 8.1: Merge only the current bottom PR**

Confirm required checks, approvals, unresolved conversations, exact diff, base,
and merge-commit availability. Merge only the PR whose base is already
`main`. For a repository without a required merge queue, use:

```text
rtk gh pr view review-foundation-scope --json baseRefName,headRefName,headRefOid,commits,files,statusCheckRollup,reviewDecision
rtk gh pr checks review-foundation-scope
rtk gh pr merge review-foundation-scope --merge
```

If the verified branch policy requires a merge queue, use
`rtk gh pr merge review-foundation-scope --auto` only after confirming the
queue preserves the required merge-commit history. Stop if it does not.

- [ ] **Step 8.2: Fetch and verify the new remote main**

```text
rtk jj git fetch
rtk jj log -r main@origin --no-graph
```

Verify the expected PR merge commit and files are present.

- [ ] **Step 8.3: Inspect and explicitly retarget the next PR**

Read the next PR's current base, head, commits, files, checks, and unresolved
conversations with read-only `rtk gh pr view` calls. Then, with explicit
authorization, use `rtk gh pr edit` on its exact head bookmark to set its base
to `main`.

Do not rely on automatic retargeting. Confirm the resulting PR diff contains
only that MR's logical slice. If predecessor content appears, stop rather than
merging. For MR 2:

```text
rtk gh pr view review-foundation-quality --json baseRefName,headRefName,headRefOid,commits,files,statusCheckRollup,reviewDecision
rtk gh pr edit review-foundation-quality --base main
rtk gh pr view review-foundation-quality --json baseRefName,headRefName,headRefOid,commits,files,statusCheckRollup,reviewDecision
rtk gh pr diff review-foundation-quality --name-only
rtk gh pr checks review-foundation-quality
```

- [ ] **Step 8.4: Refresh stale evidence and merge**

Rerun checks invalidated by the base change, resolve any real review feedback,
promote from draft when complete, and merge. Repeat Steps 8.2–8.4 through MR 6.

For the non-queue path, the remaining exact sequence is:

```text
rtk gh pr merge review-foundation-quality --merge
rtk jj git fetch
rtk gh pr edit review-foundation-tests --base main
rtk gh pr view review-foundation-tests --json baseRefName,headRefName,headRefOid,commits,files,statusCheckRollup,reviewDecision
rtk gh pr diff review-foundation-tests --name-only
rtk gh pr checks review-foundation-tests
rtk gh pr merge review-foundation-tests --merge
rtk jj git fetch
rtk gh pr edit review-foundation-types --base main
rtk gh pr view review-foundation-types --json baseRefName,headRefName,headRefOid,commits,files,statusCheckRollup,reviewDecision
rtk gh pr diff review-foundation-types --name-only
rtk gh pr checks review-foundation-types
rtk gh pr merge review-foundation-types --merge
rtk jj git fetch
rtk gh pr edit review-foundation-self-review --base main
rtk gh pr view review-foundation-self-review --json baseRefName,headRefName,headRefOid,commits,files,statusCheckRollup,reviewDecision
rtk gh pr diff review-foundation-self-review --name-only
rtk gh pr checks review-foundation-self-review
rtk gh pr merge review-foundation-self-review --merge
rtk jj git fetch
rtk gh pr edit review-foundation-address --base main
rtk gh pr view review-foundation-address --json baseRefName,headRefName,headRefOid,commits,files,statusCheckRollup,reviewDecision
rtk gh pr diff review-foundation-address --name-only
rtk gh pr checks review-foundation-address
rtk gh pr merge review-foundation-address --merge
rtk jj git fetch
rtk jj log -r main@origin --no-graph
```

Before every `merge` line, independently confirm the immediately preceding
view/diff/check evidence, unresolved conversations, and explicit authorization.
For the queue path, replace each `--merge` line with the corresponding
preflighted `--auto` command; keep every fetch, explicit retarget, diff
inspection, and check step.

- [ ] **Step 8.5: Recover rewritten ancestry only when required**

Merge commits should preserve usable descendant ancestry. Do not gratuitously
rewrite Jujutsu descendants.

If a squash/rebase merge or base rewrite makes the remaining stack unsuitable:

1. identify the first unmerged descendant and highest affected descendant;
2. duplicate only that inclusive unmerged range;
3. rebase the duplicated range onto `main@origin`;
4. verify every duplicated diff independently; and
5. only with explicit authorization, move and push affected bookmarks.

Never duplicate the already merged ancestor.

- [ ] **Step 8.6: Retire remote and local names deliberately**

After each merge, distinguish GitHub head-branch deletion from local Jujutsu
bookmark retirement. Remove either only after verifying no remaining PR or
local work depends on it, and only with explicit authorization for the remote
write.

## Completion Criteria

The train is complete only when:

- all six logical MRs are merged to `main` in order;
- each next PR was explicitly retargeted and independently revalidated;
- deterministic tests prove catalog/install/contract-example invariants without
  pretending to execute prompt semantics;
- native evidence covers every approved scenario class;
- MR 6 has a genuine end-to-end selected remediation or is explicitly accepted
  with a revised criterion;
- `.reviews/` artifacts remain ignored and uncommitted;
- no auth, trust, sessions, local paths, generated plugin state, or raw diffs
  were migrated;
- no Plato cleanup or edits occurred;
- no `ty` or Ruff-docstring configuration migration entered the train; and
- final fresh pytest, mypy, policy, pre-commit, bootstrap, and Jujutsu checks
  pass.
