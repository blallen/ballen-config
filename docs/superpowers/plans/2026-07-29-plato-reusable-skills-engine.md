# Plato Reusable Skills Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the coarse mutation lock and bounded skill-rename protocol so
`jujutsu-workflow` can become `using-jujutsu` without orphaning managed trees or
receipts.

**Architecture:** Keep the existing `SkillSpec` delivery model. Add one catalog
schema field (`renames`), one reentrant advisory lock around tree-and-receipt
mutation, and one `SkillRenameAction` with plan/apply halves. Successor install
reuses `ConfigurationEngine` tree apply; legacy cleanup uses backup plus
compare-and-remove. No general retirement subsystem, adoption, or per-target
results.

**Tech Stack:** Python 3.12, Pydantic v2, pytest, PyYAML, `fcntl` (stdlib),
Jujutsu, `uv`.

## Global Constraints

- Python 3.12; type hints; Google-style docstrings; pytest fixtures.
- Use Jujutsu (`jj`), not git, for status/diff/commit/bookmark/push.
- Prefix every shell command with `rtk`.
- Run plan-checkpoint and implementation commands from
  `/Users/ballen/Projects/ballen-config` unless a workspace is created.
- Design authority:
  `docs/superpowers/specs/2026-07-28-plato-reusable-skills-design.md`
  at change `opvyzqzn` / commit `52d2788e`.
- Do not invent MCP config, commit credentials, or migrate native auth/state.
- Do not build successor-free retirement, adoption, per-target results, or a
  reusable executable-action hierarchy (see design
  [Deferred Generic Retirement](../specs/2026-07-28-plato-reusable-skills-design.md#deferred-generic-retirement)).
- Keep `pyproject.toml` / `uv.lock` unchanged unless a stdlib-only approach
  proves impossible; prefer `fcntl.flock`.
- Stop and return to design if ownership proof, lock scope, or crash-window
  classification must change.

## Scope of This Plan

This plan covers design delivery slices **1–3** (engine chain):

1. Coarse mutation lock
2. Bounded rename protocol (no content change)
3. `jujutsu-workflow` → `using-jujutsu` caller

**Parallel plan:** slices 4–8 live in
[`2026-07-29-plato-reusable-skills-content.md`](2026-07-29-plato-reusable-skills-content.md).
That content work does not depend on this engine chain except that
`using-jujutsu`’s merge waits on Task 8 here; the other six skills may land in
any order relative to this plan.

---

## File Map

Create:

```text
tests/test_mutation_lock.py
tests/assistants/test_skill_renames.py
```

Modify:

```text
src/ballen_config/state.py
src/ballen_config/configure.py          # apply lock; run_configure + skill_renames;
                                        # ConfigurationContribution.skill_renames
src/ballen_config/assistants/models.py
src/ballen_config/assistants/skills.py
src/ballen_config/assistants/checks.py
src/ballen_config/assistants/__init__.py
src/ballen_config/cli.py
assistants/shared/skills/catalog.yaml
assistants/shared/skills/jujutsu-workflow/   → using-jujutsu/ (rename + frontmatter)
tests/test_state.py
tests/test_configure.py
tests/assistants/test_models.py
tests/assistants/test_skills.py
```

Deliberately leave unchanged:

```text
pyproject.toml
uv.lock
assistants/shared/standards/
Plato repository
```

## Execution Model

- Execute inline or subagent-driven; keep Tasks 1–3, 4–7, and 8 as three review
  gates matching design slices 1–3.
- Use TDD inside each task: failing test → implement → pass → commit.
- Run focused tests per task. Full suite + policy + pre-commit at the end of
  Tasks 3, 7, and 8.
- Create bookmark `implement-reusable-skills-engine` before Task 1.

---

## Preflight

- [ ] **Step 0.1: Confirm clean design checkpoint**

```text
rtk jj --no-pager status
rtk jj --no-pager log -r '@|@-' --no-graph -T 'change_id.short() ++ " " ++ commit_id.short() ++ " " ++ description.first_line() ++ "\n"'
rtk ./bootstrap plan --profile default
```

Expected: working copy is the design revision
`docs: close preflight and crash-window gaps in the rename protocol` (or its
successor description if amended only with this plan), and bootstrap plan exits 0.

- [ ] **Step 0.2: Create implementation bookmark**

```text
rtk jj bookmark create implement-reusable-skills-engine -r @
rtk jj new -m "wip: reusable skills engine"
```

---

## Slice 1 — Coarse Mutation Lock

### Task 1: Reentrant mutation lock on `StateStore`

**Files:**
- Modify: `src/ballen_config/state.py`
- Test: `tests/test_mutation_lock.py`, `tests/test_state.py`

**Interfaces:**
- Produces:
  - `StateStore.mutation(*, blocking: bool = True) -> AbstractContextManager[None]`
  - Lock file path: `self.paths.state_root / ".mutation.lock"`
  - Contention: raise `StateMutationContentionError` (new exception in
    `state.py`) when non-blocking acquire fails
  - Reentrancy: same-thread nested `mutation()` must succeed (depth counter)
  - `compare_and_remove` is **Task 5**, not this task

- [ ] **Step 1: Write failing lock tests**

Create `tests/test_mutation_lock.py`:

```python
"""Tests for StateStore coarse mutation locking."""

from __future__ import annotations

import os
from multiprocessing import Process, Queue
from pathlib import Path

import pytest

from ballen_config.runtime import RuntimePaths
from ballen_config.state import (
    BootstrapState,
    ManagedRecord,
    StateMutationContentionError,
    StateStore,
)


def _paths(repo_root: Path, home: Path) -> RuntimePaths:
    return RuntimePaths.from_roots(repo_root=repo_root, home=home)


def test_mutation_context_creates_private_lock_file(
    repo_root: Path, fake_home: Path
) -> None:
    store = StateStore(_paths(repo_root, fake_home))
    with store.mutation():
        lock = store.paths.state_root / ".mutation.lock"
        assert lock.is_file()
        assert lock.stat().st_mode & 0o777 == 0o600


def test_mutation_is_reentrant_on_same_store(repo_root: Path, fake_home: Path) -> None:
    store = StateStore(_paths(repo_root, fake_home))
    with store.mutation():
        with store.mutation():
            store.write(BootstrapState())
    assert store.load() == BootstrapState()


def test_record_managed_holds_lock_for_load_merge_write(
    repo_root: Path, fake_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = StateStore(_paths(repo_root, fake_home))
    held: list[bool] = []

    original_write = store.write

    def wrapped_write(state: BootstrapState) -> None:
        held.append(store._lock_depth > 0)
        original_write(state)

    monkeypatch.setattr(store, "write", wrapped_write)
    store.record_managed(
        ManagedRecord(
            resource_id="shared-skill-demo-cursor",
            source_digest="a" * 64,
            destination_digest="b" * 64,
            destination=".cursor/skills/demo",
        )
    )
    assert held == [True]


def _hold_lock(home: str, repo: str, ready: Queue, release: Queue) -> None:
    store = StateStore(RuntimePaths.from_roots(repo_root=Path(repo), home=Path(home)))
    with store.mutation():
        ready.put("ready")
        release.get()


def test_contention_raises_and_mutates_nothing(
    repo_root: Path, fake_home: Path
) -> None:
    store = StateStore(_paths(repo_root, fake_home))
    ready: Queue = Queue()
    release: Queue = Queue()
    holder = Process(
        target=_hold_lock,
        args=(str(fake_home), str(repo_root), ready, release),
    )
    holder.start()
    assert ready.get(timeout=5) == "ready"
    with pytest.raises(StateMutationContentionError):
        with store.mutation(blocking=False):
            store.write(BootstrapState())
    release.put("done")
    holder.join(timeout=5)
    assert not (fake_home / ".local/state/ballen-config/state.json").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

```text
rtk uv run --frozen pytest tests/test_mutation_lock.py -q
```

Expected: FAIL — `StateMutationContentionError` / `mutation` missing.

- [ ] **Step 3: Implement lock**

In `src/ballen_config/state.py`, add imports `errno`, `fcntl`, `threading`,
`contextmanager`, and `Iterator`. Then replace `StateStore` with:

```python
class StateMutationContentionError(RuntimeError):
    """Raised when the coarse mutation lock cannot be acquired."""


class StateStore:
    """Atomically persist private bootstrap state."""

    def __init__(self, paths: RuntimePaths) -> None:
        self.paths = paths
        self.path = paths.state_root / "state.json"
        self._lock_path = paths.state_root / ".mutation.lock"
        self._lock_fd: int | None = None
        self._lock_depth = 0
        self._lock_owner: int | None = None
        self._thread_guard = threading.Lock()

    @contextmanager
    def mutation(self, *, blocking: bool = True) -> Iterator[None]:
        """Acquire the exclusive advisory mutation lock.

        Reentrant for the owning thread. Non-blocking acquire raises
        ``StateMutationContentionError`` instead of waiting.
        """
        self._acquire(blocking=blocking)
        try:
            yield
        finally:
            self._release()

    def _acquire(self, *, blocking: bool) -> None:
        ident = threading.get_ident()
        with self._thread_guard:
            if self._lock_depth > 0:
                if self._lock_owner != ident:
                    raise StateMutationContentionError(
                        "mutation lock held by another thread"
                    )
                self._lock_depth += 1
                return
            self._validate_paths()
            self.paths.state_root.mkdir(parents=True, mode=0o700, exist_ok=True)
            self.paths.state_root.chmod(0o700)
            fd = os.open(
                self._lock_path,
                os.O_CREAT | os.O_RDWR,
                0o600,
            )
            os.fchmod(fd, 0o600)
            flags = fcntl.LOCK_EX if blocking else fcntl.LOCK_EX | fcntl.LOCK_NB
            try:
                fcntl.flock(fd, flags)
            except OSError as error:
                os.close(fd)
                if error.errno in {errno.EACCES, errno.EAGAIN}:
                    raise StateMutationContentionError(
                        "mutation lock contention"
                    ) from error
                raise
            self._lock_fd = fd
            self._lock_owner = ident
            self._lock_depth = 1

    def _release(self) -> None:
        with self._thread_guard:
            if self._lock_depth <= 0 or self._lock_fd is None:
                raise RuntimeError("mutation lock release without acquire")
            self._lock_depth -= 1
            if self._lock_depth > 0:
                return
            fd = self._lock_fd
            self._lock_fd = None
            self._lock_owner = None
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)

    def record_install(self, record: InstallRecord) -> None:
        with self.mutation():
            state = self.load()
            installs = {**state.installs, record.resource_id: record}
            self.write(state.model_copy(update={"installs": installs}))

    def record_managed(self, record: ManagedRecord) -> None:
        with self.mutation():
            state = self.load()
            managed = {**state.managed, record.resource_id: record}
            self.write(state.model_copy(update={"managed": managed}))
```

Keep existing `load`, `write`, and `_validate_paths` unchanged.
`write()` and `load()` stay callable without the lock for read-only doctor/plan;
every public mutator must enter `mutation()`.

- [ ] **Step 4: Run lock tests**

```text
rtk uv run --frozen pytest tests/test_mutation_lock.py tests/test_state.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```text
rtk jj commit -m "$(cat <<'EOF'
feat: serialize StateStore mutators behind a coarse lock

record_managed and record_install used independent load-modify-write
cycles. An exclusive reentrant fcntl lock in state_root makes those
cycles safe against concurrent configure runs.
EOF
)"
```

---

### Task 2: Hold the lock across `ConfigurationEngine.apply`

**Files:**
- Modify: `src/ballen_config/configure.py`
- Test: `tests/test_configure.py`

**Interfaces:**
- Consumes: `StateStore.mutation()`
- Produces: `ConfigurationEngine.apply` holds the lock from `_validate` through
  `_record` (backup + publish included). Nested `record_managed` reenters.

- [ ] **Step 1: Write failing apply-span test**

Add to `tests/test_configure.py` using the existing `config_paths` fixture and
`engine()` helper:

```python
def test_apply_holds_mutation_lock_across_validate_backup_publish_record(
    config_paths: RuntimePaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    active = engine(config_paths, timestamp="20260729T000000Z")
    source = config_paths.repo_root / "tree-src"
    source.mkdir()
    (source / "file.txt").write_text("hello\n", encoding="utf-8")
    spec = ManagedTreeSpec(
        id="demo-tree",
        source=source,
        destination=Path(".demo/tree"),
        component="demo",
    )
    depths: list[int] = []
    original_validate = active._validate
    original_backup = active._backup
    original_record = active._record

    def wrap_validate(spec_arg: ManagedSpec) -> None:
        depths.append(active.state_store._lock_depth)
        original_validate(spec_arg)

    def wrap_backup(destination: Path) -> Path | None:
        depths.append(active.state_store._lock_depth)
        return original_backup(destination)

    def wrap_record(spec_arg: ManagedSpec, destination: Path) -> None:
        depths.append(active.state_store._lock_depth)
        original_record(spec_arg, destination)

    monkeypatch.setattr(active, "_validate", wrap_validate)
    monkeypatch.setattr(active, "_backup", wrap_backup)
    monkeypatch.setattr(active, "_record", wrap_record)
    active.apply(spec)
    assert depths and all(depth >= 1 for depth in depths)
```

Import `ManagedSpec` if the file does not already expose it through the
existing imports (it is the union already used by `configure.py`).

- [ ] **Step 2: Run test to verify it fails**

```text
rtk uv run --frozen pytest tests/test_configure.py::test_apply_holds_mutation_lock_across_validate_backup_publish_record -q
```

Expected: FAIL — depth is 0 during validate.

- [ ] **Step 3: Wrap `apply`**

```python
def apply(self, spec: ManagedSpec) -> ConfigAction:
    """Revalidate and apply a single spec after a safe comparison."""
    with self.state_store.mutation():
        self._validate(spec)
        if isinstance(spec, ManagedFileSpec):
            destination = self._destination(spec)
            desired = self._file_bytes(spec, destination)
            return self._apply_file(spec, self._action(spec, desired), desired)
        return self._apply_tree(spec, self._action(spec))
```

No other behavior change.

- [ ] **Step 4: Run configure + lock tests**

```text
rtk uv run --frozen pytest tests/test_configure.py tests/test_mutation_lock.py tests/test_state.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```text
rtk jj commit -m "$(cat <<'EOF'
feat: hold mutation lock across configure apply

Tree publish and receipt write are separate files. Holding the coarse
lock from apply-time digest validation through backup, publish, and
record_managed prevents concurrent runs from splitting that pair.
EOF
)"
```

- [ ] **Step 6: Slice 1 gate**

```text
rtk uv run --frozen pytest -q
rtk uv run --frozen --no-sync python -m ballen_config.policy
```

Expected: full suite green; policy OK. No catalog or skill content changes.

---

## Slice 2 — Bounded Rename Protocol

### Task 3: `renames` catalog model

**Files:**
- Modify: `src/ballen_config/assistants/models.py`
- Test: `tests/assistants/test_models.py`

**Interfaces:**
- Produces:

```python
class SkillRenameSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    from_name: str = Field(alias="from", pattern=r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
    to_name: str = Field(alias="to", pattern=r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")


class SkillCatalog(BaseModel):
    skills: tuple[SkillSpec, ...]
    renames: tuple[SkillRenameSpec, ...] = ()
```

Validation (after existing graph validator, or combined):
- each `from_name` absent from `skills`
- each `to_name` present in `skills`
- unique `from_name` values
- both fields required (no successor-free retirement)

YAML uses `from` / `to` keys via aliases. Set
`model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)`
on `SkillRenameSpec` so tests may construct with `from_name=` / `to_name=`.

- [ ] **Step 1: Write failing model tests**

Add to `tests/assistants/test_models.py`:

```python
def test_skill_rename_requires_successor_absent_from_and_present_to() -> None:
    catalog = SkillCatalog.model_validate(
        {
            "skills": [
                {
                    "name": "using-jujutsu",
                    "source": "assistants/shared/skills/using-jujutsu",
                    "targets": ["cursor"],
                    "profiles": ["default"],
                    "dependencies": [],
                    "provenance": "renamed",
                    "portability_status": "reviewed-generic",
                }
            ],
            "renames": [{"from": "jujutsu-workflow", "to": "using-jujutsu"}],
        }
    )
    assert catalog.renames[0].from_name == "jujutsu-workflow"
    assert catalog.renames[0].to_name == "using-jujutsu"


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        (
            {
                "skills": [
                    {
                        "name": "jujutsu-workflow",
                        "source": "assistants/shared/skills/jujutsu-workflow",
                        "targets": ["cursor"],
                        "profiles": ["default"],
                        "dependencies": [],
                        "provenance": "x",
                        "portability_status": "reviewed-generic",
                    }
                ],
                "renames": [{"from": "jujutsu-workflow", "to": "using-jujutsu"}],
            },
            "rename from still present in skills",
        ),
        (
            {
                "skills": [
                    {
                        "name": "using-jujutsu",
                        "source": "assistants/shared/skills/using-jujutsu",
                        "targets": ["cursor"],
                        "profiles": ["default"],
                        "dependencies": [],
                        "provenance": "x",
                        "portability_status": "reviewed-generic",
                    }
                ],
                "renames": [
                    {"from": "old-a", "to": "using-jujutsu"},
                    {"from": "old-a", "to": "using-jujutsu"},
                ],
            },
            "duplicate rename from",
        ),
        (
            {
                "skills": [
                    {
                        "name": "using-jujutsu",
                        "source": "assistants/shared/skills/using-jujutsu",
                        "targets": ["cursor"],
                        "profiles": ["default"],
                        "dependencies": [],
                        "provenance": "x",
                        "portability_status": "reviewed-generic",
                    }
                ],
                "renames": [{"from": "jujutsu-workflow", "to": "missing-skill"}],
            },
            "rename to absent from skills",
        ),
    ],
)
def test_skill_rename_validation_rejects_invalid_declarations(
    payload: dict[str, object], match: str
) -> None:
    with pytest.raises(ValidationError, match=match):
        SkillCatalog.model_validate(payload)
```

Emit those exact phrases from the catalog validator (`ValueError` wrapped by
Pydantic). A payload missing `to` is rejected by the model field itself; add a
fourth case with `pytest.raises(ValidationError)` and no custom match if useful.

- [ ] **Step 2: Run to verify fail**

```text
rtk uv run --frozen pytest tests/assistants/test_models.py -k skill_rename -q
```

- [ ] **Step 3: Implement model + validator**

Keep existing dependency-graph validation. Add rename validation in the same
`validate_graph` or a second `@model_validator(mode="after")`.

- [ ] **Step 4: Pass + commit**

```text
rtk uv run --frozen pytest tests/assistants/test_models.py -k skill_rename -q
rtk jj commit -m "$(cat <<'EOF'
feat: add skill catalog renames declarations

Require from/to pairs so rename intent cannot be inferred from profile
selection, and so successor-free retirement stays unrepresentable.
EOF
)"
```

---

### Task 4: Classification

**Files:**
- Modify: `src/ballen_config/assistants/skills.py`
- Test: `tests/assistants/test_skill_renames.py`

**Interfaces:**
- Produces:

```python
class LegacyRenameState(StrEnum):
    CLEAN = "clean"
    EXACT_LIVE = "exact_live"
    EXACT_STALE = "exact_stale"
    BLOCKED_AMBIGUOUS_RECEIPT = "blocked_ambiguous_receipt"
    BLOCKED_UNMANAGED_OR_AMBIGUOUS = "blocked_unmanaged_or_ambiguous"
    BLOCKED_DRIFT = "blocked_drift"
    BLOCKED_UNMANAGED_SUCCESSOR = "blocked_unmanaged_successor"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class RenameTargetClassification:
    target: AgentName
    legacy_state: LegacyRenameState
    legacy_record: ManagedRecord | None
    legacy_relative: Path
    successor_relative: Path
```

```python
def classify_rename_target(
    *,
    from_name: str,
    to_name: str,
    target: AgentName,
    home: Path,
    state: BootstrapState,
    successor_digest: str,
    enabled: bool,
) -> RenameTargetClassification:
    """Classify one enabled or skipped target for a declared rename."""
```

Exact receipt means: resource id
`f"shared-skill-{from_name}-{target.value}"`, destination equals
`(_SKILL_ROOTS[target] / from_name).as_posix()`, and live tree digest equals
`record.destination_digest` when the tree is present.

`_matching_record` currently raises on mismatch/duplicate. Classification must
**catch** that condition and return `BLOCKED_AMBIGUOUS_RECEIPT` / unmanaged
rather than aborting the planner with `ValueError`.

Successor feasibility: if successor destination exists, is a directory, has
digest `== successor_digest`, and has **no** exact managed receipt for
`shared-skill-{to_name}-{target}`, classify
`BLOCKED_UNMANAGED_SUCCESSOR` (crash-window / hand-authored case).

- [ ] **Step 1: Write parameterized classification tests**

Cover every design table row for Cursor, Claude Code, and Codex (parametrize
`target`). Include:
- clean / exact live / exact stale → accepted
- absent + mismatched receipt → blocked ambiguous
- present + no receipt → blocked unmanaged
- present + exact receipt + digest mismatch → blocked drift
- skipped target → `SKIPPED`, never inspects filesystem
- unreceipted successor at exact digest → `BLOCKED_UNMANAGED_SUCCESSOR`

Use `temporary_home`, write tiny skill trees, and seed `StateStore` with
`ManagedRecord` values.

- [ ] **Step 2: Fail, implement `classify_rename_target`, pass**

- [ ] **Step 3: Commit**

```text
rtk jj commit -m "$(cat <<'EOF'
feat: classify declared skill rename targets

Map legacy tree and receipt pairs onto the three accepted rename states
and the blocking states, including unreceipted successor trees.
EOF
)"
```

---

### Task 5: Plan + apply `SkillRenameAction`

**Files:**
- Modify: `src/ballen_config/assistants/skills.py`
- Modify: `src/ballen_config/configure.py` (`run_configure` signature or sibling)
- Modify: `src/ballen_config/cli.py`
- Modify: `src/ballen_config/assistants/__init__.py` (exports)
- Test: `tests/assistants/test_skill_renames.py`

**Interfaces:**
- Produces:

```python
class SkillRenameBlockedError(ValueError):
    """Raised when a declared rename cannot proceed on an enabled target."""

    def __init__(
        self,
        from_name: str,
        to_name: str,
        target: AgentName,
        state: LegacyRenameState,
    ) -> None:
        self.from_name = from_name
        self.to_name = to_name
        self.target = target
        self.state = state
        super().__init__(
            f"skill rename blocked: {from_name} -> {to_name} on {target.value} ({state})"
        )

    def outcome(self) -> str:
        """Return a redacted CLI outcome without absolute paths or digests."""
        return (
            f"shared skill rename blocked: {self.from_name} -> {self.to_name} "
            f"on {self.target.value}"
        )


@dataclass(frozen=True)
class SkillRenameAction:
    from_name: str
    to_name: str
    target: AgentName
    legacy_state: LegacyRenameState  # CLEAN | EXACT_LIVE | EXACT_STALE only
    legacy_record: ManagedRecord | None
    legacy_relative: Path
    successor_resource_id: str
    successor_relative: Path


def plan_skill_renames(
    *,
    catalog: SkillCatalog,
    setup: ResolvedSetup,
    paths: RuntimePaths,
    state: BootstrapState,
) -> tuple[SkillRenameAction, ...]:
    """Plan renames from the complete catalog before selection filtering.

    Raises:
        SkillRenameBlockedError: If any enabled target is not an accepted state
            or successor install cannot produce a receipt.
    """


def apply_skill_rename_cleanups(
    engine: ConfigurationEngine,
    actions: tuple[SkillRenameAction, ...],
) -> None:
    """Revalidate and remove exact legacy state. Caller holds mutation lock."""
```

**Planning rules:**
1. Candidates come from `catalog.renames` only; never from “absent in resolved
   selection.”
2. For each rename, classify every concrete target on the `to` skill that is
   enabled; skipped agents emit nothing and are not inspected.
3. If any enabled target is blocked → raise `SkillRenameBlockedError`.
4. Emit one `SkillRenameAction` per enabled accepted target, freezing the
   exact `legacy_record` when present.
5. Extend `ConfigurationContribution` with
   `skill_renames: tuple[SkillRenameAction, ...] = ()` and concatenate in
   `merge_configuration_contributions`.
6. `skills.configuration()` calls `plan_skill_renames` before emitting copy
   specs, so a block fails the plan stage like `SkillCollisionError`.
7. Plan display: for each action, contribute redacted configure `PlanAction`s
   via `ConfigurationPlanContributor` overrides or an adjacent contributor:
   - cleanup actions use `action="skill-rename-cleanup"`
   - `path` is the legacy relative POSIX path only
   - no digests or absolute homes

**Apply wiring (locked decision):** successors install through ordinary
`ManagedTreeSpec`s already emitted for `to_name`. `run_configure` holds one
outer mutation lock for the whole stage, applies every spec (reentrant per
`apply`), then runs cleanups before release:

```python
def run_configure(
    engine: ConfigurationEngine,
    specs: Sequence[ManagedSpec],
    *,
    skill_renames: Sequence[SkillRenameAction] = (),
) -> ConfigureStageReport:
    """Plan, apply specs, then apply rename cleanups under one mutation lock."""
    with engine.state_store.mutation():
        planned = engine.plan(specs)
        ordered = tuple(sorted(specs, key=lambda spec: spec.id))
        applied = tuple(
            engine.apply(spec) for spec, _ in zip(ordered, planned, strict=True)
        )
        apply_skill_rename_cleanups(engine, tuple(skill_renames))
    return ConfigureStageReport(
        actions=applied,
        changed_count=sum(action.outcome != "unchanged" for action in applied),
    )
```

**Cleanup rules** (`apply_skill_rename_cleanups`, lock already held):
1. Reclassify each action’s target against live state; on any change from the
   frozen accepted state → raise `SkillRenameBlockedError` (fail closed).
2. Require successor managed receipt
   `shared-skill-{to_name}-{target}` to exist after the apply loop.
3. `EXACT_LIVE`: `engine._backup(legacy_destination)`, then
   `compare_and_remove(expected=action.legacy_record)`.
4. `EXACT_STALE`: `compare_and_remove` only.
5. `CLEAN`: no cleanup.
6. Backup/remove failure: restore legacy from backup when the tree was moved;
   keep successor; re-raise.

**`compare_and_remove` on `StateStore`:**

```python
def compare_and_remove(self, expected: ManagedRecord) -> bool:
    """Delete managed record only if stored value exactly equals expected.

    Must be called while ``mutation()`` is held. Returns True if removed.
    Returns False and writes nothing on mismatch.
    """
    state = self.load()
    current = state.managed.get(expected.resource_id)
    if current != expected:
        return False
    managed = {
        key: value
        for key, value in state.managed.items()
        if key != expected.resource_id
    }
    self.write(state.model_copy(update={"managed": managed}))
    return True
```

**CLI wiring:**
- Catch `SkillRenameBlockedError` beside `SkillCollisionError` in `cli.py`.
- Pass `configuration.skill_renames` into `run_configure` from
  `configure_stage`.

Planning must have rejected unreceipted-successor cases, so successor receipt
verification after apply is the protocol’s step-5 proof. If a successor was
already managed-and-unchanged, its receipt already exists and cleanup may
proceed.

- [ ] **Step 1: Write plan/apply tests**

Required cases (parametrize targets where useful):

| Test | Contract |
|---|---|
| `test_plan_clean_target_installs_only` | Accepted CLEAN → action with `legacy_record is None` |
| `test_plan_exact_live_sequences_install_then_cleanup` | EXACT_LIVE carries frozen record |
| `test_plan_exact_stale_cleanup_without_backup` | EXACT_STALE |
| `test_plan_blocks_when_any_target_infeasible` | One blocked target → error, no actions |
| `test_candidate_ignores_profile_exclusion` | `work`-only skill absent from default selection is not renamed without declaration |
| `test_undeclared_orphan_record_is_not_cleaned` | Name absent from skills and renames → untouched |
| `test_apply_removes_exact_live_legacy` | After configure, legacy tree backed up, receipt gone, successor receipt present |
| `test_apply_idempotent_second_run` | Second run: zero cleanup, zero new backups |
| `test_toc_tou_legacy_change_fails_closed` | Mutate legacy between plan freeze and apply → no remove |
| `test_compare_and_remove_mismatch_is_noop` | Stored record differs → False, state unchanged |
| `test_crash_between_publish_and_receipt_blocks` | Simulate published successor without receipt → next plan raises blocked unmanaged successor; doctor later |

For the crash simulation: write successor tree bytes matching source digest,
omit managed receipt, seed legacy exact receipt, assert plan blocks.

- [ ] **Step 2: Implement plan/apply + `compare_and_remove` + CLI catch**

- [ ] **Step 3: Pass focused tests**

```text
rtk uv run --frozen pytest tests/assistants/test_skill_renames.py tests/test_mutation_lock.py -q
```

- [ ] **Step 4: Commit**

```text
rtk jj commit -m "$(cat <<'EOF'
feat: add bounded skill rename plan and apply protocol

Plan from declared renames only, require accepted legacy states and
successor feasibility before mutation, then install successors and
compare-and-remove exact legacy receipts under the coarse lock.
EOF
)"
```

---

### Task 6: Doctor reporting for rename states

**Files:**
- Modify: `src/ballen_config/assistants/checks.py`
- Test: `tests/assistants/test_skill_renames.py` or
  `tests/assistants/test_checks.py` if that module exists

**Interfaces:**
- Extend `_skill_findings` (or adjacent helper) to report design doctor rows
  using existing `FindingStatus` values only:

| Situation | State | Severity |
|---|---|---|
| Unmanaged/ambiguous/duplicated legacy; rename blocked | `manual` | warning |
| Unreceipted successor at destination; rename blocked | `manual` | warning |
| Managed legacy digest mismatch | `drift` | error |
| Successor installed while legacy tree/receipt remains | `drift` | error |
| Harness skipped | `skipped` | info |
| Clean | no finding | n/a |

Finding ids: stable, redacted, no absolute paths — e.g.
`skill-rename.jujutsu-workflow.cursor`.

Never recommend deleting a `renames` declaration.

- [ ] **Step 1: Write doctor tests for blocked and interrupted states**
- [ ] **Step 2: Implement findings**
- [ ] **Step 3: Pass + commit**

```text
rtk jj commit -m "$(cat <<'EOF'
feat: report skill rename blocks and interrupted cleanup in doctor

Map rename classifications onto existing doctor states so duplicate
authority and unreceipted successors cannot stay silent.
EOF
)"
```

---

### Task 7: Slice 2 integration gate (fixture rename only)

**Files:**
- Test fixtures in `tests/assistants/test_skill_renames.py`
- No production catalog content change yet

- [ ] **Step 1: End-to-end fixture test**

Using a temp repo catalog with `old-skill` → `new-skill` trees (not the real
jujutsu skill): plan → configure → doctor clean → configure again idempotent.

- [ ] **Step 2: Full gate**

```text
rtk uv run --frozen pytest -q
rtk uv run --frozen --no-sync python -m ballen_config.policy
rtk ./bootstrap plan --profile default
```

Expected: green; plan shows no real rename yet (catalog unchanged).

- [ ] **Step 3: Commit fixture helpers if any production-adjacent test utilities
  were added; if the gate used only `test_skill_renames.py` fixtures already
  committed in Tasks 4–6, skip an empty commit and continue to Task 8**

---

## Slice 3 — Rename `jujutsu-workflow` → `using-jujutsu`

### Task 8: Content rename + catalog declaration

**Files:**
- Rename dir: `assistants/shared/skills/jujutsu-workflow/` →
  `assistants/shared/skills/using-jujutsu/`
- Modify: `assistants/shared/skills/using-jujutsu/SKILL.md` frontmatter
  `name: using-jujutsu`, and change the H1 from `Jujutsu Workflow` to
  `Using Jujutsu` so the entrypoint title matches the skill name
- Modify: `assistants/shared/skills/catalog.yaml`
- Modify: `tests/assistants/test_skills.py` synchronization test
- Modify: any inventory/docs references to the old skill path/name

**Catalog end state:**

```yaml
skills:
  - name: using-jujutsu
    source: assistants/shared/skills/using-jujutsu
    targets: [cursor, claude-code, codex]
    profiles: [default]
    dependencies: []
    provenance: >-
      Renamed from the promoted jujutsu-workflow skill added in commit
      2d057f673971232e2327924c1a5f846ff9ace48e, itself promoted from
      plato/skills/jujutsu-workflow at commit
      f3b91eead0eff7d0c9cada3bc8e689f7610fba55; commit history records both.
    portability_status: reviewed-generic

renames:
  - from: jujutsu-workflow
    to: using-jujutsu
```

Pinned digests in tests **must be recomputed** after frontmatter rename:

```text
rtk uv run --frozen python - <<'PY'
from pathlib import Path
from ballen_config.assistants.skills import hash_skill_tree
from hashlib import sha256
root = Path("assistants/shared/skills/using-jujutsu")
print("tree", hash_skill_tree(root))
print("skill", sha256((root / "SKILL.md").read_bytes()).hexdigest())
print("ref", sha256((root / "reference.md").read_bytes()).hexdigest())
PY
```

Keep the **legacy** digest
`e7ca3f2e0a0f3f79dff90cc8fd718d74fecf18234d9b57dfeb0245480af1a8ec` in a rename
test as the expected digest of an already-installed `jujutsu-workflow` tree.
Build that fixture by writing the pre-rename tree bytes (read them from
`jj file show opvyzqzn:assistants/shared/skills/jujutsu-workflow/SKILL.md` and
`reference.md` before the move, or from the parent commit that still has the
directory). The new `using-jujutsu` tree digest will differ because `name:` and
the H1 changed.

- [ ] **Step 1: Update synchronization test to expect `using-jujutsu` + `renames`**
- [ ] **Step 2: Run test — fail**
- [ ] **Step 3: Move tree, edit frontmatter, update catalog, paste new digests**
- [ ] **Step 4: Add integration test**
  `test_jujutsu_workflow_rename_converges_managed_install` that:
  1. Seeds managed `jujutsu-workflow` install at legacy digest for all three
     targets
  2. Runs configure
  3. Asserts successor receipts for `using-jujutsu`
  4. Asserts legacy receipts gone and legacy trees absent (backed up)
  5. Runs configure again — no further backup/cleanup
- [ ] **Step 5: Full gate**

```text
rtk uv run --frozen pytest -q
rtk uv run --frozen --no-sync python -m ballen_config.policy
rtk ./bootstrap plan --profile default
rtk ./bootstrap doctor --profile default
```

- [ ] **Step 6: Commit**

```text
rtk jj commit -m "$(cat <<'EOF'
feat: rename jujutsu-workflow skill to using-jujutsu

Declare the catalog rename and converge managed installs through the
bounded rename protocol so legacy trees and receipts do not remain as a
second workflow authority.
EOF
)"
```

---

## Final Branch Checkpoint

- [ ] **Step F.1: Full verification**

```text
rtk uv run --frozen pytest -q
rtk uv run --frozen --no-sync python -m ballen_config.policy
rtk uv run --frozen pre-commit run --all-files
rtk ./bootstrap plan --profile default
rtk ./bootstrap doctor --profile default
```

- [ ] **Step F.2: Push bookmark when remote available**

```text
rtk jj bookmark set implement-reusable-skills-engine -r @
rtk jj git push --bookmark implement-reusable-skills-engine
```

---

## Spec Coverage Checklist

| Design requirement | Task |
|---|---|
| Coarse lock across validate/backup/publish/record | 1–2 |
| Lock covers every state mutator | 1 |
| Contention fails closed | 1 |
| `renames` with required `to` | 3 |
| Candidacy from full catalog, not selection | 5 |
| Three accepted legacy states | 4–5 |
| Blocking classifications + unreceipted successor | 4–5 |
| All-or-nothing blocking | 5 |
| compare-and-remove exact receipt | 5 |
| Install before cleanup; revalidate under lock | 5 |
| Resumable exact stale; crash publish window blocks | 5 |
| Doctor mapping | 6 |
| `jujutsu-workflow` → `using-jujutsu` | 8 |
| No adoption / pure retirement / per-target results | Non-goals; absent by design |

---

## Parallel Content Plan

Slices 4–8 are specified in
[`2026-07-29-plato-reusable-skills-content.md`](2026-07-29-plato-reusable-skills-content.md).
Coordinate only on `catalog.yaml` merges; do not perform the `jujutsu-workflow`
rename from that plan.
