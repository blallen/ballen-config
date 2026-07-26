# Core Laptop Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a safe, typed, idempotent macOS bootstrap that installs the approved software profiles, manages portable shell/VCS/Wave configuration, diagnoses drift, and documents all manual authentication and transfer work.

**Architecture:** A small Zsh shim handles only the stage-zero gap and launches a frozen Python 3.12 environment. A Pydantic-validated Python application resolves declarative manifests into deterministic plan, install, configure, and doctor operations; filesystem and subprocess boundaries are dependency-injected for tests. The optional memory-transfer capability and coding-agent configuration are intentionally outside this plan.

**Tech Stack:** Zsh, Python 3.12, Pydantic 2.8, PyYAML, `argparse`, Homebrew, `uv`, Pytest fixtures, Ruff, mypy, pre-commit, Jujutsu.

---

## Scope and delivery boundary

This is the first of two implementation plans. It must leave a useful bootstrap
that can install and configure the base or work profile without the second
plan. The dependent coding-agent plan adds Cursor, Claude Code, and Codex
configuration after this plan is complete.

Do not add `memories.py`, `manifests/memories.yaml`,
`manifests/memory-source-ids.txt`, `age`, or memory commands. The README should
state that encrypted memory transfer is deferred.

## File map

| Path | Responsibility |
| --- | --- |
| `bootstrap` | Zsh argument validation, prerequisite preparation, frozen Python launch |
| `pyproject.toml`, `uv.lock` | Python 3.12 application and reproducible development environment |
| `src/ballen_config/models.py` | Pydantic domain models and enums |
| `src/ballen_config/manifests.py` | Manifest loading, profile inheritance, include/skip resolution |
| `src/ballen_config/runtime.py` | Injected repository, home, state, and backup roots |
| `src/ballen_config/runner.py` | Typed subprocess boundary |
| `src/ballen_config/planning.py` | Structural, deterministic, redacted plans |
| `src/ballen_config/install.py` | Homebrew and Git-source installation |
| `src/ballen_config/state.py` | Atomic checksum, ownership, and normalized outcome records |
| `src/ballen_config/paths.py` | Approved-root and no-follow path validation |
| `src/ballen_config/configure.py` | Backup, symlink, copy, render, and convergence |
| `src/ballen_config/doctor.py` | Non-mutating checks and normalized readiness |
| `src/ballen_config/policy.py` | Tracked-tree secret/state/legacy policy |
| `src/ballen_config/cli.py`, `__main__.py` | Command dispatch and exit codes |
| `manifests/*.yaml` | Intentional software and managed-file declarations |
| `dotfiles/` | Repository-owned shell and VCS configuration |
| `terminal/wave/settings.json` | Portable Wave settings |
| `README.md`, `CLAUDE.md`, `docs/*.md` | Rationale, usage, manual auth, and SSH transfer |
| `tests/` | Unit and temporary-home integration coverage |
| `.github/workflows/ci.yml` | macOS verification |

### Task 1: Scaffold the typed Python project

**Files:**

- Create: `pyproject.toml`
- Create: `.python-version`
- Create: `.gitignore`
- Create: `src/ballen_config/__init__.py`
- Create: `src/ballen_config/runtime.py`
- Create: `tests/conftest.py`
- Create: `tests/test_package.py`
- Create: `tests/test_runtime.py`
- Delete: `ruff.toml` after consolidating its settings in `pyproject.toml`

- [ ] **Step 1: Add the project metadata**

Create `.python-version` with exactly:

```text
3.12
```

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "ballen-config"
version = "0.1.0"
description = "Typed macOS bootstrap for Brandon Allen's development environment"
readme = "README.md"
requires-python = ">=3.12,<3.13"
dependencies = [
  "pydantic==2.8.*",
  "PyYAML>=6.0,<7.0",
  "tomlkit>=0.13,<1.0",
]

[project.scripts]
ballen-config = "ballen_config.cli:main"

[dependency-groups]
dev = [
  "mypy>=1.11",
  "pytest>=8.3",
  "ruff>=0.15",
  "types-PyYAML>=6.0",
]

[tool.hatch.build.targets.wheel]
packages = ["src/ballen_config"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = ["-q"]

[tool.mypy]
python_version = "3.12"
strict = true
packages = ["ballen_config"]

[tool.ruff]
target-version = "py312"
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "RUF"]
ignore = ["E501"]
```

Create `.gitignore` with exactly:

```gitignore
.DS_Store
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
*.age
```

- [ ] **Step 2: Write the failing package test and shared fixtures**

```python
# tests/conftest.py
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Provide an isolated home directory."""
    home = tmp_path / "home"
    home.mkdir(mode=0o700)
    monkeypatch.setenv("HOME", str(home))
    yield home


@pytest.fixture
def repo_root() -> Path:
    """Return the repository root."""
    return Path(__file__).resolve().parents[1]
```

```python
# tests/test_package.py
import ballen_config


def test_package_exposes_version() -> None:
    assert ballen_config.__version__ == "0.1.0"
```

```python
# tests/test_runtime.py
from pathlib import Path

from ballen_config.runtime import RuntimePaths


def test_runtime_paths_derive_private_state_roots(
    repo_root: Path,
    fake_home: Path,
) -> None:
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=fake_home)
    assert paths.repo_root == repo_root.resolve()
    assert paths.home == fake_home.resolve()
    assert paths.state_root == fake_home / ".local/state/ballen-config"
    assert paths.backup_root == paths.state_root / "backups"
```

- [ ] **Step 3: Run the test and verify the package is missing**

Run:

```bash
rtk uv lock
rtk uv run --frozen pytest tests/test_package.py -v
```

Expected: FAIL during collection with `ModuleNotFoundError: No module named
'ballen_config'`.

- [ ] **Step 4: Add the minimal package**

```python
# src/ballen_config/__init__.py
"""Portable development-environment bootstrap."""

__version__ = "0.1.0"
```

```python
# src/ballen_config/runtime.py
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class RuntimePaths(BaseModel):
    """Approved roots injected into every filesystem operation."""

    model_config = ConfigDict(frozen=True)

    repo_root: Path
    home: Path
    state_root: Path
    backup_root: Path

    @classmethod
    def from_roots(
        cls,
        *,
        repo_root: Path,
        home: Path,
    ) -> RuntimePaths:
        """Construct normalized repository and private state roots."""
        normalized_home = home.resolve()
        state_root = normalized_home / ".local/state/ballen-config"
        return cls(
            repo_root=repo_root.resolve(),
            home=normalized_home,
            state_root=state_root,
            backup_root=state_root / "backups",
        )
```

- [ ] **Step 5: Verify the scaffold**

Run:

```bash
rtk uv run --frozen pytest tests/test_package.py tests/test_runtime.py -v
rtk uv run --frozen ruff check src tests
rtk uv run --frozen mypy
```

Expected: one passing test; Ruff and mypy exit 0.

- [ ] **Step 6: Record the checkpoint**

```bash
rtk jj describe -m "build: scaffold typed bootstrap project"
rtk jj new
```

### Task 2: Model and resolve software manifests

**Files:**

- Create: `src/ballen_config/models.py`
- Create: `src/ballen_config/manifests.py`
- Create: `manifests/component-ids.txt`
- Create: `manifests/profiles/default.yaml`
- Create: `manifests/profiles/work.yaml`
- Create: `manifests/packages.yaml`
- Create: `manifests/applications.yaml`
- Create: `tests/test_manifests.py`

- [ ] **Step 1: Write failing profile-resolution tests**

```python
# tests/test_manifests.py
from pathlib import Path

import pytest

from ballen_config.manifests import ManifestRepository
from ballen_config.models import Profile, ResolutionRequest


@pytest.fixture
def repository(repo_root: Path) -> ManifestRepository:
    return ManifestRepository.load(repo_root / "manifests")


def ids(repository: ManifestRepository, request: ResolutionRequest) -> set[str]:
    return {component.id for component in repository.resolve(request).components}


def test_work_profile_extends_default(repository: ManifestRepository) -> None:
    resolved = ids(repository, ResolutionRequest(profile="work"))
    assert {"uv", "gh", "glab", "jj", "wave", "libmagic", "awscli"} <= resolved
    assert {"obsidian", "signal", "mactex"}.isdisjoint(resolved)


def test_shell_parent_precedes_nested_git_components(
    repository: ManifestRepository,
) -> None:
    """Install Oh My Zsh before repositories nested beneath it."""
    ordered = [
        component.id
        for component in repository.resolve(
            ResolutionRequest(profile="default")
        ).components
    ]
    parent_index = ordered.index("oh-my-zsh")
    for child in (
        "forgit",
        "powerlevel10k",
        "zsh-autosuggestions",
        "zsh-completions",
        "zsh-syntax-highlighting",
    ):
        assert parent_index < ordered.index(child)


def test_profile_cycle_is_rejected(tmp_path: Path) -> None:
    """Reject cyclic inheritance before resolving components."""
    repository = ManifestRepository(
        tmp_path,
        {
            "a": Profile(name="a", extends=("b",)),
            "b": Profile(name="b", extends=("a",)),
        },
        (),
    )
    with pytest.raises(ValueError, match="profile inheritance cycle"):
        repository.resolve(ResolutionRequest(profile="a"))


@pytest.mark.parametrize("include", ["obsidian", "signal", "mactex"])
def test_personal_applications_are_opt_in(
    repository: ManifestRepository,
    include: str,
) -> None:
    resolved = ids(
        repository,
        ResolutionRequest(profile="default", includes=(include,)),
    )
    assert include in resolved


@pytest.mark.parametrize("skip", ["cursor", "claude-code", "codex", "wave"])
def test_skip_removes_complete_component(
    repository: ManifestRepository,
    skip: str,
) -> None:
    result = repository.resolve(
        ResolutionRequest(profile="work", skips=(skip,)),
    )
    assert skip not in {component.id for component in result.components}
    assert skip in result.skipped


def test_interface_ids_match_manifests(repository: ManifestRepository) -> None:
    expected = (
        "profile default",
        "profile work",
        "include mactex",
        "include obsidian",
        "include signal",
        "skip claude-code",
        "skip codex",
        "skip cursor",
        "skip wave",
    )
    assert repository.interface_lines() == expected
    interface_path = repository.root / "component-ids.txt"
    assert tuple(interface_path.read_text().splitlines()) == expected
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
rtk uv run --frozen pytest tests/test_manifests.py -v
```

Expected: FAIL because `models.py` and `manifests.py` do not exist.

- [ ] **Step 3: Add Pydantic models and the resolver**

```python
# src/ballen_config/models.py
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Manager(StrEnum):
    """Supported installation mechanisms."""

    BREW_FORMULA = "brew_formula"
    BREW_CASK = "brew_cask"
    GIT = "git"


class Component(BaseModel):
    """One intentional installable component."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    manager: Manager
    package: str
    profiles: tuple[str, ...] = ("default",)
    destination: str | None = None
    depends_on: tuple[str, ...] = ()
    application_paths: tuple[str, ...] = ()
    receipt_prefixes: tuple[str, ...] = ()
    enabled_by_default: bool = True
    include_key: str | None = None
    skip_key: str | None = None
    required: bool = True
    large: bool = False

    @model_validator(mode="after")
    def validate_selection(self) -> "Component":
        if not self.enabled_by_default and self.include_key is None:
            raise ValueError("optional components require include_key")
        if self.manager is Manager.GIT and self.destination is None:
            raise ValueError("git components require destination")
        if self.destination is not None:
            destination = Path(self.destination)
            if destination.is_absolute() or ".." in destination.parts:
                raise ValueError("component destination must be home-relative")
        return self


class ComponentFile(BaseModel):
    """Manifest file containing components."""

    components: tuple[Component, ...]


class Profile(BaseModel):
    """Named additive profile."""

    model_config = ConfigDict(frozen=True)

    name: str
    extends: tuple[str, ...] = ()


class ResolutionRequest(BaseModel):
    """User selection supplied to all stages."""

    model_config = ConfigDict(frozen=True)

    profile: str = "default"
    includes: tuple[str, ...] = ()
    skips: tuple[str, ...] = ()


class ResolvedSetup(BaseModel):
    """Deterministic resolved component set."""

    model_config = ConfigDict(frozen=True)

    profiles: tuple[str, ...]
    components: tuple[Component, ...]
    skipped: tuple[str, ...]

    def is_enabled(self, component_id: str) -> bool:
        """Return whether a component survived profile/include/skip resolution."""
        return any(
            component.id == component_id
            for component in self.components
        )
```

```python
# src/ballen_config/manifests.py
from pathlib import Path
from typing import Any

import yaml

from ballen_config.models import (
    Component,
    ComponentFile,
    Profile,
    ResolutionRequest,
    ResolvedSetup,
)


def _yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


class ManifestRepository:
    """Load and resolve declarative bootstrap manifests."""

    def __init__(
        self,
        root: Path,
        profiles: dict[str, Profile],
        components: tuple[Component, ...],
    ) -> None:
        self.root = root
        self.profiles = profiles
        self.components = components

    @classmethod
    def load(cls, root: Path) -> "ManifestRepository":
        profiles = {
            path.stem: Profile.model_validate(_yaml(path))
            for path in sorted((root / "profiles").glob("*.yaml"))
        }
        component_files = (
            ComponentFile.model_validate(_yaml(root / "packages.yaml")),
            ComponentFile.model_validate(_yaml(root / "applications.yaml")),
        )
        components = tuple(
            component
            for component_file in component_files
            for component in component_file.components
        )
        ids = [component.id for component in components]
        if len(ids) != len(set(ids)):
            raise ValueError("component ids must be unique")
        return cls(root, profiles, components)

    def _profile_names(
        self,
        name: str,
        visiting: frozenset[str] = frozenset(),
    ) -> set[str]:
        if name not in self.profiles:
            raise ValueError(f"unknown profile: {name}")
        if name in visiting:
            raise ValueError(f"profile inheritance cycle: {name}")
        names = {name}
        for parent in self.profiles[name].extends:
            names.update(self._profile_names(parent, visiting | {name}))
        return names

    @staticmethod
    def _dependency_order(
        components: list[Component],
    ) -> tuple[Component, ...]:
        by_id = {component.id: component for component in components}
        ordered: list[Component] = []
        permanent: set[str] = set()
        temporary: set[str] = set()

        def visit(component_id: str) -> None:
            if component_id in permanent:
                return
            if component_id in temporary:
                raise ValueError(f"component dependency cycle: {component_id}")
            temporary.add(component_id)
            component = by_id[component_id]
            for dependency in sorted(component.depends_on):
                if dependency not in by_id:
                    raise ValueError(
                        f"{component_id} requires unselected {dependency}"
                    )
                visit(dependency)
            temporary.remove(component_id)
            permanent.add(component_id)
            ordered.append(component)

        for component_id in sorted(by_id):
            visit(component_id)
        return tuple(ordered)

    def resolve(self, request: ResolutionRequest) -> ResolvedSetup:
        profile_names = self._profile_names(request.profile)
        include_keys = set(request.includes)
        skip_keys = set(request.skips)
        known_includes = {
            component.include_key
            for component in self.components
            if component.include_key is not None
        }
        known_skips = {
            component.skip_key
            for component in self.components
            if component.skip_key is not None
        }
        unknown_includes = include_keys - known_includes
        unknown_skips = skip_keys - known_skips
        if unknown_includes:
            raise ValueError(f"unknown includes: {sorted(unknown_includes)}")
        if unknown_skips:
            raise ValueError(f"unknown skips: {sorted(unknown_skips)}")

        selected = []
        for component in self.components:
            if not profile_names.intersection(component.profiles):
                continue
            if component.skip_key in skip_keys:
                continue
            if not component.enabled_by_default and component.include_key not in include_keys:
                continue
            selected.append(component)
        return ResolvedSetup(
            profiles=tuple(sorted(profile_names)),
            components=self._dependency_order(selected),
            skipped=tuple(sorted(skip_keys)),
        )

    def interface_lines(self) -> tuple[str, ...]:
        includes = {
            component.include_key
            for component in self.components
            if component.include_key
        }
        skips = {
            component.skip_key
            for component in self.components
            if component.skip_key
        }
        return tuple(
            [f"profile {name}" for name in sorted(self.profiles)]
            + [f"include {name}" for name in sorted(includes)]
            + [f"skip {name}" for name in sorted(skips)]
        )
```

- [ ] **Step 4: Add the exact initial manifests**

```yaml
# manifests/profiles/default.yaml
name: default
extends: []
```

```yaml
# manifests/profiles/work.yaml
name: work
extends:
  - default
```

```yaml
# manifests/packages.yaml
components:
  - {id: uv, manager: brew_formula, package: uv, profiles: [default]}
  - {id: gh, manager: brew_formula, package: gh, profiles: [default]}
  - {id: glab, manager: brew_formula, package: glab, profiles: [default]}
  - {id: jj, manager: brew_formula, package: jj, profiles: [default]}
  - {id: node, manager: brew_formula, package: node, profiles: [default]}
  - {id: ripgrep, manager: brew_formula, package: ripgrep, profiles: [default]}
  - {id: rtk, manager: brew_formula, package: rtk, profiles: [default]}
  - {id: libmagic, manager: brew_formula, package: libmagic, profiles: [work]}
  - {id: awscli, manager: brew_formula, package: awscli, profiles: [work]}
  - id: oh-my-zsh
    manager: git
    package: https://github.com/ohmyzsh/ohmyzsh.git
    destination: .oh-my-zsh
    profiles: [default]
  - id: powerlevel10k
    manager: git
    package: https://github.com/romkatv/powerlevel10k.git
    destination: .oh-my-zsh/custom/themes/powerlevel10k
    depends_on: [oh-my-zsh]
    profiles: [default]
  - id: zsh-autosuggestions
    manager: git
    package: https://github.com/zsh-users/zsh-autosuggestions.git
    destination: .oh-my-zsh/custom/plugins/zsh-autosuggestions
    depends_on: [oh-my-zsh]
    profiles: [default]
  - id: zsh-completions
    manager: git
    package: https://github.com/zsh-users/zsh-completions.git
    destination: .oh-my-zsh/custom/plugins/zsh-completions
    depends_on: [oh-my-zsh]
    profiles: [default]
  - id: zsh-syntax-highlighting
    manager: git
    package: https://github.com/zsh-users/zsh-syntax-highlighting.git
    destination: .oh-my-zsh/custom/plugins/zsh-syntax-highlighting
    depends_on: [oh-my-zsh]
    profiles: [default]
  - id: forgit
    manager: git
    package: https://github.com/wfxr/forgit.git
    destination: .oh-my-zsh/custom/plugins/forgit
    depends_on: [oh-my-zsh]
    profiles: [default]
```

```yaml
# manifests/applications.yaml
components:
  - id: wave
    manager: brew_cask
    package: wave
    profiles: [default]
    skip_key: wave
    application_paths: [/Applications/Wave.app]
  - id: cursor
    manager: brew_cask
    package: cursor
    profiles: [default]
    skip_key: cursor
    application_paths: [/Applications/Cursor.app]
  - {id: claude-code, manager: brew_cask, package: claude-code, profiles: [default], skip_key: claude-code}
  - {id: codex, manager: brew_cask, package: codex, profiles: [default], skip_key: codex}
  - id: brave-browser
    manager: brew_cask
    package: brave-browser
    profiles: [default]
    application_paths: [/Applications/Brave Browser.app]
  - {id: meslo-font, manager: brew_cask, package: font-meslo-lg-nerd-font, profiles: [default]}
  - id: obsidian
    manager: brew_cask
    package: obsidian
    profiles: [default]
    application_paths: [/Applications/Obsidian.app]
    enabled_by_default: false
    include_key: obsidian
    required: false
  - id: signal
    manager: brew_cask
    package: signal
    profiles: [default]
    application_paths: [/Applications/Signal.app]
    enabled_by_default: false
    include_key: signal
    required: false
  - id: mactex
    manager: brew_cask
    package: mactex
    profiles: [default]
    application_paths: [/Library/TeX/texbin/latex]
    receipt_prefixes: [org.tug.mactex.gui]
    enabled_by_default: false
    include_key: mactex
    required: false
    large: true
```

```text
# manifests/component-ids.txt
profile default
profile work
include mactex
include obsidian
include signal
skip claude-code
skip codex
skip cursor
skip wave
```

- [ ] **Step 5: Run the focused tests**

Run:

```bash
rtk uv run --frozen pytest tests/test_manifests.py -v
```

Expected: all profile, include, skip, and interface tests PASS.

- [ ] **Step 6: Record the checkpoint**

```bash
rtk jj describe -m "feat: define bootstrap software profiles"
rtk jj new
```

### Task 3: Build deterministic, redacted planning and CLI parsing

**Files:**

- Create: `src/ballen_config/runner.py`
- Create: `src/ballen_config/planning.py`
- Create: `src/ballen_config/cli.py`
- Create: `tests/test_planning.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing plan and CLI tests**

```python
# tests/test_planning.py
from pathlib import Path

from ballen_config.manifests import ManifestRepository
from ballen_config.models import ResolutionRequest, ResolvedSetup
from ballen_config.planning import (
    ComponentState,
    CoreManualContributor,
    PlanAction,
    build_plan,
    format_plan,
)


class FakeInspector:
    def state(self, component_id: str) -> ComponentState:
        if component_id == "gh":
            return ComponentState.PRESENT
        return ComponentState.MISSING


class FakeContributor:
    def actions(self, resolved: ResolvedSetup) -> tuple[PlanAction, ...]:
        return (
            PlanAction(
                component_id="wave-settings",
                category="configure",
                action="update-fields",
                owner="bootstrap",
                path="~/.config/waveterm/settings.json",
            ),
            PlanAction(
                component_id="gitlab-auth",
                category="manual",
                action="run glab auth login",
                owner="user",
                required=False,
            ),
        )


def test_plan_is_sorted_and_never_contains_destination_values(
    repo_root: Path,
) -> None:
    plan = build_plan(
        repo_root / "manifests",
        ResolutionRequest(profile="default"),
        FakeInspector(),
        contributors=(FakeContributor(),),
    )
    output = format_plan(plan)
    expected = [
        component.id
        for component in ManifestRepository.load(
            repo_root / "manifests"
        ).resolve(ResolutionRequest(profile="default")).components
    ]
    assert [
        action.component_id
        for action in plan.actions[: len(expected)]
    ] == expected
    assert "install gh (owner=bootstrap): present" in output
    assert "install glab (owner=bootstrap): install" in output
    assert "~/.config/waveterm/settings.json" in output
    assert "prompt: confirm package and configuration changes" in output
    assert "glpat-secret-value" not in output
```

```python
# tests/test_cli.py
from ballen_config.cli import parse_args


def test_cli_accepts_repeated_include_and_skip() -> None:
    options = parse_args(
        [
            "plan",
            "--profile",
            "work",
            "--include",
            "mactex",
            "--skip",
            "cursor",
            "--skip",
            "codex",
        ]
    )
    assert options.stage == "plan"
    assert options.request.includes == ("mactex",)
    assert options.request.skips == ("cursor", "codex")
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
rtk uv run --frozen pytest tests/test_planning.py tests/test_cli.py -v
```

Expected: FAIL because planning and CLI modules do not exist.

- [ ] **Step 3: Add the typed runner and structural plan**

```python
# src/ballen_config/runner.py
import subprocess
from collections.abc import Sequence
from typing import Protocol, TypedDict


class CommandResult(TypedDict):
    """Captured subprocess result."""

    returncode: int
    stdout: str
    stderr: str


class Runner(Protocol):
    """Subprocess boundary used by installers and diagnostics."""

    def run(self, command: Sequence[str]) -> CommandResult:
        """Run a command without displaying captured output."""


type CommandRunner = Runner


class SubprocessRunner:
    """Production subprocess runner."""

    def run(self, command: Sequence[str]) -> CommandResult:
        try:
            completed = subprocess.run(
                list(command),
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            return {"returncode": 127, "stdout": "", "stderr": ""}
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
```

```python
# src/ballen_config/planning.py
from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict

from ballen_config.manifests import ManifestRepository
from ballen_config.models import ResolutionRequest, ResolvedSetup


class ComponentState(StrEnum):
    """Observed component state."""

    PRESENT = "present"
    MISSING = "missing"


class Inspector(Protocol):
    """Read-only component state provider."""

    def state(self, component_id: str) -> ComponentState:
        """Return structural state without exposing command output."""


class PlanContributor(Protocol):
    """Extension seam for configuration, manual, and assistant actions."""

    def actions(self, resolved: ResolvedSetup) -> tuple[PlanAction, ...]:
        """Return redacted structural actions for the resolved setup."""


class PlanAction(BaseModel):
    """One redacted plan action."""

    model_config = ConfigDict(frozen=True)
    component_id: str
    category: Literal["install", "configure", "manual", "diagnostic"]
    action: str
    owner: str
    path: str | None = None
    required: bool = True
    large: bool = False


class CoreManualContributor:
    """Cross-cutting manual actions owned by the core bootstrap."""

    def actions(self, resolved: ResolvedSetup) -> tuple[PlanAction, ...]:
        actions = [
            PlanAction(
                component_id="github-auth",
                category="manual",
                action="run-gh-auth-login",
                owner="user",
                required=False,
            ),
            PlanAction(
                component_id="gitlab-auth",
                category="manual",
                action="run-glab-auth-login",
                owner="user",
                required=False,
            ),
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
        if "work" in resolved.profiles:
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


class SetupPlan(BaseModel):
    """Deterministic setup plan."""

    model_config = ConfigDict(frozen=True)
    profile: str
    profiles: tuple[str, ...]
    skipped: tuple[str, ...]
    actions: tuple[PlanAction, ...]
    expected_prompts: tuple[str, ...]


def build_plan(
    manifest_root: Path,
    request: ResolutionRequest,
    inspector: Inspector,
    contributors: Sequence[PlanContributor] = (),
) -> SetupPlan:
    resolved = ManifestRepository.load(manifest_root).resolve(request)
    install_actions = tuple(
        PlanAction(
            component_id=component.id,
            category="install",
            action=(
                "present"
                if inspector.state(component.id) is ComponentState.PRESENT
                else "install"
            ),
            owner="bootstrap",
            required=component.required,
            large=component.large,
        )
        for component in resolved.components
    )
    contributed_actions = tuple(
        sorted(
            (
                action
                for contributor in contributors
                for action in contributor.actions(resolved)
            ),
            key=lambda item: (
                item.category,
                item.component_id,
                item.path or "",
            ),
        )
    )
    actions = install_actions + contributed_actions
    action_ids = [action.component_id for action in actions]
    if len(action_ids) != len(set(action_ids)):
        raise ValueError("duplicate PlanAction.component_id")
    return SetupPlan(
        profile=request.profile,
        profiles=resolved.profiles,
        skipped=resolved.skipped,
        actions=actions,
        expected_prompts=("confirm package and configuration changes",),
    )


def format_plan(plan: SetupPlan) -> str:
    lines = [f"profile: {plan.profile}"]
    lines.extend(f"skip: {name} (intentional)" for name in plan.skipped)
    lines.extend(
        f"{action.category} {action.component_id} "
        f"(owner={action.owner}): {action.action}"
        + (f" [{action.path}]" if action.path else "")
        + (" (large download)" if action.large else "")
        for action in plan.actions
    )
    lines.extend(f"prompt: {prompt}" for prompt in plan.expected_prompts)
    return "\n".join(lines)
```

- [ ] **Step 4: Add complete CLI parsing**

```python
# src/ballen_config/cli.py
import argparse
from collections.abc import Sequence
from dataclasses import dataclass

from ballen_config.models import ResolutionRequest


STAGES = ("all", "prepare", "plan", "install", "configure", "doctor")


@dataclass(frozen=True)
class CliOptions:
    """Parsed bootstrap options."""

    stage: str
    request: ResolutionRequest


def parse_args(arguments: Sequence[str] | None = None) -> CliOptions:
    parser = argparse.ArgumentParser(prog="bootstrap")
    parser.add_argument("stage", nargs="?", choices=STAGES, default="all")
    parser.add_argument("--profile", default="default")
    parser.add_argument("--include", action="append", default=[])
    parser.add_argument("--skip", action="append", default=[])
    namespace = parser.parse_args(arguments)
    return CliOptions(
        stage=namespace.stage,
        request=ResolutionRequest(
            profile=namespace.profile,
            includes=tuple(namespace.include),
            skips=tuple(namespace.skip),
        ),
    )
```

At this checkpoint, tests call `parse_args()` and `build_plan()` directly.
Create the production `main()` and `__main__.py` in Task 7, where all stage
entry points and stage-zero error codes can be wired without a temporary
implementation.

- [ ] **Step 5: Run focused verification**

Run:

```bash
rtk uv run --frozen pytest tests/test_planning.py tests/test_cli.py -v
rtk uv run --frozen mypy
```

Expected: focused tests PASS and mypy exits 0.

- [ ] **Step 6: Record the checkpoint**

```bash
rtk jj describe -m "feat: add deterministic bootstrap planning"
rtk jj new
```

### Task 4: Implement the non-mutating stage-zero contract

**Files:**

- Create: `bootstrap`
- Create: `tests/test_bootstrap.py`

- [ ] **Step 1: Write failing shell-contract tests**

```python
# tests/test_bootstrap.py
import os
import shutil
import subprocess
from pathlib import Path


def copy_stage_zero(repo_root: Path, tmp_path: Path) -> Path:
    root = tmp_path / "checkout"
    (root / "manifests").mkdir(parents=True)
    shutil.copy2(repo_root / "bootstrap", root / "bootstrap")
    shutil.copy2(
        repo_root / "manifests/component-ids.txt",
        root / "manifests/component-ids.txt",
    )
    return root


def run_bootstrap(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/zsh", str(root / "bootstrap"), *arguments],
        cwd=root,
        env={**os.environ, "PATH": "/usr/bin:/bin"},
        check=False,
        capture_output=True,
        text=True,
    )


def test_plan_on_unprepared_checkout_is_read_only(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    root = copy_stage_zero(repo_root, tmp_path)
    before = sorted(path.relative_to(root) for path in root.rglob("*"))
    result = run_bootstrap(root, "plan", "--profile", "work")
    after = sorted(path.relative_to(root) for path in root.rglob("*"))
    assert result.returncode == 20
    assert "run ./bootstrap prepare" in result.stderr
    assert before == after


def test_unknown_component_fails_before_preparation(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    root = copy_stage_zero(repo_root, tmp_path)
    result = run_bootstrap(root, "install", "--include", "unknown")
    assert result.returncode == 2
    assert "unknown include: unknown" in result.stderr
    assert not (root / ".venv").exists()
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
rtk uv run --frozen pytest tests/test_bootstrap.py -v
```

Expected: FAIL because `bootstrap` does not exist.

- [ ] **Step 3: Add the complete Zsh shim**

```zsh
#!/bin/zsh
set -eu
umask 077

readonly ROOT_DIR="${0:A:h}"
readonly IDS_FILE="$ROOT_DIR/manifests/component-ids.txt"
readonly PREPARE_REQUIRED=20
readonly TEST_TOOL_ROOT="${BALLEN_BOOTSTRAP_TOOL_ROOT:-}"
typeset UNAME_BIN="${TEST_TOOL_ROOT:+$TEST_TOOL_ROOT/}uname"
typeset XCODE_SELECT_BIN="${TEST_TOOL_ROOT:+$TEST_TOOL_ROOT/}xcode-select"
typeset CURL_BIN="${TEST_TOOL_ROOT:+$TEST_TOOL_ROOT/}curl"
typeset BASH_BIN="${TEST_TOOL_ROOT:+$TEST_TOOL_ROOT/}bash"
typeset -a ORIGINAL_ARGS
ORIGINAL_ARGS=("$@")
typeset -g UV_BIN=""

if [[ -z "$TEST_TOOL_ROOT" ]]; then
  UNAME_BIN=/usr/bin/uname
  XCODE_SELECT_BIN=/usr/bin/xcode-select
  CURL_BIN=/usr/bin/curl
  BASH_BIN=/bin/bash
fi

fail() {
  print -u2 -- "$1"
  exit "${2:-2}"
}

has_id() {
  local kind="$1"
  local value="$2"
  /usr/bin/grep -Fqx "$kind $value" "$IDS_FILE"
}

validate_arguments() {
  local stage="all"
  local index=1
  if (( $# > 0 )) && [[ "$1" != --* ]]; then
    stage="$1"
    index=2
  fi
  case "$stage" in
    all|prepare|plan|install|configure|doctor) ;;
    *) fail "unknown stage: $stage" ;;
  esac
  while (( index <= $# )); do
    local option="${@[index]}"
    case "$option" in
      --profile|--include|--skip)
        (( index + 1 <= $# )) || fail "missing value for $option"
        local value="${@[index + 1]}"
        local kind="${option#--}"
        has_id "$kind" "$value" || fail "unknown $kind: $value"
        (( index += 2 ))
        ;;
      *) fail "unknown option: $option" ;;
    esac
  done
  print -- "$stage"
}

brew_path() {
  if command -v brew >/dev/null 2>&1; then
    command -v brew
  elif [[ -x /opt/homebrew/bin/brew ]]; then
    print -- /opt/homebrew/bin/brew
  elif [[ -x /usr/local/bin/brew ]]; then
    print -- /usr/local/bin/brew
  else
    return 1
  fi
}

confirm() {
  print -- "$1"
  read "reply?Continue? [y/N] "
  [[ "$reply" == [yY] ]]
}

find_uv() {
  if command -v uv >/dev/null 2>&1; then
    command -v uv
    return
  fi
  local brew
  brew="$(brew_path)" || return 1
  local candidate
  candidate="$("$brew" --prefix)/bin/uv"
  [[ -x "$candidate" ]] || return 1
  print -- "$candidate"
}

runtime_ready() {
  [[ -x "$ROOT_DIR/.venv/bin/python" ]] || return 1
  "$ROOT_DIR/.venv/bin/python" --version 2>&1 \
    | /usr/bin/grep -Eq '^Python 3\.12(\.|$)'
}

prepare_runtime() {
  [[ "$("$UNAME_BIN" -s)" == Darwin ]] || fail "macOS is required"
  if ! "$XCODE_SELECT_BIN" -p >/dev/null 2>&1; then
    "$XCODE_SELECT_BIN" --install
    fail "installation started; rerun ./bootstrap prepare when it completes" "$PREPARE_REQUIRED"
  fi
  local brew
  if ! brew="$(brew_path)"; then
    "$BASH_BIN" -c "$("$CURL_BIN" -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    brew="$(brew_path)" || fail "Homebrew installation did not produce brew"
  fi
  if ! UV_BIN="$(find_uv)"; then
    "$brew" install uv
    UV_BIN="$(find_uv)" || fail "Homebrew installation did not produce uv"
  fi
  "$UV_BIN" python install 3.12
  "$UV_BIN" sync --frozen --python 3.12
}

readonly STAGE="$(validate_arguments "$@")"
if [[ "$STAGE" == prepare ]]; then
  confirm "Prepare Command Line Tools, Homebrew, uv, Python 3.12, and the frozen environment?" \
    || exit 0
  prepare_runtime
  exit 0
fi

if ! runtime_ready; then
  case "$STAGE" in
    install|all)
      confirm "The runtime is missing. Run the reviewed prepare step now?" \
        || exit 0
      prepare_runtime
      ;;
    *) fail "bootstrap runtime is missing; run ./bootstrap prepare" "$PREPARE_REQUIRED" ;;
  esac
fi

if [[ -z "$UV_BIN" ]]; then
  UV_BIN="$(find_uv)" || fail "uv is missing; run ./bootstrap prepare" "$PREPARE_REQUIRED"
fi
exec "$UV_BIN" run --frozen --no-sync python -m ballen_config "${ORIGINAL_ARGS[@]}"
```

- [ ] **Step 4: Extend tests with fake PATH commands**

Add a `fake_stage_zero_tools` fixture that creates executable fake `uname`,
`xcode-select`, `curl`, `bash`, `brew`, and `uv` commands under
`tmp_path / "tools"`. Pass that directory through
`BALLEN_BOOTSTRAP_TOOL_ROOT`; prepend it to `PATH` for `brew` and `uv`
discovery; and append each invocation to `COMMAND_LOG`. The fake `uv sync`
creates an executable `.venv/bin/python` that prints `Python 3.12.9` for
`--version`. Provide `input="y\n"` only to tests that expect a prepare
confirmation. Assert:

```python
assert "sync --frozen --python 3.12" in command_log.read_text()
assert "run --frozen --no-sync python -m ballen_config plan" in command_log.read_text()
```

Also assert `plan`, `doctor`, and `configure` never call `sync`, while `prepare`
always calls frozen sync even when a valid `.venv` already exists. Assert a
declined prepare/all confirmation performs no tool calls or writes. Tests must
not replace or invoke the real `/usr/bin` tools.

- [ ] **Step 5: Run shell and Python verification**

Run:

```bash
rtk uv run --frozen pytest tests/test_bootstrap.py -v
rtk zsh -n bootstrap
```

Expected: all tests PASS and Zsh reports no syntax errors.

- [ ] **Step 6: Record the checkpoint**

```bash
rtk jj describe -m "feat: add safe stage-zero bootstrap"
rtk jj new
```

### Task 5: Install intentional Homebrew and Git components

**Files:**

- Create: `src/ballen_config/install.py`
- Create: `src/ballen_config/paths.py`
- Create: `src/ballen_config/state.py`
- Create: `tests/test_install.py`
- Create: `tests/test_state.py`
- Modify: `src/ballen_config/cli.py`
- Modify: `src/ballen_config/planning.py`

- [ ] **Step 1: Write failing installer tests**

```python
# tests/test_install.py
import hashlib
from pathlib import Path

import pytest

from ballen_config.install import (
    InstallAction,
    InstallError,
    Installer,
    run_install,
)
from ballen_config.models import Component, Manager
from ballen_config.runtime import RuntimePaths
from ballen_config.runner import CommandResult
from ballen_config.state import StateStore


class FakeRunner:
    def __init__(self, results: list[CommandResult]) -> None:
        self.results = iter(results)
        self.commands: list[tuple[str, ...]] = []

    def run(self, command: list[str] | tuple[str, ...]) -> CommandResult:
        self.commands.append(tuple(command))
        return next(self.results)


class FakeDownloader:
    def __init__(self, payloads: dict[str, bytes]) -> None:
        self.payloads = payloads
        self.destinations: list[Path] = []

    def download(
        self,
        *,
        url: str,
        destination: Path,
        maximum_bytes: int,
    ) -> None:
        payload = self.payloads[url]
        if len(payload) > maximum_bytes:
            raise InstallError("download exceeds declared size")
        self.destinations.append(destination)
        destination.write_bytes(payload)


def result(code: int = 0, stdout: str = "", stderr: str = "") -> CommandResult:
    return {"returncode": code, "stdout": stdout, "stderr": stderr}


def test_present_formula_is_a_no_op(tmp_path: Path) -> None:
    runner = FakeRunner([result(stdout="gh\n")])
    installer = Installer(runner, tmp_path)
    component = Component(
        id="gh",
        manager=Manager.BREW_FORMULA,
        package="gh",
    )
    outcome = installer.install(component)
    assert outcome.state == "present"
    assert runner.commands == [("brew", "list", "--formula", "gh")]


def test_missing_formula_is_installed(tmp_path: Path) -> None:
    runner = FakeRunner([result(1), result()])
    installer = Installer(runner, tmp_path)
    component = Component(
        id="gh",
        manager=Manager.BREW_FORMULA,
        package="gh",
    )
    outcome = installer.install(component)
    assert outcome.state == "installed"
    assert runner.commands[-1] == ("brew", "install", "gh")


def test_existing_application_bundle_satisfies_cask(tmp_path: Path) -> None:
    runner = FakeRunner([])
    installer = Installer(
        runner,
        tmp_path,
        path_exists=lambda path: path == Path("/Applications/Brave Browser.app"),
    )
    component = Component(
        id="brave-browser",
        manager=Manager.BREW_CASK,
        package="brave-browser",
        application_paths=("/Applications/Brave Browser.app",),
    )
    assert installer.install(component).state == "present"
    assert runner.commands == []


def test_vendor_mactex_satisfies_opt_in_cask(tmp_path: Path) -> None:
    runner = FakeRunner(
        [result(stdout="org.tug.mactex.gui2025\norg.tug.texlive2025\n")]
    )
    installer = Installer(
        runner,
        tmp_path,
        path_exists=lambda path: path == Path("/Library/TeX/texbin/latex"),
    )
    component = Component(
        id="mactex",
        manager=Manager.BREW_CASK,
        package="mactex",
        application_paths=("/Library/TeX/texbin/latex",),
        receipt_prefixes=("org.tug.mactex.gui",),
        enabled_by_default=False,
        include_key="mactex",
        required=False,
        large=True,
    )
    assert installer.install(component).state == "present"
    assert runner.commands == [("pkgutil", "--pkgs")]


def test_unmanaged_git_destination_is_preserved(tmp_path: Path) -> None:
    destination = tmp_path / ".oh-my-zsh"
    destination.mkdir()
    installer = Installer(FakeRunner([]), tmp_path)
    component = Component(
        id="oh-my-zsh",
        manager=Manager.GIT,
        package="https://github.com/ohmyzsh/ohmyzsh.git",
        destination=".oh-my-zsh",
    )
    with pytest.raises(InstallError, match="unmanaged git destination"):
        installer.install(component)
    assert destination.is_dir()


def test_git_destination_rejects_symlinked_parent(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / ".oh-my-zsh").symlink_to(outside, target_is_directory=True)
    installer = Installer(FakeRunner([]), tmp_path)
    component = Component(
        id="forgit",
        manager=Manager.GIT,
        package="https://github.com/wfxr/forgit.git",
        destination=".oh-my-zsh/custom/plugins/forgit",
    )
    with pytest.raises(ValueError, match="symlinked path component"):
        installer.install(component)
    assert list(outside.iterdir()) == []


def test_optional_failure_is_reported_without_raising(tmp_path: Path) -> None:
    runner = FakeRunner([result(1), result(1, stderr="download failed")])
    installer = Installer(runner, tmp_path)
    component = Component(
        id="signal",
        manager=Manager.BREW_CASK,
        package="signal",
        enabled_by_default=False,
        include_key="signal",
        required=False,
    )
    assert installer.install(component).state == "optional-failure"


def test_verified_download_checks_size_hash_runs_and_cleans(
    fake_home: Path,
    tmp_path: Path,
) -> None:
    payload = b"extension bytes"
    downloader = FakeDownloader({"https://example.test/tool.vsix": payload})
    runner = FakeRunner([result()])
    paths = RuntimePaths.from_roots(repo_root=tmp_path, home=fake_home)
    installer = Installer(
        runner,
        fake_home,
        downloader=downloader,
        private_temp_root=paths.state_root / "tmp",
    )
    action = InstallAction(
        component_id="cursor-extension",
        kind="verified-download",
        argv=("cursor", "--install-extension", "{artifact}"),
        url="https://example.test/tool.vsix",
        artifact_name="tool.vsix",
        size_bytes=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
    )
    assert installer.run_action(action).state == "installed"
    artifact = Path(runner.commands[0][2])
    assert runner.commands[0][:2] == ("cursor", "--install-extension")
    assert not artifact.exists()
    assert not (paths.state_root / "tmp").exists()


@pytest.mark.parametrize(
    ("size_delta", "digest"),
    [(1, None), (0, "0" * 64)],
)
def test_verified_download_rejects_unverified_payload_and_cleans(
    fake_home: Path,
    tmp_path: Path,
    size_delta: int,
    digest: str | None,
) -> None:
    payload = b"extension bytes"
    downloader = FakeDownloader({"https://example.test/tool.vsix": payload})
    runner = FakeRunner([])
    paths = RuntimePaths.from_roots(repo_root=tmp_path, home=fake_home)
    installer = Installer(
        runner,
        fake_home,
        downloader=downloader,
        private_temp_root=paths.state_root / "tmp",
    )
    action = InstallAction(
        component_id="cursor-extension",
        kind="verified-download",
        argv=("cursor", "--install-extension", "{artifact}"),
        url="https://example.test/tool.vsix",
        artifact_name="tool.vsix",
        size_bytes=len(payload) + size_delta,
        sha256=digest or hashlib.sha256(payload).hexdigest(),
    )
    with pytest.raises(InstallError, match="verification failed"):
        installer.run_action(action)
    assert runner.commands == []
    assert not (paths.state_root / "tmp").exists()


@pytest.mark.parametrize(
    ("size_delta", "digest"),
    [(1, None), (0, "0" * 64)],
)
def test_optional_verified_download_failure_is_nonfatal(
    fake_home: Path,
    tmp_path: Path,
    size_delta: int,
    digest: str | None,
) -> None:
    """Normalize optional size and digest failures without running VSIX."""
    payload = b"extension bytes"
    downloader = FakeDownloader({"https://example.test/tool.vsix": payload})
    runner = FakeRunner([])
    paths = RuntimePaths.from_roots(repo_root=tmp_path, home=fake_home)
    installer = Installer(
        runner,
        fake_home,
        downloader=downloader,
        private_temp_root=paths.state_root / "tmp",
    )
    action = InstallAction(
        component_id="cursor-extension",
        kind="verified-download",
        argv=("cursor", "--install-extension", "{artifact}"),
        required=False,
        url="https://example.test/tool.vsix",
        artifact_name="tool.vsix",
        size_bytes=len(payload) + size_delta,
        sha256=digest or hashlib.sha256(payload).hexdigest(),
    )
    assert installer.run_action(action).state == "optional-failure"
    assert runner.commands == []
    assert not (paths.state_root / "tmp").exists()


def test_run_install_records_normalized_outcomes(
    fake_home: Path,
    tmp_path: Path,
) -> None:
    paths = RuntimePaths.from_roots(repo_root=tmp_path, home=fake_home)
    store = StateStore(paths)
    runner = FakeRunner([result(1), result()])
    report = run_install(
        components=(
            Component(
                id="gh",
                manager=Manager.BREW_FORMULA,
                package="gh",
            ),
        ),
        actions=(),
        runner=runner,
        paths=paths,
        state_store=store,
        downloader=FakeDownloader({}),
    )
    assert report.exit_code == 0
    assert report.outcomes == ("gh: installed",)
    assert store.load().installs["gh"].state == "installed"
```

```python
# tests/test_state.py
import stat
from pathlib import Path

import pytest

from ballen_config.runtime import RuntimePaths
from ballen_config.state import (
    BootstrapState,
    InstallRecord,
    ManagedRecord,
    StateStore,
)


def test_state_store_is_atomic_and_private(
    repo_root: Path,
    fake_home: Path,
) -> None:
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=fake_home)
    store = StateStore(paths)
    state = BootstrapState(
        installs={
            "signal": InstallRecord(
                resource_id="signal",
                state="optional-failure",
            )
        },
        managed={
            "zshrc": ManagedRecord(
                resource_id="zshrc",
                source_digest="a" * 64,
                destination_digest="b" * 64,
                destination=".zshrc",
            )
        },
    )
    store.write(state)
    assert store.load() == state
    assert stat.S_IMODE(paths.state_root.stat().st_mode) == 0o700
    assert stat.S_IMODE(store.path.stat().st_mode) == 0o600
    assert "optional-failure" in store.path.read_text()


def test_state_never_persists_native_command_output(
    repo_root: Path,
    fake_home: Path,
) -> None:
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=fake_home)
    store = StateStore(paths)
    store.record_install(
        InstallRecord(resource_id="signal", state="optional-failure")
    )
    assert "download failed with token" not in store.path.read_text()


def test_state_store_rejects_symlinked_state_root(
    repo_root: Path,
    fake_home: Path,
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    state_parent = fake_home / ".local"
    state_parent.mkdir()
    (state_parent / "state").symlink_to(outside, target_is_directory=True)
    store = StateStore(
        RuntimePaths.from_roots(repo_root=repo_root, home=fake_home)
    )
    with pytest.raises(ValueError, match="symlinked path component"):
        store.load()
    with pytest.raises(ValueError, match="symlinked path component"):
        store.write(BootstrapState())
    assert list(outside.iterdir()) == []


def test_state_store_rejects_terminal_state_symlink(
    repo_root: Path,
    fake_home: Path,
    tmp_path: Path,
) -> None:
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=fake_home)
    paths.state_root.mkdir(parents=True)
    outside = tmp_path / "outside.json"
    outside.write_text('{"secret": "unchanged"}')  # pragma: allowlist secret
    (paths.state_root / "state.json").symlink_to(outside)
    store = StateStore(paths)
    with pytest.raises(ValueError, match="symlinked path component"):
        store.load()
    with pytest.raises(ValueError, match="symlinked path component"):
        store.write(BootstrapState())
    assert outside.read_text() == '{"secret": "unchanged"}'  # pragma: allowlist secret


def test_state_store_rejects_state_path_outside_home(
    repo_root: Path,
    fake_home: Path,
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside"
    paths = RuntimePaths(
        repo_root=repo_root,
        home=fake_home,
        state_root=outside,
        backup_root=outside / "backups",
    )
    with pytest.raises(ValueError, match="path escapes approved root"):
        StateStore(paths).write(BootstrapState())
    assert not outside.exists()
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
rtk uv run --frozen pytest tests/test_install.py tests/test_state.py -v
```

Expected: FAIL because `install.py` and `state.py` do not exist.

- [ ] **Step 3: Implement idempotent installation**

Create the shared approved-root helpers before using them:

```python
# src/ballen_config/paths.py
import os
from pathlib import Path
import stat


def assert_contained(path: Path, root: Path) -> Path:
    """Return a normalized path only when it remains beneath root."""
    normalized_root = root.resolve()
    normalized = Path(os.path.abspath(path))
    try:
        normalized.relative_to(normalized_root)
    except ValueError as error:
        raise ValueError(f"path escapes approved root: {path}") from error
    return normalized


def assert_no_symlink_components(
    path: Path,
    *,
    stop: Path,
    include_leaf: bool = False,
) -> None:
    """Reject existing symlinks between an approved root and a path."""
    relative = path.relative_to(stop)
    current = stop
    parts = relative.parts if include_leaf else relative.parts[:-1]
    for part in parts:
        current /= part
        try:
            metadata = os.lstat(current)
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError(f"symlinked path component: {current}")
        if not stat.S_ISDIR(metadata.st_mode):
            raise ValueError(f"non-directory path component: {current}")
```

Create the persistent ownership/outcome store:

```python
# src/ballen_config/state.py
from __future__ import annotations

from pathlib import Path
from typing import Literal
import os
import stat
import tempfile

from pydantic import BaseModel, ConfigDict, Field

from ballen_config.paths import assert_contained, assert_no_symlink_components
from ballen_config.runtime import RuntimePaths


class ManagedRecord(BaseModel):
    """Checksums proving ownership of one managed destination."""

    model_config = ConfigDict(frozen=True)
    resource_id: str
    source_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    destination_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    destination: str


class InstallRecord(BaseModel):
    """Normalized install outcome without native command output."""

    model_config = ConfigDict(frozen=True)
    resource_id: str
    state: Literal["present", "installed", "optional-failure"]


class BootstrapState(BaseModel):
    """Versioned local ownership and outcome state."""

    model_config = ConfigDict(frozen=True)
    version: Literal[1] = 1
    installs: dict[str, InstallRecord] = Field(default_factory=dict)
    managed: dict[str, ManagedRecord] = Field(default_factory=dict)


class StateStore:
    """Atomically persist private bootstrap state."""

    def __init__(self, paths: RuntimePaths) -> None:
        self.paths = paths
        self.path = paths.state_root / "state.json"

    def _validate_paths(self) -> None:
        """Reject state paths outside home or through any symlink."""
        assert_contained(self.paths.state_root, self.paths.home)
        assert_contained(self.paths.backup_root, self.paths.home)
        assert_contained(self.path, self.paths.state_root)
        assert_no_symlink_components(
            self.paths.state_root,
            stop=self.paths.home,
            include_leaf=True,
        )
        assert_no_symlink_components(
            self.path,
            stop=self.paths.state_root,
        )
        try:
            metadata = os.lstat(self.path)
        except FileNotFoundError:
            return
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError(f"symlinked path component: {self.path}")
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError(f"state path is not a regular file: {self.path}")

    def load(self) -> BootstrapState:
        """Load state, or return an empty versioned state."""
        self._validate_paths()
        if not self.path.exists():
            return BootstrapState()
        return BootstrapState.model_validate_json(self.path.read_text())

    def write(self, state: BootstrapState) -> None:
        """Write mode-0600 JSON through a same-directory atomic rename."""
        self._validate_paths()
        self.paths.state_root.mkdir(parents=True, mode=0o700, exist_ok=True)
        self._validate_paths()
        self.paths.state_root.chmod(0o700)
        payload = state.model_dump_json(indent=2) + "\n"
        descriptor, temporary_name = tempfile.mkstemp(
            dir=self.paths.state_root,
            prefix=".state.",
        )
        temporary = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            self._validate_paths()
            temporary.replace(self.path)
        finally:
            temporary.unlink(missing_ok=True)

    def record_install(self, record: InstallRecord) -> None:
        """Update one normalized install result."""
        state = self.load()
        installs = {**state.installs, record.resource_id: record}
        self.write(state.model_copy(update={"installs": installs}))

    def record_managed(self, record: ManagedRecord) -> None:
        """Update one managed-destination ownership record."""
        state = self.load()
        managed = {**state.managed, record.resource_id: record}
        self.write(state.model_copy(update={"managed": managed}))
```

`ConfigEngine` adds an equivalent `record_managed()` call only after a
successful destination replacement. Planning compares the stored source and
destination digests to distinguish an unmanaged conflict from drift in a
previously managed destination. Never store subprocess stdout/stderr or file
contents.

```python
# src/ballen_config/install.py
from __future__ import annotations

from collections.abc import Callable, Sequence
import hashlib
import os
from pathlib import Path
import shutil
import stat
import tempfile
from typing import Literal, Protocol
import urllib.request

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ballen_config.models import Component, Manager, ResolvedSetup
from ballen_config.paths import assert_contained, assert_no_symlink_components
from ballen_config.runtime import RuntimePaths
from ballen_config.runner import CommandResult, Runner
from ballen_config.state import InstallRecord, StateStore


class InstallOutcome(BaseModel):
    """Normalized install result without subprocess output."""

    model_config = ConfigDict(frozen=True)
    component_id: str
    state: Literal["present", "installed", "optional-failure"]


class InstallAction(BaseModel):
    """One redacted command or verified-download installation."""

    model_config = ConfigDict(frozen=True)
    component_id: str
    kind: Literal["command", "verified-download"] = "command"
    argv: tuple[str, ...]
    required: bool = True
    url: str | None = None
    artifact_name: str | None = None
    size_bytes: int | None = Field(default=None, gt=0)
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_variant(self) -> InstallAction:
        """Require complete, internally consistent variant fields."""
        metadata = (
            self.url,
            self.artifact_name,
            self.size_bytes,
            self.sha256,
        )
        if self.kind == "command":
            if any(value is not None for value in metadata):
                raise ValueError("command action cannot contain download metadata")
            if "{artifact}" in self.argv:
                raise ValueError("command action cannot use {artifact}")
            return self
        if any(value is None for value in metadata):
            raise ValueError("verified-download action requires all metadata")
        if not self.url or not self.url.startswith("https://"):
            raise ValueError("verified download requires HTTPS")
        if (
            not self.artifact_name
            or Path(self.artifact_name).name != self.artifact_name
        ):
            raise ValueError("artifact_name must be one filename")
        if self.argv.count("{artifact}") != 1:
            raise ValueError("verified argv requires one {artifact}")
        return self


class Downloader(Protocol):
    """Bounded download boundary used by verified install actions."""

    def download(
        self,
        *,
        url: str,
        destination: Path,
        maximum_bytes: int,
    ) -> None:
        """Download one HTTPS resource without exceeding the byte limit."""


class HttpsDownloader:
    """Production streaming HTTPS downloader."""

    def download(
        self,
        *,
        url: str,
        destination: Path,
        maximum_bytes: int,
    ) -> None:
        """Stream a bounded HTTPS response to a private destination."""
        if not url.startswith("https://"):
            raise InstallError("verified download requires HTTPS")
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                if not response.geturl().startswith("https://"):
                    raise InstallError("download redirected away from HTTPS")
                with destination.open("xb") as stream:
                    total = 0
                    while chunk := response.read(64 * 1024):
                        total += len(chunk)
                        if total > maximum_bytes:
                            raise InstallError("download exceeds declared size")
                        stream.write(chunk)
                    stream.flush()
                    os.fsync(stream.fileno())
        except Exception:
            destination.unlink(missing_ok=True)
            raise


class InstallError(RuntimeError):
    """Raised when a required component cannot be installed."""


class Installer:
    """Install missing intentional components without removing anything."""

    def __init__(
        self,
        runner: Runner,
        home: Path,
        path_exists: Callable[[Path], bool] = Path.exists,
        *,
        downloader: Downloader | None = None,
        private_temp_root: Path | None = None,
    ) -> None:
        self.runner = runner
        self.home = home
        self.path_exists = path_exists
        self.downloader = downloader or HttpsDownloader()
        self.private_temp_root = (
            private_temp_root
            or home / ".local/state/ballen-config/tmp"
        )

    def install(self, component: Component) -> InstallOutcome:
        if component.manager in {Manager.BREW_FORMULA, Manager.BREW_CASK}:
            return self._brew(component)
        return self._git(component)

    def run_action(self, action: InstallAction) -> InstallOutcome:
        """Execute a prevalidated extension action without exposing output."""
        if action.kind == "verified-download":
            try:
                completed = self._run_verified_download(action)
            except InstallError as error:
                if action.required:
                    raise InstallError(
                        f"{error}: {action.component_id}"
                    ) from error
                return InstallOutcome(
                    component_id=action.component_id,
                    state="optional-failure",
                )
        else:
            completed = self.runner.run(action.argv)
        if completed["returncode"] == 0:
            return InstallOutcome(
                component_id=action.component_id,
                state="installed",
            )
        if action.required:
            raise InstallError(
                f"required install failed: {action.component_id}"
            )
        return InstallOutcome(
            component_id=action.component_id,
            state="optional-failure",
        )

    def _run_verified_download(
        self,
        action: InstallAction,
    ) -> CommandResult:
        """Download, verify, consume, and remove one private artifact."""
        assert action.url is not None
        assert action.artifact_name is not None
        assert action.size_bytes is not None
        assert action.sha256 is not None
        temp_root = assert_contained(self.private_temp_root, self.home)
        assert_no_symlink_components(
            temp_root,
            stop=self.home,
            include_leaf=True,
        )
        temp_root.mkdir(parents=True, mode=0o700, exist_ok=False)
        os.chmod(temp_root, 0o700)
        workspace = Path(tempfile.mkdtemp(prefix="action-", dir=temp_root))
        os.chmod(workspace, 0o700)
        artifact = workspace / action.artifact_name
        try:
            try:
                self.downloader.download(
                    url=action.url,
                    destination=artifact,
                    maximum_bytes=action.size_bytes,
                )
            except InstallError:
                raise
            except Exception as error:
                raise InstallError("download failed") from error
            metadata = os.lstat(artifact)
            if not stat.S_ISREG(metadata.st_mode):
                raise InstallError("download verification failed")
            payload = artifact.read_bytes()
            if (
                len(payload) != action.size_bytes
                or hashlib.sha256(payload).hexdigest() != action.sha256
            ):
                raise InstallError("download verification failed")
            os.chmod(artifact, 0o600)
            argv = tuple(
                str(artifact) if value == "{artifact}" else value
                for value in action.argv
            )
            return self.runner.run(argv)
        finally:
            shutil.rmtree(workspace, ignore_errors=True)
            shutil.rmtree(temp_root, ignore_errors=True)

    def _brew(self, component: Component) -> InstallOutcome:
        if component.application_paths and all(
            self.path_exists(Path(path))
            for path in component.application_paths
        ):
            if not component.receipt_prefixes:
                return InstallOutcome(
                    component_id=component.id,
                    state="present",
                )
            receipts = self.runner.run(("pkgutil", "--pkgs"))
            installed_receipts = receipts["stdout"].splitlines()
            if receipts["returncode"] == 0 and all(
                any(
                    receipt.startswith(prefix)
                    for receipt in installed_receipts
                )
                for prefix in component.receipt_prefixes
            ):
                return InstallOutcome(
                    component_id=component.id,
                    state="present",
                )
        type_flag = (
            "--formula"
            if component.manager is Manager.BREW_FORMULA
            else "--cask"
        )
        present = self.runner.run(
            ("brew", "list", type_flag, component.package)
        )
        if present["returncode"] == 0:
            return InstallOutcome(component_id=component.id, state="present")
        command = ["brew", "install"]
        if component.manager is Manager.BREW_CASK:
            command.append("--cask")
        command.append(component.package)
        installed = self.runner.run(command)
        if installed["returncode"] == 0:
            return InstallOutcome(component_id=component.id, state="installed")
        if component.required:
            raise InstallError(f"required install failed: {component.id}")
        return InstallOutcome(
            component_id=component.id,
            state="optional-failure",
        )

    def _git(self, component: Component) -> InstallOutcome:
        assert component.destination is not None
        destination = assert_contained(
            self.home / component.destination,
            self.home,
        )
        assert_no_symlink_components(destination, stop=self.home)
        if destination.is_symlink():
            raise InstallError(f"git destination is a symlink: {component.id}")
        if (destination / ".git").is_dir():
            return InstallOutcome(component_id=component.id, state="present")
        if destination.exists():
            raise InstallError(
                f"unmanaged git destination exists: {component.id}"
            )
        destination.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        stage = destination.with_name(f".{destination.name}.bootstrap-stage")
        if stage.exists() or stage.is_symlink():
            raise InstallError(f"stale git stage exists: {component.id}")
        completed = self.runner.run(
            ("git", "clone", "--depth=1", component.package, str(stage))
        )
        if completed["returncode"] == 0:
            os.replace(stage, destination)
            return InstallOutcome(component_id=component.id, state="installed")
        if stage.is_dir() and not stage.is_symlink():
            shutil.rmtree(stage)
        if component.required:
            raise InstallError(f"required install failed: {component.id}")
        return InstallOutcome(
            component_id=component.id,
            state="optional-failure",
        )


class InstallStageReport(BaseModel):
    """Normalized install-stage result."""

    model_config = ConfigDict(frozen=True)
    exit_code: Literal[0, 1]
    outcomes: tuple[str, ...]


type InstallActionSupplier = Callable[
    [ResolvedSetup, RuntimePaths, Runner],
    Sequence[InstallAction],
]


def run_install(
    *,
    components: Sequence[Component],
    actions: Sequence[InstallAction],
    runner: Runner,
    paths: RuntimePaths,
    state_store: StateStore,
    downloader: Downloader,
) -> InstallStageReport:
    """Execute resolved components and extension actions in stable order."""
    installer = Installer(
        runner,
        paths.home,
        downloader=downloader,
        private_temp_root=paths.state_root / "tmp",
    )
    outcomes: list[str] = []
    try:
        for component in components:
            outcome = installer.install(component)
            state_store.record_install(
                InstallRecord(
                    resource_id=outcome.component_id,
                    state=outcome.state,
                )
            )
            outcomes.append(f"{outcome.component_id}: {outcome.state}")
        for action in actions:
            outcome = installer.run_action(action)
            state_store.record_install(
                InstallRecord(
                    resource_id=outcome.component_id,
                    state=outcome.state,
                )
            )
            outcomes.append(f"{outcome.component_id}: {outcome.state}")
    except InstallError as error:
        component_id = str(error).rsplit(": ", maxsplit=1)[-1]
        outcomes.append(f"{component_id}: required-failure")
        return InstallStageReport(exit_code=1, outcomes=tuple(outcomes))
    return InstallStageReport(exit_code=0, outcomes=tuple(outcomes))
```

- [ ] **Step 4: Verify installation behavior**

Run:

```bash
rtk uv run --frozen pytest tests/test_install.py tests/test_planning.py tests/test_cli.py -v
rtk uv run --frozen mypy
```

Expected: all focused tests PASS and mypy exits 0.

- [ ] **Step 5: Record the checkpoint**

```bash
rtk jj describe -m "feat: install intentional bootstrap components"
rtk jj new
```

### Task 6: Add safe configuration, backups, and portable dotfiles

**Files:**

- Modify: `src/ballen_config/paths.py`
- Create: `src/ballen_config/configure.py`
- Create: `manifests/configuration.yaml`
- Create: `tests/test_configure.py`
- Move: `.zshrc` to `dotfiles/shell/zshrc`
- Move: `.zprofile` to `dotfiles/shell/zprofile`
- Move: `.p10k.zsh` to `dotfiles/shell/p10k.zsh`
- Move: `.gitconfig` to `dotfiles/vcs/gitconfig`
- Move: `.config/git/ignore` to `dotfiles/vcs/gitignore`
- Move: `.config/jj/config.toml` to `dotfiles/vcs/jj-config.toml`
- Create: `terminal/wave/settings.json`
- Modify: `src/ballen_config/models.py`
- Modify: `src/ballen_config/cli.py`

- [ ] **Step 1: Write adversarial temporary-home tests**

```python
# tests/test_configure.py
import stat
from pathlib import Path

import pytest
from pydantic import ValidationError

from ballen_config.configure import (
    ApplyMethod,
    ConfigEngine,
    ManagedFileSpec,
    run_configure,
)
from ballen_config.runtime import RuntimePaths


def managed(
    source: Path,
    destination: Path,
    method: ApplyMethod,
    mode: int = 0o600,
) -> ManagedFileSpec:
    return ManagedFileSpec(
        id="test-file",
        source=source,
        destination=destination,
        method=method,
        mode=mode,
    )


def test_conflict_is_backed_up_before_atomic_copy(
    fake_home: Path,
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.write_text("new\n")
    destination = fake_home / ".config/tool/settings.json"
    destination.parent.mkdir(parents=True)
    destination.write_text("secret old value\n")
    configurator = ConfigEngine(
        paths=RuntimePaths.from_roots(
            repo_root=tmp_path,
            home=fake_home,
        ),
        timestamp=lambda: "20260725T120000Z",
    )
    assert configurator.apply(managed(source, destination, ApplyMethod.COPY)) == "updated"
    backup = (
        fake_home
        / ".local/state/ballen-config/backups/20260725T120000Z"
        / ".config/tool/settings.json"
    )
    assert backup.read_text() == "secret old value\n"
    assert destination.read_text() == "new\n"
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600


def test_second_apply_is_a_no_op(fake_home: Path, tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("same\n")
    destination = fake_home / ".tool"
    configurator = ConfigEngine(
        paths=RuntimePaths.from_roots(
            repo_root=tmp_path,
            home=fake_home,
        ),
        timestamp=lambda: "fixed",
    )
    assert configurator.apply(managed(source, destination, ApplyMethod.COPY)) == "created"
    assert configurator.apply(managed(source, destination, ApplyMethod.COPY)) == "unchanged"


def test_symlinked_parent_is_rejected(fake_home: Path, tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("value")
    outside = tmp_path / "outside"
    outside.mkdir()
    (fake_home / ".config").symlink_to(outside, target_is_directory=True)
    configurator = ConfigEngine(
        paths=RuntimePaths.from_roots(
            repo_root=tmp_path,
            home=fake_home,
        ),
        timestamp=lambda: "fixed",
    )
    with pytest.raises(ValueError, match="symlinked path component"):
        configurator.apply(
            managed(source, fake_home / ".config/tool/file", ApplyMethod.COPY)
        )


def test_managed_file_mode_is_applied(
    fake_home: Path,
    tmp_path: Path,
) -> None:
    source = tmp_path / "hook.sh"
    source.write_text("#!/bin/zsh\n")
    destination = fake_home / ".local/bin/hook"
    configurator = ConfigEngine(
        paths=RuntimePaths.from_roots(repo_root=tmp_path, home=fake_home),
        timestamp=lambda: "fixed",
    )
    configurator.apply(
        managed(source, destination, ApplyMethod.COPY, mode=0o700)
    )
    assert stat.S_IMODE(destination.stat().st_mode) == 0o700


@pytest.mark.parametrize("mode", [0o644, 0o755, 0])
def test_managed_file_rejects_non_private_modes(
    tmp_path: Path,
    mode: int,
) -> None:
    with pytest.raises(ValidationError, match="mode must be 0600 or 0700"):
        managed(tmp_path / "source", tmp_path / "destination", ApplyMethod.COPY, mode)


def test_run_configure_validates_every_spec_before_writing(
    fake_home: Path,
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.write_text("safe")
    valid_destination = fake_home / ".first"
    invalid_destination = tmp_path / "outside"
    engine = ConfigEngine(
        paths=RuntimePaths.from_roots(repo_root=tmp_path, home=fake_home),
        timestamp=lambda: "fixed",
    )
    with pytest.raises(ValueError, match="path escapes approved root"):
        run_configure(
            specs=(
                managed(source, valid_destination, ApplyMethod.COPY),
                managed(source, invalid_destination, ApplyMethod.COPY),
            ),
            engine=engine,
        )
    assert not valid_destination.exists()
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
rtk uv run --frozen pytest tests/test_configure.py -v
```

Expected: FAIL because configuration modules do not exist.

- [ ] **Step 3: Implement path validation and atomic application**

Define:

```python
# src/ballen_config/configure.py
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
import tomllib
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator
import yaml

from ballen_config.models import ResolvedSetup
from ballen_config.paths import assert_contained, assert_no_symlink_components
from ballen_config.planning import PlanAction
from ballen_config.runtime import RuntimePaths
from ballen_config.runner import Runner
from ballen_config.state import ManagedRecord, StateStore


class ApplyMethod(StrEnum):
    """Supported managed-file methods."""

    COPY = "copy"
    SYMLINK = "symlink"
    RENDER = "render"


class ManagedFileSpec(BaseModel):
    """One repository-owned destination."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    kind: Literal["file"] = "file"
    id: str
    source: Path
    destination: Path
    method: ApplyMethod
    mode: int = 0o600
    component: str | None = None
    renderer_id: str | None = None
    validator_id: str | None = None

    @field_validator("mode", mode="before")
    @classmethod
    def validate_mode(cls, value: int | str) -> int:
        """Allow only private data or private executable modes."""
        normalized = int(value, 8) if isinstance(value, str) else value
        if normalized not in {0o600, 0o700}:
            raise ValueError("mode must be 0600 or 0700")
        return normalized


class ManagedTreeSpec(BaseModel):
    """One repository-owned directory destination."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    kind: Literal["tree"] = "tree"
    id: str
    source: Path
    destination: Path
    component: str | None = None


type ManagedSpec = ManagedFileSpec | ManagedTreeSpec

type Renderer = Callable[[bytes, bytes | None], bytes]
type SourceValidator = Callable[[Path], None]


@dataclass(frozen=True)
class ConfigurationContribution:
    """Specs plus the named functions required to apply them."""

    specs: tuple[ManagedSpec, ...]
    renderers: Mapping[str, Renderer] = field(default_factory=dict)
    validators: Mapping[str, SourceValidator] = field(default_factory=dict)


type ConfigurationSupplier = Callable[
    [ResolvedSetup, RuntimePaths],
    ConfigurationContribution,
]


class ConfigAction(BaseModel):
    """One structural configuration action."""

    model_config = ConfigDict(frozen=True)
    id: str
    destination: str
    action: Literal["created", "updated", "unchanged"]


class ConfigureStageReport(BaseModel):
    """Normalized configure-stage effects."""

    model_config = ConfigDict(frozen=True)
    changed_count: int
    outcomes: tuple[str, ...]


class ConfigurationManifest(BaseModel):
    """Validated core managed-file manifest."""

    model_config = ConfigDict(frozen=True)
    files: tuple[ManagedFileSpec, ...]


class ConfigEngine:
    """Plan and atomically apply repository-owned configuration."""

    def __init__(
        self,
        *,
        paths: RuntimePaths,
        timestamp: Callable[[], str],
        replace: Callable[[Path, Path], None] = os.replace,
        renderers: Mapping[str, Renderer] | None = None,
        validators: Mapping[str, SourceValidator] | None = None,
        state_store: StateStore | None = None,
    ) -> None:
        self.paths = paths
        self.timestamp = timestamp
        self.replace = replace
        self.renderers = dict(renderers or {})
        self.validators = dict(validators or {})
        self.state_store = state_store or StateStore(paths)

    def plan(
        self,
        specs: Sequence[ManagedSpec],
    ) -> tuple[ConfigAction, ...]:
        """Validate all specs and return a deterministic read-only plan."""
        validated = tuple(specs)
        for spec in validated:
            self._validate(spec)
        return tuple(
            ConfigAction(
                id=spec.id,
                destination=str(spec.destination.relative_to(self.paths.home)),
                action=self._action(spec),
            )
            for spec in sorted(validated, key=lambda item: item.id)
        )

    def apply(self, spec: ManagedSpec) -> str:
        """Apply one prevalidated file or tree without following symlinks."""
        self._validate(spec)
        if isinstance(spec, ManagedTreeSpec):
            return self._apply_tree(spec)
        return self._apply_file(spec)

    def _validate(self, spec: ManagedSpec) -> None:
        assert_contained(spec.source, self.paths.repo_root)
        assert_contained(spec.destination, self.paths.home)
        assert_no_symlink_components(spec.destination, stop=self.paths.home)
        source_metadata = os.lstat(spec.source)
        if isinstance(spec, ManagedFileSpec):
            if not stat.S_ISREG(source_metadata.st_mode):
                raise ValueError(f"source is not a regular file: {spec.id}")
            if spec.method is ApplyMethod.RENDER and not spec.renderer_id:
                raise ValueError("render method requires renderer_id")
            if spec.method is not ApplyMethod.RENDER and spec.renderer_id:
                raise ValueError("renderer_id requires render method")
            if spec.renderer_id and spec.renderer_id not in self.renderers:
                raise ValueError(f"unknown renderer: {spec.renderer_id}")
            if spec.validator_id:
                try:
                    validator = self.validators[spec.validator_id]
                except KeyError as error:
                    raise ValueError(
                        f"unknown validator: {spec.validator_id}"
                    ) from error
                validator(spec.source)
            return
        if not stat.S_ISDIR(source_metadata.st_mode):
            raise ValueError(f"source is not a directory: {spec.id}")
        for source_path in spec.source.rglob("*"):
            if stat.S_ISLNK(os.lstat(source_path).st_mode):
                raise ValueError(f"tree source contains symlink: {spec.id}")

    def _desired_file(self, spec: ManagedFileSpec) -> bytes:
        source = spec.source.read_bytes()
        if spec.method is not ApplyMethod.RENDER:
            return source
        existing: bytes | None = None
        try:
            metadata = os.lstat(spec.destination)
        except FileNotFoundError:
            pass
        else:
            if stat.S_ISREG(metadata.st_mode):
                existing = spec.destination.read_bytes()
        assert spec.renderer_id is not None
        return self.renderers[spec.renderer_id](source, existing)

    def _action(self, spec: ManagedSpec) -> Literal["created", "updated", "unchanged"]:
        if isinstance(spec, ManagedTreeSpec):
            desired = self._tree_digest(spec.source)
            try:
                current = self._tree_digest(spec.destination)
            except FileNotFoundError:
                return "created"
            return "unchanged" if current == desired else "updated"
        if spec.method is ApplyMethod.SYMLINK:
            if spec.destination.is_symlink():
                return (
                    "unchanged"
                    if Path(os.readlink(spec.destination)) == spec.source
                    else "updated"
                )
            return "updated" if os.path.lexists(spec.destination) else "created"
        desired = self._desired_file(spec)
        try:
            metadata = os.lstat(spec.destination)
        except FileNotFoundError:
            return "created"
        if stat.S_ISREG(metadata.st_mode) and spec.destination.read_bytes() == desired:
            return "unchanged"
        return "updated"

    def _backup(self, destination: Path) -> Path | None:
        if not os.path.lexists(destination):
            return None
        relative = destination.relative_to(self.paths.home)
        backup = self.paths.backup_root / self.timestamp() / relative
        assert_contained(backup, self.paths.backup_root)
        assert_no_symlink_components(backup, stop=self.paths.backup_root)
        backup.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        os.chmod(backup.parent, 0o700)
        metadata = os.lstat(destination)
        if stat.S_ISLNK(metadata.st_mode):
            os.symlink(os.readlink(destination), backup)
        elif stat.S_ISREG(metadata.st_mode):
            shutil.copyfile(destination, backup, follow_symlinks=False)
            os.chmod(backup, 0o600)
        elif stat.S_ISDIR(metadata.st_mode):
            self.replace(destination, backup)
        else:
            raise ValueError("unsupported destination type")
        return backup

    def _apply_file(self, spec: ManagedFileSpec) -> str:
        action = self._action(spec)
        if action == "unchanged":
            return action
        spec.destination.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        backup = self._backup(spec.destination)
        temporary = spec.destination.with_name(
            f".{spec.destination.name}.ballen-config"
        )
        try:
            if os.path.lexists(temporary):
                raise ValueError(f"temporary destination exists: {temporary}")
            if spec.method is ApplyMethod.SYMLINK:
                os.symlink(spec.source, temporary)
                digest = hashlib.sha256(str(spec.source).encode()).hexdigest()
            else:
                desired = self._desired_file(spec)
                descriptor = os.open(
                    temporary,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    spec.mode,
                )
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(desired)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.chmod(temporary, spec.mode)
                digest = hashlib.sha256(desired).hexdigest()
            self.replace(temporary, spec.destination)
        except Exception:
            temporary.unlink(missing_ok=True)
            if backup is not None and not os.path.lexists(spec.destination):
                self.replace(backup, spec.destination)
            raise
        self.state_store.record_managed(
            ManagedRecord(
                resource_id=spec.id,
                source_digest=hashlib.sha256(spec.source.read_bytes()).hexdigest(),
                destination_digest=digest,
                destination=str(spec.destination.relative_to(self.paths.home)),
            )
        )
        return action

    def _tree_digest(self, root: Path) -> str:
        metadata = os.lstat(root)
        if not stat.S_ISDIR(metadata.st_mode):
            raise ValueError(f"tree destination is not a directory: {root}")
        digest = hashlib.sha256()
        for item in sorted(root.rglob("*")):
            item_metadata = os.lstat(item)
            if stat.S_ISLNK(item_metadata.st_mode):
                raise ValueError(f"tree contains symlink: {item}")
            relative = str(item.relative_to(root)).encode()
            digest.update(relative)
            digest.update(b"x" if item_metadata.st_mode & 0o111 else b"-")
            if stat.S_ISREG(item_metadata.st_mode):
                digest.update(item.read_bytes())
        return digest.hexdigest()

    def _apply_tree(self, spec: ManagedTreeSpec) -> str:
        action = self._action(spec)
        if action == "unchanged":
            return action
        state = self.state_store.load()
        if os.path.lexists(spec.destination) and spec.id not in state.managed:
            raise ValueError(f"unmanaged tree collision: {spec.id}")
        spec.destination.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        stage = Path(tempfile.mkdtemp(
            prefix=f".{spec.destination.name}.",
            dir=spec.destination.parent,
        ))
        shutil.rmtree(stage)
        shutil.copytree(spec.source, stage, symlinks=False)
        for item in (stage, *stage.rglob("*")):
            metadata = os.lstat(item)
            if stat.S_ISDIR(metadata.st_mode):
                os.chmod(item, 0o700)
            elif stat.S_ISREG(metadata.st_mode):
                os.chmod(item, 0o700 if metadata.st_mode & 0o111 else 0o600)
        backup = self._backup(spec.destination)
        try:
            self.replace(stage, spec.destination)
        except Exception:
            shutil.rmtree(stage, ignore_errors=True)
            if backup is not None and not spec.destination.exists():
                self.replace(backup, spec.destination)
            raise
        digest = self._tree_digest(spec.destination)
        self.state_store.record_managed(
            ManagedRecord(
                resource_id=spec.id,
                source_digest=self._tree_digest(spec.source),
                destination_digest=digest,
                destination=str(spec.destination.relative_to(self.paths.home)),
            )
        )
        return action


def core_validators(runner: Runner) -> dict[str, SourceValidator]:
    """Return secret-suppressing validators for reviewed core formats."""

    def json_file(path: Path) -> None:
        json.loads(path.read_text())

    def toml_file(path: Path) -> None:
        tomllib.loads(path.read_text())

    def command(argv: tuple[str, ...]) -> SourceValidator:
        def validate(path: Path) -> None:
            result = runner.run((*argv, str(path)))
            if result["returncode"] != 0:
                raise ValueError(f"source validation failed: {path.name}")
        return validate

    return {
        "json": json_file,
        "toml": toml_file,
        "zsh": command(("zsh", "-n")),
        "git-config": command(("git", "config", "--file")),
    }


def configuration_specs(
    repo_root: Path,
    paths: RuntimePaths,
    resolved: ResolvedSetup,
) -> tuple[ManagedSpec, ...]:
    """Load core specs and resolve paths without applying them."""
    manifest_path = repo_root / "manifests/configuration.yaml"
    manifest = ConfigurationManifest.model_validate(
        yaml.safe_load(manifest_path.read_text())
    )
    return tuple(
        spec.model_copy(
            update={
                "source": repo_root / spec.source,
                "destination": paths.home / spec.destination,
            }
        )
        for spec in manifest.files
        if spec.component is None or spec.component not in resolved.skipped
    )


def run_configure(
    *,
    specs: Sequence[ManagedSpec],
    engine: ConfigEngine,
) -> ConfigureStageReport:
    """Validate every spec before applying any configuration."""
    plan = engine.plan(specs)
    outcomes = tuple(
        f"{action.id}: {engine.apply(spec)}"
        for action, spec in zip(plan, sorted(specs, key=lambda item: item.id), strict=True)
    )
    return ConfigureStageReport(
        changed_count=sum(not item.endswith(": unchanged") for item in outcomes),
        outcomes=outcomes,
    )


def core_configuration(
    resolved: ResolvedSetup,
    paths: RuntimePaths,
) -> ConfigurationContribution:
    """Build the core contribution consumed by every CLI stage."""
    return ConfigurationContribution(
        specs=configuration_specs(paths.repo_root, paths, resolved)
    )


def merge_configuration_contributions(
    contributions: Sequence[ConfigurationContribution],
) -> ConfigurationContribution:
    """Merge ordered contributions while rejecting ambiguous identifiers."""
    specs: list[ManagedSpec] = []
    renderers: dict[str, Renderer] = {}
    validators: dict[str, SourceValidator] = {}
    spec_ids: set[str] = set()
    for contribution in contributions:
        for spec in contribution.specs:
            if spec.id in spec_ids:
                raise ValueError(f"duplicate managed spec: {spec.id}")
            spec_ids.add(spec.id)
            specs.append(spec)
        for name, renderer in contribution.renderers.items():
            if name in renderers:
                raise ValueError(f"duplicate renderer: {name}")
            renderers[name] = renderer
        for name, validator in contribution.validators.items():
            if name in validators:
                raise ValueError(f"duplicate validator: {name}")
            validators[name] = validator
    return ConfigurationContribution(
        specs=tuple(specs),
        renderers=renderers,
        validators=validators,
    )


class ConfigurationPlanContributor:
    """Adapt a prevalidated configuration plan to shared plan actions."""

    def __init__(
        self,
        engine: ConfigEngine,
        specs: Sequence[ManagedSpec],
    ) -> None:
        self.engine = engine
        self.specs = tuple(specs)

    def actions(self, resolved: ResolvedSetup) -> tuple[PlanAction, ...]:
        """Return structural actions; resolved was applied by suppliers."""
        del resolved
        configure_actions = tuple(
            PlanAction(
                component_id=action.id,
                category="configure",
                action=action.action,
                owner="ballen-config",
                path=action.destination,
            )
            for action in self.engine.plan(self.specs)
        )
        diagnostics = tuple(
            PlanAction(
                component_id=f"{spec.id}.brittle-path",
                category="diagnostic",
                action="replace-brittle-path",
                owner="ballen-config",
                path=str(
                    spec.source.relative_to(self.engine.paths.repo_root)
                ),
                required=False,
            )
            for spec in sorted(self.specs, key=lambda item: item.id)
            if spec.source.is_file()
            and b"/Users/" in spec.source.read_bytes()
        )
        return configure_actions + diagnostics
```

- [ ] **Step 4: Move the existing dotfiles and add portable sources**

Run:

```bash
rtk mkdir -p dotfiles/shell dotfiles/vcs terminal/wave
rtk mv .zshrc dotfiles/shell/zshrc
rtk mv .zprofile dotfiles/shell/zprofile
rtk mv .p10k.zsh dotfiles/shell/p10k.zsh
rtk mv .gitconfig dotfiles/vcs/gitconfig
rtk mv .config/git/ignore dotfiles/vcs/gitignore
rtk mv .config/jj/config.toml dotfiles/vcs/jj-config.toml
```

Replace `dotfiles/shell/zprofile` Homebrew initialization with:

```zsh
if [[ -x /opt/homebrew/bin/brew ]]; then
  eval "$(/opt/homebrew/bin/brew shellenv)"
elif [[ -x /usr/local/bin/brew ]]; then
  eval "$(/usr/local/bin/brew shellenv)"
fi

export PATH="$HOME/.local/bin:$PATH"
```

Create:

```json
// terminal/wave/settings.json
{
  "term:fontfamily": "MesloLGS Nerd Font Mono",
  "term:fontsize": 14
}
```

Create:

```yaml
# manifests/configuration.yaml
files:
  - {id: zshrc, source: dotfiles/shell/zshrc, destination: .zshrc, method: symlink, mode: "0600", validator_id: zsh}
  - {id: zprofile, source: dotfiles/shell/zprofile, destination: .zprofile, method: symlink, mode: "0600", validator_id: zsh}
  - {id: p10k, source: dotfiles/shell/p10k.zsh, destination: .p10k.zsh, method: symlink, mode: "0600", validator_id: zsh}
  - {id: gitconfig, source: dotfiles/vcs/gitconfig, destination: .gitconfig, method: symlink, mode: "0600", validator_id: git-config}
  - {id: gitignore, source: dotfiles/vcs/gitignore, destination: .config/git/ignore, method: symlink, mode: "0600"}
  - {id: jj-config, source: dotfiles/vcs/jj-config.toml, destination: .config/jj/config.toml, method: symlink, mode: "0600", validator_id: toml}
  - {id: wave-settings, source: terminal/wave/settings.json, destination: .config/waveterm/settings.json, method: copy, mode: "0600", component: wave, validator_id: json}
```

- [ ] **Step 5: Verify convergence and safety**

Run:

```bash
rtk uv run --frozen pytest tests/test_configure.py tests/test_manifests.py -v
rtk uv run --frozen ruff check src tests
rtk uv run --frozen mypy
```

Expected: all focused tests PASS; Ruff and mypy exit 0.

- [ ] **Step 6: Record the checkpoint**

```bash
rtk jj describe -m "feat: manage portable configuration safely"
rtk jj new
```

### Task 7: Add non-mutating doctor checks

**Files:**

- Create: `src/ballen_config/doctor.py`
- Create: `tests/test_doctor.py`
- Modify: `src/ballen_config/cli.py`

- [ ] **Step 1: Write failing normalized-diagnostic tests**

```python
# tests/test_doctor.py
import os
from pathlib import Path

from ballen_config.doctor import (
    CheckSeverity,
    Doctor,
    FindingStatus,
    run_doctor,
)
from ballen_config.models import Component, Manager
from ballen_config.runner import CommandResult


class FakeRunner:
    def __init__(self, results: dict[tuple[str, ...], CommandResult]) -> None:
        self.results = results

    def run(self, command: tuple[str, ...]) -> CommandResult:
        return self.results.get(
            command,
            {"returncode": 127, "stdout": "", "stderr": ""},
        )


def test_auth_output_is_never_returned(fake_home: Path) -> None:
    secret = "account@example.com token scopes api"  # pragma: allowlist secret
    runner = FakeRunner(
        {
            ("glab", "auth", "status"): {
                "returncode": 0,
                "stdout": secret,
                "stderr": "",
            }
        }
    )
    report = run_doctor(Doctor(runner, fake_home).authentication_checks())
    assert report.finding("gitlab-auth").message == "ready"
    assert secret not in report.render()


def test_skip_is_informational_not_missing(fake_home: Path) -> None:
    report = run_doctor(
        Doctor(FakeRunner({}), fake_home).skipped_checks(("wave",))
    )
    finding = report.finding("wave")
    assert finding.status is FindingStatus.SKIPPED
    assert finding.severity is CheckSeverity.INFO
    assert report.exit_code == 0


def test_aws_readiness_runs_only_for_work(fake_home: Path) -> None:
    default = Doctor(
        FakeRunner({}),
        fake_home,
        profiles=("default",),
    ).authentication_checks()
    work = Doctor(
        FakeRunner({}),
        fake_home,
        profiles=("default", "work"),
    ).authentication_checks()
    assert "aws-auth" not in {finding.id for finding in default}
    assert "aws-auth" in {finding.id for finding in work}


def test_core_manual_checks_are_limited_to_cross_cutting_actions(
    fake_home: Path,
) -> None:
    checks = Doctor(
        FakeRunner({}),
        fake_home,
        profiles=("default", "work"),
    ).manual_checks()
    assert {finding.id for finding in checks} == {
        "ssh-transfer",
        "it-managed-applications",
    }
    rendered = run_doctor(checks).render().lower()
    assert "notion" not in rendered
    assert "browser" not in rendered
    assert "cursor" not in rendered
    assert "claude" not in rendered
    assert "codex" not in rendered


def test_required_component_failure_sets_exit_one(fake_home: Path) -> None:
    component = Component(
        id="gh",
        manager=Manager.BREW_FORMULA,
        package="gh",
    )
    report = run_doctor(
        Doctor(
            FakeRunner(
                {
                    ("brew", "list", "--formula", "gh"): {
                        "returncode": 1,
                        "stdout": "secret",
                        "stderr": "token",
                    }
                }
            ),
            fake_home,
        ).component_checks((component,))
    )
    assert report.finding("gh").status is FindingStatus.MISSING
    assert report.exit_code == 1
    assert "secret" not in report.render()
    assert "token" not in report.render()
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
rtk uv run --frozen pytest tests/test_doctor.py -v
```

Expected: FAIL because `doctor.py` does not exist.

- [ ] **Step 3: Implement normalized checks and exit codes**

```python
# src/ballen_config/doctor.py
from collections.abc import Callable, Sequence
from enum import StrEnum
import os
from pathlib import Path
import stat

from pydantic import BaseModel, ConfigDict

from ballen_config.configure import ConfigEngine, ManagedSpec
from ballen_config.models import Component, Manager, ResolvedSetup
from ballen_config.runtime import RuntimePaths
from ballen_config.runner import Runner


class CheckSeverity(StrEnum):
    """Doctor result severity."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class FindingStatus(StrEnum):
    """Normalized resource state."""

    READY = "ready"
    MISSING = "missing"
    DRIFT = "drift"
    SKIPPED = "skipped"
    MANUAL = "manual"
    UNAVAILABLE = "unavailable"


class DoctorFinding(BaseModel):
    """One normalized diagnostic."""

    model_config = ConfigDict(frozen=True)
    id: str
    status: FindingStatus
    severity: CheckSeverity
    message: str


type DoctorCheck = DoctorFinding


class DoctorReport(BaseModel):
    """Deterministic doctor findings and exit semantics."""

    model_config = ConfigDict(frozen=True)
    findings: tuple[DoctorFinding, ...]

    @property
    def exit_code(self) -> int:
        """Return one only when a required check failed."""
        return int(
            any(
                finding.severity is CheckSeverity.ERROR
                for finding in self.findings
            )
        )

    def finding(self, finding_id: str) -> DoctorFinding:
        """Return a finding by stable ID."""
        return next(
            finding
            for finding in self.findings
            if finding.id == finding_id
        )

    def render(self) -> str:
        """Render normalized fields without native command output."""
        return "\n".join(
            f"{item.id}: {item.status} - {item.message}"
            for item in self.findings
        )


def run_doctor(checks: Sequence[DoctorCheck]) -> DoctorReport:
    """Package already-normalized, non-mutating checks deterministically."""
    return DoctorReport(
        findings=tuple(sorted(checks, key=lambda item: item.id))
    )


class Doctor:
    """Run non-mutating checks without returning captured command output."""

    def __init__(
        self,
        runner: Runner,
        home: Path,
        profiles: tuple[str, ...] = ("default",),
        path_exists: Callable[[Path], bool] = Path.exists,
    ) -> None:
        self.runner = runner
        self.home = home
        self.profiles = profiles
        self.path_exists = path_exists

    def component_checks(
        self,
        components: Sequence[Component],
    ) -> tuple[DoctorCheck, ...]:
        """Check resolved packages without exposing native output."""
        checks: list[DoctorFinding] = []
        for component in components:
            if component.manager in {
                Manager.BREW_FORMULA,
                Manager.BREW_CASK,
            }:
                type_flag = (
                    "--formula"
                    if component.manager is Manager.BREW_FORMULA
                    else "--cask"
                )
                result = self.runner.run(
                    ("brew", "list", type_flag, component.package)
                )
                present = result["returncode"] == 0 or any(
                    self.path_exists(Path(path))
                    for path in component.application_paths
                )
            else:
                assert component.destination is not None
                destination = self.home / component.destination
                present = (
                    not destination.is_symlink()
                    and (destination / ".git").is_dir()
                )
            checks.append(
                DoctorFinding(
                    id=component.id,
                    status=(
                        FindingStatus.READY
                        if present
                        else FindingStatus.MISSING
                    ),
                    severity=(
                        CheckSeverity.INFO
                        if present
                        else (
                            CheckSeverity.ERROR
                            if component.required
                            else CheckSeverity.WARNING
                        )
                    ),
                    message="ready" if present else "not installed",
                )
            )
        return tuple(checks)

    def homebrew_check(self) -> DoctorCheck:
        """Check Homebrew without returning its machine-specific prefix."""
        result = self.runner.run(("brew", "--prefix"))
        ready = result["returncode"] == 0
        return DoctorFinding(
            id="homebrew",
            status=FindingStatus.READY if ready else FindingStatus.MISSING,
            severity=CheckSeverity.INFO if ready else CheckSeverity.ERROR,
            message="ready" if ready else "not installed",
        )

    def managed_checks(
        self,
        engine: ConfigEngine,
        specs: Sequence[ManagedSpec],
    ) -> tuple[DoctorCheck, ...]:
        """Convert read-only configuration actions into drift findings."""
        return tuple(
            DoctorFinding(
                id=f"managed-{action.id}",
                status=(
                    FindingStatus.READY
                    if action.action == "unchanged"
                    else FindingStatus.DRIFT
                ),
                severity=(
                    CheckSeverity.INFO
                    if action.action == "unchanged"
                    else CheckSeverity.WARNING
                ),
                message=(
                    "ready"
                    if action.action == "unchanged"
                    else "configuration differs"
                ),
            )
            for action in engine.plan(specs)
        )

    def authentication_checks(self) -> tuple[DoctorCheck, ...]:
        checks: list[DoctorFinding] = []
        commands: list[tuple[str, tuple[str, ...]]] = [
            ("github-auth", ("gh", "auth", "status")),
            ("gitlab-auth", ("glab", "auth", "status")),
        ]
        if "work" in self.profiles:
            commands.append(
                ("aws-auth", ("aws", "sts", "get-caller-identity"))
            )
        for name, command in commands:
            result = self.runner.run(command)
            ready = result["returncode"] == 0
            checks.append(
                DoctorFinding(
                    id=name,
                    status=(
                        FindingStatus.READY
                        if ready
                        else FindingStatus.MANUAL
                    ),
                    severity=(
                        CheckSeverity.INFO
                        if ready
                        else CheckSeverity.WARNING
                    ),
                    message=(
                        "ready"
                        if ready
                        else "not authenticated"
                    ),
                )
            )
        return tuple(checks)

    def skipped_checks(self, skipped: tuple[str, ...]) -> tuple[DoctorCheck, ...]:
        return tuple(
            DoctorFinding(
                id=name,
                status=FindingStatus.SKIPPED,
                severity=CheckSeverity.INFO,
                message="intentionally skipped",
            )
            for name in skipped
        )

    def manual_checks(self) -> tuple[DoctorCheck, ...]:
        """Return only core-owned SSH and IT-managed manual actions."""
        try:
            ssh_mode = stat.S_IMODE(os.lstat(self.home / ".ssh").st_mode)
        except FileNotFoundError:
            ssh_ready = False
        else:
            ssh_ready = ssh_mode == 0o700
        return (
            DoctorFinding(
                id="ssh-transfer",
                status=(
                    FindingStatus.READY
                    if ssh_ready
                    else FindingStatus.MANUAL
                ),
                severity=(
                    CheckSeverity.INFO
                    if ssh_ready
                    else CheckSeverity.WARNING
                ),
                message=(
                    "directory permissions ready"
                    if ssh_ready
                    else "follow secure SSH transfer guide"
                ),
            ),
            DoctorFinding(
                id="it-managed-applications",
                status=FindingStatus.MANUAL,
                severity=CheckSeverity.INFO,
                message="complete the IT-managed application checklist",
            ),
        )


type DoctorCheckSupplier = Callable[
    [ResolvedSetup, RuntimePaths, Runner],
    Sequence[DoctorCheck],
]


def core_doctor_checks(
    resolved: ResolvedSetup,
    paths: RuntimePaths,
    runner: Runner,
    *,
    engine: ConfigEngine,
    specs: Sequence[ManagedSpec],
) -> tuple[DoctorCheck, ...]:
    """Build every production core check without mutation."""
    doctor = Doctor(runner, paths.home, profiles=resolved.profiles)
    return (
        doctor.homebrew_check(),
        *doctor.component_checks(resolved.components),
        *doctor.managed_checks(engine, specs),
        *doctor.authentication_checks(),
        *doctor.manual_checks(),
        *doctor.skipped_checks(resolved.skipped),
    )
```

- [ ] **Step 4: Prove doctor is non-mutating**

Add this exact snapshot helper and test:

```python
def home_snapshot(home: Path) -> tuple[tuple[str, int, bytes], ...]:
    return tuple(
        (
            str(path.relative_to(home)),
            os.lstat(path).st_mode,
            path.read_bytes() if path.is_file() and not path.is_symlink() else b"",
        )
        for path in sorted(home.rglob("*"))
    )


def test_doctor_does_not_mutate_home(fake_home: Path) -> None:
    (fake_home / ".ssh").mkdir(mode=0o700)
    before = home_snapshot(fake_home)
    doctor = Doctor(
        FakeRunner(
            {
                ("gh", "auth", "status"): {
                    "returncode": 1,
                    "stdout": "token-like stdout",
                    "stderr": "token-like stderr",
                }
            }
        ),
        fake_home,
    )
    report = run_doctor(
        (*doctor.authentication_checks(), *doctor.manual_checks())
    )
    assert home_snapshot(fake_home) == before
    assert "token-like" not in report.render()
```

- [ ] **Step 5: Wire the complete production dispatcher**

Create `src/ballen_config/__main__.py`:

```python
from ballen_config.cli import main

raise SystemExit(main())
```

Add these stable return models to `cli.py`:

```python
class StageReport(BaseModel):
    """Normalized effects from one CLI invocation."""

    model_config = ConfigDict(frozen=True)
    changed_count: int = 0
    outcomes: tuple[str, ...] = ()


class RunResult(BaseModel):
    """Exit status plus a secret-free programmatic report."""

    model_config = ConfigDict(frozen=True)
    exit_code: int
    report: StageReport
```

Refactor `planning.build_plan()` so its existing body delegates to this
resolved-setup entry point:

```python
def build_resolved_plan(
    resolved: ResolvedSetup,
    *,
    profile: str,
    inspector: Inspector,
    contributors: Sequence[PlanContributor] = (),
) -> SetupPlan:
    """Build a deterministic plan from one already-resolved setup."""
    install_actions = tuple(
        PlanAction(
            component_id=component.id,
            category="install",
            action=(
                "present"
                if inspector.state(component.id) is ComponentState.PRESENT
                else "install"
            ),
            owner="bootstrap",
            required=component.required,
            large=component.large,
        )
        for component in resolved.components
    )
    contributed_actions = tuple(
        sorted(
            (
                action
                for contributor in contributors
                for action in contributor.actions(resolved)
            ),
            key=lambda item: (
                item.category,
                item.component_id,
                item.path or "",
            ),
        )
    )
    actions = install_actions + contributed_actions
    action_ids = [action.component_id for action in actions]
    if len(action_ids) != len(set(action_ids)):
        raise ValueError("duplicate PlanAction.component_id")
    return SetupPlan(
        profile=profile,
        profiles=resolved.profiles,
        skipped=resolved.skipped,
        actions=actions,
        expected_prompts=("confirm package and configuration changes",),
    )
```

Replace `src/ballen_config/cli.py` with the completed dispatcher below,
retaining the Task 3 `parse_args()` definition unchanged:

```python
import argparse
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
import os
from pathlib import Path
import sys

from pydantic import BaseModel, ConfigDict, ValidationError

from ballen_config.configure import (
    ConfigEngine,
    ConfigurationPlanContributor,
    ConfigurationSupplier,
    core_configuration,
    core_validators,
    merge_configuration_contributions,
    run_configure,
)
from ballen_config.doctor import (
    DoctorCheckSupplier,
    core_doctor_checks,
    run_doctor,
)
from ballen_config.install import (
    Downloader,
    HttpsDownloader,
    InstallActionSupplier,
    run_install,
)
from ballen_config.manifests import ManifestRepository
from ballen_config.models import Component, Manager, ResolutionRequest
from ballen_config.planning import (
    ComponentState,
    CoreManualContributor,
    Inspector,
    PlanContributor,
    build_resolved_plan,
    format_plan,
)
from ballen_config.runner import CommandRunner, SubprocessRunner
from ballen_config.runtime import RuntimePaths
from ballen_config.state import StateStore


STAGES = ("all", "prepare", "plan", "install", "configure", "doctor")


@dataclass(frozen=True)
class CliOptions:
    """Parsed bootstrap options."""

    stage: str
    request: ResolutionRequest


class StageReport(BaseModel):
    """Normalized effects from one CLI invocation."""

    model_config = ConfigDict(frozen=True)
    changed_count: int = 0
    outcomes: tuple[str, ...] = ()


class RunResult(BaseModel):
    """Exit status plus a secret-free programmatic report."""

    model_config = ConfigDict(frozen=True)
    exit_code: int
    report: StageReport


class ResolvedInspector:
    """Read-only installation inspector for resolved components."""

    def __init__(
        self,
        runner: CommandRunner,
        components: Sequence[Component],
        home: Path,
    ) -> None:
        self.runner = runner
        self.components = {item.id: item for item in components}
        self.home = home

    def state(self, component_id: str) -> ComponentState:
        component = self.components[component_id]
        if any(Path(path).exists() for path in component.application_paths):
            return ComponentState.PRESENT
        if component.manager in {Manager.BREW_FORMULA, Manager.BREW_CASK}:
            flag = (
                "--formula"
                if component.manager is Manager.BREW_FORMULA
                else "--cask"
            )
            result = self.runner.run(
                ("brew", "list", flag, component.package)
            )
            return (
                ComponentState.PRESENT
                if result["returncode"] == 0
                else ComponentState.MISSING
            )
        assert component.destination is not None
        destination = self.home / component.destination
        return (
            ComponentState.PRESENT
            if not destination.is_symlink()
            and (destination / ".git").is_dir()
            else ComponentState.MISSING
        )


def parse_args(arguments: Sequence[str] | None = None) -> CliOptions:
    parser = argparse.ArgumentParser(prog="bootstrap")
    parser.add_argument("stage", nargs="?", choices=STAGES, default="all")
    parser.add_argument("--profile", default="default")
    parser.add_argument("--include", action="append", default=[])
    parser.add_argument("--skip", action="append", default=[])
    namespace = parser.parse_args(arguments)
    return CliOptions(
        stage=namespace.stage,
        request=ResolutionRequest(
            profile=namespace.profile,
            includes=tuple(namespace.include),
            skips=tuple(namespace.skip),
        ),
    )


def run(
    arguments: Sequence[str],
    *,
    repo_root: Path,
    home: Path,
    runner: CommandRunner,
    downloader: Downloader,
    confirm: Callable[[str], bool],
    output: Callable[[str], None],
    timestamp: Callable[[], str],
    install_action_suppliers: Sequence[InstallActionSupplier] = (),
    configuration_suppliers: Sequence[ConfigurationSupplier] = (),
    doctor_check_suppliers: Sequence[DoctorCheckSupplier] = (),
    plan_contributors: Sequence[PlanContributor] = (),
) -> RunResult:
    """Execute one validated stage with all side effects injected."""
    try:
        options = parse_args(arguments)
        if options.stage == "prepare":
            return RunResult(exit_code=2, report=StageReport())
        paths = RuntimePaths.from_roots(repo_root=repo_root, home=home)
        repository = ManifestRepository.load(repo_root / "manifests")
        resolved = repository.resolve(options.request)
        supplied_configuration = tuple(
            supplier(resolved, paths)
            for supplier in configuration_suppliers
        )
        configuration = merge_configuration_contributions(
            (core_configuration(resolved, paths), *supplied_configuration)
        )
        validators = core_validators(runner)
        for name, validator in configuration.validators.items():
            if name in validators:
                raise ValueError(f"duplicate validator: {name}")
            validators[name] = validator
        engine = ConfigEngine(
            paths=paths,
            timestamp=timestamp,
            renderers=configuration.renderers,
            validators=validators,
        )
        inspector: Inspector = ResolvedInspector(
            runner,
            resolved.components,
            paths.home,
        )
        contributors = (
            ConfigurationPlanContributor(engine, configuration.specs),
            *plan_contributors,
        )
        plan = build_resolved_plan(
            resolved,
            profile=options.request.profile,
            inspector=inspector,
            contributors=contributors,
        )
    except (SystemExit, ValidationError, ValueError):
        return RunResult(
            exit_code=2,
            report=StageReport(outcomes=("invalid configuration",)),
        )

    output(format_plan(plan))
    if options.stage == "plan":
        return RunResult(exit_code=0, report=StageReport())

    action_suppliers = tuple(
        action
        for supplier in install_action_suppliers
        for action in supplier(resolved, paths, runner)
    )

    def install_stage() -> RunResult:
        report = run_install(
            components=resolved.components,
            actions=action_suppliers,
            runner=runner,
            paths=paths,
            state_store=StateStore(paths),
            downloader=downloader,
        )
        return RunResult(
            exit_code=report.exit_code,
            report=StageReport(outcomes=report.outcomes),
        )

    def configure_stage() -> RunResult:
        report = run_configure(specs=configuration.specs, engine=engine)
        return RunResult(
            exit_code=0,
            report=StageReport(
                changed_count=report.changed_count,
                outcomes=report.outcomes,
            ),
        )

    def doctor_stage() -> RunResult:
        checks = list(
            core_doctor_checks(
                resolved,
                paths,
                runner,
                engine=engine,
                specs=configuration.specs,
            )
        )
        for supplier in doctor_check_suppliers:
            checks.extend(supplier(resolved, paths, runner))
        finding_ids = [check.id for check in checks]
        if len(finding_ids) != len(set(finding_ids)):
            return RunResult(
                exit_code=2,
                report=StageReport(
                    outcomes=("duplicate doctor finding IDs",)
                ),
            )
        report = run_doctor(checks)
        output(report.render())
        return RunResult(
            exit_code=report.exit_code,
            report=StageReport(
                outcomes=tuple(
                    f"{item.id}: {item.status}" for item in report.findings
                )
            ),
        )

    if options.stage == "doctor":
        return doctor_stage()
    if not confirm("Apply the displayed bootstrap changes?"):
        return RunResult(
            exit_code=0,
            report=StageReport(outcomes=("declined",)),
        )
    if options.stage == "install":
        return install_stage()
    if options.stage == "configure":
        return configure_stage()

    installed = install_stage()
    if installed.exit_code != 0:
        return installed
    configured = configure_stage()
    diagnosed = doctor_stage()
    return RunResult(
        exit_code=diagnosed.exit_code,
        report=StageReport(
            changed_count=configured.report.changed_count,
            outcomes=(
                *installed.report.outcomes,
                *configured.report.outcomes,
                *diagnosed.report.outcomes,
            ),
        ),
    )


def main(arguments: Sequence[str] | None = None) -> int:
    """Construct production dependencies and return the process exit code."""
    previous_umask = os.umask(0o077)
    try:
        result = run(
            tuple(sys.argv[1:] if arguments is None else arguments),
            repo_root=Path(__file__).resolve().parents[2],
            home=Path.home(),
            runner=SubprocessRunner(),
            downloader=HttpsDownloader(),
            confirm=lambda prompt: input(f"{prompt} [y/N] ").lower() == "y",
            output=print,
            timestamp=lambda: datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
            plan_contributors=(CoreManualContributor(),),
        )
        for outcome in result.report.outcomes:
            print(outcome)
        return result.exit_code
    finally:
        os.umask(previous_umask)
```

Append these dispatcher tests:

```python
import os
from pathlib import Path
import stat

import pytest

from ballen_config.cli import RunResult, StageReport, main, run
from ballen_config.configure import ConfigureStageReport
from ballen_config.doctor import CheckSeverity, DoctorFinding, FindingStatus
from ballen_config.install import InstallStageReport
from ballen_config.runner import CommandResult


class FakeRunner:
    def __init__(self, results: list[CommandResult]) -> None:
        self.results = iter(results)
        self.commands: list[tuple[str, ...]] = []

    def run(self, command: tuple[str, ...]) -> CommandResult:
        self.commands.append(command)
        return next(
            self.results,
            {"returncode": 0, "stdout": "", "stderr": ""},
        )


class FakeDownloader:
    def __init__(self, payloads: dict[str, bytes] | None = None) -> None:
        self.payloads = payloads or {}

    def download(
        self,
        *,
        url: str,
        destination: Path,
        maximum_bytes: int,
    ) -> None:
        raise AssertionError("no download expected")


@pytest.mark.parametrize("stage", ["install", "configure", "all"])
def test_declined_mutating_stage_calls_no_executor(
    stage: str,
    repo_root: Path,
    fake_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        "ballen_config.cli.run_install",
        lambda **kwargs: calls.append("install"),
    )
    monkeypatch.setattr(
        "ballen_config.cli.run_configure",
        lambda **kwargs: calls.append("configure"),
    )
    result = run(
        (stage,),
        repo_root=repo_root,
        home=fake_home,
        runner=FakeRunner([]),
        downloader=FakeDownloader({}),
        confirm=lambda _: False,
        output=lambda _: None,
        timestamp=lambda: "fixed",
    )
    assert result.exit_code == 0
    assert result.report.outcomes == ("declined",)
    assert calls == []


def test_all_orders_stages_and_short_circuits_required_install(
    repo_root: Path,
    fake_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        "ballen_config.cli.run_install",
        lambda **kwargs: (
            calls.append("install")
            or InstallStageReport(exit_code=1, outcomes=("gh: required-failure",))
        ),
    )
    monkeypatch.setattr(
        "ballen_config.cli.run_configure",
        lambda **kwargs: (
            calls.append("configure")
            or ConfigureStageReport(changed_count=1, outcomes=("zshrc: created",))
        ),
    )
    monkeypatch.setattr(
        "ballen_config.cli.core_doctor_checks",
        lambda *args, **kwargs: calls.append("doctor") or (),
    )
    result = run(
        ("all",),
        repo_root=repo_root,
        home=fake_home,
        runner=FakeRunner([]),
        downloader=FakeDownloader({}),
        confirm=lambda _: True,
        output=lambda _: None,
        timestamp=lambda: "fixed",
    )
    assert result.exit_code == 1
    assert calls == ["install"]


def test_all_runs_install_configure_doctor_in_order(
    repo_root: Path,
    fake_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        "ballen_config.cli.run_install",
        lambda **kwargs: (
            calls.append("install")
            or InstallStageReport(exit_code=0, outcomes=("gh: present",))
        ),
    )
    monkeypatch.setattr(
        "ballen_config.cli.run_configure",
        lambda **kwargs: (
            calls.append("configure")
            or ConfigureStageReport(
                changed_count=0,
                outcomes=("zshrc: unchanged",),
            )
        ),
    )
    monkeypatch.setattr(
        "ballen_config.cli.core_doctor_checks",
        lambda *args, **kwargs: calls.append("doctor") or (),
    )
    result = run(
        ("all",),
        repo_root=repo_root,
        home=fake_home,
        runner=FakeRunner([]),
        downloader=FakeDownloader(),
        confirm=lambda _: True,
        output=lambda _: None,
        timestamp=lambda: "fixed",
    )
    assert result.exit_code == 0
    assert calls == ["install", "configure", "doctor"]


def test_doctor_exit_is_independent_of_mutating_stages(
    repo_root: Path,
    fake_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        "ballen_config.cli.run_install",
        lambda **kwargs: calls.append("install"),
    )
    monkeypatch.setattr(
        "ballen_config.cli.run_configure",
        lambda **kwargs: calls.append("configure"),
    )
    monkeypatch.setattr(
        "ballen_config.cli.core_doctor_checks",
        lambda *args, **kwargs: (
            DoctorFinding(
                id="required-tool",
                status=FindingStatus.MISSING,
                severity=CheckSeverity.ERROR,
                message="missing",
            ),
        ),
    )
    result = run(
        ("doctor",),
        repo_root=repo_root,
        home=fake_home,
        runner=FakeRunner([]),
        downloader=FakeDownloader(),
        confirm=lambda _: pytest.fail("doctor must not confirm"),
        output=lambda _: None,
        timestamp=lambda: "fixed",
    )
    assert result.exit_code == 1
    assert calls == []


def test_invalid_arguments_have_no_commands_or_files(
    repo_root: Path,
    fake_home: Path,
) -> None:
    runner = FakeRunner([])
    before = tuple(fake_home.rglob("*"))
    result = run(
        ("plan", "--profile", "unknown"),
        repo_root=repo_root,
        home=fake_home,
        runner=runner,
        downloader=FakeDownloader({}),
        confirm=lambda _: pytest.fail("must not confirm"),
        output=lambda _: None,
        timestamp=lambda: "fixed",
    )
    assert result.exit_code == 2
    assert runner.commands == []
    assert tuple(fake_home.rglob("*")) == before


def test_duplicate_doctor_ids_fail_closed(
    repo_root: Path,
    fake_home: Path,
) -> None:
    """Reject ambiguous IDs after core and extension checks are merged."""

    def duplicates(*args: object) -> tuple[DoctorFinding, ...]:
        del args
        finding = DoctorFinding(
            id="duplicate",
            status=FindingStatus.READY,
            severity=CheckSeverity.INFO,
            message="ready",
        )
        return (finding, finding)

    result = run(
        ("doctor",),
        repo_root=repo_root,
        home=fake_home,
        runner=FakeRunner([]),
        downloader=FakeDownloader(),
        confirm=lambda _: pytest.fail("doctor must not confirm"),
        output=lambda _: None,
        timestamp=lambda: "fixed",
        doctor_check_suppliers=(duplicates,),
    )
    assert result.exit_code == 2
    assert result.report.outcomes == ("duplicate doctor finding IDs",)
```

```python
def test_main_applies_private_umask(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = tmp_path / "created"

    def fake_run(*args: object, **kwargs: object) -> RunResult:
        descriptor = os.open(created, os.O_CREAT | os.O_WRONLY, 0o666)
        os.close(descriptor)
        return RunResult(exit_code=0, report=StageReport())

    monkeypatch.setattr("ballen_config.cli.run", fake_run)
    assert main(()) == 0
    assert stat.S_IMODE(created.stat().st_mode) == 0o600
```

- [ ] **Step 6: Run focused verification**

Run:

```bash
rtk uv run --frozen pytest tests/test_doctor.py tests/test_cli.py -v
rtk uv run --frozen mypy
```

Expected: all focused tests PASS and mypy exits 0.

- [ ] **Step 7: Record the checkpoint**

```bash
rtk jj describe -m "feat: diagnose bootstrap readiness safely"
rtk jj new
```

### Task 8: Replace legacy setup guidance with the operational README

**Files:**

- Rewrite: `README.md`
- Rewrite: `CLAUDE.md`
- Create: `docs/manual-steps.md`
- Create: `docs/ssh-transfer.md`
- Create: `tests/test_docs.py`
- Modify: `src/ballen_config/planning.py`
- Modify: `tests/test_planning.py`
- Delete: `ssh/config`
- Delete: `cursor/mcp.json`

- [ ] **Step 1: Write failing documentation contract tests**

```python
# tests/test_docs.py
from pathlib import Path


def test_readme_contains_operating_rationale(repo_root: Path) -> None:
    text = (repo_root / "README.md").read_text()
    for heading in (
        "## Quick start",
        "## Why this bootstrap is structured this way",
        "## Profiles",
        "## Software choices",
        "## Coding-agent portability",
        "## Security and state boundary",
        "## Manual steps",
    ):
        assert heading in text
    for decision in (
        "Wave",
        "MacTeX",
        "libmagic",
        "glab",
    ):
        assert decision in text


def test_legacy_secret_and_mcp_guidance_is_gone(repo_root: Path) -> None:
    operational_paths = (
        repo_root / "README.md",
        repo_root / "CLAUDE.md",
        repo_root / "docs/manual-steps.md",
        repo_root / "docs/ssh-transfer.md",
        repo_root / "cursor/extensions.txt",
        repo_root / "cursor/settings.json",
        repo_root / "claude-code/settings.json",
    )
    tracked_text = "\n".join(
        path.read_text(errors="ignore")
        for path in operational_paths
        if path.exists()
    )
    assert "<YOUR_GITLAB_TOKEN>" not in tracked_text
    assert "gitlab-mr-mcp" not in tracked_text
    assert "@playwright/mcp" not in tracked_text
    assert "cp ~/.aws" not in tracked_text
    assert "id_ed25519_2025" not in tracked_text
    assert not (repo_root / "cursor/mcp.json").exists()
    assert not (repo_root / "ssh/config").exists()
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
rtk uv run --frozen pytest tests/test_docs.py -v
```

Expected: FAIL on missing headings and legacy files/content.

- [ ] **Step 3: Rewrite README and CLAUDE.md with exact ownership**

README must contain:

```markdown
# ballen-config

Portable, agent-friendly setup for a personal/work macOS development machine.

## Quick start

`./bootstrap --profile work`

Run `prepare`, `plan`, `install`, `configure`, and `doctor` independently when
reviewing or repairing one stage.

## Why this bootstrap is structured this way

The Zsh entry point exists only to bridge a clean Mac to Homebrew, `uv`, and
Python 3.12. Everything after that boundary runs in the frozen Python
environment so manifests, validation, path safety, and diagnostics are typed
and testable. The manifests are the inventory authority; this repository does
not replay every package Homebrew happened to install as a dependency.

Every mutating flow prints a structural plan first. Existing unmanaged files
are preserved under a timestamped private backup before replacement, and a
second run is a no-op when desired and actual state match. The bootstrap is
intentionally readable rather than fully unattended so a coding agent can help
resolve machine-specific exceptions without weakening the safety boundary.

## Profiles

`default` installs the portable development baseline. `work` extends that
baseline with AWS tooling and `libmagic`. Repeated `--include` flags opt into
personal applications such as Obsidian, Signal, and full MacTeX. Repeated
`--skip` flags remove Cursor, Claude Code, Codex, or Wave as whole components
from every applicable stage. For example,
`./bootstrap --profile work --skip wave` keeps the rest of the work profile
while leaving the terminal choice unmanaged.

## Software choices

Wave is the default terminal trial; the bootstrap does not uninstall iTerm, so
it remains an easy fallback. The `mactex` include installs the full MacTeX
distribution matching this laptop's TUG MacTeX/TeX Live setup, not BasicTeX,
and is opt-in because it is large. `libmagic` belongs to the work profile
because it is a direct runtime prerequisite for repositories using
`python-magic`, including Plato and code inherited by Avogadro. Homebrew
resolves transitive dependencies; only intentional formulae/casks are declared
here.

## Coding-agent portability

The dependent coding-agent phase restores reviewed Cursor, Claude Code, and
Codex settings, extensions/plugins, hooks, and general skills. Portable
components have one canonical source and agent-native adapters rather than
pretending the three tools share configuration formats. Memory transfer is
deferred from the MVP.

## Security and state boundary

Git owns reviewed manifests, dotfiles, application settings, instructions, and
portable tooling declarations. Credentials, OAuth state, SSH private keys,
sessions, histories, caches, indexes, trust databases, worktrees, and
repository-specific setup never enter this repository. Local ownership
checksums and backups live mode-private beneath
`~/.local/state/ballen-config`.

## Manual steps

Use [manual steps](docs/manual-steps.md) for GitHub, GitLab, work AWS, SSH,
and IT-managed applications. Use the
[SSH transfer guide](docs/ssh-transfer.md) for keys; the repository never
stores them. The approved design remains in
`docs/superpowers/specs/2026-07-25-laptop-migration-bootstrap-design.md`.
```

`CLAUDE.md` must tell an agent to run `./bootstrap plan` before mutations, never
copy credentials, never invent MCP configuration, respect skips/profiles, and
use `doctor` after changes. It must link the README instead of maintaining a
second stale setup sequence.

- [ ] **Step 4: Add safe manual-auth and SSH-transfer guides**

`docs/manual-steps.md` must cover Homebrew/CLT prompts, `gh auth login`,
`glab auth login`, work AWS sign-in, SSH, IT-managed apps, and the MacTeX
download warning. It must say that status output is not copied into Git.
Coding-agent sign-in, browser features, Notion, Atlassian, and other
agent-specific integrations belong exclusively to the dependent coding-agent
plan and must not appear as core manual or doctor actions.

`docs/ssh-transfer.md` must recommend a new per-machine key first. For existing
keys, require an encrypted local medium or trusted direct connection, mode
`0700` for `~/.ssh`, mode `0600` for private keys/config, mode `0644` for public
keys, Keychain loading, out-of-band host-fingerprint verification, and removal
of the temporary encrypted copy. Prohibit plaintext cloud folders and
unencrypted USB media.

Use this operational content rather than another abstract checklist:

```markdown
# Manual post-install steps

1. Complete any Command Line Tools or Homebrew prompt from `prepare`, then run
   `./bootstrap prepare` again.
2. Authenticate GitHub with `gh auth login` and GitLab with
   `glab auth login`. Do not paste status output into this repository.
3. For the work profile, complete the organization's AWS sign-in flow and
   verify only through `./bootstrap doctor --profile work`.
4. Follow `docs/ssh-transfer.md` for any SSH key work.
5. Install IT-managed applications through the company-supported channel.
6. Before `--include mactex`, allow for the full MacTeX download and disk
   footprint.
7. Finish with `./bootstrap doctor --profile work` (or `default`) and resolve
   only the normalized manual findings.
```

```markdown
# SSH transfer

Prefer generating a fresh per-machine key and registering its public key with
each service. If an existing key must move, inspect `~/.ssh` first and
distinguish private keys, `.pub` public keys, optional `config`, and expendable
`known_hosts`.

Transfer only through an encrypted local medium or a direct trusted
connection. Never use a plaintext cloud folder or unencrypted removable
media. On the destination, set `~/.ssh` to `0700`, private keys and `config` to
`0600`, and public keys to `0644`. Load the selected key into the macOS agent
and Keychain, then test GitHub, GitLab, and required hosts.

For a host not already known, verify its fingerprint out of band before
accepting it. After successful verification, securely remove the temporary
encrypted transfer copy. Do not commit keys, host credentials, or remote-login
state to this repository.
```

- [ ] **Step 5: Remove contradictory legacy material**

Delete `ssh/config` and `cursor/mcp.json`. Remove no other Cursor or Claude
files in this core change. The dependent coding-agent
plan reviews the extension list and moves the Bedrock environment into a
work-only overlay in the same checkpoint as their replacement sources. Do not
add replacement MCP files.

```bash
rtk rm ssh/config cursor/mcp.json
```

The core contributor was defined with the planning seam in Task 3. Pass
`CoreManualContributor()` in production `main()` through a
`core_plan_contributors` default used by `run()`. Add this ownership test:

```python
def test_core_manual_actions_are_cross_cutting_only(
    repository: ManifestRepository,
) -> None:
    contributor = CoreManualContributor()
    default = repository.resolve(ResolutionRequest(profile="default"))
    work = repository.resolve(ResolutionRequest(profile="work"))
    default_ids = {
        action.component_id for action in contributor.actions(default)
    }
    work_ids = {
        action.component_id for action in contributor.actions(work)
    }
    assert default_ids == {
        "github-auth",
        "gitlab-auth",
        "ssh-transfer",
        "it-managed-applications",
    }
    assert work_ids == default_ids | {"aws-auth"}
    for forbidden in (
        "cursor",
        "claude-code",
        "codex",
        "browser",
        "notion",
        "atlassian",
    ):
        assert all(forbidden not in item for item in work_ids)
```

- [ ] **Step 6: Run the documentation contracts**

Run:

```bash
rtk uv run --frozen pytest tests/test_docs.py -v
```

Expected: all documentation and legacy-removal assertions PASS.

- [ ] **Step 7: Record the checkpoint**

```bash
rtk jj describe -m "docs: replace legacy laptop setup guidance"
rtk jj new
```

### Task 9: Enforce the tracked-tree boundary and add CI

**Files:**

- Create: `src/ballen_config/policy.py`
- Create: `tests/test_policy.py`
- Create: `tests/test_integration.py`
- Create: `.github/workflows/ci.yml`
- Modify: `.pre-commit-config.yaml`

- [ ] **Step 1: Write failing policy tests**

```python
# tests/test_policy.py
from pathlib import Path

import pytest

from ballen_config.policy import Violation, main, scan_paths, scan_tree


def test_policy_rejects_secret_and_generated_state(tmp_path: Path) -> None:
    (tmp_path / "bad.pem").write_text(
        "-----BEGIN " + "OPENSSH PRIVATE KEY-----\nvalue\n"
    )
    (tmp_path / "sessions").mkdir()
    (tmp_path / "sessions/chat.json").write_text("{}")
    violations = scan_paths(
        tmp_path,
        (Path("bad.pem"), Path("sessions/chat.json")),
    )
    assert {violation.rule for violation in violations} == {
        "private-key",
        "generated-state",
    }


def test_repository_passes_policy(repo_root: Path) -> None:
    assert scan_tree(repo_root) == ()


def test_policy_main_reports_rule_and_path_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Return one without echoing the matched secret-bearing content."""
    monkeypatch.setattr(
        "ballen_config.policy.scan_tree",
        lambda root: (
            Violation(rule="private-key", path="bad.pem"),
        ),
    )
    assert main(tmp_path) == 1
    assert capsys.readouterr().out == "private-key: bad.pem\n"


def test_policy_main_returns_zero_for_clean_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Return zero and print nothing for a clean tracked tree."""
    monkeypatch.setattr(
        "ballen_config.policy.scan_tree",
        lambda root: (),
    )
    assert main(tmp_path) == 0
    assert capsys.readouterr().out == ""
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
rtk uv run --frozen pytest tests/test_policy.py -v
```

Expected: FAIL because `policy.py` does not exist.

- [ ] **Step 3: Implement deterministic tracked-tree scanning**

```python
# src/ballen_config/policy.py
from collections.abc import Iterable
from pathlib import Path
import re
import subprocess

from pydantic import BaseModel, ConfigDict


class Violation(BaseModel):
    """One repository policy violation."""

    model_config = ConfigDict(frozen=True)
    rule: str
    path: str


FORBIDDEN_PARTS = {
    "sessions",
    "history",
    "transcripts",
    "cache",
    "__pycache__",
}
CONTENT_RULES = {
    "private-key": re.compile(
        r"BEGIN (?:OPENSSH|RSA|EC) PRIVATE KEY"
    ),
}
PORTABILITY_RULES = {
    "credential-placeholder": re.compile(
        r"<YOUR_GITLAB_TOKEN>|glpat-[A-Za-z0-9_-]{20,}"
    ),
    "machine-path": re.compile(r"/Users/ballen/"),
    "legacy-mcp": re.compile(
        r"gitlab-mr-mcp|@playwright/mcp|MR_MCP_GITLAB_TOKEN"
    ),
}
PORTABLE_PREFIXES = {
    "assistants",
    "dotfiles",
    "manifests",
    "terminal",
}
PORTABLE_ROOT_FILES = {"bootstrap"}


def tracked_paths(root: Path) -> tuple[Path, ...]:
    """List working-copy files without traversing ignored state."""
    try:
        jj = subprocess.run(
            ("jj", "file", "list"),
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        jj = None
    if jj is not None and jj.returncode == 0:
        return tuple(
            sorted(Path(line) for line in jj.stdout.splitlines() if line)
        )
    git = subprocess.run(
        ("git", "ls-files", "-z"),
        cwd=root,
        check=False,
        capture_output=True,
    )
    if git.returncode != 0:
        raise RuntimeError("cannot enumerate tracked repository files")
    return tuple(
        sorted(
            Path(raw.decode())
            for raw in git.stdout.split(b"\0")
            if raw
        )
    )


def scan_paths(
    root: Path,
    relative_paths: Iterable[Path],
) -> tuple[Violation, ...]:
    """Scan explicit repository-relative paths without printing matches."""
    violations: list[Violation] = []
    for relative in sorted(relative_paths):
        path = root / relative
        if not path.is_file():
            continue
        if FORBIDDEN_PARTS.intersection(relative.parts) or path.suffix in {
            ".sqlite",
            ".sqlite3",
            ".age",
        }:
            violations.append(
                Violation(rule="generated-state", path=str(relative))
            )
            continue
        text = path.read_text(errors="ignore")
        for rule, pattern in CONTENT_RULES.items():
            if pattern.search(text):
                violations.append(Violation(rule=rule, path=str(relative)))
        portable = (
            bool(relative.parts)
            and (
                relative.parts[0] in PORTABLE_PREFIXES
                or relative.as_posix() in PORTABLE_ROOT_FILES
            )
        )
        if portable:
            for rule, pattern in PORTABILITY_RULES.items():
                if pattern.search(text):
                    violations.append(
                        Violation(rule=rule, path=str(relative))
                    )
    return tuple(violations)


def scan_tree(root: Path) -> tuple[Violation, ...]:
    """Scan only files tracked by the current Jujutsu/Git checkout."""
    return scan_paths(root, tracked_paths(root))


def main(root: Path | None = None) -> int:
    """Scan the checkout, print only normalized violations, and return status."""
    repository_root = root or Path(__file__).resolve().parents[2]
    violations = scan_tree(repository_root)
    for violation in violations:
        print(f"{violation.rule}: {violation.path}")
    return int(bool(violations))


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Wire pre-commit and macOS CI**

Add `detect-private-key` from `pre-commit-hooks`, add Yelp
`detect-secrets`, and add this local hook:

```yaml
- repo: local
  hooks:
    - id: ballen-config-policy
      name: ballen-config tracked-tree policy
      entry: uv run --frozen --no-sync python -m ballen_config.policy
      language: system
      pass_filenames: false
    - id: bootstrap-zsh-syntax
      name: bootstrap Zsh syntax
      entry: zsh -n
      language: system
      files: ^bootstrap$
```

Create:

```yaml
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
  push:
    branches: [main]

jobs:
  verify:
    runs-on: macos-14
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
        with:
          python-version: "3.12"
          enable-cache: true
      - run: uv sync --frozen
      - run: uv run --frozen ruff check src tests
      - run: uv run --frozen ruff format --check src tests
      - run: uv run --frozen mypy
      - run: uv run --frozen pytest -v
      - run: zsh -n bootstrap
      - run: uv run --frozen python -m ballen_config.policy
      - run: ./bootstrap plan --profile work
```

The CI plan command must use a prepared `.venv` and must not install anything.

- [ ] **Step 5: Prove complete configure convergence in a temporary home**

```python
# tests/test_integration.py
from collections.abc import Sequence
import os
import stat
from hashlib import sha256
from pathlib import Path

from ballen_config.configure import (
    ConfigEngine,
    configuration_specs,
    core_validators,
)
from ballen_config.manifests import ManifestRepository
from ballen_config.models import ResolutionRequest
from ballen_config.runtime import RuntimePaths
from ballen_config.runner import CommandResult


class SuccessfulRunner:
    """Accept syntax-validation commands without invoking local tools."""

    def run(self, command: Sequence[str]) -> CommandResult:
        """Return one captured successful command result."""
        del command
        return {"returncode": 0, "stdout": "", "stderr": ""}


def snapshot_tree(root: Path) -> dict[str, tuple[int, str]]:
    """Capture paths, modes, link targets, and file hashes."""
    snapshot: dict[str, tuple[int, str]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        mode = stat.S_IMODE(path.lstat().st_mode)
        if path.is_symlink():
            payload = os.readlink(path)
        elif path.is_file():
            payload = sha256(path.read_bytes()).hexdigest()
        else:
            payload = "directory"
        snapshot[relative] = (mode, payload)
    return snapshot


def test_complete_configure_flow_is_idempotent(
    repo_root: Path,
    fake_home: Path,
) -> None:
    """Converge every default-profile file without touching the real home."""
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=fake_home)
    resolved = ManifestRepository.load(repo_root / "manifests").resolve(
        ResolutionRequest(profile="default")
    )
    specs = configuration_specs(repo_root, paths, resolved)
    engine = ConfigEngine(
        paths=paths,
        timestamp=lambda: "20260725T120000Z",
        validators=core_validators(SuccessfulRunner()),
    )

    first = tuple(engine.apply(spec) for spec in specs)
    assert first
    assert set(first) == {"created"}
    after_first = snapshot_tree(fake_home)

    second = tuple(engine.apply(spec) for spec in specs)
    assert set(second) == {"unchanged"}
    assert snapshot_tree(fake_home) == after_first


def test_skip_wave_removes_wave_configuration(
    repo_root: Path,
    fake_home: Path,
) -> None:
    """Apply a whole-component skip before constructing managed specs."""
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=fake_home)
    resolved = ManifestRepository.load(repo_root / "manifests").resolve(
        ResolutionRequest(profile="work", skips=("wave",))
    )
    specs = configuration_specs(repo_root, paths, resolved)
    assert "wave" in resolved.skipped
    assert "wave-settings" not in {spec.id for spec in specs}
```

Run:

```bash
rtk uv run --frozen pytest tests/test_integration.py -v
```

Expected: both tests PASS; the real home and installed software are untouched.

- [ ] **Step 6: Run complete verification**

Run:

```bash
rtk uv run --frozen ruff check src tests
rtk uv run --frozen ruff format --check src tests
rtk uv run --frozen mypy
rtk uv run --frozen pytest -v
rtk zsh -n bootstrap
rtk uv run --frozen python -m ballen_config.policy
rtk ./bootstrap plan --profile work
rtk ./bootstrap doctor --profile work
```

Expected: every command exits 0; plan and doctor perform no writes or installs.

- [ ] **Step 7: Re-run the idempotence proof**

Run the integration fixture twice and assert the second report contains only
`unchanged` actions and creates no new backup directory.

Expected: PASS.

- [ ] **Step 8: Record the final core checkpoint**

```bash
rtk jj describe -m "ci: verify portable laptop bootstrap"
rtk jj new
rtk jj status
```

Expected: the working copy has no changes. Proceed to
`2026-07-25-coding-agent-portability.md`.
