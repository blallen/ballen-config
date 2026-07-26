"""Safe, declarative management of portable user configuration."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
from collections.abc import Callable, Mapping, Sequence
from enum import StrEnum
from pathlib import Path
from typing import Literal, Protocol

import tomlkit
import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ballen_config.models import ResolvedSetup
from ballen_config.paths import assert_contained, assert_no_symlink_components
from ballen_config.runner import Runner, SubprocessRunner
from ballen_config.runtime import RuntimePaths
from ballen_config.state import ManagedRecord, StateStore


class ApplyMethod(StrEnum):
    """Supported materialization methods for managed files."""

    COPY = "copy"
    SYMLINK = "symlink"
    RENDER = "render"


def _private_mode(value: int | str) -> int:
    """Normalize and validate a private filesystem mode."""
    mode = int(value, 8) if isinstance(value, str) else value
    if mode not in (0o600, 0o700):
        raise ValueError("mode must be 0600 or 0700")
    return mode


class ManagedFileSpec(BaseModel):
    """A single repository file managed beneath the user's home directory."""

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    kind: Literal["file"] = "file"
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    source: Path
    destination: Path
    method: ApplyMethod
    mode: int | str = 0o600
    component: str
    renderer_id: str | None = None
    validator_id: str | None = None

    @field_validator("mode", mode="before")
    @classmethod
    def validate_mode(cls, value: int | str) -> int:
        """Accept only deliberately private modes."""
        return _private_mode(value)


class ManagedTreeSpec(BaseModel):
    """A symlink-free source directory managed as one atomic tree."""

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    kind: Literal["tree"] = "tree"
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    source: Path
    destination: Path
    component: str


type ManagedSpec = ManagedFileSpec | ManagedTreeSpec
type Renderer = Callable[[bytes, bytes | None], bytes]
type SourceValidator = Callable[[Path], None]


class ConfigurationContribution(BaseModel):
    """Configuration supplied by one independently testable contributor."""

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    specs: tuple[ManagedFileSpec | ManagedTreeSpec, ...] = ()
    renderers: Mapping[str, Callable[[bytes, bytes | None], bytes]] = Field(
        default_factory=dict
    )
    validators: Mapping[str, Callable[[Path], None]] = Field(default_factory=dict)


class ConfigurationSupplier(Protocol):
    """Provide configuration for a resolved setup."""

    def __call__(
        self, resolved: ResolvedSetup, paths: RuntimePaths
    ) -> ConfigurationContribution:
        """Return portable configuration for a setup."""


class ConfigAction(BaseModel):
    """A redacted, deterministic result of one configuration comparison."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    destination: str
    outcome: Literal["created", "updated", "unchanged"]


class ConfigureStageReport(BaseModel):
    """Normalized result for an entire configure stage."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    actions: tuple[ConfigAction, ...]
    changed_count: int


class ConfigurationManifest(BaseModel):
    """YAML boundary model for configuration declarations."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    files: tuple[ManagedFileSpec | ManagedTreeSpec, ...]


def _digest_file(path: Path) -> str:
    """Return SHA-256 for a regular file without following unsafe types."""
    metadata = os.lstat(path)
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError(f"source is not a regular file: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest_tree(path: Path) -> str:
    """Hash a tree's names, bytes, and executable bits while rejecting links."""
    digest = hashlib.sha256()
    for child in sorted(path.rglob("*"), key=lambda candidate: candidate.as_posix()):
        metadata = os.lstat(child)
        relative = child.relative_to(path).as_posix().encode()
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError(f"tree contains symlink: {child}")
        if stat.S_ISDIR(metadata.st_mode):
            digest.update(b"D\0" + relative + b"\0")
            continue
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError(f"tree contains unsupported source: {child}")
        executable = b"1" if metadata.st_mode & stat.S_IXUSR else b"0"
        digest.update(b"F\0" + relative + b"\0" + executable + b"\0")
        digest.update(child.read_bytes())
    return digest.hexdigest()


def core_validators(runner: Runner | None = None) -> dict[str, SourceValidator]:
    """Return built-in source validators with redacted command failures."""
    active_runner = runner or SubprocessRunner()

    def json_validator(source: Path) -> None:
        try:
            json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError("source validation failed") from error

    def toml_validator(source: Path) -> None:
        try:
            tomlkit.parse(source.read_text(encoding="utf-8"))
        except (OSError, tomlkit.exceptions.ParseError) as error:
            raise ValueError("source validation failed") from error

    def command_validator(
        command: list[str], trailing: Sequence[str] = ()
    ) -> SourceValidator:
        def validate(source: Path) -> None:
            result = active_runner.run([*command, str(source), *trailing])
            if result["returncode"] != 0:
                raise ValueError("source validation failed")

        return validate

    return {
        "json": json_validator,
        "toml": toml_validator,
        "zsh": command_validator(["zsh", "-n"]),
        "git-config": command_validator(["git", "config", "--file"], ["--list"]),
    }


class ConfigurationEngine:
    """Safely compare, back up, and atomically materialize configuration."""

    def __init__(
        self,
        *,
        paths: RuntimePaths,
        state_store: StateStore,
        timestamp: str | None = None,
        replace: Callable[[Path, Path], None] | None = None,
        renderers: Mapping[str, Renderer] | None = None,
        validators: Mapping[str, SourceValidator] | None = None,
    ) -> None:
        """Initialize with injected external boundaries."""
        self.paths = paths
        self.state_store = state_store
        self.timestamp = timestamp or "current"
        self.replace = replace or os.replace
        self.renderers = dict(renderers or {})
        self.validators = dict(validators or {})

    def _destination(self, spec: ManagedSpec) -> Path:
        destination = assert_contained(
            self.paths.home / spec.destination, self.paths.home
        )
        assert_no_symlink_components(destination, stop=self.paths.home)
        return destination

    def _validate(self, spec: ManagedSpec) -> None:
        source = assert_contained(spec.source, self.paths.repo_root)
        assert_no_symlink_components(source, stop=self.paths.repo_root)
        metadata = os.lstat(source)
        if isinstance(spec, ManagedFileSpec):
            if not stat.S_ISREG(metadata.st_mode):
                raise ValueError(f"source is not a regular file: {source}")
            if spec.method is ApplyMethod.RENDER and not spec.renderer_id:
                raise ValueError("render method requires renderer_id")
            if spec.method is not ApplyMethod.RENDER and spec.renderer_id:
                raise ValueError("renderer_id requires render method")
            if spec.renderer_id and spec.renderer_id not in self.renderers:
                raise ValueError("unknown renderer")
            if spec.validator_id:
                validator = self.validators.get(spec.validator_id)
                if validator is None:
                    raise ValueError("unknown source validator")
                try:
                    validator(source)
                except Exception as error:
                    raise ValueError("source validation failed") from error
        else:
            if not stat.S_ISDIR(metadata.st_mode):
                raise ValueError(f"source is not a directory: {source}")
            _digest_tree(source)
        self._destination(spec)

    def _file_bytes(self, spec: ManagedFileSpec, destination: Path) -> bytes:
        source_bytes = spec.source.read_bytes()
        if spec.method is not ApplyMethod.RENDER:
            return source_bytes
        current: bytes | None = None
        try:
            metadata = os.lstat(destination)
        except FileNotFoundError:
            metadata = None
        if metadata is not None and stat.S_ISREG(metadata.st_mode):
            current = destination.read_bytes()
        return self.renderers[spec.renderer_id or ""](source_bytes, current)

    def _action(
        self, spec: ManagedSpec, desired_file: bytes | None = None
    ) -> ConfigAction:
        destination = self._destination(spec)
        relative = str(destination.relative_to(self.paths.home))
        try:
            metadata = os.lstat(destination)
        except FileNotFoundError:
            return ConfigAction(id=spec.id, destination=relative, outcome="created")
        if isinstance(spec, ManagedFileSpec):
            if spec.method is ApplyMethod.SYMLINK:
                target = (
                    os.readlink(destination) if stat.S_ISLNK(metadata.st_mode) else None
                )
                desired_target = os.path.relpath(spec.source, start=destination.parent)
                same = target == desired_target
            else:
                desired_bytes = (
                    desired_file
                    if desired_file is not None
                    else self._file_bytes(spec, destination)
                )
                same = (
                    stat.S_ISREG(metadata.st_mode)
                    and destination.read_bytes() == desired_bytes
                    and stat.S_IMODE(metadata.st_mode) == _private_mode(spec.mode)
                )
        else:
            same = stat.S_ISDIR(metadata.st_mode) and _digest_tree(
                destination
            ) == _digest_tree(spec.source)
        return ConfigAction(
            id=spec.id,
            destination=relative,
            outcome="unchanged" if same else "updated",
        )

    def plan(self, specs: Sequence[ManagedSpec]) -> tuple[ConfigAction, ...]:
        """Validate every spec, then return deterministic read-only actions."""
        ordered = tuple(sorted(specs, key=lambda spec: spec.id))
        for spec in ordered:
            self._validate(spec)
        return tuple(self._action(spec) for spec in ordered)

    def _private_parent(self, path: Path) -> None:
        assert_contained(path, self.paths.home)
        assert_no_symlink_components(path, stop=self.paths.home, include_leaf=True)
        path.mkdir(parents=True, mode=0o700, exist_ok=True)
        assert_no_symlink_components(path, stop=self.paths.home, include_leaf=True)
        path.chmod(0o700)

    def _backup(self, destination: Path) -> Path | None:
        try:
            metadata = os.lstat(destination)
        except FileNotFoundError:
            return None
        relative = destination.relative_to(self.paths.home)
        backup = assert_contained(
            self.paths.backup_root / self.timestamp / relative, self.paths.home
        )
        self._private_parent(backup.parent)
        if os.path.lexists(backup):
            raise ValueError(f"backup already exists: {relative}")
        if stat.S_ISLNK(metadata.st_mode):
            backup.symlink_to(os.readlink(destination))
        elif stat.S_ISREG(metadata.st_mode):
            shutil.copyfile(destination, backup, follow_symlinks=False)
            backup.chmod(0o600)
        elif stat.S_ISDIR(metadata.st_mode):
            shutil.move(str(destination), str(backup))
        else:
            raise ValueError(f"unsupported destination type: {destination}")
        return backup

    def _restore(self, backup: Path | None, destination: Path) -> None:
        if backup is not None and not os.path.lexists(destination):
            self.replace(backup, destination)

    def _record(self, spec: ManagedSpec, destination: Path) -> None:
        source_digest = (
            _digest_file(spec.source)
            if isinstance(spec, ManagedFileSpec)
            else _digest_tree(spec.source)
        )
        destination_digest = (
            _digest_file(destination)
            if isinstance(spec, ManagedFileSpec) and not destination.is_symlink()
            else (
                _digest_tree(destination)
                if isinstance(spec, ManagedTreeSpec)
                else source_digest
            )
        )
        self.state_store.record_managed(
            ManagedRecord(
                resource_id=spec.id,
                source_digest=source_digest,
                destination_digest=destination_digest,
                destination=str(destination.relative_to(self.paths.home)),
            )
        )

    def _apply_file(
        self, spec: ManagedFileSpec, action: ConfigAction, desired: bytes
    ) -> ConfigAction:
        if action.outcome == "unchanged":
            return action
        destination = self._destination(spec)
        self._private_parent(destination.parent)
        backup = self._backup(destination)
        temporary = destination.with_name(f".{destination.name}.ballen-config.tmp")
        if os.path.lexists(temporary):
            raise ValueError(f"stale temporary sibling: {temporary.name}")
        try:
            if spec.method is ApplyMethod.SYMLINK:
                os.symlink(
                    os.path.relpath(spec.source, start=destination.parent), temporary
                )
            else:
                descriptor = os.open(
                    temporary,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    _private_mode(spec.mode),
                )
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(desired)
                    stream.flush()
                    os.fsync(stream.fileno())
                temporary.chmod(_private_mode(spec.mode))
            self.replace(temporary, destination)
        except Exception:
            temporary.unlink(missing_ok=True)
            self._restore(backup, destination)
            raise
        self._record(spec, destination)
        return action

    def _copy_tree(self, source: Path, stage: Path) -> None:
        for child in source.rglob("*"):
            relative = child.relative_to(source)
            target = stage / relative
            metadata = os.lstat(child)
            if stat.S_ISDIR(metadata.st_mode):
                target.mkdir(mode=0o700)
            elif stat.S_ISREG(metadata.st_mode):
                shutil.copyfile(child, target)
                target.chmod(0o700 if metadata.st_mode & stat.S_IXUSR else 0o600)
            else:
                raise ValueError(f"tree contains unsupported source: {child}")

    def _apply_tree(self, spec: ManagedTreeSpec, action: ConfigAction) -> ConfigAction:
        if action.outcome == "unchanged":
            return action
        destination = self._destination(spec)
        if action.outcome == "updated":
            state = self.state_store.load()
            record = state.managed.get(spec.id)
            if record is None or record.destination != str(spec.destination):
                raise ValueError("refusing to replace unmanaged tree")
        self._private_parent(destination.parent)
        stage = Path(
            tempfile.mkdtemp(
                prefix=f".{destination.name}.stage.", dir=destination.parent
            )
        )
        stage.chmod(0o700)
        try:
            self._copy_tree(spec.source, stage)
            backup = self._backup(destination)
            try:
                self.replace(stage, destination)
            except Exception:
                self._restore(backup, destination)
                raise
        finally:
            if stage.exists():
                shutil.rmtree(stage)
        self._record(spec, destination)
        return action

    def apply(self, spec: ManagedSpec) -> ConfigAction:
        """Revalidate and apply a single spec after a safe comparison."""
        self._validate(spec)
        if isinstance(spec, ManagedFileSpec):
            destination = self._destination(spec)
            desired = self._file_bytes(spec, destination)
            return self._apply_file(spec, self._action(spec, desired), desired)
        return self._apply_tree(spec, self._action(spec))


def configuration_specs(
    manifest_path: Path, resolved: ResolvedSetup, paths: RuntimePaths
) -> tuple[ManagedSpec, ...]:
    """Load configuration YAML, resolve its paths, and honor skipped components."""
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest = ConfigurationManifest.model_validate(payload)
    return tuple(
        spec.model_copy(
            update={
                "source": paths.repo_root / spec.source,
                "destination": Path(spec.destination),
            }
        )
        for spec in manifest.files
        if spec.component not in resolved.skipped
    )


def core_configuration(
    resolved: ResolvedSetup, paths: RuntimePaths
) -> ConfigurationContribution:
    """Supply the repository's built-in portable configuration."""
    return ConfigurationContribution(
        specs=configuration_specs(
            paths.repo_root / "manifests/configuration.yaml", resolved, paths
        ),
        validators=core_validators(),
    )


def merge_configuration_contributions(
    contributions: Sequence[ConfigurationContribution],
) -> ConfigurationContribution:
    """Merge contributors while rejecting duplicate public identifiers."""
    specs = tuple(spec for contribution in contributions for spec in contribution.specs)
    for values, name in (
        ([spec.id for spec in specs], "spec id"),
        ([str(spec.destination) for spec in specs], "managed destination"),
        (
            [key for contribution in contributions for key in contribution.renderers],
            "renderer id",
        ),
        (
            [key for contribution in contributions for key in contribution.validators],
            "validator id",
        ),
    ):
        if len(values) != len(set(values)):
            raise ValueError(f"duplicate {name}")
    return ConfigurationContribution(
        specs=specs,
        renderers={
            key: value for c in contributions for key, value in c.renderers.items()
        },
        validators={
            key: value for c in contributions for key, value in c.validators.items()
        },
    )


def run_configure(
    engine: ConfigurationEngine, specs: Sequence[ManagedSpec]
) -> ConfigureStageReport:
    """Plan every spec before applying the matching deterministic actions."""
    actions = engine.plan(specs)
    ordered = tuple(sorted(specs, key=lambda spec: spec.id))
    applied = tuple(
        engine.apply(spec) for spec, _ in zip(ordered, actions, strict=True)
    )
    return ConfigureStageReport(
        actions=applied,
        changed_count=sum(action.outcome != "unchanged" for action in applied),
    )


class ConfigurationPlanContributor:
    """Adapt safe configuration planning to the generic setup plan."""

    def __init__(
        self, engine: ConfigurationEngine, supplier: ConfigurationSupplier
    ) -> None:
        """Initialize with the read-only engine and configuration supplier."""
        self.engine = engine
        self.supplier = supplier

    def actions(self, resolved: ResolvedSetup) -> tuple[object, ...]:
        """Return configuration actions and portable-path diagnostics."""
        from ballen_config.planning import PlanAction

        contribution = self.supplier(resolved, self.engine.paths)
        planned = self.engine.plan(contribution.specs)
        actions: list[PlanAction] = [
            PlanAction(
                component_id=item.id,
                category="configure",
                action=item.outcome,
                owner="bootstrap",
                path=f"~/{item.destination}",
            )
            for item in planned
        ]
        actions.extend(
            PlanAction(
                component_id=f"{spec.id}.brittle-path",
                category="diagnostic",
                action="replace-brittle-path",
                owner="bootstrap",
                path=str(spec.source.relative_to(self.engine.paths.repo_root)),
                required=False,
            )
            for spec in contribution.specs
            if isinstance(spec, ManagedFileSpec)
            and b"/Users/" in spec.source.read_bytes()
        )
        return tuple(actions)
