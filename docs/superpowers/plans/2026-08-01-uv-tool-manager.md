# uv Tool Manager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `uv_tool` component manager so the manifest can declare
uv-managed Python tools, then move `pre-commit` off Homebrew and bring `ruff`
under repository ownership.

**Architecture:** One new `Manager` enum member plus one branch at each of the
three sites that dispatch on manager type. Ordering reuses the existing
`depends_on` field and resolver, so a tool entry declares `depends_on: [uv]`
and installing before uv exists becomes a resolution error rather than a
runtime failure. No new fields, no new outcome vocabulary.

**Tech Stack:** Python 3.12, pydantic v2, pytest, `uv run --frozen`, jj.

**Approved design:**
[uv tool manager design](../specs/2026-08-01-uv-tool-manager-design.md)

---

## Conventions

Run every command from the repository root. Tests run through the frozen
environment:

```bash
uv run --frozen pytest -q
```

Commit with `rtk jj`, matching the existing plans in this directory. The `cc`
alias runs pre-commit against the working copy before you describe a change.

Do not run `brew uninstall` from any code path in this repository. The
Homebrew cleanup in Task 7 is a one-time local action performed by a human.

---

## Task 1: Add the UV_TOOL manager

**Files:**

- Modify: `src/ballen_config/models.py:8-13`
- Test: `tests/test_models.py`

**Step 1: Write the failing test**

- [ ] Add to `tests/test_models.py`:

```python
def test_uv_tool_manager_is_supported() -> None:
    """Tools installed by uv are expressible as components."""
    component = Component(
        id="pre-commit",
        manager=Manager("uv_tool"),
        package="pre-commit",
        depends_on=("uv",),
    )
    assert component.manager is Manager.UV_TOOL
```

**Step 2: Run it and confirm it fails**

- [ ] Run: `uv run --frozen pytest tests/test_models.py::test_uv_tool_manager_is_supported -q`
- [ ] Expected: `ValueError: 'uv_tool' is not a valid Manager`

**Step 3: Add the enum member**

- [ ] In `src/ballen_config/models.py`, add to `Manager`:

```python
    UV_TOOL = "uv_tool"
```

**Step 4: Confirm it passes**

- [ ] Run: `uv run --frozen pytest tests/test_models.py -q`
- [ ] Expected: all pass

**Step 5: Commit**

- [ ] Run:

```bash
rtk jj describe -m 'feat: add uv_tool manager to the component model'
rtk jj new
```

---

## Task 2: Prove the ordering guarantee

No production code changes. This task pins the behavior the design depends on,
so a later refactor cannot silently remove it.

**Withdrawn.** This task originally added the two ordering tests here and left
them failing until Task 6. That contradicted Tasks 3, 4, and 5, each of which
requires a green suite before committing: every later task would have met two
known-red tests and either stalled or fixed them out of scope.

The ordering tests are the red step for the manifest change, so they now live
in Task 6 alongside it. Nothing is lost — the guarantee is still pinned, and
every commit stays green.

Task numbering is unchanged so the tasks below keep their original names.

---

## Task 3: Install path

**Files:**

- Modify: `src/ballen_config/install.py:244-248`
- Test: `tests/test_install.py`

**Step 1: Write the failing tests**

- [ ] Add to `tests/test_install.py`, reusing the existing `FakeRunner`:

```python
def _uv_component() -> Component:
    return Component(
        id="pre-commit",
        manager=Manager.UV_TOOL,
        package="pre-commit",
        depends_on=("uv",),
    )


def test_uv_tool_already_installed_is_present(tmp_path: Path) -> None:
    """An installed tool is reported without a second install."""
    runner = FakeRunner(
        [{"returncode": 0, "stdout": "pre-commit v4.6.0\n- pre-commit\n", "stderr": ""}]
    )
    installer = Installer(runner=runner, home=tmp_path)
    outcome = installer.install(_uv_component())
    assert outcome.state == "present"
    assert runner.commands == [("uv", "tool", "list")]


def test_uv_tool_missing_is_installed(tmp_path: Path) -> None:
    """A missing tool is installed through uv."""
    runner = FakeRunner(
        [
            {"returncode": 0, "stdout": "ruff v0.15.2\n", "stderr": ""},
            {"returncode": 0, "stdout": "", "stderr": ""},
        ]
    )
    installer = Installer(runner=runner, home=tmp_path)
    outcome = installer.install(_uv_component())
    assert outcome.state == "installed"
    assert runner.commands[-1] == ("uv", "tool", "install", "pre-commit")


def test_required_uv_tool_failure_raises(tmp_path: Path) -> None:
    """A required tool that will not install stops the run."""
    runner = FakeRunner(
        [
            {"returncode": 0, "stdout": "", "stderr": ""},
            {"returncode": 1, "stdout": "", "stderr": ""},
        ]
    )
    installer = Installer(runner=runner, home=tmp_path)
    with pytest.raises(InstallError):
        installer.install(_uv_component())
```

- [ ] Match the `Installer(...)` constructor arguments used by the
      surrounding brew tests; the calls above show intent, not exact keywords.

**Step 2: Run and confirm they fail**

- [ ] Run: `uv run --frozen pytest tests/test_install.py -q -k uv_tool`
- [ ] Expected: FAIL. `install` currently falls through to `_git`, which
      raises on missing `destination`.

**Step 3: Implement**

- [ ] In `src/ballen_config/install.py`, change `install` to dispatch:

```python
    def install(self, component: Component) -> InstallOutcome:
        """Install one component, returning only its normalized outcome."""
        if component.manager in {Manager.BREW_FORMULA, Manager.BREW_CASK}:
            return self._brew(component)
        if component.manager is Manager.UV_TOOL:
            return self._uv_tool(component)
        return self._git(component)
```

- [ ] Add the branch, mirroring `_brew`'s shape and outcome vocabulary:

```python
    def _uv_tool(self, component: Component) -> InstallOutcome:
        """Install and verify one uv-managed tool."""
        listed = self.runner.run(("uv", "tool", "list"))
        if listed["returncode"] == 0 and any(
            line.split(" ", 1)[0] == component.package
            for line in listed["stdout"].splitlines()
        ):
            return InstallOutcome(component_id=component.id, state="present")
        installed = self.runner.run(("uv", "tool", "install", component.package))
        if installed["returncode"] == 0:
            return InstallOutcome(component_id=component.id, state="installed")
        if component.required:
            raise InstallError(f"required install failed: {component.id}")
        return InstallOutcome(
            component_id=component.id, state="optional-failure"
        )
```

- [ ] Note the parsing contract: `uv tool list` prints `name vX.Y.Z` for each
      tool and indented `- entrypoint` lines beneath it. Matching on the first
      space-delimited field is what keeps an entrypoint named like another
      tool from producing a false present.

**Step 4: Confirm they pass**

- [ ] Run: `uv run --frozen pytest tests/test_install.py -q`
- [ ] Expected: all pass

**Step 5: Commit**

- [ ] Run:

```bash
rtk jj describe -m 'feat: install uv-managed tools'
rtk jj new
```

---

## Task 4: Doctor probe

**Files:**

- Modify: `src/ballen_config/doctor.py:152-160`
- Test: `tests/test_doctor.py`

**Step 1: Write the failing tests**

- [ ] Add ready and missing cases to `tests/test_doctor.py`, matching the
      existing brew diagnostics tests:

```python
def test_uv_tool_present_is_ready(tmp_path: Path) -> None:
    runner = FakeRunner(
        [{"returncode": 0, "stdout": "pre-commit v4.6.0\n", "stderr": ""}]
    )
    findings = Doctor(runner=runner, home=tmp_path).check([_uv_component()])
    assert findings[0].status == "ready"


def test_uv_tool_absent_is_missing(tmp_path: Path) -> None:
    runner = FakeRunner([{"returncode": 0, "stdout": "", "stderr": ""}])
    findings = Doctor(runner=runner, home=tmp_path).check([_uv_component()])
    assert findings[0].status == "missing"
```

**Step 2: Run and confirm they fail**

- [ ] Run: `uv run --frozen pytest tests/test_doctor.py -q -k uv_tool`
- [ ] Expected: FAIL with `ValueError: git component lacks destination`

**Step 3: Implement**

- [ ] In `src/ballen_config/doctor.py`, add a branch before the git fallback:

```python
            elif component.manager is Manager.UV_TOOL:
                result = self.runner.run(("uv", "tool", "list"))
                present = result["returncode"] == 0 and any(
                    line.split(" ", 1)[0] == component.package
                    for line in result["stdout"].splitlines()
                )
```

**Step 4: Confirm they pass**

- [ ] Run: `uv run --frozen pytest tests/test_doctor.py -q`

**Step 5: Commit**

- [ ] Run:

```bash
rtk jj describe -m 'feat: report uv-managed tools in doctor'
rtk jj new
```

---

## Task 5: CLI probe

This is the third and last dispatch site. The design names keeping these three
in sync as the main maintenance cost, so do not skip it because the behavior
looks redundant.

**Files:**

- Modify: `src/ballen_config/cli.py:152-165`
- Test: `tests/test_cli.py`

**Step 1: Write the failing test**

- [ ] Add a test asserting `ComponentState.PRESENT` for a `uv_tool` component
      whose name appears in `uv tool list`, following the brew equivalent in
      `tests/test_cli.py`.

**Step 2: Run and confirm it fails**

- [ ] Run: `uv run --frozen pytest tests/test_cli.py -q -k uv_tool`
- [ ] Expected: FAIL with `ValueError: git component lacks destination`

**Step 3: Implement**

- [ ] In `src/ballen_config/cli.py`, add after the brew branch:

```python
        if component.manager is Manager.UV_TOOL:
            result = self.runner.run(("uv", "tool", "list"))
            return (
                ComponentState.PRESENT
                if result["returncode"] == 0
                and any(
                    line.split(" ", 1)[0] == component.package
                    for line in result["stdout"].splitlines()
                )
                else ComponentState.MISSING
            )
```

**Step 4: Confirm it passes**

- [ ] Run: `uv run --frozen pytest tests/test_cli.py -q`

**Step 5: Commit**

- [ ] Run:

```bash
rtk jj describe -m 'feat: resolve uv-managed tool state in the CLI'
rtk jj new
```

---

## Task 6: Move the manifest to uv

This task carries the ordering tests withdrawn from Task 2, so it follows the
same red-then-green shape as the tasks before it.

**Files:**

- Modify: `manifests/packages.yaml:9`
- Test: `tests/test_manifests.py`

**Step 1: Write the two failing tests**

- [ ] Add to `tests/test_manifests.py`, following the fixture style already
      used by `test_shell_parent_precedes_nested_git_components`:

```python
def test_uv_tool_component_orders_after_uv(
    manifest_repository: ManifestRepository,
) -> None:
    """uv installs before any tool it owns."""
    ordered = [
        component.id
        for component in manifest_repository.resolve(
            ResolutionRequest(profile="default")
        ).components
    ]
    assert ordered.index("uv") < ordered.index("pre-commit")


def test_uv_tool_requires_uv_to_be_selected(
    manifest_repository: ManifestRepository,
) -> None:
    """A tool cannot resolve when its manager is skipped."""
    with pytest.raises(ValueError, match="requires unselected uv"):
        manifest_repository.resolve(
            ResolutionRequest(profile="default", skips=("uv",))
        )
```

- [ ] If `ResolutionRequest` does not accept `skips`, read its definition in
      `src/ballen_config/manifests.py` and use the actual keyword. Do not
      change the production signature to fit the test.

**Step 2: Run and confirm they fail**

- [ ] Run: `uv run --frozen pytest tests/test_manifests.py -q`
- [ ] Expected: both FAIL. The first because `pre-commit` is still a
      `brew_formula` with no `depends_on`, so ordering is incidental rather
      than guaranteed. The second because nothing declares the dependency yet.

**Step 3: Change the entries**

- [ ] Replace the `pre-commit` line with:

```yaml
  - {id: pre-commit, manager: uv_tool, package: pre-commit, depends_on: [uv], profiles: [default]}
```

- [ ] Add `ruff` immediately after it:

```yaml
  - {id: ruff, manager: uv_tool, package: ruff, depends_on: [uv], profiles: [default]}
```

**Step 4: Confirm they pass**

- [ ] Run: `uv run --frozen pytest tests/test_manifests.py -q`
- [ ] Expected: both previously failing tests now pass

**Step 5: Confirm nothing regressed**

- [ ] Run: `uv run --frozen pytest -q`
- [ ] Expected: all pass, including
      `test_work_profile_extends_default`, which asserts `pre-commit`
      resolves. It is unaffected because only the manager changed.

**Step 6: Verify the plan end to end**

- [ ] Run: `./bootstrap plan --skip codex --skip cursor`
- [ ] Expected: `pre-commit` and `ruff` appear as install actions ordered
      after `uv`, and no `brew` action references either.

**Step 7: Commit**

- [ ] Run:

```bash
cc
rtk jj describe -m 'feat: manage pre-commit and ruff through uv'
rtk jj new
```

---

## Task 7: Local cleanup and verification

Not a code change. Perform once, on a machine that already ran the old
manifest.

**Step 1: Confirm the new state**

- [ ] Run: `./bootstrap doctor --skip codex --skip cursor`
- [ ] Expected: `pre-commit` and `ruff` both `ready`

**Step 2: Drop the superseded Homebrew formula**

- [ ] Run:

```bash
brew uninstall pre-commit
brew autoremove
```

- [ ] `brew autoremove` should remove `python@3.14`, which existed only as a
      dependency of the Homebrew `pre-commit`. Read its output before
      confirming; if it proposes removing anything else, stop and inspect.

**Step 3: Confirm resolution is unchanged**

- [ ] Run: `zsh -lc 'command -v pre-commit ruff; pre-commit --version'`
- [ ] Expected: both resolve under `~/.local/bin`, unchanged, because the uv
      copies already shadowed Homebrew's on `PATH`.

**Step 4: Confirm the repository still checks out clean**

- [ ] Run: `uv run --frozen pre-commit run --all-files`
- [ ] Run: `uv run --frozen pytest -q`

---

## Out of scope

Carried from the design; do not add these while implementing:

- Version pinning in manifest entries.
- `uv tool upgrade` or any reconcile-to-latest behavior.
- Promoting `mypy` to a global tool.
- Any code path that uninstalls Homebrew packages.
