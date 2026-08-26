# Employer Profiles and Wave Removal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the mixed `work` profile into `fsp` and `wsh`, remove Wave from live desired state, make `glab` an include, and prune owned managed files that left the current configure plan.

**Architecture:** Keep the existing one-leaf `--profile` resolver. Replace `work` with two leaves that extend `default`. Retarget Python `"work"` special cases to `fsp` or `wsh`. After `run_configure` applies the current spec set, prune `StateStore` records whose ids are not in that set when destination ownership still holds. Do not rename `zprofile.work` or `settings.work.json`.

**Tech Stack:** Python 3.12, pydantic v2, pytest, `uv run --frozen`, Jujutsu (`rtk jj`).

**Approved design:**
[Employer profiles and Wave removal design](../specs/2026-08-26-employer-profiles-and-wave-removal-design.md)

## Global Constraints

- Python 3.12; type hints; Google-style docstrings; pytest.
- Do not add Warp, iTerm, or any dedicated terminal to desired state.
- Do not uninstall Wave.app; pruning may remove owned `~/.config/waveterm/settings.json`.
- Do not rename `dotfiles/shell/zprofile.work` or `assistants/cursor/settings.work.json`.
- Do not rewrite historical specs or plans under `docs/superpowers/` except this plan and the approved design.
- Do not add an `ensure-absent` manifest field, destination override rules, or an active-profile marker.
- Keep `using-gitlab` on `default`. Keep the tracked-tree `plato` import guard.
- Agent-run shell commands are prefixed with `rtk`.
- Daily current-job command is `./bootstrap --profile wsh`.

---

## Conventions

Run every command from the repository root:

```bash
rtk uv run --frozen pytest -q
```

Commit with `rtk jj`, matching the existing plans in this directory:

```bash
rtk jj describe -m 'feat: …'
rtk jj new
```

Synthetic assistant-catalog fixtures that use `profiles: [work]` as a dummy non-default tag and never resolve the real profile set may stay. Every `ResolutionRequest(profile="work")` against real manifests, and every production `"work" in profiles` check, must change.

---

## File structure

| File | Responsibility |
| --- | --- |
| `src/ballen_config/configure.py` | `ConfigAction.outcome` includes `"removed"`; `plan` lists prunes; `run_configure` applies specs then prunes. Do not prune inside per-spec `apply`. |
| `src/ballen_config/planning.py` | GitLab manual action only if `glab` is enabled; AWS only if `fsp` is in profiles. |
| `src/ballen_config/doctor.py` | Same gating for auth checks. |
| `src/ballen_config/assistants/cursor.py` | Bedrock overlay and Atlassian spec when `fsp` is selected. |
| `src/ballen_config/assistants/models.py` | Atlassian exception requires `profiles == ("fsp",)`. |
| `src/ballen_config/assistants/checks.py` | Approved MCP is allowed only on `fsp`. |
| `manifests/profiles/fsp.yaml`, `manifests/profiles/wsh.yaml` | New leaves. Delete `work.yaml`. |
| `manifests/packages.yaml` | `awscli`/`libmagic` → `fsp`; `glab` becomes an include. |
| `manifests/applications.yaml` | Remove `wave`. |
| `manifests/configuration.yaml` | `zprofile-work` → `profiles: [wsh]`; delete `wave-settings`. |
| `manifests/component-ids.txt` | Public interface. |
| `assistants/inventory.yaml` | Overlay and Atlassian `profiles: [fsp]`. |
| `terminal/wave/settings.json` | Delete. |
| `README.md`, `docs/manual-steps.md`, `tests/test_docs.py` | Live contracts. |

---

### Task 1: Prune owned managed files that left the plan

**Files:**
- Modify: `src/ballen_config/configure.py`
- Test: `tests/test_configure.py`

**Interfaces:**
- Consumes: `ManagedRecord`, `StateStore.compare_and_remove`, `ConfigurationEngine.apply`, `run_configure`
- Produces: `ConfigAction.outcome` literal `"removed"`; `ConfigurationEngine.plan` may append prune actions; `run_configure` applies current specs then prunes; `ConfigurationEngine.apply` of one spec does not prune siblings

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_configure.py` (distinct source files; `file_spec` always writes `repo/source`):

```python
def owned_spec(
    paths: RuntimePaths, spec_id: str, destination: str, payload: bytes
) -> ManagedFileSpec:
    """Build a copy spec with its own source path."""
    source = paths.repo_root / spec_id
    source.write_bytes(payload)
    return ManagedFileSpec(
        id=spec_id,
        source=source,
        destination=Path(destination),
        method=ApplyMethod.COPY,
        mode=0o600,
        component="shell",
    )


def test_run_configure_prunes_owned_file_that_left_the_plan(
    config_paths: RuntimePaths,
) -> None:
    """Owned extras disappear when their spec is no longer selected."""
    extra = owned_spec(config_paths, "extra", ".config/extra", b"extra\n")
    keep = owned_spec(config_paths, "keep", ".config/keep", b"keep\n")
    subject = engine(config_paths, timestamp="first")
    run_configure(subject, (extra, keep))
    extra_path = config_paths.home / extra.destination
    assert extra_path.is_file()
    planned = engine(config_paths).plan((keep,))
    assert extra_path.is_file()
    assert planned[-1] == ConfigAction(
        id="extra", destination=".config/extra", outcome="removed"
    )

    report = run_configure(engine(config_paths, timestamp="second"), (keep,))

    assert extra_path.exists() is False
    assert "extra" not in engine(config_paths).state_store.load().managed
    assert any(
        action.id == "extra" and action.outcome == "removed" for action in report.actions
    )


def test_prune_skips_when_destination_digest_no_longer_matches(
    config_paths: RuntimePaths,
) -> None:
    """Hand-edited leftovers stay, and ownership remains so a later apply can update."""
    spec = file_spec(config_paths)
    subject = engine(config_paths)
    run_configure(subject, (spec,))
    destination = config_paths.home / spec.destination
    destination.write_bytes(b"user edited\n")
    report = run_configure(engine(config_paths, timestamp="later"), ())
    assert destination.read_bytes() == b"user edited\n"
    assert "example" in engine(config_paths).state_store.load().managed
    assert all(action.id != "example" for action in report.actions)


def test_single_spec_apply_does_not_prune_siblings(
    config_paths: RuntimePaths,
) -> None:
    """Per-spec apply is not a configure stage and must not delete other owned files."""
    extra = owned_spec(config_paths, "extra", ".config/extra", b"extra\n")
    keep = owned_spec(config_paths, "keep", ".config/keep", b"keep\n")
    subject = engine(config_paths)
    run_configure(subject, (extra, keep))
    subject.apply(keep)
    assert (config_paths.home / extra.destination).is_file()
```

Import `run_configure` and `ConfigAction` from `ballen_config.configure` at the top of `tests/test_configure.py` (add them to the existing import block).

- [ ] **Step 2: Run tests to verify they fail**

Run: `rtk uv run --frozen pytest tests/test_configure.py::test_run_configure_prunes_owned_file_that_left_the_plan tests/test_configure.py::test_prune_skips_when_destination_digest_no_longer_matches tests/test_configure.py::test_single_spec_apply_does_not_prune_siblings -q`

Expected: FAIL (`outcome` rejects `"removed"`, `zip(..., strict=True)` length mismatch, or leftover files remain).

- [ ] **Step 3: Implement prune**

In `src/ballen_config/configure.py`:

1. Extend `ConfigAction.outcome`:

```python
outcome: Literal["created", "updated", "unchanged", "removed"]
```

2. Add helpers on `ConfigurationEngine` (keep them next to `plan`):

```python
def _live_prune_action(self, record: ManagedRecord) -> ConfigAction | None:
    """Return a removal action when ownership still holds, else None."""
    destination = assert_contained(
        self.paths.home / record.destination, self.paths.home
    )
    try:
        metadata = os.lstat(destination)
    except FileNotFoundError:
        return ConfigAction(
            id=record.resource_id,
            destination=record.destination,
            outcome="removed",
        )
    if stat.S_ISLNK(metadata.st_mode):
        return ConfigAction(
            id=record.resource_id,
            destination=record.destination,
            outcome="removed",
        )
    if stat.S_ISREG(metadata.st_mode):
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    elif stat.S_ISDIR(metadata.st_mode):
        digest = digest_tree(destination)
    else:
        raise ValueError(f"unsupported destination type: {destination}")
    if digest != record.destination_digest:
        return None
    return ConfigAction(
        id=record.resource_id,
        destination=record.destination,
        outcome="removed",
    )


def _stale_records(self, specs: Sequence[ManagedSpec]) -> tuple[ManagedRecord, ...]:
    """Return owned records whose resource ids are not in the current spec set."""
    current_ids = {spec.id for spec in specs}
    state = self.state_store.load()
    return tuple(
        record
        for resource_id, record in sorted(state.managed.items())
        if resource_id not in current_ids
    )


def prune_stale(self, specs: Sequence[ManagedSpec]) -> tuple[ConfigAction, ...]:
    """Backup and remove owned destinations that left the current spec set.

    The calling thread must already own the mutation lock. Symlink destinations
    are treated as owned when the link still exists, matching ``_record`` which
    stores ``source_digest`` as ``destination_digest`` for symlinks. Digest
    mismatch leaves the file and the record. ``compare_and_remove`` failure
    restores the backup and raises.

    Args:
        specs: Specs that remain in the current configure plan.

    Returns:
        Removal actions actually applied, in resource-id order.
    """
    applied: list[ConfigAction] = []
    for record in self._stale_records(specs):
        action = self._live_prune_action(record)
        if action is None:
            continue
        destination = assert_contained(
            self.paths.home / record.destination, self.paths.home
        )
        backup: Path | None = None
        try:
            if os.path.lexists(destination):
                backup = self.backup_managed_destination(destination)
                if os.path.lexists(destination):
                    if destination.is_dir() and not destination.is_symlink():
                        shutil.rmtree(destination)
                    else:
                        destination.unlink()
            if not self.state_store.compare_and_remove(record):
                raise ValueError("stale managed record changed")
        except Exception:
            self.restore_managed_destination(backup, destination)
            raise
        applied.append(action)
    return tuple(applied)
```

3. Change `plan` to append prune actions after current spec actions, without mutating:

```python
def plan(self, specs: Sequence[ManagedSpec]) -> tuple[ConfigAction, ...]:
    """Validate every spec, then return deterministic read-only actions."""
    ordered = tuple(sorted(specs, key=lambda spec: spec.id))
    for spec in ordered:
        self._validate(spec)
    actions = tuple(self._action(spec) for spec in ordered)
    prunes = tuple(
        action
        for record in self._stale_records(specs)
        if (action := self._live_prune_action(record)) is not None
    )
    return actions + prunes
```

4. Change `run_configure` so it does not `zip` plan rows to specs. After applying every current spec, call `prune_stale`. Update the docstring order: apply specs, prune stale, then skill-rename verify/clean. Include prune actions in the returned report and in `changed_count`.

Replace the lock body and return with:

```python
    with engine.state_store.mutation():
        planned = engine.plan(specs)
        frozen_renames = tuple(skill_renames)
        preflight_skill_rename_cleanups(engine, frozen_renames)
        ordered = tuple(sorted(specs, key=lambda spec: spec.id))
        applied = tuple(engine.apply(spec) for spec in ordered)
        removed = engine.prune_stale(specs)
        verify_skill_rename_successors(engine, frozen_renames)
        apply_skill_rename_cleanups(engine, frozen_renames)
    actions = applied + removed
    return ConfigureStageReport(
        actions=actions,
        changed_count=sum(action.outcome != "unchanged" for action in actions),
    )
```

Implication: `--skip cursor` then configure will prune owned Cursor files that left the spec set. That matches skip-as-whole-component once ownership holds.

- [ ] **Step 4: Run the new tests and `tests/test_configure.py`**

Run: `rtk uv run --frozen pytest tests/test_configure.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk jj describe -m 'feat: prune owned managed files that left the configure plan'
rtk jj new
```

---

### Task 2: Replace `work` with `fsp` and `wsh`; make `glab` an include; drop Wave

**Files:**
- Create: `manifests/profiles/fsp.yaml`
- Create: `manifests/profiles/wsh.yaml`
- Delete: `manifests/profiles/work.yaml`
- Modify: `manifests/packages.yaml`, `manifests/applications.yaml`, `manifests/component-ids.txt`
- Test: `tests/test_manifests.py`

**Interfaces:**
- Consumes: existing `Profile.extends` and `include_key` selection
- Produces: profiles `default`, `fsp`, `wsh`; `include glab`; no `wave` skip key

- [ ] **Step 1: Write the failing tests**

Replace `test_work_profile_extends_default` and the skip/interface tests in `tests/test_manifests.py` with:

```python
def test_fsp_profile_extends_default(manifest_repository: ManifestRepository) -> None:
    """fsp adds previous-job packages without optional personal apps or glab."""
    resolved = ids(manifest_repository, ResolutionRequest(profile="fsp"))
    assert {
        "uv",
        "gh",
        "jj",
        "pre-commit",
        "libmagic",
        "awscli",
    } <= resolved
    assert {"obsidian", "signal", "mactex", "glab", "wave"}.isdisjoint(resolved)


def test_wsh_profile_extends_default_without_fsp_packages(
    manifest_repository: ManifestRepository,
) -> None:
    """wsh inherits the baseline and does not install AWS, libmagic, or glab."""
    resolved = ids(manifest_repository, ResolutionRequest(profile="wsh"))
    assert {"uv", "gh", "jj"} <= resolved
    assert {"awscli", "libmagic", "glab", "wave"}.isdisjoint(resolved)
```

Change `test_personal_applications_are_opt_in` params to add `glab`.

Change `test_skip_removes_complete_component` to drop the `wave` param and use `profile="fsp"`.

Replace `test_interface_ids_match_manifests` expected tuple with:

```python
    expected = (
        "profile default",
        "profile fsp",
        "profile wsh",
        "include glab",
        "include mactex",
        "include obsidian",
        "include signal",
        "skip claude-code",
        "skip codex",
        "skip cursor",
    )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `rtk uv run --frozen pytest tests/test_manifests.py -q`

Expected: FAIL (`unknown profile: fsp` / expected interface mismatch).

- [ ] **Step 3: Update manifests**

`manifests/profiles/fsp.yaml`:

```yaml
name: fsp
extends:
  - default
```

`manifests/profiles/wsh.yaml`:

```yaml
name: wsh
extends:
  - default
```

Delete `manifests/profiles/work.yaml`.

In `manifests/packages.yaml`:
- `glab`: add `enabled_by_default: false`, `include_key: glab`, `required: false` (keep `profiles: [default]`).
- `libmagic` and `awscli`: `profiles: [fsp]`.

In `manifests/applications.yaml`: delete the entire `wave` component.

Write `manifests/component-ids.txt` as the expected tuple from the test, one line per entry, no trailing extra skip.

- [ ] **Step 4: Confirm manifest tests pass**

Run: `rtk uv run --frozen pytest tests/test_manifests.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk jj describe -m 'feat: split work into fsp and wsh profiles'
rtk jj new
```

---

### Task 3: Configuration inventory — `zprofile-work` on `wsh`, delete Wave settings

**Files:**
- Modify: `manifests/configuration.yaml`
- Delete: `terminal/wave/settings.json`
- Modify: `tests/test_configure.py` (`test_skip_wave_removes_wave_spec`, `test_configuration_specs_honor_file_profiles`)
- Modify: `tests/test_integration.py` (`test_skip_wave_removes_wave_configuration`)
- Modify: `tests/test_planning.py` (FakeContributor waveterm path)

**Interfaces:**
- Consumes: Task 1 prune; Task 2 profiles
- Produces: `zprofile-work` selected only when `wsh` is in resolved profiles; no `wave-settings` spec

- [ ] **Step 1: Write the failing tests**

In `tests/test_configure.py`, rename `test_skip_wave_removes_wave_spec` to `test_skip_cursor_removes_component_spec` and use `component: cursor` / `skipped=("cursor",)` instead of wave.

Change `test_configuration_specs_honor_file_profiles` so the extra file is `profiles: [wsh]` and the second `ResolvedSetup` is `profiles=("default", "wsh")`. Rename local `work_specs` to `wsh_specs`.

In `tests/test_integration.py`, replace `test_skip_wave_removes_wave_configuration` with:

```python
def test_zprofile_work_is_wsh_only(
    repo_root: Path,
    fake_home: Path,
) -> None:
    """wsh is the only profile that installs extra env."""
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=fake_home)
    repository = ManifestRepository.load(repo_root / "manifests")
    wsh = repository.resolve(ResolutionRequest(profile="wsh"))
    fsp = repository.resolve(ResolutionRequest(profile="fsp"))
    default = repository.resolve(ResolutionRequest(profile="default"))
    wsh_specs = configuration_specs(
        repo_root / "manifests/configuration.yaml", wsh, paths
    )
    fsp_specs = configuration_specs(
        repo_root / "manifests/configuration.yaml", fsp, paths
    )
    default_specs = configuration_specs(
        repo_root / "manifests/configuration.yaml", default, paths
    )
    assert "zprofile-work" in {spec.id for spec in wsh_specs}
    assert "zprofile-work" not in {spec.id for spec in fsp_specs}
    assert "zprofile-work" not in {spec.id for spec in default_specs}
```

In `tests/test_planning.py`, change `FakeContributor` `wave-settings` to `id="example-settings"` and path `~/.config/example/settings.json`. Update the assertion that currently looks for `waveterm`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `rtk uv run --frozen pytest tests/test_configure.py::test_configuration_specs_honor_file_profiles tests/test_integration.py::test_zprofile_work_is_wsh_only tests/test_planning.py -q`

Expected: FAIL until yaml/profile tags change.

- [ ] **Step 3: Update configuration**

In `manifests/configuration.yaml`:
- `zprofile-work` `profiles: [wsh]`
- Delete the `wave-settings` entry.

Delete `terminal/wave/settings.json`. Remove the `terminal/wave/` directory if empty.

- [ ] **Step 4: Confirm tests pass**

Run: `rtk uv run --frozen pytest tests/test_configure.py::test_skip_cursor_removes_component_spec tests/test_configure.py::test_configuration_specs_honor_file_profiles tests/test_integration.py::test_zprofile_work_is_wsh_only tests/test_planning.py::test_plan_preserves_install_order_and_redacts_native_values -q`

Expected: PASS. Other `profile="work"` failures wait for Task 6.

- [ ] **Step 5: Commit**

```bash
rtk jj describe -m 'feat: bind extra zprofile to wsh and drop Wave settings'
rtk jj new
```

---

### Task 4: Doctor and plan gating

**Files:**
- Modify: `src/ballen_config/planning.py`
- Modify: `src/ballen_config/doctor.py`
- Test: `tests/test_planning.py`, `tests/test_doctor.py`

**Interfaces:**
- Consumes: `ResolvedSetup.is_enabled("glab")`; `"fsp" in resolved.profiles`
- Produces: `gitlab-auth` only when `glab` is selected; `aws-auth` only for `fsp`; GitLab failure uses the same WARNING / `not authenticated` pattern as GitHub

- [ ] **Step 1: Write the failing tests**

Replace `test_core_manual_actions_are_stable_and_work_aware` in `tests/test_planning.py` with:

```python
def test_core_manual_actions_gate_gitlab_and_aws(
    manifest_repository: ManifestRepository,
) -> None:
    """GitLab login is include-gated; AWS sign-in is fsp-only."""
    contributor = CoreManualContributor()
    default = manifest_repository.resolve(ResolutionRequest(profile="default"))
    wsh = manifest_repository.resolve(ResolutionRequest(profile="wsh"))
    fsp = manifest_repository.resolve(ResolutionRequest(profile="fsp"))
    with_glab = manifest_repository.resolve(
        ResolutionRequest(profile="wsh", includes=("glab",))
    )
    default_ids = [action.component_id for action in contributor.actions(default)]
    assert default_ids == [
        "github-auth",
        "ssh-transfer",
        "it-managed-applications",
    ]
    assert [action.component_id for action in contributor.actions(wsh)] == default_ids
    assert "gitlab-auth" in {
        action.component_id for action in contributor.actions(with_glab)
    }
    assert [action.component_id for action in contributor.actions(fsp)][-1] == "aws-auth"
```

In `tests/test_doctor.py`:

- Change `test_missing_gitlab_auth_is_explicitly_optional` into `test_gitlab_auth_runs_only_when_glab_is_enabled`: with empty enabled set, `gitlab-auth` is absent; with `enabled=frozenset({"glab"})` and a failing runner, status is `MANUAL`, severity `WARNING`, message `not authenticated`.
- Pass `enabled=frozenset({"glab"})` into the existing GitLab-ready secret-redaction test.
- Change `authentication_checks` callers to the new signature.
- Rename `test_aws_readiness_runs_only_for_work` to `test_aws_readiness_runs_only_for_fsp` and use `profiles=("default", "fsp")`.
- `test_skip_is_informational_not_missing`: use `skipped=("cursor",)` and finding id `cursor`.
- `test_core_doctor_check_order_is_stable`: `skipped=("cursor",)`, expected ids without `gitlab-auth` and with `cursor` instead of `wave`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `rtk uv run --frozen pytest tests/test_planning.py::test_core_manual_actions_gate_gitlab_and_aws tests/test_doctor.py -q`

Expected: FAIL on GitLab still always present / AWS still keyed off `work`.

- [ ] **Step 3: Implement gating**

`src/ballen_config/planning.py` `CoreManualContributor.actions`:

```python
        actions = [
            PlanAction(
                component_id="github-auth",
                category="manual",
                action="run-gh-auth-login",
                owner="user",
                required=False,
            ),
        ]
        if resolved.is_enabled("glab"):
            actions.append(
                PlanAction(
                    component_id="gitlab-auth",
                    category="manual",
                    action="run-glab-auth-login",
                    owner="user",
                    required=False,
                )
            )
        actions.extend(
            [
                PlanAction(
                    component_id="ssh-transfer",
                    category="manual",
                    action="follow-secure-transfer-guide",
                    owner="user",
                    path="docs/ssh-transfer.md",
                    required=False,
                ),
                PlanAction(
                    component_id="it-managed-applications",
                    category="manual",
                    action="use-company-supported-channel",
                    owner="user",
                    required=False,
                ),
            ]
        )
        if "fsp" in resolved.profiles:
            actions.append(
                PlanAction(
                    component_id="aws-auth",
                    category="manual",
                    action="complete-organization-sign-in",
                    owner="user",
                    required=False,
                )
            )
        return tuple(actions)
```

`src/ballen_config/doctor.py`:

```python
    def authentication_checks(
        self, enabled: frozenset[str] = frozenset()
    ) -> tuple[DoctorCheck, ...]:
        """Check relevant authentication without exposing identity output."""
        commands: list[tuple[str, tuple[str, ...]]] = [
            ("github-auth", ("gh", "auth", "status")),
        ]
        if "glab" in enabled:
            commands.append(("gitlab-auth", ("glab", "auth", "status")))
        if "fsp" in self.profiles:
            commands.append(("aws-auth", ("aws", "sts", "get-caller-identity")))
        checks: list[DoctorFinding] = []
        for finding_id, command in commands:
            result = self.runner.run(command)
            ready = result["returncode"] == 0
            checks.append(
                DoctorFinding(
                    id=finding_id,
                    status=(FindingStatus.READY if ready else FindingStatus.MANUAL),
                    severity=(
                        CheckSeverity.INFO if ready else CheckSeverity.WARNING
                    ),
                    message=("ready" if ready else "not authenticated"),
                )
            )
        return tuple(checks)
```

In `core_doctor_checks`, call:

```python
        *doctor.authentication_checks(
            frozenset(component.id for component in resolved.components)
        ),
```

Delete `optional_gitlab`.

- [ ] **Step 4: Confirm tests pass**

Run: `rtk uv run --frozen pytest tests/test_planning.py tests/test_doctor.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk jj describe -m 'feat: gate GitLab and AWS doctor and plan actions'
rtk jj new
```

---

### Task 5: Cursor overlay and Atlassian exception on `fsp`

**Files:**
- Modify: `assistants/inventory.yaml`
- Modify: `src/ballen_config/assistants/cursor.py`
- Modify: `src/ballen_config/assistants/models.py`
- Modify: `src/ballen_config/assistants/checks.py`
- Test: `tests/assistants/test_cursor.py`, `tests/assistants/test_models.py`, `tests/assistants/test_checks.py`

**Interfaces:**
- Consumes: `"fsp" in setup.profiles` / `profiles == ("fsp",)`
- Produces: Bedrock overlay and Atlassian MCP only for `fsp`; resource ids and source paths unchanged

- [ ] **Step 1: Write the failing tests**

In `tests/assistants/test_cursor.py`:
- `render_settings(..., profiles=("default", "work"))` → `("default", "fsp")` everywhere the overlay is expected.
- `test_inventory_is_synchronized_with_cursor_sources_and_catalog`: `work.profiles == ("fsp",)` and `atlassian_mcp.profiles == ("fsp",)`.
- `_resolved_setup("cursor", profiles=("default", "work"))` → `fsp` where it tests overlay/Atlassian contribution.

In `tests/assistants/test_models.py` `test_file_resource_allows_exact_work_cursor_atlassian_mcp_destination`: `profiles: ["fsp"]` and `resource.profiles == ("fsp",)`. Parametrized extra-profile cases that used `["default", "work"]` against the Atlassian exception should use `["default", "fsp"]` or a non-`fsp` extra that must fail.

In `tests/assistants/test_checks.py` `test_approved_cursor_atlassian_mcp_is_work_profile_only`: profiles `("default", "fsp")` for the accept case.

- [ ] **Step 2: Run tests to verify they fail**

Run: `rtk uv run --frozen pytest tests/assistants/test_cursor.py::test_inventory_is_synchronized_with_cursor_sources_and_catalog tests/assistants/test_models.py::test_file_resource_allows_exact_work_cursor_atlassian_mcp_destination tests/assistants/test_checks.py::test_approved_cursor_atlassian_mcp_is_work_profile_only -q`

Expected: FAIL (`profiles == ("work",)` still required).

- [ ] **Step 3: Retarget production checks**

`assistants/inventory.yaml`: `cursor.settings.work` and `cursor.atlassian-mcp` `profiles: [fsp]`.

`src/ballen_config/assistants/models.py`: `self.profiles == ("fsp",)` in the Atlassian exception. Docstring: “fsp resource”.

`src/ballen_config/assistants/cursor.py`:
- `render_settings`: `if "fsp" not in profiles`
- Atlassian contribution: `if "fsp" in setup.profiles`
- `cursor_settings_renderer(..., work="fsp" in setup.profiles)` — keep the `work` parameter name; only the profile membership check changes.

`src/ballen_config/assistants/checks.py`: `if "fsp" not in profiles or not approved`

- [ ] **Step 4: Confirm assistant tests pass**

Run: `rtk uv run --frozen pytest tests/assistants/test_cursor.py tests/assistants/test_models.py tests/assistants/test_checks.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk jj describe -m 'feat: bind Cursor Bedrock overlay and Atlassian MCP to fsp'
rtk jj new
```

---

### Task 6: Live docs and remaining test retargets

**Files:**
- Modify: `README.md`, `docs/manual-steps.md`, `tests/test_docs.py`
- Modify remaining production callers of `--profile work` / `"work"` against real manifests: `tests/test_cli.py`, `tests/test_bootstrap.py`, `tests/assistants/test_inventory.py`, `tests/assistants/test_desired_state.py`, `tests/assistants/test_integration.py`, and any leftover hits from `rg 'profile="work"|--profile", "work"|profile work|skip wave'` in `tests/` and `src/`

**Interfaces:**
- Consumes: Tasks 2–5
- Produces: live README/manual-steps contracts; full pytest suite green

- [ ] **Step 1: Write the failing doc tests**

In `tests/test_docs.py` `test_readme_contains_exact_operating_rationale`:
- `for decision in ("MacTeX", "libmagic", "glab", "Atlassian"):` (drop `"Wave"`).
- Assert `"fsp"` and `"wsh"` appear.
- Assert `"Wave"` does not appear.
- Assert `"./bootstrap --profile wsh"` appears.

In `test_manual_steps_cover_core_and_agent_handoffs`:
- Replace `"./bootstrap doctor --profile work"` with `"./bootstrap doctor --profile wsh"`.
- Assert `"./bootstrap doctor --profile fsp"` and `"--include glab"` appear.

- [ ] **Step 2: Run doc tests to verify they fail**

Run: `rtk uv run --frozen pytest tests/test_docs.py -q`

Expected: FAIL on Wave still present / work doctor command.

- [ ] **Step 3: Update live docs**

`README.md` Quick start:

```markdown
Run `./bootstrap --profile wsh` for the current-job setup, `./bootstrap --profile fsp`
for the previous-job setup, or `./bootstrap` for the default personal development
baseline.
```

`README.md` Profiles: `default` is the baseline; `wsh` adds current-job extra env; `fsp` adds AWS CLI, `libmagic`, Bedrock overlay, and Atlassian MCP. Includes: Obsidian, Signal, MacTeX, `glab`. Skips: Cursor, Claude Code, Codex. Example: `./bootstrap --profile wsh --skip codex`.

`README.md` Software choices: no dedicated terminal in desired state; iTerm remains an unmanaged fallback; `libmagic` belongs to `fsp`; `glab` is `--include glab`. Do not mention Warp. Do not mention Plato or Avogadro.

`README.md` coding-agent paragraph: Bedrock overlay and Atlassian MCP are `fsp`-only.

`docs/manual-steps.md`:
- Step 2: GitLab login only when `glab` was included.
- Step 3: AWS only for `fsp`; verify with `./bootstrap doctor --profile fsp`.
- Step 11: Atlassian OAuth for `fsp` Cursor.
- Step 13: finish with `./bootstrap doctor --profile wsh`, `--profile fsp`, or `--profile default`.

- [ ] **Step 4: Sweep remaining tests**

Run: `rtk rg -n 'profile="work"|--profile", "work"|profile work|skip wave' tests src README.md docs/manual-steps.md manifests`

Retarget real-manifest uses:
- `--profile work` / `profile="work"` → `fsp` when the test needs AWS/Atlassian/`libmagic`
- → `wsh` when it is the daily employer profile / extra env
- `skip wave` → `skip cursor` or drop the case
- CLI bootstrap argument-forwarding tests: `--profile wsh`

Leave synthetic catalog `profiles: [work]` fixtures that never load `manifests/profiles/`.

- [ ] **Step 5: Run the full suite**

Run: `rtk uv run --frozen pytest -q`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
rtk jj describe -m 'docs: retarget live bootstrap contracts to fsp and wsh'
rtk jj new
```

If the sweep also touched `src/` or `tests/assistants/` files not in this `git add`, include those paths in the same commit.

---

## Self-review

**Spec coverage:**
- `fsp` / `wsh` leaves, delete `work` — Task 2
- `glab` include — Task 2
- Wave component and settings gone; unknown `--skip wave` — Tasks 2–3
- `zprofile-work` on `wsh` only, no rename — Task 3
- Prune owned leftovers including ADC, Atlassian MCP, Wave settings — Task 1 (behavior), Tasks 3/5 (ids still `zprofile-work` / `cursor.atlassian-mcp`)
- AWS doctor/plan on `fsp`; GitLab only with `glab`; drop GitLab INFO special case — Task 4
- Cursor overlay + Atlassian on `fsp`, keep paths/ids — Task 5
- Live README/manual-steps; no historical spec rewrites; no Plato/Avogadro names — Task 6
- Digest-mismatch prune skip — Task 1
- Wave.app not uninstalled — Global Constraints; prune only managed settings file

**Placeholders:** none.

**Type consistency:** `ConfigAction.outcome` includes `"removed"` in Task 1 and is what `run_configure` returns; `authentication_checks(enabled: frozenset[str])` is the Task 4 signature `core_doctor_checks` must call.
