# Self-review: `laptop-bootstrap-review`

## Verdict

**CLEAN** after reviewing and validating the complete stack.

The initial review found several high-confidence opportunities to remove
framework theater, consolidate repeated boundary code, and make documentation
carry intent rather than mirror signatures. All Important, Moderate, and Minor
findings below were resolved or deliberately retained with a documented
standards reason.

A follow-up review then covered every non-Python file in
`main..laptop-bootstrap-review`, including assistant defaults, manifests,
shell and VCS configuration, CI, deleted legacy files, and documentation. That
pass found the additional issues recorded under **Full-stack follow-up**. All
findings were remediated and revalidated. A final application against the
current laptop then exercised the actual package, plugin, configuration,
backup, and diagnostic boundaries.

## Scope

- Compared: `main..laptop-bootstrap-review`
- Review branch: `laptop-bootstrap-review`
- Change size: 110 files, 29,701 additions, 648 deletions
- Python: 26 source files and 29 test files
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

## Initial baseline verification

- `uv run pytest -q`: passed
- `uv run ruff check .`: passed
- `uv run mypy`: passed, 24 source files

## Initial cleanup result

- Source: 18 files, 178 additions, 384 deletions (**net -206 lines**)
- Tests: 17 files, 329 additions, 238 deletions (**net +91 lines**)
- Source and tests combined: **net -115 lines**
- Test functions: 294 to 289
- Collected test cases: 451 to 446
- Test docstrings: 0 missing and 0 stray string literals

The test line increase comes from the Plato requirement that every test function
carry an intent docstring and from stable parameter IDs. Consolidation still
removed five redundant test functions and five collected cases.

The full-stack follow-up added 13 focused regression cases for issues that were
only visible once the executable defaults and live machine state were reviewed.
Applying the result to the current laptop exposed three additional native
integration defects and added another 13 cases, bringing the final suite to
472 cases.

## Final verification

- `uv run --frozen pytest -q`: 472 passed
- `uv run --frozen ruff check .`: passed
- `uv run --frozen ruff format --check src/ballen_config tests`: passed
- `uv run --frozen mypy`: passed, 26 source files
- `uv run --frozen pre-commit run --all-files`: all 11 hooks passed
- `uv lock --check`: passed
- Clean-home default plan: passed, 114 actions
- Clean-home work plan: passed, 124 actions
- Current-laptop work plan: passed

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

18. **Mutable Git heads supply shell code executed on every login**

    Six default-profile shell components clone the current upstream default
    branch, after which `.zshrc` sources or activates their code. This leaves
    both reproducibility and the supply-chain boundary weaker than the pinned
    stage-zero installer. Require an immutable commit for every Git component
    and clone that exact revision before publishing the staged checkout.

### Important

19. **JJ fix tools are unsafe global content transformers**

    `dotfiles/vcs/jj-config.toml` configures `pre-commit` and Ruff commands as
    `jj fix` content filters even though they do not read one file from stdin
    and emit only its replacement on stdout. The Ruff commands also reference
    the deleted `ruff.toml`. Remove these global transformers, safely quote
    filenames in the explicit aliases, and install the remaining
    `pre-commit` dependency through the default profile.

20. **CI does not run the complete pre-commit contract**

    CI invokes two security hooks and duplicates several later checks, but it
    omits trailing-whitespace, end-of-file, YAML, TOML, and large-file hooks.
    Run the complete pre-commit suite in CI while retaining the deeper type and
    test stages.

21. **The approved design describes deferred memory support as implemented**

    The design's CLI and repository-layout sections name memory commands and
    `memory-source-ids.txt`, while the implementation plans correctly defer
    memory transfer. Mark those entries as future capability so the design
    remains an accurate explanation of the shipped defaults.

### Minor

22. **Two archival plans use Unicode directory trees**

    The Plato documentation standard prefers Mermaid for diagrams. Replace the
    two small repository trees with compact tables, which are easier to keep
    accurate and accessible in these archival plans.

## Local-application findings

23. **Native plugin schemas differ from the synthetic test contract**

    Current Claude Code returns separate top-level plugin and marketplace
    arrays, while Codex returns separate `installed` and `marketplaces`
    documents. The adapters expected a combined synthetic shape, so base
    installation completed but assistant inspection stopped the first live
    run before configuration. Validate only the planning fields from each
    current native response, fail closed before crossing the next command
    boundary, and treat only user-scoped Claude plugins as satisfying
    user-scoped defaults.

24. **Stage-zero help is unavailable on an unprepared laptop**

    The Zsh argument gate rejects `--help`, and forwarding it through the
    prepared Python runtime converts argparse's successful exit into
    `invalid configuration`. Provide concise help before runtime preparation
    and preserve argparse's successful read-only exit when invoked directly.

25. **Cursor rewrites managed settings into its native byte format**

    Cursor serializes `settings.json` with four-space indentation and no
    trailing newline. A semantically identical two-space document therefore
    drifted immediately after configuration. Render this one native document
    in Cursor's byte format while preserving unrelated settings.

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
8. Accepted Cursor's native leading comment preamble without weakening strict
   decoding for reviewed repository JSON.
9. Pinned and checksum-verified the stage-zero Homebrew installer.
10. Removed unsafe global JJ content filters, safely quoted changed filenames,
    installed `pre-commit`, and made CI exercise the full hook contract.
11. Corrected the design's deferred-memory claims and replaced archival Unicode
    directory trees with maintainable tables.
12. Ignored bundled Cursor packages that are not extensions while preserving
    strict validation for packages that expose an extension identity.
13. Pinned all six Git-managed shell components to reviewed commits and made
    clean, expected-origin checkouts converge safely to those pins.
14. Validated the public package, cask, Git, plugin, extension, and VSIX
    references against their live sources.
15. Updated Claude and Codex inspection for their current native schemas,
    including separate marketplace queries and Claude user-scope semantics.
16. Made bootstrap help available before runtime preparation and preserved a
    successful Python argparse help exit.
17. Matched Cursor's native settings serialization and proved byte-stable
    convergence while Cursor was running.

## Live-source validation boundary

- Every declared Homebrew formula and cask resolved and was neither deprecated
  nor disabled.
- All six shell repositories resolved, and each pinned commit was fetched and
  checked out in an isolated smoke test.
- Public Claude and Codex marketplace repositories resolved, and declared
  public plugin identifiers matched their upstream manifests.
- Twenty-four curated Cursor extensions resolved through the Visual Studio
  Marketplace. The two Cursor-specific identifiers were validated against the
  installed Cursor packages. The pinned JJ Graph VSIX matched both its declared
  byte size and SHA-256 digest.
- The private Piste GitLab remote is deliberately outside the repository's
  portable authentication boundary. The current local cache confirms the
  declared `ami-qsp-tools` and `fieldkit` package versions. A later local
  marketplace refresh correctly failed closed when GitLab rejected the
  machine's SSH key; no credential workaround was attempted.

## Local application result

- `./bootstrap all --profile work` installed the missing work-profile base:
  AWS CLI 2.36.8, pre-commit 4.6.1, uv 0.11.32, Claude Code 2.1.212, Wave
  0.14.5, and Meslo Nerd Font 3.4.0.
- The six shell repositories converged to their reviewed commits. The two
  missing Cursor extensions and six missing user-scoped Claude plugins were
  installed.
- Managed Claude, Codex, Cursor, Git, JJ, Zsh, Powerlevel10k, Wave, and shared
  RTK resources were applied. Two private timestamped backup sets were retained
  beneath `~/.local/state/ballen-config/backups`.
- The empty stale `~/.cursor/worktrees/plato` directory was removed without
  touching repository data.
- A final work-profile doctor reported every managed resource and base
  component ready. Only the designed manual integration findings remain.
- The optional user-scoped `fieldkit@piste` install remains pending because
  GitLab SSH authentication is unavailable on this machine. Existing
  project-scoped cached state was left intact.
