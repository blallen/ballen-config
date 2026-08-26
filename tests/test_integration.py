"""End-to-end configuration convergence tests in an isolated home."""

import hashlib
import os
import stat
from collections.abc import Sequence
from pathlib import Path
from typing import Literal, TypedDict

from ballen_config.configure import (
    ApplyMethod,
    ConfigurationEngine,
    configuration_specs,
    core_validators,
    run_configure,
)
from ballen_config.manifests import ManifestRepository
from ballen_config.models import ResolutionRequest
from ballen_config.runner import CommandResult
from ballen_config.runtime import RuntimePaths
from ballen_config.state import StateStore


class SnapshotEntry(TypedDict):
    """One normalized filesystem entry in an isolated-home snapshot."""

    kind: Literal["directory", "file", "symlink"]
    mode: int
    payload: str


class SuccessfulRunner:
    """Accept syntax-validation commands without invoking local tools."""

    def run(self, command: Sequence[str]) -> CommandResult:
        """Return one captured successful command result.

        Args:
            command: Validation command that would otherwise run locally.

        Returns:
            A successful, output-free command result.
        """
        del command
        return {"returncode": 0, "stdout": "", "stderr": ""}


def snapshot_tree(root: Path) -> dict[str, SnapshotEntry]:
    """Capture paths, types, modes, link targets, and file hashes.

    Args:
        root: Filesystem tree to capture.

    Returns:
        Deterministic metadata keyed by paths relative to ``root``.
    """
    snapshot: dict[str, SnapshotEntry] = {}
    for path in sorted(root.rglob("*"), key=lambda candidate: candidate.as_posix()):
        relative = path.relative_to(root).as_posix()
        metadata = path.lstat()
        mode = stat.S_IMODE(metadata.st_mode)
        if stat.S_ISLNK(metadata.st_mode):
            kind: Literal["directory", "file", "symlink"] = "symlink"
            payload = os.readlink(path)
        elif stat.S_ISREG(metadata.st_mode):
            kind = "file"
            payload = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            kind = "directory"
            payload = ""
        snapshot[relative] = {
            "kind": kind,
            "mode": mode,
            "payload": payload,
        }
    return snapshot


def test_complete_configure_flow_is_idempotent(
    repo_root: Path,
    fake_home: Path,
) -> None:
    """Converge every default-profile file without touching the real home."""
    existing_gitconfig = b"[user]\n\tname = Existing User\n"
    existing_gitignore = b".local-only\n"
    gitconfig = fake_home / ".gitconfig"
    gitconfig.write_bytes(existing_gitconfig)
    git_directory = fake_home / ".config/git"
    git_directory.mkdir(parents=True, mode=0o700)
    gitignore = git_directory / "ignore"
    gitignore.write_bytes(existing_gitignore)

    paths = RuntimePaths.from_roots(repo_root=repo_root, home=fake_home)
    resolved = ManifestRepository.load(repo_root / "manifests").resolve(
        ResolutionRequest(profile="default")
    )
    specs = configuration_specs(
        repo_root / "manifests/configuration.yaml",
        resolved,
        paths,
    )
    state_store = StateStore(paths)
    first_engine = ConfigurationEngine(
        paths=paths,
        state_store=state_store,
        timestamp="20260725T120000Z",
        validators=core_validators(SuccessfulRunner()),
    )

    first_plan = first_engine.plan(specs)
    ssh_spec = next(spec for spec in specs if spec.id == "ssh-config")
    expected_outcomes = {
        spec.id: ("updated" if spec.id in {"gitconfig", "gitignore"} else "created")
        for spec in specs
    }
    assert ssh_spec.destination == Path(".ssh/config")
    assert ssh_spec.method is ApplyMethod.COPY
    assert ssh_spec.mode == 0o600
    assert len(specs) == 8
    assert {action.id: action.outcome for action in first_plan} == expected_outcomes
    first_report = run_configure(first_engine, specs)
    assert {
        action.id: action.outcome for action in first_report.actions
    } == expected_outcomes
    assert first_report.changed_count == len(specs)

    first_backup = paths.backup_root / "20260725T120000Z"
    assert (first_backup / ".gitconfig").read_bytes() == existing_gitconfig
    assert (first_backup / ".config/git/ignore").read_bytes() == existing_gitignore
    ssh_config = fake_home / ".ssh/config"
    assert ssh_config.read_bytes() == (repo_root / "dotfiles/ssh/config").read_bytes()
    assert stat.S_IMODE(ssh_config.stat().st_mode) == 0o600
    assert stat.S_IMODE(ssh_config.parent.stat().st_mode) == 0o700
    after_first = snapshot_tree(fake_home)
    state_after_first = state_store.load()
    backups_after_first = snapshot_tree(paths.backup_root)

    second_engine = ConfigurationEngine(
        paths=paths,
        state_store=state_store,
        timestamp="20260725T120001Z",
        validators=core_validators(SuccessfulRunner()),
    )
    second_plan = second_engine.plan(specs)
    assert second_plan
    assert {action.outcome for action in second_plan} == {"unchanged"}
    second_report = run_configure(second_engine, specs)

    assert {action.outcome for action in second_report.actions} == {"unchanged"}
    assert second_report.changed_count == 0
    assert snapshot_tree(fake_home) == after_first
    assert state_store.load() == state_after_first
    assert snapshot_tree(paths.backup_root) == backups_after_first
    assert not (paths.backup_root / "20260725T120001Z").exists()


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
