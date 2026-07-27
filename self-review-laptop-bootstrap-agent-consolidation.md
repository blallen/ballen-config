## Self-Review: laptop-bootstrap-agent-consolidation

**Range:** `ymsmsltm::qupmtxup` (inclusive; diff from `ymsmsltm-`)
**Files changed:** 34
**Commits:** 6
**Diff size:** 3,795 insertions, 908 deletions
**Standards source:** `/Users/ballen/Projects/plato`

The diff exceeded the self-review single-pass threshold, so it was reviewed in
complete source, test, standards/documentation, and Ponytail batches. No files
were sampled or omitted.

### Standards Discovery Inventory

#### Found

- Cursor workspace rules: 12 files under `plato/.cursor/rules/`
- Agent instructions: `plato/AGENTS.md`, `plato/CLAUDE.md`
- Contribution/docs standards:
  `plato/docs/agent_charter/tool_design_guidelines.md`,
  `plato/docs/agent_charter/agent_construction_standard.md`,
  `plato/docs/evals/threshold_guidelines.md`, and
  `plato/docs/tooling/uv_workspace_guide.md`
- Accumulated lessons: `plato/.cursor/rules/lessons_learned.mdc` and
  `plato/.cursor/rules/lessons_promoted.mdc`

#### Missing

- Agent instructions: `GEMINI.md`, `COPILOT.md`,
  `.github/copilot-instructions.md`
- Contribution standard: `CONTRIBUTING.md`

#### Prioritized Read Order

1. `plato/AGENTS.md` and `plato/CLAUDE.md`
2. `plato/.cursor/rules/104_python_style_guide.mdc`
3. `plato/.cursor/rules/104_pydantic_style_guide.mdc`
4. `plato/.cursor/rules/104_data_validation.mdc`
5. `plato/.cursor/rules/test_rules_micro.mdc`
6. `plato/.cursor/rules/test_rules_macro.mdc`
7. The active and promoted lesson archives

#### Coverage Note

The agent-construction, tool-design, and evaluation-threshold guides were read
but do not govern this non-agent bootstrap implementation. Their applicable
general typing and simplicity principles are already represented by the
project instructions and Cursor rules above.

### Standards & Lessons

No critical or blocking standards violation was found. Documentation,
declarative catalogs, target separation, secret/state exclusions, and removal
of the former per-agent plugin files are internally consistent.

| Severity | Location | Rule | Detail |
| --- | --- | --- | --- |
| Suggestion | `src/ballen_config/assistants/desired_state.py:208` | `104_python_style_guide.mdc`: no `assert` in production | Three `assert isinstance(...)` statements narrow `_catalog()`'s return union even though `_catalog()` has already checked the type. Make `_catalog()` generic or overloaded, or use explicit casts, so optimized Python does not remove production checks used as control-flow documentation. |
| Suggestion | `src/ballen_config/assistants/desired_state.py:44`, `src/ballen_config/assistants/inventory.py:29` | `104_pydantic_style_guide.mdc`: Pydantic at ingestion boundaries; dataclasses for internal runtime containers | `PluginCatalogProjection`, `AssistantDesiredState`, `LoadedCatalog`, and `LoadedInventory` have no validators and are constructed only from already validated objects. Frozen dataclasses provide true container immutability without Pydantic initialization or schema machinery. `ResolvedInventory` is the adjacent pre-existing instance of the same pattern. |
| Suggestion | `src/ballen_config/assistants/models.py:215` | `104_pydantic_style_guide.mdc`: document Pydantic fields with `Field(description=...)` | The newly added YAML-boundary models `Marketplace`, `NativeMarketplacePlugin`, `CursorMarketplacePlugin`, `CursorLocalPlugin`, and `PluginCatalog` omit descriptions on their semantic fields. Their one-line class docstrings are already appropriate; add concise field descriptions rather than expanding the docstrings. |
| Nit | `src/ballen_config/assistants/cursor_plugins.py:3`, `src/ballen_config/assistants/desired_state.py:3`, `src/ballen_config/assistants/orchestrator.py:3` | `104_pydantic_style_guide.mdc`: do not add future annotations by default on Python 3.12+ | None of the three new modules has a real forward-reference requirement. Remove the imports. |
| Nit | `src/ballen_config/assistants/desired_state.py:33` | `104_python_style_guide.mdc`: module singletons are `Final` | `_CONCRETE_AGENTS` is immutable but lacks `Final[tuple[ConcreteAgentName, ...]]`. |

The three new 301–359-line modules cross Plato's review trigger for module
size, but each remains cohesive around one concern. Splitting them now would
scatter desired-state preflight, Cursor plugin safety, or orchestration without
reducing complexity, so no split is recommended.

### Test Quality

Fourteen changed test/fixture files containing 241 test functions were read in
full. No theatre tests, missing test docstrings, untyped test functions,
snapshot artifacts, or blocking coverage gaps were found. The tests generally
exercise behavior and failure boundaries rather than Pydantic or framework
mechanics.

| Severity | Location | Rule | Detail |
| --- | --- | --- | --- |
| Suggestion | `tests/assistants/test_cursor_plugins.py:147`, `tests/assistants/test_cursor_plugins.py:167`, `tests/assistants/test_integration.py:403` | `test_rules_micro.mdc`: repeated cases use explicit stable IDs | These three parametrizations added by the stack use bare values. Use `pytest.param(..., id="...")`. Across the complete touched files, 34 functions/35 parametrization decorators lack explicit IDs; the remainder are inherited cleanup rather than new regressions. |
| Suggestion | `src/ballen_config/assistants/cursor_plugins.py:183` | `test_rules_macro.mdc`: cover behavior branches and error paths | `_skill_roots()` has no positive test for explicit `manifest.skills` as either a string or tuple. Add parametrized collision tests proving both forms are resolved and inspected rather than silently ignored. |
| Nit | `src/ballen_config/assistants/desired_state.py:93` | `test_rules_macro.mdc`: cover meaningful error handling | `cursor_local_plugin_snapshots()` has an untested `KeyError` to secret-free `ValueError` path. A constructed inconsistent desired state can cover the defensive contract. |
| Nit | `tests/assistants/test_models.py:674` | `test_rules_micro.mdc`: assertions should verify behavior | This pre-existing acceptance test in a touched file only calls `AssistantInventory.model_validate()`. It meaningfully guards allowed paths and is not theatre, but asserting the returned resource variant or preserved field would make the contract explicit. |

High-quality examples include:

- `tests/assistants/test_integration.py:237`, which verifies the error plus
  commands, downloads, confirmations, state, backups, and filesystem effects;
- `tests/assistants/test_cursor_plugins.py:272`, which exercises managed-tree
  backup and rollback;
- `tests/assistants/test_desired_state.py:263`, which proves preflight snapshots
  are reused rather than recomputed; and
- `tests/assistants/test_checks.py:125`, which protects bounded, non-recursive
  private-state inspection.

### Type Safety

Mypy passes all 29 source files. No untyped public signature, broad `Any`,
unsafe `Optional` usage, duplicate boundary model, or type-ignore comment was
found. The type-design improvements are the frozen-dataclass and generic
`_catalog()` recommendations already listed under Standards & Lessons.

### Ponytail Review

The Ponytail pass reviewed only over-engineering and deletion opportunities;
it did not assess correctness, security, or performance.

- `src/ballen_config/assistants/models.py:234`: `yagni:` Cursor marketplace and
  local-plugin variants have no production entries and account for roughly
  800–850 lines of implementation and tests. Keep only the manual Customize
  guidance and add native support with the first reviewed plugin.
  This is a valid scope-reduction option, but it conflicts with the approved
  design goal of supporting an independently managed future Cursor plugin.
  Retain it unless that capability is intentionally deferred.
- `src/ballen_config/assistants/codex.py:48`: `shrink:` the three snapshot
  `TypedDict` wrappers and `_plugin_snapshot()` reshape installed plugin IDs
  only for `install_actions()` to flatten them again. Strictly parse directly
  to `frozenset[str]`.
- `tests/assistants/test_claude.py:50` and
  `tests/assistants/test_codex.py:43`: `shrink:` two roughly 100-line
  `PluginCatalogProjection` fixtures duplicate checked-in catalog declarations.
  Load and project the reviewed catalog from a shared fixture, or use a much
  smaller synthetic projection for adapter-only behavior.
- `tests/assistants/conftest.py:80`: `shrink:` the nested checkout factory has
  an eight-line Args/Returns docstring for one self-evident parameter and
  return. Keep a one-line helper docstring.

Ponytail's theoretical result is `net: -1,050 lines possible.` Approximately
800–850 of those lines require dropping an approved Cursor capability; the
remaining fixture, decoder, and docstring reductions preserve the current
scope.

### Code Quality (linting)

All checks passed at `qupmtxup`:

- `uv run --frozen pre-commit run --all-files`
  - whitespace, EOF, YAML, TOML, large-file, private-key, and secret checks
  - Ruff lint and format
  - `ballen-config` policy
  - bootstrap Zsh syntax
- `uv run --frozen mypy`: 29 source files, no issues
- `uv run --frozen pytest -q`: 542 tests passed
- `./bootstrap plan --profile default`: passed
- `./bootstrap doctor --profile default`: passed

### Verdict: NEEDS_ATTENTION

There are no blockers, failed checks, theatre tests, or discovered correctness
defects. The production assertions, internal Pydantic containers, duplicated
adapter fixtures, and focused test gaps are worthwhile cleanup before merging
the stack. The large Cursor deletion is an explicit product-scope choice, not
a required remediation.

No fixes were applied during this report-first review.
