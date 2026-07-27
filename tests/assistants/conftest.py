"""Fixtures for coding-agent portability tests."""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.assistants.fakes import StatefulAssistantFake


@pytest.fixture
def repo_root() -> Path:
    """Return the checkout root used by assistant tests."""
    return Path(__file__).resolve().parents[2]


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
