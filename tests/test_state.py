import stat
from pathlib import Path

import pytest

from ballen_config.runtime import RuntimePaths
from ballen_config.state import BootstrapState, InstallRecord, ManagedRecord, StateStore


def test_state_store_is_atomic_and_private(repo_root: Path, fake_home: Path) -> None:
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=fake_home)
    state = BootstrapState(
        installs={
            "signal": InstallRecord(resource_id="signal", state="optional-failure")
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
    store = StateStore(paths)
    store.write(state)
    assert store.load() == state
    assert stat.S_IMODE(paths.state_root.stat().st_mode) == 0o700
    assert stat.S_IMODE(store.path.stat().st_mode) == 0o600


def test_state_never_persists_native_command_output(
    repo_root: Path, fake_home: Path
) -> None:
    store = StateStore(RuntimePaths.from_roots(repo_root=repo_root, home=fake_home))
    store.record_install(InstallRecord(resource_id="signal", state="optional-failure"))
    assert "download failed with token" not in store.path.read_text()


def test_state_store_rejects_symlinked_state_root(
    repo_root: Path, fake_home: Path, tmp_path: Path
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    state_parent = fake_home / ".local"
    state_parent.mkdir()
    (state_parent / "state").symlink_to(outside, target_is_directory=True)
    store = StateStore(RuntimePaths.from_roots(repo_root=repo_root, home=fake_home))
    with pytest.raises(ValueError, match="symlinked path component"):
        store.load()
    with pytest.raises(ValueError, match="symlinked path component"):
        store.write(BootstrapState())
    assert list(outside.iterdir()) == []


def test_state_store_rejects_terminal_state_symlink(
    repo_root: Path, fake_home: Path, tmp_path: Path
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
    repo_root: Path, fake_home: Path, tmp_path: Path
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
