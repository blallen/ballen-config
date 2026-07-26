# Self-review: `laptop-bootstrap-review`

## Verdict

**REMEDIATION IN PROGRESS** after expanding the review to the complete stack.

The initial review found several high-confidence opportunities to remove
framework theater, consolidate repeated boundary code, and make documentation
carry intent rather than mirror signatures. All Important, Moderate, and Minor
findings below were resolved or deliberately retained with a documented
standards reason.

A follow-up review then covered every non-Python file in
`main..laptop-bootstrap-review`, including assistant defaults, manifests,
shell and VCS configuration, CI, deleted legacy files, and documentation. That
pass found the additional issues recorded under **Full-stack follow-up**.

## Scope

- Compared: `main...laptop-bootstrap-agents`
- Review branch: `laptop-bootstrap-review`
- Change size: 104 files, 28,452 additions, 506 deletions
- Python: 24 source files and 28 test files
- Review batches:
  - core source and docstrings
  - core tests
  - coding-agent tests
  - assistant defaults and manifests
  - shell, CI, dotfiles, security, and deleted files
  - documentation and default guidance

This is a large stack, so the review was intentionally split by subsystem. The
findings below focus on source quality, tests, and documentation; they do not
re-litigate the approved laptop-migration feature design.

## Standards inventory

Coding standards were discovered from `/Users/ballen/Projects/plato`, as
requested:

- `AGENTS.md` and `CLAUDE.md`
- every file under `.cursor/rules/*.mdc`
- especially:
  - `104_python_style_guide.mdc`
  - `104_pythonic_apis.mdc`
  - `104_pydantic_style_guide.mdc`
  - `104_data_validation.mdc`
  - `test_rules_micro.mdc`
  - `test_rules_macro.mdc`
  - `lessons_learned.mdc`
  - `lessons_promoted.mdc`

Applicable rules favor simple, readable Python 3.12; typed signatures; Pydantic
at validated boundaries and lighter internal containers; Google-style
docstrings that add semantic value; pytest fixtures; parameter IDs; and tests
of business behavior rather than framework mechanics.

## Baseline verification

- `uv run pytest -q`: passed
- `uv run ruff check .`: passed
- `uv run mypy`: passed, 24 source files

## Final result

- Source: 18 files, 178 additions, 384 deletions (**net -206 lines**)
- Tests: 17 files, 329 additions, 238 deletions (**net +91 lines**)
- Source and tests combined: **net -115 lines**
- Test functions: 294 to 289
- Collected test cases: 451 to 446
- Test docstrings: 0 missing and 0 stray string literals
- Final verification:
  - `uv run pytest -q`: 446 passed
  - `uv run ruff check .`: passed
  - `uv run ruff format --check src/ballen_config tests`: passed
  - `uv run mypy`: passed, 26 source files
  - `uv run pre-commit run --all-files`: all 11 hooks passed

The test line increase comes from the Plato requirement that every test function
carry an intent docstring and from stable parameter IDs. Consolidation still
removed five redundant test functions and five collected cases.

## Findings

### Important

1. **Production assertions guard boundary values**

   `src/ballen_config/install.py`, `doctor.py`, and `cli.py` use seven
   production `assert` statements before download or filesystem operations.
   Assertions disappear under optimized Python and violate the Plato style
   guide. Replace them with explicit, normalized exceptions.

2. **Strict JSON decoding is implemented four times**

   `assistants/claude.py`, `codex.py`, `cursor.py`, and `hooks.py` independently
   reject duplicate keys and non-finite values. Extract one neutral strict JSON
   decoder and keep each adapter's current exception translation at its
   boundary.

3. **Reviewed-file containment is duplicated and inconsistent**

   Claude, Codex, and Cursor maintain similar checkout-containment and symlink
   checks. Consolidate them into one regular-file loader; the shared version
   should retain the strongest current invariant.

4. **An internal callable container uses Pydantic without a validation
   boundary**

   `ConfigurationContribution` exists only inside the process and requires
   `arbitrary_types_allowed=True`. Replace it with a frozen dataclass and use
   `dataclasses.replace` at its two copy sites.

5. **Tests directly re-check Pydantic behavior**

   - `tests/assistants/test_models.py` mutates frozen models and asserts generic
     extra-field rejection.
   - `tests/test_policy.py` repeats the same framework checks for `Violation`.
   - `tests/test_configure.py` tests accepted Pydantic coercions for file modes.

   Remove framework-mechanics assertions. Retain domain validation tests where
   an unsafe mode or unknown inventory field is an intentional input contract.

### Moderate

6. **Repeated tests and fixtures can be consolidated**

   - The manifest repository fixture is duplicated in `test_manifests.py` and
     `test_planning.py`.
   - The initial empty shared-skill catalog is asserted in both
     `test_inventory.py` and `test_skills.py`.
   - An unprepared `plan` bootstrap test is subsumed by the existing
     parameterized read-only-stage test.
   - Installer size/hash failures repeat the same setup and should form one
     parameterized matrix.

7. **Several parameter matrices lack stable case IDs**

   Add `pytest.param(..., id="...")` to semantically distinct cases in model,
   skill, CLI, bootstrap, and installer tests. This is diagnostic
   parameterization, not a reason to split behavior into more tests.

8. **A bounded-scan test over-models iterator internals**

   `tests/assistants/test_checks.py` uses a 28-line `SentinelScan` protocol
   surrogate to detect a fourth iterator request. Preserve bounded-consumption
   coverage with a small reusable guarded-scandir helper.

9. **A prose test snapshots authored wording byte-for-byte**

   `tests/assistants/test_instructions.py` locks the full
   `engineering.md` document even though renderer tests already cover ordering
   and newline behavior. Assert only the portable content invariants that
   consumers require.

10. **Docstrings often repeat signatures or validator mechanics**

    The largest concentrations are `paths.py`, private validators in
    `assistants/models.py`, and simple constructors/adapters in `state.py`,
    `runner.py`, `cli.py`, `hooks.py`, and `skills.py`. Keep security rationale,
    public behavior, and non-obvious exclusions; remove mechanical
    Args/Returns/Raises sections and trivial private-helper narration.

11. **Test docstring coverage is inconsistent**

    Fifty-four test functions have no docstring even though Plato requires each
    test to explain its intent. Consolidate redundant tests first, then add
    concise intent statements only where the test name and assertions do not
    already communicate the governing behavior.

12. **Module-level constant immutability is inconsistent**

    Constants in assistant models, inventory, skills, and checks should use
    `Final`; mutable mapping constants should expose immutable mappings.

### Minor

13. **Low-value source helpers remain**

    - `_skill_roots` has no callers.
    - `_enabled` rebuilds a string set on every call despite typed callers.
    - A `try` block around `setdefault(...).add()` handles no operation that can
      raise its declared exceptions.
    - `CommandRunner` aliases `Runner` for one production consumer.

14. **The package-version smoke test is release-coupled**

   `tests/test_package.py` hard-codes `0.1.0`. Remove it or compare installed
   package metadata with `ballen_config.__version__`.

## Full-stack follow-up

### Critical

15. **Cursor's stock JSONC keybindings block planning on an existing laptop**

    Cursor initializes `keybindings.json` with a leading `//` comment, but the
    native-state renderer uses the reviewed-source strict JSON decoder.
    `./bootstrap plan --profile work` therefore fails with
    `invalid Cursor keybindings JSON` on this laptop. Keep repository defaults
    strict JSON while accepting Cursor's native JSONC input, then prove both
    clean-home and real-home plans.

16. **The stage-zero Homebrew installer executes a mutable remote script**

    `bootstrap` downloads `Homebrew/install@HEAD` directly into Bash without a
    pinned revision or integrity check. Replace the mutable execution path with
    a pinned installer revision and verify its SHA-256 digest before execution.

17. **One unrelated bundled Cursor package blocks extension inspection**

    Cursor 3.13.10 includes `theme-cursor/package.json` without a `publisher`
    field. `read_bundled_extensions()` treats that as a malformed extension and
    aborts the complete scan, so extension installation cannot inspect this
    otherwise valid Cursor build. Ignore package directories that do not expose
    a canonical extension identity while retaining strict validation for
    identities that are present.

### Important

18. **JJ fix tools are unsafe global content transformers**

    `dotfiles/vcs/jj-config.toml` configures `pre-commit` and Ruff commands as
    `jj fix` content filters even though they do not read one file from stdin
    and emit only its replacement on stdout. The Ruff commands also reference
    the deleted `ruff.toml`. Remove these global transformers, safely quote
    filenames in the explicit aliases, and install the remaining
    `pre-commit` dependency through the default profile.

19. **CI does not run the complete pre-commit contract**

    CI invokes two security hooks and duplicates several later checks, but it
    omits trailing-whitespace, end-of-file, YAML, TOML, and large-file hooks.
    Run the complete pre-commit suite in CI while retaining the deeper type and
    test stages.

20. **The approved design describes deferred memory support as implemented**

    The design's CLI and repository-layout sections name memory commands and
    `memory-source-ids.txt`, while the implementation plans correctly defer
    memory transfer. Mark those entries as future capability so the design
    remains an accurate explanation of the shipped defaults.

### Minor

21. **Two archival plans use Unicode directory trees**

    The Plato documentation standard prefers Mermaid for diagrams. Replace the
    two small repository trees with compact tables, which are easier to keep
    accurate and accessible in these archival plans.

## Ponytail review

The Ponytail pass was limited to over-engineering, not correctness. Its
highest-confidence cuts are:

- `delete`: Pydantic-mechanics tests and the duplicate unprepared-plan test
- `delete`: the unused `_skill_roots` helper
- `shrink`: repeated strict decoders and reviewed-file loaders
- `shrink`: duplicated manifest fixtures and shared-catalog assertions
- `shrink`: the bespoke `SentinelScan` protocol surrogate
- `shrink`: mechanical docstring sections on private validators and adapters
- `yagni`: the single-use `CommandRunner` alias

After adjusting for overlap between findings, the initial review estimated
roughly 200–300 removable lines. The implemented source cleanup removed 206 net
lines while preserving trust-boundary validation, error normalization, bounded
scans, and behavioral coverage.

The final Ponytail-only pass identified 55 one-line test docstrings as
theoretically removable. They remain because Plato's explicit test standard
requires a docstring on every test function. The independent test-quality pass
confirmed that the retained docstrings state test intent and that no stray
standalone string literals remain.

## Remediation completed

1. Replaced production assertions with explicit normalized guards.
2. Consolidated strict JSON parsing and reviewed regular-file loading.
3. Replaced the internal Pydantic contribution model with a frozen dataclass.
4. Removed unused helpers, mutable constant maps, and mechanical source
   docstring sections.
5. Removed framework-theater and duplicate tests, centralized fixtures, and
   added stable parameter IDs.
6. Added a strict Claude-settings regression after final source review found
   one decoder bypass.
7. Ran focused checks, the complete suite, and independent source, test, and
   Ponytail reviews.
