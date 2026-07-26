"""Tests for safe, idempotent configuration management."""

from __future__ import annotations

import os
import stat
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

import pytest
from pydantic import ValidationError

from ballen_config.configure import (
    ApplyMethod,
    ConfigurationContribution,
    ConfigurationEngine,
    ConfigurationPlanContributor,
    ManagedFileSpec,
    ManagedTreeSpec,
    Renderer,
    SourceValidator,
    core_validators,
    merge_configuration_contributions,
)
from ballen_config.models import ResolvedSetup
from ballen_config.planning import PlanAction
from ballen_config.runner import CommandResult
from ballen_config.runtime import RuntimePaths
from ballen_config.state import StateStore


@pytest.fixture
def config_paths(tmp_path: Path) -> RuntimePaths:
    """Provide isolated repository and home roots."""
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    repo.mkdir()
    home.mkdir(mode=0o700)
    return RuntimePaths.from_roots(repo_root=repo, home=home)


def file_spec(
    paths: RuntimePaths,
    *,
    destination: str = ".config/example",
    method: ApplyMethod = ApplyMethod.COPY,
    mode: int | str = 0o600,
    validator_id: str | None = None,
) -> ManagedFileSpec:
    """Build one ordinary managed file specification."""
    source = paths.repo_root / "source"
    source.write_bytes(b"new bytes\n")
    return ManagedFileSpec(
        id="example",
        source=source,
        destination=Path(destination),
        method=method,
        mode=mode,
        component="shell",
        validator_id=validator_id,
    )


def engine(
    paths: RuntimePaths,
    *,
    timestamp: str | None = None,
    replace: Callable[[Path, Path], None] | None = None,
    renderers: Mapping[str, Renderer] | None = None,
    validators: Mapping[str, SourceValidator] | None = None,
) -> ConfigurationEngine:
    """Build a configuration engine with private state."""
    return ConfigurationEngine(
        paths=paths,
        state_store=StateStore(paths),
        timestamp=timestamp,
        replace=replace,
        renderers=renderers,
        validators=validators,
    )


def test_apply_replaces_regular_file_after_private_backup(
    config_paths: RuntimePaths,
) -> None:
    """Conflicting content is preserved before a private atomic replacement."""
    spec = file_spec(config_paths)
    destination = config_paths.home / spec.destination
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"old bytes\n")
    destination.chmod(0o644)

    report = engine(config_paths, timestamp="20260725T120000Z").apply(spec)

    backup = config_paths.backup_root / "20260725T120000Z" / spec.destination
    assert report.outcome == "updated"
    assert backup.read_bytes() == b"old bytes\n"
    assert destination.read_bytes() == b"new bytes\n"
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600
    assert stat.S_IMODE(backup.stat().st_mode) == 0o600


def test_second_apply_is_unchanged_without_backup(config_paths: RuntimePaths) -> None:
    """An unchanged managed file is not backed up again."""
    spec = file_spec(config_paths)
    subject = engine(config_paths, timestamp="one")
    subject.apply(spec)
    report = engine(config_paths, timestamp="two").apply(spec)
    assert report.outcome == "unchanged"
    assert not (config_paths.backup_root / "two").exists()


@pytest.mark.parametrize("method", [ApplyMethod.COPY, ApplyMethod.RENDER])
def test_matching_file_bytes_with_wrong_mode_are_updated(
    config_paths: RuntimePaths,
    method: ApplyMethod,
) -> None:
    """Copy and render specs converge private mode even when bytes match."""
    spec = file_spec(config_paths, method=method)
    renderers: Mapping[str, Renderer] | None = None
    if method is ApplyMethod.RENDER:
        spec = spec.model_copy(update={"renderer_id": "identity"})
        renderers = {"identity": lambda source, _current: source}
    destination = config_paths.home / spec.destination
    destination.parent.mkdir(parents=True)
    destination.write_bytes(spec.source.read_bytes())
    destination.chmod(0o644)
    subject = engine(config_paths, timestamp=method.value, renderers=renderers)

    assert subject.plan((spec,))[0].outcome == "updated"
    assert subject.apply(spec).outcome == "updated"
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600


def test_symlink_converges_and_replaces_conflicting_file_with_backup(
    config_paths: RuntimePaths,
) -> None:
    """A symlink spec converges exactly and preserves prior regular content."""
    spec = file_spec(config_paths, method=ApplyMethod.SYMLINK)
    destination = config_paths.home / spec.destination
    destination.parent.mkdir(parents=True)
    destination.write_text("user content")
    subject = engine(config_paths, timestamp="first")
    assert subject.apply(spec).outcome == "updated"
    assert destination.is_symlink()
    assert os.readlink(destination) == os.path.relpath(spec.source, destination.parent)
    backup = config_paths.backup_root / "first" / spec.destination
    assert backup.read_text() == "user content"
    assert engine(config_paths, timestamp="second").apply(spec).outcome == "unchanged"


def test_symlinked_parent_is_rejected_without_outside_write(
    config_paths: RuntimePaths, tmp_path: Path
) -> None:
    """Destination traversal cannot escape through an existing symlink."""
    spec = file_spec(config_paths, destination=".config/example")
    outside = tmp_path / "outside"
    outside.mkdir()
    (config_paths.home / ".config").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlinked path component"):
        engine(config_paths).apply(spec)
    assert list(outside.iterdir()) == []


def test_symlinked_backup_ancestor_is_rejected_before_directory_creation(
    config_paths: RuntimePaths,
    tmp_path: Path,
) -> None:
    """Backup setup fails closed before following a symlink outside home."""
    spec = file_spec(config_paths)
    destination = config_paths.home / spec.destination
    destination.parent.mkdir(parents=True)
    destination.write_text("user content")
    outside = tmp_path / "outside"
    outside.mkdir()
    (config_paths.home / ".local").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="symlinked path component"):
        engine(config_paths, timestamp="unsafe").apply(spec)

    assert destination.read_text() == "user content"
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize("mode", [0o600, 0o700, "0600", "0700"])
def test_only_private_modes_are_accepted(
    config_paths: RuntimePaths, mode: int | str
) -> None:
    """Private accepted modes normalize through Pydantic."""
    assert file_spec(config_paths, mode=mode).mode in (0o600, 0o700)


@pytest.mark.parametrize("mode", [0o644, "0644"])
def test_non_private_modes_are_rejected(
    config_paths: RuntimePaths, mode: int | str
) -> None:
    """Unsafe modes are rejected at the manifest boundary."""
    with pytest.raises(ValidationError):
        file_spec(config_paths, mode=mode)


def test_plan_validates_all_specs_before_writes(config_paths: RuntimePaths) -> None:
    """A later invalid spec prevents every planned write."""
    valid = file_spec(config_paths)
    invalid = valid.model_copy(update={"id": "invalid", "source": Path("/tmp/x")})
    with pytest.raises(ValueError, match="path escapes"):
        engine(config_paths).plan((valid, invalid))
    assert not (config_paths.home / valid.destination).exists()


def test_plan_is_read_only_and_deterministic(config_paths: RuntimePaths) -> None:
    """Planning sorts actions without creating directories or state."""
    first = file_spec(config_paths)
    second = first.model_copy(update={"id": "alpha", "destination": Path(".alpha")})
    planned = engine(config_paths).plan((first, second))
    assert [item.id for item in planned] == ["alpha", "example"]
    assert all(item.outcome == "created" for item in planned)
    assert not config_paths.state_root.exists()
    assert not (config_paths.home / ".config").exists()


def test_render_callback_and_named_validator_are_applied(
    config_paths: RuntimePaths,
) -> None:
    """Render receives current bytes and named validation finds its callback."""
    spec = file_spec(
        config_paths, method=ApplyMethod.RENDER, validator_id="valid"
    ).model_copy(update={"renderer_id": "join"})
    destination = config_paths.home / spec.destination
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"old")
    seen: list[bytes | None] = []

    def render(source: bytes, current: bytes | None) -> bytes:
        seen.append(current)
        return source + (current or b"")

    engine(
        config_paths,
        renderers={"join": render},
        validators={"valid": lambda _: None},
    ).apply(spec)
    assert seen == [b"old"]
    assert destination.read_bytes() == b"new bytes\nold"


def test_source_must_be_regular_and_inside_repository(
    config_paths: RuntimePaths,
) -> None:
    """Files outside the repository and directory file-sources are refused."""
    outside = file_spec(config_paths).model_copy(update={"source": Path("/tmp/no")})
    directory = config_paths.repo_root / "directory"
    directory.mkdir()
    non_regular = file_spec(config_paths).model_copy(update={"source": directory})
    for spec in (outside, non_regular):
        with pytest.raises(ValueError):
            engine(config_paths).plan((spec,))


def test_source_symlink_is_rejected(config_paths: RuntimePaths) -> None:
    """A managed source cannot resolve through a repository symlink."""
    outside = config_paths.repo_root / "outside"
    outside.write_text("outside")
    source = config_paths.repo_root / "link"
    source.symlink_to(outside)
    spec = file_spec(config_paths).model_copy(update={"source": source})
    with pytest.raises(ValueError, match="source is not a regular file"):
        engine(config_paths).plan((spec,))


def test_tree_collision_is_refused_then_managed_tree_updates(
    config_paths: RuntimePaths,
) -> None:
    """Unmanaged trees are protected while owned trees update atomically."""
    source = config_paths.repo_root / "tree"
    source.mkdir()
    (source / "item").write_text("one")
    spec = ManagedTreeSpec(
        id="tree", source=source, destination=Path(".tree"), component="x"
    )
    destination = config_paths.home / ".tree"
    destination.mkdir()
    (destination / "user").write_text("preserve")
    with pytest.raises(ValueError, match="unmanaged"):
        engine(config_paths).apply(spec)
    destination.rename(config_paths.home / ".tree-user")
    subject = engine(config_paths, timestamp="one")
    assert subject.apply(spec).outcome == "created"
    (source / "item").write_text("two")
    assert engine(config_paths, timestamp="two").apply(spec).outcome == "updated"
    assert (destination / "item").read_text() == "two"
    assert not any(path.is_symlink() for path in destination.rglob("*"))


def test_tree_with_symlinked_source_is_rejected(config_paths: RuntimePaths) -> None:
    """Tree copying never follows a symlink from the repository source."""
    source = config_paths.repo_root / "tree"
    source.mkdir()
    (source / "link").symlink_to(config_paths.repo_root / "missing")
    spec = ManagedTreeSpec(
        id="tree", source=source, destination=Path(".tree"), component="x"
    )
    with pytest.raises(ValueError, match="tree contains symlink"):
        engine(config_paths).plan((spec,))


def test_replace_failure_leaves_existing_file_in_place(
    config_paths: RuntimePaths,
) -> None:
    """A failed atomic replacement retains the previous destination bytes."""
    spec = file_spec(config_paths)
    destination = config_paths.home / spec.destination
    destination.parent.mkdir(parents=True)
    destination.write_text("old")

    def fail_replace(source: Path, target: Path) -> None:
        """Simulate a failed atomic rename."""
        raise OSError("replace failed")

    with pytest.raises(OSError, match="replace failed"):
        engine(config_paths, replace=fail_replace).apply(spec)
    assert destination.read_text() == "old"


def test_duplicate_contribution_fields_are_rejected(config_paths: RuntimePaths) -> None:
    """Merging contributions fails closed for every public identifier."""
    spec = file_spec(config_paths)
    contribution = ConfigurationContribution(specs=(spec,))
    duplicate_destination = ConfigurationContribution(
        specs=(spec.model_copy(update={"id": "other"}),)
    )
    with pytest.raises(ValueError, match="duplicate managed destination"):
        merge_configuration_contributions((contribution, duplicate_destination))


def test_core_validators_redact_native_command_output(
    config_paths: RuntimePaths,
) -> None:
    """Command failures expose a generic source-validation message only."""
    source = config_paths.repo_root / "source"
    source.write_text("not shell")

    class FailedRunner:
        """Return a secret-looking captured failure."""

        def run(self, command: object) -> dict[str, object]:
            """Return a failed process result."""
            return {"returncode": 1, "stdout": "token=secret", "stderr": "bad"}

    with pytest.raises(ValueError, match="source validation failed") as error:
        core_validators(FailedRunner())["zsh"](source)  # type: ignore[arg-type]
    assert "secret" not in str(error.value)


def test_git_validator_uses_read_only_list_action(
    config_paths: RuntimePaths,
) -> None:
    """Git syntax validation requests a real read-only configuration action."""
    source = config_paths.repo_root / "source"
    source.write_text("[user]\nname = Example\n")

    class CapturingRunner:
        """Capture the validator command without invoking Git."""

        def __init__(self) -> None:
            self.commands: list[tuple[str, ...]] = []

        def run(self, command: Sequence[str]) -> CommandResult:
            """Record one successful read-only command."""
            self.commands.append(tuple(command))
            return {"returncode": 0, "stdout": "", "stderr": ""}

    runner = CapturingRunner()
    core_validators(runner)["git-config"](source)
    assert runner.commands == [("git", "config", "--file", str(source), "--list")]


def test_skip_wave_removes_wave_spec(config_paths: RuntimePaths) -> None:
    """Core configuration honors component skips from setup resolution."""
    from ballen_config.configure import configuration_specs

    manifest = config_paths.repo_root / "manifests"
    manifest.mkdir()
    (manifest / "configuration.yaml").write_text(
        "files:\n  - id: wave-settings\n    source: source\n    destination: .config/waveterm/settings.json\n    method: copy\n    mode: '0600'\n    component: wave\n"
    )
    (config_paths.repo_root / "source").write_text("{}")
    resolved = ResolvedSetup(profiles=("default",), components=(), skipped=("wave",))
    assert (
        configuration_specs(manifest / "configuration.yaml", resolved, config_paths)
        == ()
    )


def test_configuration_plan_contributor_returns_structural_action_read_only(
    config_paths: RuntimePaths,
) -> None:
    """A normal managed spec becomes a redacted configure plan action."""
    spec = file_spec(config_paths)
    contributor = ConfigurationPlanContributor(
        engine(config_paths),
        lambda _resolved, _paths: ConfigurationContribution(specs=(spec,)),
    )
    resolved = ResolvedSetup(profiles=("default",), components=(), skipped=())

    actions = contributor.actions(resolved)

    assert actions == (
        PlanAction(
            component_id="example",
            category="configure",
            action="created",
            owner="bootstrap",
            path="~/.config/example",
        ),
    )
    assert not (config_paths.home / spec.destination).exists()
    assert not config_paths.state_root.exists()


def test_configuration_plan_contributor_reports_redacted_brittle_path(
    config_paths: RuntimePaths,
) -> None:
    """Brittle paths emit one redacted diagnostic without source contents."""
    spec = file_spec(config_paths)
    spec.source.write_text('export TOOL_PATH="/Users/name/tool"\n')
    contributor = ConfigurationPlanContributor(
        engine(config_paths),
        lambda _resolved, _paths: ConfigurationContribution(specs=(spec,)),
    )

    actions = contributor.actions(
        ResolvedSetup(profiles=("default",), components=(), skipped=())
    )

    diagnostic = actions[1]
    assert diagnostic == PlanAction(
        component_id="example.brittle-path",
        category="diagnostic",
        action="replace-brittle-path",
        owner="bootstrap",
        path="source",
        required=False,
    )
    assert "/Users/" not in str(diagnostic)
    assert spec.source.read_text() not in str(diagnostic)
    assert not (config_paths.home / spec.destination).exists()
