# Plato Reusable Skills Content Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the six additive first-release skills (design slices 4–8)
through the existing shared-skill catalog without engine changes.

**Architecture:** One canonical tree per skill under
`assistants/shared/skills/<name>/`, one `SkillSpec` catalog entry each, digest
pinning in tests, and portability review before claiming `reviewed-generic`.
No plugin packaging, no rename protocol, no `StateStore` changes. The standards
pair is the only coupled content slice; forge skills are drafted together but
land as separate commits.

**Tech Stack:** Python 3.12, pytest, PyYAML, Markdown, Jujutsu, `uv`, Plato
read-only at commit `f3b91eead0eff7d0c9cada3bc8e689f7610fba55`.

## Global Constraints

- Python 3.12; Google-style docstrings in any new Python; pytest fixtures.
- Use Jujutsu (`jj`), not git. Prefix every shell command with `rtk`.
- Design authority:
  `docs/superpowers/specs/2026-07-28-plato-reusable-skills-design.md`.
- Treat `/Users/ballen/Projects/plato` as **read-only**. Never edit or commit
  there. Immutable reviewed revision:
  `f3b91eead0eff7d0c9cada3bc8e689f7610fba55`.
- Do not migrate credentials, MCP config, auth state, sessions, absolute project
  paths, or generated plugin state into skill trees.
- Do not claim `portability_status: reviewed-generic` until that skill’s
  portability checklist in this plan passes.
- Do not edit `src/ballen_config/` except tests under `tests/` — this plan is
  content-only. Engine work lives in
  [`2026-07-29-plato-reusable-skills-engine.md`](2026-07-29-plato-reusable-skills-engine.md).
- Keep `pyproject.toml` / `uv.lock` unchanged.
- Stop and return to design if a skill needs a catalog schema change, a shared
  forge router, or a standards-reference skill.

## Relationship to the Engine Plan

This plan is **parallel** to the engine plan (slices 1–3).

| Concern | Rule |
|---|---|
| Execution | May start immediately; does not wait on the lock or rename protocol |
| `catalog.yaml` | Both plans edit it — rebase/merge carefully; never delete the other’s entries |
| `using-jujutsu` | Owned by the engine plan; do not rename `jujutsu-workflow` here |
| Merge order | Content PRs may land before, after, or interleaved with the engine PR |
| Bookmark | Use a separate bookmark: `implement-reusable-skills-content` |

---

## File Map

Create (per skill, under `assistants/shared/skills/`):

```text
discover-project-standards/SKILL.md
review-project-standards/SKILL.md
using-uv/SKILL.md
using-uv/references/dependency-management.md   # generated projection
writing-executive-communications/SKILL.md
using-gitlab/SKILL.md
using-github/SKILL.md
```

Optional supporting files only when the Plato source already has them and the
portability review keeps them (e.g. `reference.md`). Prefer a single `SKILL.md`
unless a second file is clearly warranted.

Modify:

```text
assistants/shared/skills/catalog.yaml
tests/assistants/test_skills.py
tests/assistants/test_models.py          # only if dependency fixtures need updates
```

Deliberately leave unchanged:

```text
src/ballen_config/                       # no engine changes in this plan
assistants/shared/standards/             # canonical; using-uv copies from it
assistants/shared/skills/jujutsu-workflow/   # engine plan owns rename
pyproject.toml
uv.lock
/Users/ballen/Projects/plato
```

## Execution Model

- Five reviewable commits matching design slices 4–8 (standards pair is one).
- Draft forge skills (Tasks 4–5) against each other before either commit lands.
- TDD for catalog/digest/portability tests; skill prose is reviewed against the
  design contracts, then pinned.
- Full suite + policy at the end of each task.
- Create bookmark `implement-reusable-skills-content` before Task 1.

---

## Shared Per-Skill Delivery Checklist

Every skill task uses this checklist. Do not skip steps. Copy the commands and
substitute `<name>`.

### A. Portability reject list

Before claiming `reviewed-generic`, the skill tree must contain none of:

```text
plato
/Users/
/home/
Projects/plato
ami-
pydantic 2.8
{{
sk-
ghp_
glpat-
```

Also reject fixed internal GitLab/GitHub hostnames, numeric project IDs, and
machine-specific absolute paths. Neutral prose that says “do not copy secrets”
is fine.

### B. Frontmatter contract

```yaml
---
name: <name>
description: >-
  <one trigger-oriented paragraph; no Plato product framing>
---
```

Directory name, frontmatter `name:`, and catalog `name:` must match exactly.

### C. Catalog entry shape

```yaml
  - name: <name>
    source: assistants/shared/skills/<name>
    targets: [cursor, claude-code, codex]
    profiles: [default]
    dependencies: []   # exception: review-project-standards
    provenance: <exact string from the task>
    portability_status: reviewed-generic
```

Append entries in **catalog name sort order** when editing `catalog.yaml`
(keep the file sorted by `name` for reviewability). If the engine plan has
already added `using-jujutsu` + `renames`, leave those intact.

### D. Digest pin helper

```text
rtk uv run --frozen python - <<'PY'
from hashlib import sha256
from pathlib import Path
from ballen_config.assistants.skills import hash_skill_tree
root = Path("assistants/shared/skills/<name>")
print("tree", hash_skill_tree(root))
for path in sorted(root.rglob("*")):
    if path.is_file():
        print(path.relative_to(root), sha256(path.read_bytes()).hexdigest())
PY
```

### E. Synchronization test pattern

Extend `tests/assistants/test_skills.py` with one test per skill (or extend a
parameterized sync test). Minimum assertions:

```python
def test_<name>_catalog_and_configuration_are_synchronized(
    repo_root: Path, temporary_home: Path
) -> None:
    catalog = yaml.safe_load(
        (repo_root / "assistants/shared/skills/catalog.yaml").read_text()
    )
    entry = next(item for item in catalog["skills"] if item["name"] == "<name>")
    assert entry["source"] == "assistants/shared/skills/<name>"
    assert entry["targets"] == ["cursor", "claude-code", "codex"]
    assert entry["profiles"] == ["default"]
    assert entry["portability_status"] == "reviewed-generic"
    source = repo_root / entry["source"]
    assert hash_skill_tree(source) == "<pinned-tree-digest>"
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=temporary_home)
    contribution = configuration(
        _resolved_setup("cursor", "claude-code", "codex"),
        paths,
        SkillCatalog.model_validate(catalog),
    )
    expected_ids = {
        f"shared-skill-<name>-cursor",
        f"shared-skill-<name>-claude-code",
        f"shared-skill-<name>-codex",
    }
    assert expected_ids.issubset({spec.id for spec in contribution.specs})
```

Also add a portability scan test (shared helper OK):

```python
_REJECT = (
    "plato",
    "/users/",
    "/home/",
    "projects/plato",
    "ami-",
    "pydantic 2.8",
    "{{",
    "sk-",
    "ghp_",
    "glpat-",
)


def _assert_skill_tree_portable(root: Path) -> None:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8").lower()
        for token in _REJECT:
            assert token not in text, f"{token!r} in {path}"
```

### F. Task gate

```text
rtk uv run --frozen pytest tests/assistants/test_skills.py -q
rtk uv run --frozen --no-sync python -m ballen_config.policy
rtk ./bootstrap plan --profile default
```

---

## Preflight

- [ ] **Step 0.1: Confirm Plato immutable revision (read-only)**

```text
rtk jj -R /Users/ballen/Projects/plato --no-pager log -r @- -n 1 --no-graph -T 'commit_id ++ "\n"'
```

If `@-` is not `f3b91eead0eff7d0c9cada3bc8e689f7610fba55`, resolve the reviewed
paths from that commit explicitly:

```text
rtk jj -R /Users/ballen/Projects/plato --no-pager file show f3b91eead0eff7d0c9cada3bc8e689f7610fba55:skills/tooling-discover-standards/SKILL.md | head
```

Fallback mirrors (same content family, verify before trusting):

```text
~/.claude/plugins/cache/piste/plato/0.133.0-dev1/skills/
```

- [ ] **Step 0.2: Confirm ballen-config baseline**

```text
rtk jj --no-pager status
rtk ./bootstrap plan --profile default
```

- [ ] **Step 0.3: Create content bookmark**

```text
rtk jj bookmark create implement-reusable-skills-content -r @
rtk jj new -m "wip: reusable skills content"
```

---

## Slice 4 — Standards Pair

### Task 1: `discover-project-standards` + `review-project-standards`

**Files:**
- Create: `assistants/shared/skills/discover-project-standards/SKILL.md`
- Create: `assistants/shared/skills/review-project-standards/SKILL.md`
- Modify: `assistants/shared/skills/catalog.yaml`
- Test: `tests/assistants/test_skills.py`

**Sources (read-only):**
- `/Users/ballen/Projects/plato/skills/tooling-discover-standards/SKILL.md`
- `/Users/ballen/Projects/plato/skills/tooling-review-standards/SKILL.md`
- at commit `f3b91eead0eff7d0c9cada3bc8e689f7610fba55`

**Provenance strings:**

```text
Genericized from plato/skills/tooling-discover-standards at commit f3b91eead0eff7d0c9cada3bc8e689f7610fba55; commit history records the promotion.

Genericized from plato/skills/tooling-review-standards at commit f3b91eead0eff7d0c9cada3bc8e689f7610fba55; commit history records the promotion.
```

**Catalog dependency:**

```yaml
  - name: review-project-standards
    dependencies: [discover-project-standards]
```

**Content contracts (design):**

`discover-project-standards`:
- Discover human-written standards from repository instruction filenames and
  tool config; do not analyze code.
- Cover all supported instruction filenames and precedence used in this
  repository’s agent set (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, Cursor rules,
  etc.) — expand Plato’s table if a supported harness file is missing.
- Stable logical inventory result for downstream consumers.
- Behavior when no applicable standards are found.
- Do not copy repository instructions into persistent personal state.
- Do not treat `ballen-config`’s `assistants/shared/standards/` as an implicit
  project standard for the target repo.

`review-project-standards`:
- Instruct by **name**: follow the `discover-project-standards` skill.
- May note sibling install path `../discover-project-standards/SKILL.md` as a
  hint only — not the mechanism.
- No duplicated discovery fallback procedure inside the review skill.
- Read-only by default.
- Findings: relevant standard, evidence, file/location when applicable, severity.
- Distinguish: no applicable standards; incomplete discovery; clean review;
  actionable findings.

- [ ] **Step 1: Write failing sync + dependency tests**

```python
def test_standards_pair_catalog_declares_dependency() -> None:
    catalog = SkillCatalog.model_validate(
        yaml.safe_load(
            Path("assistants/shared/skills/catalog.yaml").read_text(encoding="utf-8")
        )
    )
    by_name = {skill.name: skill for skill in catalog.skills}
    assert "discover-project-standards" in by_name
    assert by_name["review-project-standards"].dependencies == (
        "discover-project-standards",
    )


def test_review_skill_references_discovery_by_name(repo_root: Path) -> None:
    text = (
        repo_root / "assistants/shared/skills/review-project-standards/SKILL.md"
    ).read_text(encoding="utf-8")
    assert "discover-project-standards" in text
    assert "tooling-discover-standards" not in text
```

Plus the shared synchronization + portability tests for both names.

- [ ] **Step 2: Run tests — expect FAIL (trees absent)**

```text
rtk uv run --frozen pytest tests/assistants/test_skills.py -k standards_pair -q
```

- [ ] **Step 3: Promote and genericize both skills**

Copy from Plato, then edit:
- Rename frontmatter and H1 to the new names.
- Replace old sibling skill names (`tooling-discover-standards`,
  `tooling-review-standards`, other Plato tooling-* references).
- Keep discovery as a separate skill; do not fold it into review.
- Apply Shared Checklist A–C.

- [ ] **Step 4: Pin digests, update catalog, pass tests**

```text
rtk uv run --frozen pytest tests/assistants/test_skills.py -k "standards_pair or discover_project or review_project" -q
rtk uv run --frozen --no-sync python -m ballen_config.policy
```

- [ ] **Step 5: Composition release gate (opt-in smoke)**

Use isolated homes — never personal native state.

```text
rtk ./bootstrap configure --profile default
```

Then, for each enabled harness (Cursor, Claude Code, Codex), invoke
`review-project-standards` against a tiny fixture repository that has at least
one instruction file and one deliberate standards violation in a sample file.
Confirm from observable agent output that discovery runs before review findings.

Record the satisfied reference form per harness in the commit message body,
choosing one of:

- `native-name-invocation`
- `same-root-path-read` (agent opened sibling `SKILL.md` by path)
- `bundled-hint-path` (`../discover-project-standards/SKILL.md`)

If a harness fails the preferred form, narrow to the weakest form it supports.
Do **not** block Tasks 2–5 on a gate failure — fix the pair’s reference wording
or record the narrowed form, then continue.

- [ ] **Step 6: Commit**

```text
rtk jj commit -m "$(cat <<'EOF'
feat: add discover and review project-standards skills

Promote the Plato standards pair through the shared-skill catalog with a
name-based composition reference. Composition gate forms: <cursor=...>,
<claude=...>, <codex=...>.
EOF
)"
```

---

## Slice 5 — `using-uv`

### Task 2: Author `using-uv` + dependency-management projection

**Files:**
- Create: `assistants/shared/skills/using-uv/SKILL.md`
- Create: `assistants/shared/skills/using-uv/references/dependency-management.md`
- Modify: `assistants/shared/skills/catalog.yaml`
- Test: `tests/assistants/test_skills.py`
- Read-only canonical:
  `assistants/shared/standards/dependency-management.md`

**Provenance:**

```text
Authored for ballen-config against current primary uv documentation.
```

**Content contract (design):**
- Recognize `pyproject.toml`, `uv.lock`, and uv workspaces.
- Select `uv run` for project tools.
- Distinguish add / remove / sync / lock / workspace operations.
- Preserve repository-selected Python and dependency policy (do not restate the
  standard; load the co-packaged projection when detail is needed).
- Explain behavior when uv is absent or another manager is selected.
- Verify version-sensitive commands against current primary uv docs during
  authoring.
- Must not become a second dependency-management standard.

**Projection rule:**

```text
rtk cp assistants/shared/standards/dependency-management.md \
  assistants/shared/skills/using-uv/references/dependency-management.md
```

Any future edit to the canonical file must regenerate the projection in the
same change. The skill tree may only read
`references/dependency-management.md` inside its own installed tree.

- [ ] **Step 1: Write failing tests**

```python
def test_using_uv_projection_matches_canonical_standard(repo_root: Path) -> None:
    canonical = (
        repo_root / "assistants/shared/standards/dependency-management.md"
    ).read_bytes()
    projection = (
        repo_root
        / "assistants/shared/skills/using-uv/references/dependency-management.md"
    ).read_bytes()
    assert projection == canonical


def test_using_uv_skill_points_at_bundled_reference(repo_root: Path) -> None:
    text = (repo_root / "assistants/shared/skills/using-uv/SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "references/dependency-management.md" in text
    assert "assistants/shared/standards/dependency-management.md" not in text
```

Plus shared sync + portability tests for `using-uv`.

- [ ] **Step 2: Run — expect FAIL**

```text
rtk uv run --frozen pytest tests/assistants/test_skills.py -k using_uv -q
```

- [ ] **Step 3: Author SKILL.md, copy projection, catalog entry, pin digests**

In `SKILL.md`, document `uv` as the required external command and state the
fallback when it is missing (stop and tell the user; do not invent pip/poetry
workflows unless the repository selected them).

- [ ] **Step 4: Gate + commit**

```text
rtk uv run --frozen pytest tests/assistants/test_skills.py -k using_uv -q
rtk uv run --frozen --no-sync python -m ballen_config.policy
rtk jj commit -m "$(cat <<'EOF'
feat: add using-uv skill with dependency-management projection

Ship procedural uv guidance with a byte-identical copy of the canonical
dependency-management standard inside the skill tree.
EOF
)"
```

---

## Slice 6 — Executive Communications

### Task 3: Promote `writing-executive-communications`

**Files:**
- Create: `assistants/shared/skills/writing-executive-communications/SKILL.md`
- Modify: `assistants/shared/skills/catalog.yaml`
- Test: `tests/assistants/test_skills.py`

**Source (read-only):**
- `/Users/ballen/Projects/plato/skills/reports-consultant-style/SKILL.md`
- at commit `f3b91eead0eff7d0c9cada3bc8e689f7610fba55`

**Provenance:**

```text
Genericized from plato/skills/reports-consultant-style at commit f3b91eead0eff7d0c9cada3bc8e689f7610fba55; commit history records the promotion.
```

**Content contract (design):**
- Near byte-for-byte promotion is expected (source is already project-neutral).
- Rename skill + description away from “presentations-only” framing.
- Worked examples illustrate structure without implying a renderer or remote
  provider.
- Replace `Option A` / `Option B` labels with descriptive option names.
- Owns: lead with the answer, MECE, situation-complication-resolution,
  quantified claims, confidence levels, executive-summary format.
- Owns **not**: document format, presentation renderer, storage destination.

- [ ] **Step 1: Failing sync + portability + naming tests**

```python
def test_writing_executive_communications_avoids_placeholder_option_labels(
    repo_root: Path,
) -> None:
    text = (
        repo_root / "assistants/shared/skills/writing-executive-communications/SKILL.md"
    ).read_text(encoding="utf-8")
    assert "Option A" not in text
    assert "Option B" not in text
    assert "reports-consultant-style" not in text
```

- [ ] **Step 2: Promote, edit, pin, gate**

```text
rtk uv run --frozen pytest tests/assistants/test_skills.py -k writing_executive -q
rtk uv run --frozen --no-sync python -m ballen_config.policy
```

- [ ] **Step 3: Commit**

```text
rtk jj commit -m "$(cat <<'EOF'
feat: add writing-executive-communications skill

Promote Plato's consultant-style communication guidance as a portable
shared skill with descriptive option labels and no renderer coupling.
EOF
)"
```

---

## Slices 7–8 — Forge Skills (Draft Together, Land Separately)

Draft both skills in the working copy before committing either. Review them
against each other for structural parity without creating a shared router tree.

### Shared forge protocol (both skills)

Every structural bullet below must appear in both `SKILL.md` files:

1. Derive repository and remote identity from the current checkout.
2. Discover available providers; do not assume one tool surface.
3. Prefer read-only inspection.
4. Document CLI fallback (`glab` / `gh`) and behavior when neither connector nor
   CLI is available.
5. Separate provider setup from workflow guidance.
6. Preview mutations; confirm canonical remote target.
7. Require explicit user intent before remote writes.
8. Confirm the remote is the expected forge; if not, name the counterpart skill
   and stop.
9. Never migrate authentication or MCP configuration.

Keep domain vocabulary distinct (MR vs PR, glab vs gh, GitLab vs GitHub). Do
**not** introduce `using-gitforge`.

### Task 4: Rewrite and add `using-gitlab`

**Files:**
- Create: `assistants/shared/skills/using-gitlab/SKILL.md`
- Modify: `assistants/shared/skills/catalog.yaml`
- Test: `tests/assistants/test_skills.py`

**Source (read-only):**
- `/Users/ballen/Projects/plato/skills/using-gitlab/SKILL.md`
- at commit `f3b91eead0eff7d0c9cada3bc8e689f7610fba55`

**Provenance:**

```text
Rewritten for portability from plato/skills/using-gitlab at commit f3b91eead0eff7d0c9cada3bc8e689f7610fba55; commit history records the promotion.
```

**Genericization checklist (must do):**
- Remove fixed project IDs, internal hosts, Plato-specific examples.
- Replace assumed single-tool surface with provider discovery + `glab` fallback.
- Add reciprocal guard: if remote is GitHub, name `using-github` and stop.
- Strip any auth migration, token handling, or MCP install steps.

- [ ] **Step 1: Write failing tests** including forge guard:

```python
def test_using_gitlab_names_github_counterpart_for_wrong_forge(
    repo_root: Path,
) -> None:
    text = (repo_root / "assistants/shared/skills/using-gitlab/SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "using-github" in text
    assert "glab" in text
```

Plus sync + portability tests. Portability must fail if Plato host/project IDs
survive.

- [ ] **Step 2: Author portable skill (keep Task 5 draft open in the same tree)**
- [ ] **Step 3: Pin digests, catalog, focused gate**

```text
rtk uv run --frozen pytest tests/assistants/test_skills.py -k using_gitlab -q
rtk uv run --frozen --no-sync python -m ballen_config.policy
```

- [ ] **Step 4: Commit `using-gitlab` only** (leave `using-github` uncommitted
  or in the working copy for Task 5)

```text
rtk jj commit -m "$(cat <<'EOF'
feat: add portable using-gitlab skill

Rewrite Plato's GitLab workflow for provider discovery, glab fallback,
explicit mutation intent, and a reciprocal using-github guard.
EOF
)"
```

### Task 5: Add `using-github`

**Files:**
- Create: `assistants/shared/skills/using-github/SKILL.md`
- Modify: `assistants/shared/skills/catalog.yaml`
- Test: `tests/assistants/test_skills.py`

**Source:** authored new, reviewed against Task 4’s `using-gitlab` for
structural parity. Verify commands against current primary GitHub CLI (`gh`)
documentation during authoring.

**Provenance:**

```text
Authored for ballen-config as the GitHub counterpart to using-gitlab, verified against current primary GitHub CLI documentation.
```

**Content contract (design):**
- Same structural bullets as `using-gitlab`, with `gh` as CLI fallback.
- Reciprocal guard names `using-gitlab` when the remote is GitLab.
- Keep PR/checks/merge semantics visible; do not flatten into GitLab MR terms.

- [ ] **Step 1: Parity review checklist (manual, record in commit body)**

Compare both skills section-by-section. Every shared protocol bullet present in
both. Domain-specific sections may differ. No shared router file.

- [ ] **Step 2: Failing tests**

```python
def test_using_github_names_gitlab_counterpart_for_wrong_forge(
    repo_root: Path,
) -> None:
    text = (repo_root / "assistants/shared/skills/using-github/SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "using-gitlab" in text
    assert "gh" in text


def test_forge_skills_share_protocol_headings(repo_root: Path) -> None:
    gitlab = (repo_root / "assistants/shared/skills/using-gitlab/SKILL.md").read_text(
        encoding="utf-8"
    )
    github = (repo_root / "assistants/shared/skills/using-github/SKILL.md").read_text(
        encoding="utf-8"
    )
    for needle in (
        "provider",
        "read-only",
        "explicit",
        "using-github" if "glab" in gitlab else "using-gitlab",
    ):
        assert needle in gitlab
        assert needle in github
```

Refine the parity test to assert stable section headings you actually wrote
(e.g. `## Provider discovery`, `## Mutation safety`) rather than loose
substrings once the drafts exist.

- [ ] **Step 3: Author, pin, gate, commit**

```text
rtk uv run --frozen pytest tests/assistants/test_skills.py -k "using_github or using_gitlab" -q
rtk uv run --frozen --no-sync python -m ballen_config.policy
rtk jj commit -m "$(cat <<'EOF'
feat: add using-github skill as gitlab counterpart

Author the GitHub workflow skill with structural parity to using-gitlab,
gh fallback, and a reciprocal forge guard. No shared router.
EOF
)"
```

---

## Native Smokes (All Content Skills)

After Tasks 1–5, run isolated-home smokes. Do not use personal native state.

- [ ] **Step S.1: Configure into an isolated home**

```text
rtk env HOME=/tmp/ballen-config-skills-smoke ./bootstrap configure --profile default
```

(or the repository’s established temporary-home test harness if preferred)

- [ ] **Step S.2: Invoke each content skill once per enabled harness**

Skills: `discover-project-standards`, `review-project-standards`, `using-uv`,
`writing-executive-communications`, `using-gitlab`, `using-github`.

- [ ] **Step S.3: Forge guard smoke**

Against a fixture repo whose `origin` is the **other** forge, invoke each
provider skill and confirm it names its counterpart and does not proceed to
mutation.

---

## Final Branch Checkpoint

- [ ] **Step F.1: Full verification**

```text
rtk uv run --frozen pytest -q
rtk uv run --frozen ruff check .
rtk uv run --frozen ruff format --check src tests
rtk uv run --frozen mypy
rtk uv run --frozen --no-sync python -m ballen_config.policy
rtk zsh -n bootstrap
rtk uv run --frozen pre-commit run --all-files
rtk ./bootstrap plan --profile default
rtk ./bootstrap doctor --profile default
```

- [ ] **Step F.2: Catalog completeness**

```text
rtk uv run --frozen python - <<'PY'
import yaml
from pathlib import Path
catalog = yaml.safe_load(Path("assistants/shared/skills/catalog.yaml").read_text())
names = sorted(s["name"] for s in catalog["skills"])
print(names)
required = {
    "discover-project-standards",
    "review-project-standards",
    "using-github",
    "using-gitlab",
    "using-uv",
    "writing-executive-communications",
}
missing = sorted(required - set(names))
assert not missing, missing
# using-jujutsu may be present if engine plan landed; jujutsu-workflow must not
assert "jujutsu-workflow" not in names or "using-jujutsu" in names
PY
```

- [ ] **Step F.3: Push bookmark when remote available**

```text
rtk jj bookmark set implement-reusable-skills-content -r @
rtk jj git push --bookmark implement-reusable-skills-content
```

---

## Spec Coverage Checklist

| Design requirement | Task |
|---|---|
| Standards pair co-installed via catalog dependency | 1 |
| Name-based composition + path hint only | 1 |
| Composition release gate; record reference form | 1 |
| Discovery not folded into review | 1 |
| `using-uv` procedures + bundled standard projection | 2 |
| Projection byte-equality test | 2 |
| Executive communications promotion + descriptive options | 3 |
| `using-gitlab` portable rewrite | 4 |
| `using-github` authored counterpart | 5 |
| Forge reciprocal guards; no router | 4–5 |
| Portability / no secrets / no Plato coupling | All |
| Digest pins + catalog sync tests | All |
| No engine / rename / plugin work | Non-goals |

---

## Parallelism Notes for Agents

- Tasks 2 and 3 are fully independent of Task 1 and of each other after the
  shared checklist exists.
- Tasks 4 and 5 must be **drafted** together; **commit** gitlab before github.
- If the engine plan is in flight on another bookmark/workspace, do not rename
  `jujutsu-workflow` here. Rebase onto engine changes only to reconcile
  `catalog.yaml`.
- Prefer separate PRs per task (five PRs) or two PRs (standards+uv+executive,
  then forge pair). Do not require a single PR for all six skills.
