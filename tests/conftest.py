from collections.abc import Iterator
from pathlib import Path

import pytest

from ballen_config.manifests import ManifestRepository


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


@pytest.fixture
def manifest_repository(repo_root: Path) -> ManifestRepository:
    """Load manifests from the checked-out repository."""
    return ManifestRepository.load(repo_root / "manifests")
