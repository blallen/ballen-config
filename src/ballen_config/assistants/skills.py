"""Validate and converge portable shared coding-agent skills."""

from __future__ import annotations

import os
import re
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Final, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from yaml import YAMLError

from ballen_config.assistants.models import AgentName, SkillCatalog, SkillSpec
from ballen_config.configure import (
    ConfigurationContribution,
    ManagedTreeSpec,
    digest_tree,
    merge_configuration_contributions,
)
from ballen_config.models import ResolvedSetup
from ballen_config.paths import assert_contained, assert_no_symlink_components
from ballen_config.runtime import RuntimePaths
from ballen_config.state import BootstrapState, ManagedRecord, StateStore


class SkillCollisionError(ValueError):
    """Raised when one normalized skill name resolves to different content."""


@dataclass(frozen=True)
class SkillCopyAction:
    """A deterministic native skill-tree convergence action."""

    source: Path
    destination: Path
    relative_destination: Path
    digest: str
    state: Literal["create", "update", "repair"]
    resource_id: str
    target: AgentName


class _SkillFrontmatter(BaseModel):
    """Bounded metadata required from a shared skill entrypoint."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    name: str = Field(pattern=r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")


_SKILL_NAME_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$"
)
_MAX_FRONTMATTER_BYTES: Final[int] = 64 * 1024
_SKILL_ROOTS: Final[Mapping[AgentName, Path]] = MappingProxyType(
    {
        AgentName.CURSOR: Path(".cursor/skills"),
        AgentName.CLAUDE: Path(".claude/skills"),
        AgentName.CODEX: Path(".agents/skills"),
    }
)
_CURSOR_SCANNED_ROOTS: Final[tuple[Path, ...]] = (
    Path(".cursor/skills"),
    Path(".claude/skills"),
    Path(".agents/skills"),
    Path(".codex/skills"),
)


def hash_skill_tree(root: Path) -> str:
    """Hash a complete, regular shared-skill tree.

    Args:
        root: Directory containing a regular ``SKILL.md`` entrypoint.

    Returns:
        Digest produced by the core managed-tree algorithm.

    Raises:
        ValueError: If the tree is unsafe or lacks a regular ``SKILL.md``.
    """
    digest = digest_tree(root)
    entrypoint = root / "SKILL.md"
    if not entrypoint.is_file():
        raise ValueError(f"missing SKILL.md in {root}")
    return digest


def _declared_name(root: Path) -> str:
    """Parse the bounded initial YAML frontmatter name.

    Args:
        root: Validated skill root containing ``SKILL.md``.

    Returns:
        Validated globally unique skill name.

    Raises:
        ValueError: If frontmatter is missing, unterminated, invalid, or too
            large.
    """
    entrypoint = root / "SKILL.md"
    with entrypoint.open("rb") as stream:
        bounded = stream.read(_MAX_FRONTMATTER_BYTES + 1)
    lines = bounded[:_MAX_FRONTMATTER_BYTES].splitlines()
    if not lines or lines[0] != b"---":
        raise ValueError("SKILL.md is missing initial YAML frontmatter")
    try:
        closing = lines.index(b"---", 1)
    except ValueError as error:
        if len(bounded) > _MAX_FRONTMATTER_BYTES:
            raise ValueError("SKILL.md frontmatter exceeds size limit") from error
        raise ValueError("SKILL.md frontmatter is unterminated") from error
    payload_bytes = b"\n".join(lines[1:closing])
    try:
        payload = yaml.safe_load(payload_bytes.decode("utf-8"))
        frontmatter = _SkillFrontmatter.model_validate(payload)
    except (UnicodeDecodeError, ValidationError, YAMLError) as error:
        raise ValueError("SKILL.md frontmatter is invalid") from error
    return frontmatter.name


def _validate_targets(targets: tuple[AgentName, ...]) -> None:
    """Reject empty, duplicate, shared, and unsupported target tuples."""
    if not targets:
        raise ValueError("skill targets must not be empty")
    if len(targets) != len(set(targets)):
        raise ValueError("duplicate skill target")
    if any(target not in _SKILL_ROOTS for target in targets):
        raise ValueError("unsupported skill target")


def _validated_home(home: Path) -> Path:
    """Return an existing ordinary home directory without resolving links."""
    try:
        metadata = os.lstat(home)
    except FileNotFoundError as error:
        raise ValueError("home does not exist") from error
    if stat.S_ISLNK(metadata.st_mode):
        raise ValueError("home is a symlink")
    if not stat.S_ISDIR(metadata.st_mode):
        raise ValueError("home is not a directory")
    return home


def _candidate(home: Path, relative: Path) -> Path:
    """Build a contained native path and reject symlinked ancestors."""
    candidate = assert_contained(home / relative, home)
    assert_no_symlink_components(candidate, stop=home)
    return candidate


def _metadata(path: Path) -> os.stat_result | None:
    """Read path metadata without following a leaf symlink."""
    try:
        return os.lstat(path)
    except FileNotFoundError:
        return None


def _matching_record(
    *,
    state: BootstrapState,
    resource_id: str,
    relative_destination: Path,
) -> ManagedRecord | None:
    """Validate ownership identity for one desired destination."""
    relative = relative_destination.as_posix()
    record = state.managed.get(resource_id)
    if record is not None and (
        record.resource_id != resource_id or record.destination != relative
    ):
        raise ValueError("managed record mismatch")
    for key, candidate in state.managed.items():
        if candidate.destination != relative:
            continue
        if key != resource_id or candidate.resource_id != resource_id:
            raise ValueError("managed record mismatch")
    return record


def plan_skill_copies(
    *,
    source: Path,
    name: str,
    targets: tuple[AgentName, ...],
    home: Path,
    state: BootstrapState,
) -> tuple[SkillCopyAction, ...]:
    """Plan native skill copies after bounded validation and collision checks.

    Args:
        source: Canonical shared-skill source directory.
        name: Globally unique catalog skill name.
        targets: Concrete native agent targets.
        home: Existing user home root.
        state: Read-only managed-resource ownership snapshot.

    Returns:
        Deterministically ordered create, update, or repair actions.

    Raises:
        SkillCollisionError: If different unmanaged content has the same name.
        ValueError: If names, targets, paths, or ownership records are invalid.
    """
    if _SKILL_NAME_PATTERN.fullmatch(name) is None:
        raise ValueError("invalid skill name")
    _validate_targets(targets)
    home = _validated_home(home)
    source_digest = hash_skill_tree(source)
    if source.name != name or _declared_name(source) != name:
        raise ValueError("skill name mismatch")

    desired: dict[
        Path,
        tuple[AgentName, str, Path, ManagedRecord | None],
    ] = {}
    for target in targets:
        relative = _SKILL_ROOTS[target] / name
        destination = _candidate(home, relative)
        resource_id = f"shared-skill-{name}-{target.value}"
        record = _matching_record(
            state=state,
            resource_id=resource_id,
            relative_destination=relative,
        )
        desired[destination] = (target, resource_id, relative, record)

    current_digests: dict[Path, str] = {}
    for relative_root in _CURSOR_SCANNED_ROOTS:
        relative = relative_root / name
        candidate = _candidate(home, relative)
        metadata = _metadata(candidate)
        if metadata is None:
            continue
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError(f"symlinked skill destination: {relative.as_posix()}")
        if not stat.S_ISDIR(metadata.st_mode):
            raise ValueError(f"unsupported skill destination: {relative.as_posix()}")
        scanned_digest = hash_skill_tree(candidate)
        current_digests[candidate] = scanned_digest
        if scanned_digest == source_digest:
            continue
        desired_entry = desired.get(candidate)
        if desired_entry is not None and desired_entry[3] is not None:
            continue
        raise SkillCollisionError(f"skill collision: {name} at {relative.as_posix()}")

    actions: list[SkillCopyAction] = []
    for destination, (target, resource_id, relative, record) in desired.items():
        destination_digest = current_digests.get(destination)
        if destination_digest == source_digest:
            continue
        if destination_digest is None:
            action_state: Literal["create", "update", "repair"] = "create"
        else:
            if record is None:
                raise SkillCollisionError(
                    f"skill collision: {name} at {relative.as_posix()}"
                )
            action_state = (
                "update"
                if destination_digest == record.destination_digest
                else "repair"
            )
        actions.append(
            SkillCopyAction(
                source=source,
                destination=destination,
                relative_destination=relative,
                digest=source_digest,
                state=action_state,
                resource_id=resource_id,
                target=target,
            )
        )
    return tuple(
        sorted(actions, key=lambda action: action.relative_destination.as_posix())
    )


def managed_tree_spec(action: SkillCopyAction) -> ManagedTreeSpec:
    """Convert a skill action into the core atomic tree primitive."""
    return ManagedTreeSpec(
        id=action.resource_id,
        source=action.source,
        destination=action.relative_destination,
        component=action.target.value,
    )


def _eligible_targets(
    skill: SkillSpec,
    setup: ResolvedSetup,
) -> tuple[AgentName, ...]:
    """Return enabled concrete targets for one profile-eligible skill."""
    if not set(skill.profiles).intersection(setup.profiles):
        return ()
    return tuple(target for target in skill.targets if setup.is_enabled(target.value))


def _canonical_source(skill: SkillSpec, paths: RuntimePaths) -> Path:
    """Resolve one exact canonical skill source inside the checkout."""
    expected = Path("assistants/shared/skills") / skill.name
    if Path(*skill.source.parts) != expected:
        raise ValueError(f"skill source is not canonical: {skill.name}")
    source = assert_contained(paths.repo_root / expected, paths.repo_root)
    assert_no_symlink_components(
        source,
        stop=paths.repo_root,
        include_leaf=True,
    )
    return source


def configuration(
    setup: ResolvedSetup,
    paths: RuntimePaths,
) -> ConfigurationContribution:
    """Resolve every eligible shared skill through core tree primitives.

    Dependencies are validation-only: catalog entries must already be eligible
    under the active profiles, targets, and skips. Planning reads checkout,
    home, and state without creating or mutating any of them.

    Args:
        setup: Fully resolved core component and profile selection.
        paths: Approved checkout, home, state, and backup roots.

    Returns:
        Merged managed-tree specs and structural update/repair plan labels.

    Raises:
        ValueError: If a selected dependency is ineligible or a source is not
            canonical and contained.
    """
    if not any(setup.is_enabled(agent) for agent in ("cursor", "claude-code", "codex")):
        return ConfigurationContribution()
    catalog_path = paths.repo_root / "assistants/shared/skills/catalog.yaml"
    catalog = SkillCatalog.model_validate(
        yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    )
    selected = tuple(
        (skill, targets)
        for skill in sorted(catalog.skills, key=lambda item: item.name)
        if (targets := _eligible_targets(skill, setup))
    )
    if not selected:
        return ConfigurationContribution()
    selected_targets = {skill.name: frozenset(targets) for skill, targets in selected}
    for skill, targets in selected:
        consumer_targets = frozenset(targets)
        for dependency in skill.dependencies:
            dependency_targets = selected_targets.get(dependency)
            if dependency_targets is None:
                raise ValueError(f"skill dependency is not eligible: {skill.name}")
            if not consumer_targets.issubset(dependency_targets):
                raise ValueError(
                    f"skill dependency target coverage is incomplete: {skill.name}"
                )

    state = StateStore(paths).load()
    contributions: list[ConfigurationContribution] = []
    for skill, targets in selected:
        source = _canonical_source(skill, paths)
        actions = plan_skill_copies(
            source=source,
            name=skill.name,
            targets=targets,
            home=paths.home,
            state=state,
        )
        contributions.extend(
            ConfigurationContribution(
                specs=(managed_tree_spec(action),),
                plan_action_overrides=(
                    {action.resource_id: action.state}
                    if action.state in ("update", "repair")
                    else {}
                ),
            )
            for action in actions
        )
    return merge_configuration_contributions(tuple(contributions))
