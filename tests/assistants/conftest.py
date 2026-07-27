"""Fixtures for coding-agent portability tests."""

from __future__ import annotations

import shutil
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from ballen_config.assistants.desired_state import (
    PluginCatalogProjection,
    project_plugin_catalog,
)
from ballen_config.assistants.inventory import load_inventory
from ballen_config.assistants.models import AgentName, PluginCatalog
from tests.assistants.fakes import StatefulAssistantFake


@dataclass(frozen=True)
class CursorLocalPluginFixture:
    """One synthetic reviewed Cursor local-plugin source declaration."""

    id: str
    manifest_name: str | None = None
    skill_name: str | None = "example-local-skill"


type CursorLocalPluginRepoFactory = Callable[
    [tuple[CursorLocalPluginFixture, ...]], Path
]


@pytest.fixture
def repo_root() -> Path:
    """Return the checkout root used by assistant tests."""
    return Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def target_aware_plugin_catalog() -> PluginCatalog:
    """Load the checked-in shared plugin catalog through production inventory."""
    root = Path(__file__).resolve().parents[2]
    loaded = load_inventory(root / "assistants/inventory.yaml", root)
    for catalog in loaded.catalogs:
        if catalog.resource_id == "shared.plugins.catalog":
            assert isinstance(catalog.document, PluginCatalog)
            return catalog.document
    raise AssertionError("shared plugin catalog is missing from inventory")


@pytest.fixture
def claude_projection(
    target_aware_plugin_catalog: PluginCatalog,
) -> PluginCatalogProjection:
    """Project the checked-in catalog for Claude adapter tests."""
    return project_plugin_catalog(
        target_aware_plugin_catalog,
        target=AgentName.CLAUDE,
        profiles=("default",),
    )


@pytest.fixture
def codex_projection(
    target_aware_plugin_catalog: PluginCatalog,
) -> PluginCatalogProjection:
    """Project the checked-in catalog for Codex adapter tests."""
    return project_plugin_catalog(
        target_aware_plugin_catalog,
        target=AgentName.CODEX,
        profiles=("default",),
    )


@pytest.fixture
def temporary_home(tmp_path: Path) -> Path:
    """Create a private isolated home directory."""
    home = tmp_path / "home"
    home.mkdir(mode=0o700)
    return home


@pytest.fixture
def isolated_environment(
    monkeypatch: pytest.MonkeyPatch,
    temporary_home: Path,
) -> Iterator[Path]:
    """Point HOME at the isolated directory for one test."""
    monkeypatch.setenv("HOME", str(temporary_home))
    yield temporary_home


@pytest.fixture
def fake_runner(temporary_home: Path) -> StatefulAssistantFake:
    """Provide captured native-command and verified-download boundaries."""
    return StatefulAssistantFake(temporary_home)


@pytest.fixture
def invalid_repo_root(tmp_path: Path, repo_root: Path) -> Path:
    """Copy tracked assistant inputs and corrupt the shared plugin catalog."""
    destination = tmp_path / "invalid-repository"
    shutil.copytree(repo_root / "manifests", destination / "manifests")
    shutil.copytree(repo_root / "assistants", destination / "assistants")
    (destination / "assistants/shared/plugins/catalog.yaml").write_text(
        "marketplaces: []\nplugins:\n  - kind: native-marketplace\n"
    )
    return destination


@pytest.fixture
def cursor_local_plugin_repo_factory(
    repo_root: Path,
    tmp_path: Path,
) -> CursorLocalPluginRepoFactory:
    """Return a factory for copied checkouts with reviewed local plugins."""
    index = 0

    def create(specifications: tuple[CursorLocalPluginFixture, ...]) -> Path:
        """Copy the checkout and append declared local plugins."""
        nonlocal index
        index += 1
        copied = tmp_path / f"cursor-local-plugin-repository-{index}"
        shutil.copytree(
            repo_root,
            copied,
            ignore=shutil.ignore_patterns(
                ".git",
                ".jj",
                ".venv",
                ".pytest_cache",
                ".ruff_cache",
                ".mypy_cache",
                "__pycache__",
            ),
        )
        catalog_path = copied / "assistants/shared/plugins/catalog.yaml"
        payload = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
        for specification in specifications:
            source = copied / "assistants/shared/plugins/local" / specification.id
            (source / ".cursor-plugin").mkdir(parents=True)
            (source / ".cursor-plugin/plugin.json").write_text(
                f'{{"name":"{specification.manifest_name or specification.id}"}}\n',
                encoding="utf-8",
            )
            if specification.skill_name is not None:
                skill = source / "skills" / specification.skill_name
                skill.mkdir(parents=True)
                (skill / "SKILL.md").write_text(
                    "---\n"
                    f"name: {specification.skill_name}\n"
                    "description: Example.\n"
                    "---\n",
                    encoding="utf-8",
                )
            payload["plugins"].append(
                {
                    "kind": "cursor-local",
                    "id": specification.id,
                    "source": (f"assistants/shared/plugins/local/{specification.id}"),
                    "targets": ["cursor"],
                    "profiles": ["default"],
                    "required": True,
                }
            )
        catalog_path.write_text(
            yaml.safe_dump(payload, sort_keys=False),
            encoding="utf-8",
        )
        return copied

    return create
