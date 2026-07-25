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
