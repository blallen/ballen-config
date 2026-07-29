# Reusable Skills Review Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve the verified engine safety, diagnostic, test-quality, typing,
and documentation findings on top of the downstream reusable-skills content
tip.

**Architecture:** Preserve the bounded rename protocol and its frozen-plan
model. Harden the coarse lock first, then make rename execution a four-phase
locked transaction: global legacy/successor preflight, successor installation,
global successor proof, and legacy cleanup. Keep doctor classification
read-only and independent from mutating action planning.

**Tech Stack:** Python 3.12, Pydantic 2.8, pytest, Jujutsu, `uv`, Ruff, strict
mypy.

---

## Authority and constraints

- Base revision: `vmmvuoto`, including testing rule `uwuxqmzt`.
- Design:
  `docs/superpowers/specs/2026-07-28-plato-reusable-skills-design.md`.
- Original engine plan:
  `docs/superpowers/plans/2026-07-29-plato-reusable-skills-engine.md`.
- Review: engine self-review findings, enumerated in the task list below. The
  review artifact itself is not committed.
- Follow `assistants/shared/standards/testing.md`, especially:
  - regression-first behavior tests;
  - observable outcomes rather than private counters or mock wiring;
  - short behavior docstrings;
  - explicit parameter IDs;
  - no substring assertions or opaque digests for human-authored instruction
    prose unless production consumes that exact structure.
- Use Jujutsu only. Each task ends in one described change and `jj new`.
- Every behavior fix follows red-green-refactor. Record the expected red failure
  in the worker report.
- Keep the protocol bounded to declared `from`/`to` skill renames.

## File map

- `src/ballen_config/state.py`: lock path, descriptor, and owner invariants.
- `src/ballen_config/assistants/skills.py`: frozen rename proof, preflight,
  successor verification, and cleanup.
- `src/ballen_config/configure.py`: typed contribution and locked phase order.
- `src/ballen_config/assistants/checks.py`: independent doctor classification.
- `src/ballen_config/assistants/models.py`: rename boundary descriptions.
- `src/ballen_config/assistants/__init__.py`: complete public rename exports.
- `src/ballen_config/cli.py`: doctor planning mode and apply-time translation.
- `tests/test_mutation_lock.py`: process-visible lock behavior.
- `tests/test_configure.py`: whole tree/receipt transaction behavior.
- `tests/assistants/test_skill_renames.py`: rename matrix and end-to-end
  protocol behavior.
- `tests/assistants/test_models.py`: compact rename declaration validation.
- `tests/test_cli.py`: normalized stage behavior.

## Deliberate non-changes

- Do not collapse distinct ambiguous rename states; doctor diagnostics use
  their distinctions.
- Do not remove frozen action identity fields. Successor proof requires more
  frozen identity, not less.
- Do not pass a cached planning state snapshot into doctor checks; doctor must
  inspect current on-disk state independently.
- Do not generalize into retirement, adoption, successor-free deletion, or
  per-target partial success.
- Do not test skill prose by substring or opaque digest.

---

## Task 1: Harden mutation-lock path and owner invariants

**Commit:** `fix: harden StateStore mutation lock safety`

**Files:**

- Modify: `src/ballen_config/state.py`
- Modify: `tests/test_mutation_lock.py`
- Modify: `tests/test_configure.py`

- [ ] **Step 1: Add failing lock-leaf tests**

Add behavior tests:

```python
def test_mutation_rejects_symlinked_lock_leaf_without_touching_target(
    repo_root: Path,
    fake_home: Path,
) -> None:
    """A linked lock leaf is rejected without changing its target."""
```

The test creates the state directory, links `.mutation.lock` to an outside
regular file, records the target mode and bytes, expects `ValueError`, and
asserts both remain unchanged.

Add an injected `os.fchmod` failure test that records the opened descriptor and
asserts `os.fstat(descriptor)` raises `OSError` after acquisition fails.

- [ ] **Step 2: Add failing ownership tests**

Add:

```python
def test_compare_and_remove_rejects_non_owner_thread(...) -> None:
    """Only the thread owning mutation() may remove a receipt."""

def test_release_rejects_non_owner_thread(...) -> None:
    """A non-owner thread cannot decrement or release the active lock."""
```

The owner thread holds `mutation()`. A second thread calls the operation and
must receive `StateMutationContentionError`; the receipt and outer lock remain
intact.

- [ ] **Step 3: Replace counter-based lock theatre**

Replace private `_lock_depth` assertions with process-observable tests:

- nested mutation keeps a second process blocked until the outer context exits;
- `record_managed()` serializes concurrent updates without losing either
  receipt;
- `ConfigurationEngine.apply()` pauses at its injected `replace` boundary while
  another process fails a non-blocking acquire, then succeeds after apply.

- [ ] **Step 4: Verify the tests fail for the expected reasons**

Run:

```bash
uv run --frozen pytest tests/test_mutation_lock.py tests/test_configure.py -q
```

Expected failures: linked leaf is followed; non-owner removal succeeds; old
counter-based tests have not yet been replaced by observable exclusion.

- [ ] **Step 5: Implement minimal lock hardening**

In `StateStore`:

- validate `.mutation.lock` as absent or an ordinary regular file;
- open with `O_NOFOLLOW` where available and fail closed otherwise;
- validate the opened descriptor with `os.fstat`;
- place `fchmod`, `flock`, and state assignment inside one cleanup boundary;
- close the descriptor on every setup failure;
- check `_lock_owner == threading.get_ident()` under `_thread_guard` in
  `_release()` and `compare_and_remove()`;
- update `StateMutationContentionError` and `mutation()` Google-style
  docstrings.

- [ ] **Step 6: Verify green**

```bash
uv run --frozen pytest tests/test_mutation_lock.py tests/test_configure.py tests/test_state.py -q
uv run --frozen mypy
```

- [ ] **Step 7: Describe and advance**

```bash
jj describe -m "fix: harden StateStore mutation lock safety"
jj new
```

---

## Task 2: Freeze complete successor proof and reject unsafe leaves

**Commit:** `fix: require exact successor proof for skill renames`

**Files:**

- Modify: `src/ballen_config/assistants/skills.py`
- Modify: `src/ballen_config/assistants/__init__.py`
- Modify: `tests/assistants/test_skill_renames.py`
- Modify: `tests/test_configure.py`

- [ ] **Step 1: Add failing executable-boundary regressions**

Add:

```python
def test_classify_legacy_leaf_symlink_blocks(...) -> None:
    """A linked legacy leaf is blocking rather than clean."""

def test_apply_rejects_stale_successor_receipt(...) -> None:
    """Cleanup requires the successor receipt to match the frozen proof."""

def test_apply_rejects_successor_receipt_with_mismatched_destination(...) -> None:
    """A successor receipt for another destination cannot authorize cleanup."""

def test_compare_and_remove_rollback_restores_legacy_tree(...) -> None:
    """A receipt race after backup restores the exact legacy tree."""
```

Use synthetic skill trees and structured `ManagedRecord` assertions. Do not
assert prose content beyond what production frontmatter parsing consumes.

- [ ] **Step 2: Verify red**

```bash
uv run --frozen pytest tests/assistants/test_skill_renames.py tests/test_configure.py -q
```

Expected failures: an in-home symlink classifies `CLEAN`; stale or mismatched
successor receipts authorize cleanup.

- [ ] **Step 3: Implement frozen successor proof**

- Treat any present non-directory legacy leaf as blocking.
- Extend `SkillRenameAction` with the expected successor source digest and exact
  expected destination identity.
- Build the expected successor `ManagedRecord` from the planned source digest,
  resource ID, target destination, and verified live destination digest.
- Verify receipt key, embedded resource ID, destination, source digest,
  destination digest, and live tree digest before cleanup.
- Export `RenameTargetClassification` with its public classifier.

- [ ] **Step 4: Verify green**

```bash
uv run --frozen pytest tests/assistants/test_skill_renames.py tests/test_configure.py -q
uv run --frozen mypy
```

- [ ] **Step 5: Describe and advance**

```bash
jj describe -m "fix: require exact successor proof for skill renames"
jj new
```

---

## Task 3: Enforce global rename preflight before mutation

**Commit:** `fix: preflight all skill renames before mutation`

**Files:**

- Modify: `src/ballen_config/assistants/skills.py`
- Modify: `src/ballen_config/configure.py`
- Modify: `tests/assistants/test_skill_renames.py`
- Modify: `tests/test_configure.py`

- [ ] **Step 1: Strengthen the time-of-check regression**

Extend `test_toc_tou_legacy_change_fails_closed` to assert:

- legacy tree and receipt remain;
- successor tree is absent;
- successor receipt is absent;
- no backup was created.

- [ ] **Step 2: Add all-target phase-order tests**

Add:

```python
def test_apply_preflights_all_targets_before_any_successor_mutation(...) -> None:
    """One late blocked target prevents every successor mutation."""

def test_apply_verifies_all_successors_before_any_legacy_cleanup(...) -> None:
    """One invalid successor proof prevents every legacy cleanup."""

def test_apply_removes_exact_stale_receipt_without_backup(...) -> None:
    """Exact stale cleanup removes only its receipt after successor proof."""
```

Use real directories, receipts, and the injected publish boundary. Assert
observable trees, receipts, and backup directories.

- [ ] **Step 3: Verify red**

```bash
uv run --frozen pytest tests/assistants/test_skill_renames.py tests/test_configure.py -q
```

Expected failures: successor state changes before legacy revalidation; cleanup
can begin before all successor proofs pass.

- [ ] **Step 4: Implement locked phases**

Add narrow functions adjacent to cleanup:

```python
def preflight_skill_renames(
    engine: ConfigurationEngine,
    actions: tuple[SkillRenameAction, ...],
) -> None:
    """Revalidate every frozen legacy action before mutation."""

def verify_skill_rename_successors(
    engine: ConfigurationEngine,
    actions: tuple[SkillRenameAction, ...],
) -> None:
    """Verify every successor tree and exact receipt before cleanup."""
```

Under the existing outer mutation lock, order `run_configure()` as:

1. validate and plan every managed spec;
2. globally preflight all rename actions and successor feasibility;
3. apply managed specs;
4. globally verify every successor;
5. clean legacy actions.

Cleanup must not repeat or weaken the global proof.

- [ ] **Step 5: Verify green**

```bash
uv run --frozen pytest tests/assistants/test_skill_renames.py tests/test_configure.py tests/test_mutation_lock.py -q
uv run --frozen ruff check src tests
```

- [ ] **Step 6: Describe and advance**

```bash
jj describe -m "fix: preflight all skill renames before mutation"
jj new
```

---

## Task 4: Preserve doctor diagnostics and normalize apply failures

**Commit:** `fix: normalize blocked skill rename stages`

**Files:**

- Modify: `src/ballen_config/assistants/skills.py`
- Modify: `src/ballen_config/cli.py`
- Modify: `tests/assistants/test_skill_renames.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add failing CLI behavior tests**

Add:

```python
def test_configure_normalizes_apply_time_skill_rename_block(...) -> None:
    """Configure returns a redacted exit-2 result for an apply-time block."""

def test_all_stops_before_doctor_on_apply_time_skill_rename_block(...) -> None:
    """All stops after a blocked configure stage without running doctor."""

def test_doctor_cli_reports_blocked_declared_rename(...) -> None:
    """Doctor renders structured findings even when configure would block."""
```

Assert `RunResult`, `StageReport`, doctor finding IDs/status/severity, and
redacted output. Do not assert human-authored skill prose.

- [ ] **Step 2: Verify red**

```bash
uv run --frozen pytest tests/test_cli.py tests/assistants/test_skill_renames.py -q
```

Expected failures: apply-time exception escapes; doctor exits during mutating
rename planning.

- [ ] **Step 3: Separate read-only doctor classification**

- Let assistant configuration skip construction of mutating rename actions for
  the doctor stage while retaining ordinary configuration specs/checks.
- Keep `_skill_rename_findings()` independently loading and classifying current
  state.
- Catch `SkillRenameBlockedError` around configure execution and return the same
  redacted exit-2 outcome as planning-time blocks.
- In `all`, stop after a nonzero configure result and do not run doctor.

- [ ] **Step 4: Verify green**

```bash
uv run --frozen pytest tests/test_cli.py tests/assistants/test_skill_renames.py -q
uv run --frozen pytest -q
```

- [ ] **Step 5: Describe and advance**

```bash
jj describe -m "fix: normalize blocked skill rename stages"
jj new
```

---

## Task 5: Consolidate rename tests at executable boundaries

**Commit:** `test: consolidate skill rename behavior coverage`

**Files:**

- Modify: `tests/test_mutation_lock.py`
- Modify: `tests/test_configure.py`
- Modify: `tests/assistants/test_skill_renames.py`
- Modify: `tests/assistants/test_models.py`

- [ ] **Step 1: Parameterize classifier behavior**

Use a case factory and a matrix with fields:

```python
case_id
legacy_tree
legacy_receipt
successor_tree
expected_state
expect_record
```

Parametrize concrete targets with IDs `cursor`, `claude-code`, and `codex`.
Keep the poisoned-filesystem skipped test separate.

- [ ] **Step 2: Parameterize accepted plan states**

Use fields:

```python
case_id
legacy_present
receipt_kind
expected_state
expect_record
```

Remove `assert digest`, which checks only helper output.

- [ ] **Step 3: Replace the false profile test**

Declare a work-only rename, run the default profile, poison the filesystem
classifier boundary, and assert no inspection or action.

- [ ] **Step 4: Consolidate model and doctor plumbing**

- Build one valid catalog payload and parametrize invalid rename deltas with IDs
  `from-still-present`, `duplicate-from`, and `missing-successor`.
- Extract only doctor invocation and finding lookup; keep state setup visible.
- Remove the duplicate catalog rewrite.

- [ ] **Step 5: Add behavior docstrings**

Add short docstrings to every touched lock, configure, model, and rename test.
Do not describe implementation details; state the observable behavior.

- [ ] **Step 6: Verify no behavior changed**

```bash
uv run --frozen pytest tests/test_mutation_lock.py tests/test_configure.py tests/assistants/test_skill_renames.py tests/assistants/test_models.py -q
uv run --frozen ruff format --check src tests
```

- [ ] **Step 7: Describe and advance**

```bash
jj describe -m "test: consolidate skill rename behavior coverage"
jj new
```

---

## Task 6: Publish typed contracts and focused documentation

**Commit:** `refactor: publish typed skill rename contracts`

**Files:**

- Modify: `src/ballen_config/configure.py`
- Modify: `src/ballen_config/assistants/skills.py`
- Modify: `src/ballen_config/assistants/models.py`
- Modify: `src/ballen_config/assistants/__init__.py`
- Modify: `src/ballen_config/state.py`
- Modify: affected tests only for public API names

- [ ] **Step 1: Remove erased and invalid type contracts**

- Replace `tuple[Any, ...]` and `Sequence[Any]` with
  `SkillRenameAction` through a cycle-safe type import.
- Narrow classifier targets to concrete agent targets or explicitly reject
  `AgentName.SHARED`.
- Remove newly added `from __future__ import annotations` imports.
- Correct `multiprocessing.Queue` annotations in tests.

- [ ] **Step 2: Publish the cleanup boundary**

Replace cross-module calls to `_backup()` / `_restore()` with narrowly named
public transaction operations, without creating a generic action hierarchy.

- [ ] **Step 3: Add focused documentation**

- Add Pydantic field descriptions to `SkillRenameSpec.from_name` and `to_name`.
- Document lock ownership/reentrancy and failure contracts.
- Expand `run_configure()` with Google-style Args, Returns, Raises, and phase
  ordering.
- Document non-obvious frozen action fields and accepted rename states.

- [ ] **Step 4: Apply safe Ponytail reductions**

- Consolidate repeated doctor finding append plumbing only if distinct
  status/severity/message mappings remain explicit.
- Do not cache doctor state, collapse classifications, or delete frozen proof.

- [ ] **Step 5: Verify**

```bash
uv run --frozen mypy
uv run --frozen ruff check src tests
uv run --frozen ruff format --check src tests
uv run --frozen pytest -q
```

- [ ] **Step 6: Describe and advance**

```bash
jj describe -m "refactor: publish typed skill rename contracts"
jj new
```

---

## Task 7: Second self-review and final gate

**Commit:** No commit unless review remediation changes are required.

- [ ] **Step 1: Re-run self-review under the downstream testing rule**

Review the complete remediation range with:

- standards and design compliance;
- test theatre and consolidation;
- type safety and docstrings;
- Ponytail over-engineering;
- explicit scan for instruction substring assertions and opaque prose digests.

- [ ] **Step 2: Fix every confirmed Critical or Important finding**

Use a new failing regression before any production behavior correction. Put
review-only cleanup in one final logical change if needed.

- [ ] **Step 3: Run the full gate**

```bash
uv run --frozen pytest -q
uv run --frozen mypy
uv run --frozen ruff check src tests
uv run --frozen ruff format --check src tests
uv run --frozen --no-sync python -m ballen_config.policy
zsh -n bootstrap
./bootstrap plan --profile default
./bootstrap doctor --profile default
```

- [ ] **Step 4: Inspect the final stack**

```bash
jj status
jj log -r 'vmmvuoto::@'
jj diff --from vmmvuoto --to @ --stat
```
