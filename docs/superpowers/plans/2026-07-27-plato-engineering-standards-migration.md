# Plato Engineering Standards Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port Plato's reviewed engineering defaults into generic tooling
starters, concise native coding-agent baselines, and eight canonical topic
standards without changing Plato or introducing managed standards runtime
behavior.

**Architecture:** Keep the existing shared engineering instruction as the
single global core rendered independently for Cursor, Claude Code, and Codex.
Add passive, copy-once repository templates beside a normative Markdown
standards library. Validate static assets with focused pytest contracts and the
existing portability policy; do not add a catalog, resolver, installer,
selector, generator, or synchronization path.

**Tech Stack:** Python 3.12, pytest, PyYAML, `tomllib`, Ruff, mypy,
pre-commit, Markdownlint, Markdown, and Jujutsu.

---

## Execution Model

This plan follows the operating model in
[`2026-07-27-laptop-bootstrap-four-pr-retrospective.md`](https://github.com/blallen/ballen-config/blob/main/docs/retrospectives/2026-07-27-laptop-bootstrap-four-pr-retrospective.md):

- Execute inline because the three slices share one working copy and ordered
  contracts.
- Keep the three approved logical commits as meaningful 30–60 minute feature
  slices; the checkboxes are checkpoints, not separate worker assignments.
- Use subagents only for focused read-only review at feature boundaries.
- Run focused tests and lint per commit. Run the full suite, mypy, policy, and
  pre-commit once at the final branch checkpoint.
- Create the implementation bookmark before changing assets and push after
  each meaningful commit when the configured remote is available.
- Stop and return to design if a review exposes a new ownership, precedence,
  or runtime question.

The architecture gate is satisfied: source of truth, native destinations,
precedence, exclusions, snapshot ownership, and deferred progressive loading
are settled in:

- `docs/superpowers/specs/2026-07-27-plato-generic-assets-migration-design.md`
- `docs/superpowers/specs/2026-07-27-plato-engineering-standards-migration-design.md`

## Invariants

- Run plan-checkpoint commands from `/Users/ballen/Projects/ballen-config`.
  After the preflight, run implementation commands from the isolated Jujutsu
  workspace `/Users/ballen/Projects/ballen-config-standards`.
- Prefix every shell command with `rtk`.
- Use Jujutsu for status, diffs, commits, bookmarks, and pushes.
- Treat `/Users/ballen/Projects/plato` as read-only. Never edit it or create a
  commit there.
- Capture Plato's immutable parent revision with `@-`; its `@` may be an empty
  working-copy commit.
- Stop if Plato is dirty or reviewed source paths changed after
  `6bb59d00ac01fd3238c091d90f2aea43872934c9`.
- Do not migrate authentication, credentials, trust, sessions, absolute
  project paths, generated plugin state, or internal identifiers.
- Keep `pyproject.toml` and `uv.lock` unchanged. The application's Pydantic pin
  is separate from the generic standards version policy.
- Treat copied rules and tooling as repository-owned snapshots. Do not add
  drift detection, repair, upgrade, or synchronization.
- Keep tooling separate from repository-rule copy modes.
- Keep command recipes out of topic standards; later workflow skills own them.

## File Map

Create:

```text
assistants/shared/standards/
├── README.md
├── api-design.md
├── dependency-management.md
├── documentation.md
├── pydantic.md
├── python.md
├── source-control.md
├── testing.md
├── validation.md
└── templates/
    ├── python/
    │   ├── .markdownlint.json
    │   ├── .pre-commit-config.yaml
    │   ├── README.md
    │   ├── mypy.ini
    │   ├── pytest.ini
    │   └── ruff.toml
    └── repository-rules/
        ├── AGENTS.md
        ├── CLAUDE.md
        └── README.md
docs/superpowers/specs/
└── 2026-07-27-plato-engineering-standards-provenance.yaml
tests/assistants/
├── test_repository_rules.py
├── test_standard_templates.py
└── test_standards.py
```

Modify:

```text
assistants/shared/instructions/core.md
assistants/cursor/user-rules.md
assistants/claude/CLAUDE.md
assistants/codex/AGENTS.md
tests/assistants/test_instructions.py
tests/assistants/test_cursor.py
tests/assistants/test_claude.py
tests/assistants/test_codex.py
```

Two file-map decisions changed during implementation and are recorded in
[Implemented deviations](#implemented-deviations): provenance moved into one
manifest beside the approved decision, and the repository-rule bundle ships no
Cursor `.mdc` entry.

Deliberately leave unchanged:

```text
assistants/inventory.yaml
src/ballen_config/assistants/instructions.py
src/ballen_config/assistants/cursor.py
src/ballen_config/assistants/claude.py
src/ballen_config/assistants/codex.py
pyproject.toml
uv.lock
```

## Preflight and Implementation Bookmark

- [ ] Confirm the required bootstrap preview and clean plan checkpoint:

```text
rtk ./bootstrap plan --profile default
rtk jj --no-pager status
rtk jj --no-pager log -r '@|@-' --no-graph -T 'commit_id.short() ++ " " ++ description.first_line() ++ "\n"'
```

- [ ] Confirm Plato is clean at the reviewed immutable parent:

```text
rtk jj -R /Users/ballen/Projects/plato --no-pager status
rtk jj -R /Users/ballen/Projects/plato --no-pager log -r @- -n 1 --no-graph -T 'commit_id ++ "\n"'
```

Expected revision:
`6bb59d00ac01fd3238c091d90f2aea43872934c9`.

- [ ] If it differs, run the read-only scoped comparison:

```text
rtk jj -R /Users/ballen/Projects/plato --no-pager diff --summary --from 6bb59d00ac01fd3238c091d90f2aea43872934c9 --to @- root:AGENTS.md root:ruff.toml root:src/plato/mypy.ini root:pytest.ini root:.pre-commit-config.yaml root:.markdownlint.json root:.cursor/rules/104_python_style_guide.mdc root:.cursor/rules/104_pydantic_style_guide.mdc root:.cursor/rules/104_data_validation.mdc root:.cursor/rules/104_pythonic_apis.mdc root:.cursor/rules/test_rules_macro.mdc root:.cursor/rules/test_rules_micro.mdc root:.cursor/rules/lessons_learned.mdc root:.cursor/rules/lessons_promoted.mdc root:.cursor/rules/uv.mdc root:docs/tooling/uv_workspace_guide.md root:skills/jujutsu-workflow/SKILL.md root:skills/jujutsu-workflow/reference.md
```

Expected: no output. Otherwise stop for source re-review and update the one
captured revision consistently in metadata and tests.

- [ ] From the committed plan checkpoint, create the implementation bookmark:

```text
rtk jj bookmark create implement-plato-standards -r port-plato-standards
rtk jj git push --bookmark implement-plato-standards
rtk jj workspace add /Users/ballen/Projects/ballen-config-standards --name standards-implementation -r implement-plato-standards
rtk jj -R /Users/ballen/Projects/ballen-config-standards --no-pager status
```

If the push is unavailable, continue locally only after reporting it; do not
delay the local bookmark or workspace. All remaining commands run from the
new workspace.

## Task 1: Generic Python Tooling Starter

**Commit:** `feat: add generic Python tooling starter bundle`

**Files:** the six files under
`assistants/shared/standards/templates/python/` and
`tests/assistants/test_standard_templates.py`.

### Test contract

- [ ] Add the focused test module first with four tests:

| Test | Contract |
|---|---|
| `test_python_tooling_bundle_has_expected_files` | Exactly the five configuration files plus README; no generated files |
| `test_python_tooling_templates_parse` | Parse TOML with `tomllib`, INI with `ConfigParser(interpolation=None)`, YAML with `yaml.safe_load`, and JSON with `json.loads` |
| `test_python_tooling_templates_encode_approved_defaults` | Assert the defaults, hook IDs, repository URLs, and revisions below |
| `test_python_tooling_bundle_is_portable_and_copy_once` | Require ownership/adaptation prose and reject repository coupling, placeholders, and token-like samples |

Use case-normalized literal rejection for:

```python
(
    "plato",
    "/users/",
    "autopilot",
    "ami-",
    "pydantic 2.8",
    "--project src",
    "{{",
)
```

Use explicit regular expressions for unfinished placeholder markers and
credential assignments with values of eight or more token-like characters.
Neutral prose about not copying secrets remains valid.

- [ ] Run the first test and confirm it fails because the bundle is absent:

```text
rtk uv run --frozen pytest tests/assistants/test_standard_templates.py::test_python_tooling_bundle_has_expected_files -q
```

### Asset contract

- [ ] Add the starter files with these exact boundaries:

| File | Required baseline | Exclude |
|---|---|---|
| `ruff.toml` | Python 3.12, 100 columns, formatter settings, `select = ["ALL"]`, Google docstrings, generic test exceptions | Paths, first-party packages, vendored exclusions, AMI workarounds, temporary `ASYNC240`, `UP042`, and `PLW0108` suppressions |
| `mypy.ini` | Python 3.12, typed definitions, strict optional, checked untyped bodies, error codes, unused-ignore warnings | Global missing-import suppression, third-party overrides, scratch/layout/cache paths |
| `pytest.ini` | `-ra`, `testpaths = tests`, strict expected failures, documented `integration` and `slow` markers | Memray, coverage, `pythonpath`, project markers, warning suppressions |
| `.pre-commit-config.yaml` | Integrity hooks, native Ruff check/format, Markdownlint | Local `uv run`, `--project src`, path excludes, uv-lock, commit policy |
| `.markdownlint.json` | Reviewed Plato values reproduced below | Repository paths |
| `README.md` | Ownership, tools, adaptation points, optional Pydantic/uv-lock/conventional commits, pin maintenance | Generator or synchronization claims |

Retain these deliberate Ruff ignores rather than inventing a stricter policy:

```toml
ignore = [
  "COM", "CPY", "FIX", "TC", "D401", "N803", "N806",
  "TD003", "ISC001", "RET504", "TRY300", "PLR0913",
]
```

Keep the Pydantic mypy plugin commented and conditional.

Use this exact Markdownlint document:

```json
{
  "default": true,
  "no-hard-tabs": true,
  "MD013": false,
  "MD007": { "indent": 4 },
  "MD024": { "siblings_only": true },
  "MD025": false,
  "MD029": { "style": "ordered" }
}
```

Use this exact pre-commit repository map:

| Repository | Revision | Hooks |
|---|---|---|
| `https://github.com/pre-commit/pre-commit-hooks` | `v6.0.0` | `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-toml`, `check-added-large-files` |
| `https://github.com/astral-sh/ruff-pre-commit` | `v0.16.0` | `ruff-check` with `--fix`, `ruff-format` |
| `https://github.com/DavidAnson/markdownlint-cli2` | `v0.23.2` | `markdownlint-cli2` with `.markdownlint.json` |

Primary pin sources:

- <https://github.com/pre-commit/pre-commit-hooks/releases>
- <https://github.com/astral-sh/ruff/releases>
- <https://github.com/DavidAnson/markdownlint-cli2#pre-commit>

### Focused verification and checkpoint

- [ ] Run:

```text
rtk uv run --frozen pytest tests/assistants/test_standard_templates.py -q
rtk uv run --frozen pre-commit validate-config assistants/shared/standards/templates/python/.pre-commit-config.yaml
rtk uv run --frozen pre-commit install-hooks --config /Users/ballen/Projects/ballen-config-standards/assistants/shared/standards/templates/python/.pre-commit-config.yaml
rtk uvx --from ruff==0.16.0 ruff check --config assistants/shared/standards/templates/python/ruff.toml --show-settings tests/assistants/test_standard_templates.py
rtk uv run --frozen ruff check tests/assistants/test_standard_templates.py
rtk uv run --frozen pre-commit run --files assistants/shared/standards/templates/python/README.md assistants/shared/standards/templates/python/ruff.toml assistants/shared/standards/templates/python/mypy.ini assistants/shared/standards/templates/python/pytest.ini assistants/shared/standards/templates/python/.pre-commit-config.yaml assistants/shared/standards/templates/python/.markdownlint.json tests/assistants/test_standard_templates.py
```

Expected: four focused tests and all validators pass. `install-hooks` proves
the nested revisions and hook IDs resolve without running the starter policy
over ballen-config. Run only the `install-hooks` line from the colocated Git
checkout `/Users/ballen/Projects/ballen-config`; a secondary Jujutsu workspace
intentionally has no `.git` directory.

- [ ] Request one targeted read-only review for tooling portability, pins, and
  newly invented policy. Resolve findings, rerun only the affected focused
  checks, then record the commit:

```text
rtk jj --no-pager diff
rtk jj describe -m "feat: add generic Python tooling starter bundle"
rtk jj bookmark move implement-plato-standards --to @
rtk jj git push --bookmark implement-plato-standards
rtk jj new
```

## Task 2: Portable Global and Repository Baselines

**Commit:** `feat: add portable engineering baselines`

**Files:** the four shared/native instruction sources and tests listed in the
file map, plus `templates/repository-rules/` and
`tests/assistants/test_repository_rules.py`.

### Global core and native renderers

- [ ] Update the existing tests first:

  - core is at most 200 words;
  - it contains repository/executable-configuration precedence,
    staff-level judgment, simplest sufficient solution, readability,
    maintainability, fresh verification, conditional Python 3.12,
    `TypedDict`, Pydantic v2, Google docstrings, pytest fixtures, and
    conditional `.jj/` routing;
  - `Pydantic 2.8` is absent;
  - each rendered native output contains the exact core once and the
    precedence sentence once; and
  - precedence is absent from each native suffix while existing agent-specific
    safety assertions remain.

- [ ] Run the focused renderer tests and confirm the old wording fails:

```text
rtk uv run --frozen pytest tests/assistants/test_instructions.py::test_engineering_defaults_contain_portable_requirements tests/assistants/test_cursor.py::test_rendered_user_rules_are_canonical_and_manual_only tests/assistants/test_claude.py::test_instruction_renderer_uses_canonical_guidance_and_claude_suffix tests/assistants/test_codex.py::test_instruction_and_configuration_own_only_codex_resources -q
```

- [ ] Replace `assistants/shared/instructions/engineering.md` exactly with:

```markdown
# Engineering defaults

Repository instructions and executable configuration take precedence.

Use staff-level judgment and choose the simplest sufficient solution. Optimize
for readability and maintainability. Avoid unrelated scope, and run fresh
verification before claiming completion.

For Python repositories unless their own configuration says otherwise:

- Use Python 3.12.
- Use type hints, `TypedDict` for controlled mapping shapes, and Pydantic v2 for
  validated models.
- Use Google-style docstrings and pytest fixtures.

Use Jujutsu when `.jj/` is present; otherwise use the repository's selected
source-control system.
```

- [ ] Remove only the duplicated precedence sentence from the Cursor, Claude,
  and Codex suffixes. Preserve headings, includes, integrations, manual Cursor
  handoff language, and all target-specific safety rules.

### Passive repository rules

- [ ] Add a focused repository-rule test module that asserts:

  - the bundle contains only README and the three native entries;
  - `AGENTS.md` and `CLAUDE.md` equal the exact shared core plus the routing
    sentence below;
  - the Cursor body is byte-identical and its frontmatter has
    `alwaysApply: true`;
  - README documents only Default, All, and direct narrower copies;
  - tooling files are absent from All; and
  - these passive assets are absent from `assistants/inventory.yaml`.

Routing sentence:

```markdown
If `docs/engineering-standards/` exists, read the applicable topic documents before relevant implementation or review work.
```

- [ ] Run the new module and confirm it fails before the templates exist:

```text
rtk uv run --frozen pytest tests/assistants/test_repository_rules.py -q
```

- [ ] Add:

  - `AGENTS.md` and `CLAUDE.md` as exact core snapshots plus the routing
    sentence;
  - `.cursor/rules/engineering.mdc` with description
    `Repository-owned engineering defaults`, blank `globs:`, and
    `alwaysApply: true`, followed by the identical body; and
  - a four-section README: Ownership, Default, All, Narrower migrations.

Default copies exactly the three native entries. All copies Default plus
`README.md` and the eight canonical topic files into
`docs/engineering-standards/`. State that tooling is separate, existing files
must be merged rather than silently overwritten, copied files become
repository-owned snapshots, and there is no installer or file-selector
command.

### Focused verification and checkpoint

- [ ] Run:

```text
rtk uv run --frozen pytest tests/assistants/test_instructions.py tests/assistants/test_repository_rules.py tests/assistants/test_cursor.py::test_rendered_user_rules_are_canonical_and_manual_only tests/assistants/test_claude.py::test_instruction_renderer_uses_canonical_guidance_and_claude_suffix tests/assistants/test_codex.py::test_instruction_and_configuration_own_only_codex_resources -q
rtk uv run --frozen ruff check tests/assistants/test_instructions.py tests/assistants/test_repository_rules.py tests/assistants/test_cursor.py tests/assistants/test_claude.py tests/assistants/test_codex.py
rtk uv run --frozen pre-commit run --files assistants/shared/instructions/engineering.md assistants/cursor/user-rules.md assistants/claude/CLAUDE.md assistants/codex/AGENTS.md assistants/shared/standards/templates/repository-rules/README.md assistants/shared/standards/templates/repository-rules/AGENTS.md assistants/shared/standards/templates/repository-rules/CLAUDE.md assistants/shared/standards/templates/repository-rules/.cursor/rules/engineering.mdc tests/assistants/test_instructions.py tests/assistants/test_repository_rules.py tests/assistants/test_cursor.py tests/assistants/test_claude.py tests/assistants/test_codex.py
```

- [ ] Request one targeted read-only review for native rendering, snapshot
  ownership, and accidental runtime/inventory scope. Resolve findings and
  record the checkpoint:

```text
rtk jj --no-pager diff
rtk jj describe -m "feat: add portable engineering baselines"
rtk jj bookmark move implement-plato-standards --to @
rtk jj git push --bookmark implement-plato-standards
rtk jj new
```

## Task 3: Canonical Engineering Standards Library

**Commit:** `docs: add canonical engineering standards`

**Files:** nine Markdown files directly under
`assistants/shared/standards/`, `tests/assistants/test_standards.py`, and the
final copy-mode smoke test in `tests/assistants/test_repository_rules.py`.

### Focused test contract

- [ ] Add the standards tests first:

| Test | Contract |
|---|---|
| `test_standards_directory_contains_only_canonical_documents` | Exactly README plus the eight topic filenames |
| `test_standards_index_links_every_canonical_topic_once` | Every relative topic link occurs once |
| `test_standards_index_explains_authority_and_copy_modes` | Core/topic authority, precedence, Default/All, snapshot ownership, and future skill loading |
| `test_topic_standard_has_structured_provenance` | Exact source paths, one immutable revision, source roles, disposition, review date, and required correction note |
| `test_topic_standard_body_is_portable` | Exact prohibited-pattern scan described below |
| `test_topic_standard_covers_approved_content` | Per-topic requirements in the content matrix below |
| `test_pydantic_standard_records_supported_version_review` | Stable 2.13.4 review, official migration/release sources, supported `model_post_init` semantics |
| `test_procedural_standards_do_not_embed_command_recipes` | No shell fences or concrete `jj`, `git`, or `uv` command lines in source-control/dependency topics |
| `test_repository_rule_copy_modes_materialize_expected_layout` | Copy real assets into `tmp_path`; Default has three entries, All adds nine standards files, neither has tooling |

Use `TypedDict` definitions for parsed provenance and version-review mappings,
then narrow the YAML result with runtime `isinstance` checks and `cast`.

The body-only portability scanner rejects:

```text
Pydantic 2.8
/Users/
from plato
import plato
Plato
Autopilot
MechanisticModel
QSP
AMI-<digits>
GitLab
1Password
AWS Secrets Manager
src/plato
docs/agent_charter
plato:skill
plugins/cache
trust_level
.claude/sessions
.codex/sessions
.cursor/sessions
.claude/history
.codex/history
.cursor/history
mcp.json
token-shaped sk-, ghp-, or glpat- samples
TODO, TBD, or FIXME markers
```

Neutral policy terms such as credentials, secrets, authentication, and trust
boundaries remain valid.

- [ ] Run and confirm failure because the canonical documents are absent:

```text
rtk uv run --frozen pytest tests/assistants/test_standards.py tests/assistants/test_repository_rules.py -q
```

### Provenance and index

- [ ] Use this exact source map:

| Topic | Source paths |
|---|---|
| `python.md` | `AGENTS.md`; `.cursor/rules/104_python_style_guide.mdc`; both lesson files |
| `pydantic.md` | `AGENTS.md`; `.cursor/rules/104_pydantic_style_guide.mdc`; both lesson files |
| `validation.md` | data-validation rule; Pydantic rule; both lesson files |
| `api-design.md` | Pythonic APIs rule; both lesson files |
| `testing.md` | macro and micro test rules; both lesson files |
| `documentation.md` | Python rule; Pydantic rule; both lesson files |
| `source-control.md` | `AGENTS.md`; Jujutsu skill and reference |
| `dependency-management.md` | `AGENTS.md`; uv rule; uv workspace guide |

In tests, expand every shorthand above to the exact repository-relative path.
Any listed `lessons_promoted.mdc` path has role `provenance-only`. The uv
workspace guide has role `evidence-after-correction`. All other paths are
reviewed content inputs.

Use this metadata shape on every topic:

```yaml
---
provenance:
  source_repository: plato
  source_revision: 6bb59d00ac01fd3238c091d90f2aea43872934c9
  source_paths:
    - AGENTS.md
  approved_decision: docs/superpowers/specs/2026-07-27-plato-engineering-standards-migration-design.md
  disposition: adapted
  portability_result: portable-after-adaptation
  review_date: "2026-07-27"
---
```

Add `source_roles` only for the exceptional inputs. Use `corrected` plus a
short `correction_note` for Python, Pydantic, API design, testing,
documentation, source control, and dependency management. Use `adapted`
without a correction note for validation.

The Pydantic topic also records:

```yaml
version_review:
  product: Pydantic
  version: "2.13.4"
  primary_source: https://docs.pydantic.dev/latest/migration/
  release_history: https://pypi.org/project/pydantic/#history
```

If the official history shows a newer stable release, stop for re-review;
2.14.0a1 is a prerelease and does not replace the approved baseline silently.
The normative rule remains minor-agnostic `Pydantic v2`.

- [ ] Write the index with four sections: Authority, Canonical topics,
  Repository snapshots, and Future progressive loading. Link every canonical
  topic once. State that topic files are normative, the index is not a second
  authority, repository instructions/configuration take precedence, and future
  skills may load the canonical files without implying a resolver exists now.

### Topic content matrix

- [ ] Draft the eight normative topics against this matrix:

| Topic | Must include | Remove or correct |
|---|---|---|
| Python | Conditional Python 3.12, typing, `TypedDict`, naming, imports, explicit exceptions, resource handling, serialization, readable control flow | Plato/Loguru mandates; package layout; false claim that adjacent attribute strings appear in `help()` |
| Pydantic | Boundary-model decision, Pydantic v2, `extra="forbid"`, field docs, `Literal`/enums, validators, serialization, `SecretStr`, composition, supported `model_post_init`, trusted mappings, runtime dependency containers, conditional `pydantic-settings`, link to `validation.md` | Plato bases/config models; prerelease baseline; deprecated `model_post_init` claim |
| Validation | Parsing vs validation vs normalization vs business rules, trust boundaries, structured results, redaction, validated configuration | Named providers, auth flows, internal infrastructure |
| API design | Small typed contracts, HTTP semantics, structured errors, pagination, idempotency, compatibility, optional frameworks | Plato foundations; universal FastAPI or HATEOAS |
| Testing | Test levels, regression-first fixes, fixtures, patch-at-use, async-aware mocks, behavioral assertions, exception-message matching, strict expected failures, reviewed snapshots, opt-in nondeterminism, reject test theatre | Plato commands/paths/markers, thresholds, retries, Memray, provider doubles |
| Documentation | Google docstrings, supported class-attribute docs, README scope, examples, diagrams, decision records, configured Markdown lint, no duplicated API inventory | Incorrect attribute-docstring behavior |
| Source control | Repository detection, `.jj/` routing, preserve unrelated work, status/diff review, approval for destructive actions | Git staging/branch/worktree/rebase recipes; embedded commands |
| Dependency management | Repository-selected manager/environment, declarations and lockfile as authority, intentional runtime/dev dependencies, uv only when selected | uv commands, Plato workspace layout, stale membership |

The exact Pydantic sentence is:

```markdown
`model_post_init` is supported as an instance lifecycle hook.
```

### Focused and final verification

- [ ] Run the focused documentation and policy checks:

```text
rtk uv run --frozen pytest tests/assistants/test_standards.py tests/assistants/test_repository_rules.py -q
rtk uv run --frozen python -m ballen_config.policy
rtk uv run --frozen ruff check tests/assistants/test_standards.py tests/assistants/test_repository_rules.py
rtk uv run --frozen pre-commit run --files assistants/shared/standards/README.md assistants/shared/standards/python.md assistants/shared/standards/pydantic.md assistants/shared/standards/validation.md assistants/shared/standards/api-design.md assistants/shared/standards/testing.md assistants/shared/standards/documentation.md assistants/shared/standards/source-control.md assistants/shared/standards/dependency-management.md tests/assistants/test_standards.py tests/assistants/test_repository_rules.py
```

- [ ] Request one targeted read-only review for provenance, content boundaries,
  Pydantic accuracy, and Plato leakage. Resolve findings with focused checks.

- [ ] Run the single full branch gate:

```text
rtk uv run --frozen pre-commit run --all-files
rtk uv run --frozen mypy
rtk uv run --frozen pytest
rtk ./bootstrap plan --profile default
rtk ./bootstrap doctor --profile default
```

Do not run `bootstrap configure`. If doctor reports only that installed global
instructions trail the branch, record that expected local drift; repository
integrity and policy failures remain blocking.

- [ ] Reconfirm Plato is clean at the same source revision:

```text
rtk jj -R /Users/ballen/Projects/plato --no-pager status
rtk jj -R /Users/ballen/Projects/plato --no-pager log -r @- -n 1 --no-graph -T 'commit_id ++ "\n"'
```

- [ ] Review the complete branch boundary and record the final checkpoint:

```text
rtk jj --no-pager status
rtk jj --no-pager diff
rtk jj describe -m "docs: add canonical engineering standards"
rtk jj bookmark move implement-plato-standards --to @
rtk jj git push --bookmark implement-plato-standards
rtk jj new
rtk jj --no-pager status
rtk jj --no-pager diff --from port-plato-standards --to implement-plato-standards
rtk jj --no-pager log -r 'port-plato-standards::implement-plato-standards' --no-graph -T 'commit_id.short() ++ " " ++ description.first_line() ++ "\n"'
```

Expected: an empty working copy and a range containing the committed plan plus
three ordered implementation commits. The range diff contains no
runtime/inventory/dependency changes, and Plato remains unchanged.

## Acceptance Checklist

- [x] The concise core renders once for Cursor, Claude Code, and Codex.
- [x] Global and repository-native rules say Pydantic v2, not Pydantic 2.8.
- [x] The tooling bundle has five valid configs plus README and no Plato
  coupling.
- [x] Default has exactly two native entries, `AGENTS.md` plus a delegating
  `CLAUDE.md`; All adds the index and eight topics but no tooling.
- [x] Copied rules and tooling are explicitly repository-owned snapshots.
- [x] Every topic has exact provenance, review status, and required corrections
  in `provenance.yaml`.
- [x] Topic standards contain policy; procedural workflows remain deferred to
  the skills migration.
- [x] No catalog, resolver, installer, selector, generator, synchronization
  path, or runtime standards module was added.
- [x] Plato is clean and unchanged at the captured immutable revision.
- [x] Focused checks pass per commit and one full branch gate passes at the end.

## Implemented Deviations

The delivered branch differs from the design above in four reviewed ways. Task
prose earlier in this plan still describes the original intent; this section is
authoritative for what shipped.

| Planned | Delivered | Reason |
|---|---|---|
| `assistants/shared/instructions/engineering.md` | `assistants/shared/instructions/core.md` | The file is the shared core for every agent, not an engineering-only section |
| Per-topic YAML frontmatter | One manifest at `docs/superpowers/specs/2026-07-27-plato-engineering-standards-provenance.yaml` | Keeps migration audit metadata out of documents repositories copy as normative guidance, and beside the decision it records |
| Default copies three native entries including `.cursor/rules/engineering.mdc` | Default copies `AGENTS.md` plus a delegating `CLAUDE.md` | Cursor discovers root `AGENTS.md` natively, so a third copy only adds drift |
| Prose-assertion tests for topic bodies and index sections | Structural tests for file sets, links, provenance, and tooling parsing | Prose assertions restated the documents instead of protecting a contract |

### Post-migration additions

A follow-up comparison against Plato's own standards-discovery inventory found
generic rules that generalization had dropped, and three Ruff settings the
starter omitted. Both were closed after the original three commits:

- Response-tone guidance in the shared core, generalized from
  `.cursor/rules/104_llm_output.mdc`.
- Restored portable rules: logging and stack-trace preservation, no production
  `assert`, domain exception hierarchies, `Final[T]` on set-once module bindings,
  tests accompanying behavior changes, test readability, attribute-docstring
  practice, and wrap-validator scope.
- Ruff `allow-star-arg-any`, `ban-relative-imports`, and the
  flake8-pytest-style parenthesis settings, plus `SLF001` restored and `ANN`
  removed from the test per-file ignores.

A self-review and over-engineering pass then simplified the audit tests. Task 3
asked for exact repository-relative source paths in tests and runtime
`isinstance` narrowing of the parsed manifest. Both restated an asset this
repository owns, so the tests now assert invariants instead: source paths are
relative and unique, declared roles describe declared sources, dispositions
carry the matching correction note, and only the Pydantic topic records a
version review. The exact source revision, approved decision, and reviewed
Pydantic version remain pinned, because those are deliberate re-review gates.
The same pass removed a generated-cache tolerance that no tool can trigger, as
Ruff and mypy write caches to the repository root rather than beside a
configuration file.

Six files that discovery surfaces remain deliberately unmigrated as
Plato-specific: the agent charter summary, prompt decomposition, agent
construction standard, tool design guidelines, eval threshold guidelines, and
the non-tone portion of the LLM output rule.
