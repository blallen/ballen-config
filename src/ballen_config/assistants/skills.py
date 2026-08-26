"""Validate and converge portable shared coding-agent skills."""

import os
import re
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Final, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from yaml import YAMLError

from ballen_config.assistants.models import (
    AgentName,
    ConcreteAgentName,
    SkillCatalog,
    SkillSpec,
)
from ballen_config.configure import (
    ConfigurationContribution,
    ConfigurationEngine,
    ManagedTreeSpec,
    digest_tree,
    merge_configuration_contributions,
)
from ballen_config.models import ResolvedSetup
from ballen_config.paths import assert_contained, assert_no_symlink_components
from ballen_config.runtime import RuntimePaths
from ballen_config.state import BootstrapState, ManagedRecord, StateStore


class SkillCollisionError(ValueError):
    """Raised when one normalized skill name resolves to different content.

    The structured fields support a stable, redacted CLI outcome without
    exposing arbitrary exception text or an absolute home path.

    Args:
        name: Normalized shared skill name.
        relative_destination: Native destination relative to the approved home.
    """

    def __init__(self, name: str, relative_destination: Path) -> None:
        """Initialize the collision with its normalized safe context."""
        self.name = name
        self.relative_destination = relative_destination
        super().__init__(
            f"skill collision: {name} at {relative_destination.as_posix()}"
        )

    def outcome(self) -> str:
        """Return a safe, actionable outcome suitable for CLI reporting."""
        relative = self.relative_destination
        if (
            _SKILL_NAME_PATTERN.fullmatch(self.name) is None
            or relative.is_absolute()
            or ".." in relative.parts
            or relative.name != self.name
            or relative.parent not in _CURSOR_SCANNED_ROOTS
        ):
            return "shared skill collision"
        return f"shared skill collision: {self.name} at {relative.as_posix()}"


@dataclass(frozen=True)
class SkillCopyAction:
    """A deterministic native skill-tree convergence action."""

    source: Path
    destination: Path
    relative_destination: Path
    digest: str
    state: Literal["create", "update", "repair", "unchanged"]
    resource_id: str
    target: AgentName


@dataclass(frozen=True)
class _DesiredCopy:
    """One planned skill destination and the receipt currently claiming it."""

    target: AgentName
    resource_id: str
    relative: Path
    record: ManagedRecord | None


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


def declared_skill_name(root: Path) -> str:
    """Return a bounded, validated skill name from one regular tree.

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


class LegacyRenameState(StrEnum):
    """Classification of one target for a declared skill rename."""

    CLEAN = "clean"
    EXACT_LIVE = "exact_live"
    EXACT_STALE = "exact_stale"
    BLOCKED_AMBIGUOUS_RECEIPT = "blocked_ambiguous_receipt"
    BLOCKED_UNMANAGED_OR_AMBIGUOUS = "blocked_unmanaged_or_ambiguous"
    BLOCKED_DRIFT = "blocked_drift"
    BLOCKED_UNMANAGED_SUCCESSOR = "blocked_unmanaged_successor"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class RenameTargetClassification:
    """Per-target rename classification with relative destinations."""

    target: ConcreteAgentName
    legacy_state: LegacyRenameState
    legacy_record: ManagedRecord | None
    legacy_relative: Path
    successor_relative: Path


def classify_rename_target(
    *,
    from_name: str,
    to_name: str,
    target: AgentName,
    home: Path,
    state: BootstrapState,
    successor_digest: str,
    enabled: bool,
) -> RenameTargetClassification:
    """Classify one enabled or skipped concrete target for a declared rename.

    Args:
        from_name: Retired skill directory name.
        to_name: Successor skill directory name declared in the catalog.
        target: Concrete coding-agent target under consideration; ``shared`` is
            rejected because it has no native skill root.
        home: Existing user home root.
        state: Read-only managed-resource ownership snapshot.
        successor_digest: Expected digest of the successor source tree.
        enabled: Whether the target is selected for this run.

    Returns:
        Classification including relative legacy and successor paths.

    Raises:
        ValueError: If ``target`` is ``AgentName.SHARED``, or if ``home`` or a
            resolved destination path is invalid or unsafe.
    """
    if target is AgentName.SHARED:
        raise ValueError("shared is not a concrete skill target")
    legacy_relative = _SKILL_ROOTS[target] / from_name
    successor_relative = _SKILL_ROOTS[target] / to_name
    if not enabled:
        return RenameTargetClassification(
            target=target,
            legacy_state=LegacyRenameState.SKIPPED,
            legacy_record=None,
            legacy_relative=legacy_relative,
            successor_relative=successor_relative,
        )

    home = _validated_home(home)
    resource_id = f"shared-skill-{from_name}-{target.value}"
    ambiguous_receipt = False
    try:
        record = _matching_record(
            state=state,
            resource_id=resource_id,
            relative_destination=legacy_relative,
        )
    except ValueError:
        record = None
        ambiguous_receipt = True

    destination = _candidate(home, legacy_relative)
    metadata = _metadata(destination)
    leaf_present = metadata is not None
    tree_present = metadata is not None and stat.S_ISDIR(metadata.st_mode)
    live_digest: str | None = None
    if tree_present:
        try:
            live_digest = hash_skill_tree(destination)
        except ValueError:
            live_digest = None

    if ambiguous_receipt:
        legacy_state = (
            LegacyRenameState.BLOCKED_AMBIGUOUS_RECEIPT
            if not leaf_present
            else LegacyRenameState.BLOCKED_UNMANAGED_OR_AMBIGUOUS
        )
    elif not leaf_present and record is None:
        legacy_state = LegacyRenameState.CLEAN
    elif (
        tree_present
        and record is not None
        and live_digest is not None
        and live_digest == record.destination_digest
    ):
        legacy_state = LegacyRenameState.EXACT_LIVE
    elif not leaf_present and record is not None:
        legacy_state = LegacyRenameState.EXACT_STALE
    elif leaf_present and (not tree_present or record is None or live_digest is None):
        legacy_state = LegacyRenameState.BLOCKED_UNMANAGED_OR_AMBIGUOUS
    elif (
        tree_present
        and record is not None
        and live_digest is not None
        and live_digest != record.destination_digest
    ):
        legacy_state = LegacyRenameState.BLOCKED_DRIFT
    else:
        legacy_state = LegacyRenameState.BLOCKED_UNMANAGED_OR_AMBIGUOUS

    if legacy_state in {
        LegacyRenameState.CLEAN,
        LegacyRenameState.EXACT_LIVE,
        LegacyRenameState.EXACT_STALE,
    }:
        successor_live = _live_tree_digest(home, successor_relative)
        if successor_live is not None:
            successor_resource_id = f"shared-skill-{to_name}-{target.value}"
            try:
                successor_record = _matching_record(
                    state=state,
                    resource_id=successor_resource_id,
                    relative_destination=successor_relative,
                )
            except ValueError:
                successor_record = None
            if successor_live == successor_digest and successor_record is None:
                legacy_state = LegacyRenameState.BLOCKED_UNMANAGED_SUCCESSOR

    return RenameTargetClassification(
        target=target,
        legacy_state=legacy_state,
        legacy_record=record,
        legacy_relative=legacy_relative,
        successor_relative=successor_relative,
    )


class SkillRenameBlockedError(ValueError):
    """Raised when a declared rename cannot proceed on an enabled target."""

    def __init__(
        self,
        from_name: str,
        to_name: str,
        target: AgentName,
        state: LegacyRenameState,
    ) -> None:
        """Record which rename was blocked and the state that blocked it.

        Args:
            from_name: Retired predecessor skill name.
            to_name: Catalog successor skill name.
            target: Concrete agent whose native skill root is affected.
            state: Legacy classification that made cleanup unsafe. The message
                built here may name the state; use ``outcome()`` for text shown
                to the user.
        """
        self.from_name = from_name
        self.to_name = to_name
        self.target = target
        self.state = state
        super().__init__(
            f"skill rename blocked: {from_name} -> {to_name} on {target.value} ({state})"
        )

    def outcome(self) -> str:
        """Return a redacted CLI outcome without absolute paths or digests."""
        return (
            f"shared skill rename blocked: {self.from_name} -> {self.to_name} "
            f"on {self.target.value}"
        )


@dataclass(frozen=True)
class SkillRenameAction:
    """Frozen accepted rename cleanup for one enabled concrete target.

    ``plan_skill_renames`` constructs actions only for ``clean``,
    ``exact_live``, or ``exact_stale`` legacy states; that accepted-state set
    is a construction-time invariant, not a restriction of
    ``LegacyRenameState`` itself. Apply re-proves every frozen field before
    touching the filesystem.
    """

    from_name: str
    to_name: str
    target: ConcreteAgentName
    legacy_state: LegacyRenameState
    legacy_record: ManagedRecord | None
    legacy_relative: Path
    successor_resource_id: str
    successor_relative: Path
    successor_source_digest: str
    successor_destination_digest: str


_ACCEPTED_RENAME_STATES: Final[frozenset[LegacyRenameState]] = frozenset(
    {
        LegacyRenameState.CLEAN,
        LegacyRenameState.EXACT_LIVE,
        LegacyRenameState.EXACT_STALE,
    }
)


def _rename_action_order(action: SkillRenameAction) -> tuple[str, str, str]:
    """Return the deterministic plan and apply ordering key for one action.

    Args:
        action: Frozen rename cleanup action to order.

    Returns:
        Predecessor name, successor name, and concrete target value.
    """
    return (action.from_name, action.to_name, action.target.value)


def plan_skill_renames(
    *,
    catalog: SkillCatalog,
    setup: ResolvedSetup,
    paths: RuntimePaths,
    state: BootstrapState,
) -> tuple[SkillRenameAction, ...]:
    """Plan renames from the complete catalog before selection filtering.

    Args:
        catalog: Validated skill catalog including optional rename declarations.
        setup: Resolved profiles and component selection.
        paths: Approved checkout and home roots.
        state: Read-only managed-resource ownership snapshot.

    Returns:
        Deterministically ordered accepted rename actions.

    Raises:
        SkillRenameBlockedError: If any enabled target is not an accepted state
            or successor install cannot produce a receipt.
    """
    by_name = {skill.name: skill for skill in catalog.skills}
    actions: list[SkillRenameAction] = []
    for rename in catalog.renames:
        to_skill = by_name[rename.to_name]
        successor_source = _canonical_source(to_skill, paths)
        successor_digest = hash_skill_tree(successor_source)
        for target in to_skill.targets:
            enabled = bool(
                set(to_skill.profiles).intersection(setup.profiles)
                and setup.is_enabled(target.value)
            )
            classification = classify_rename_target(
                from_name=rename.from_name,
                to_name=rename.to_name,
                target=target,
                home=paths.home,
                state=state,
                successor_digest=successor_digest,
                enabled=enabled,
            )
            if classification.legacy_state == LegacyRenameState.SKIPPED:
                continue
            if classification.legacy_state not in _ACCEPTED_RENAME_STATES:
                raise SkillRenameBlockedError(
                    rename.from_name,
                    rename.to_name,
                    target,
                    classification.legacy_state,
                )
            actions.append(
                SkillRenameAction(
                    from_name=rename.from_name,
                    to_name=rename.to_name,
                    target=classification.target,
                    legacy_state=classification.legacy_state,
                    legacy_record=classification.legacy_record,
                    legacy_relative=classification.legacy_relative,
                    successor_resource_id=(
                        f"shared-skill-{rename.to_name}-{classification.target.value}"
                    ),
                    successor_relative=classification.successor_relative,
                    successor_source_digest=successor_digest,
                    successor_destination_digest=successor_digest,
                )
            )
    return tuple(sorted(actions, key=_rename_action_order))


def _require_exact_successor_proof(
    *,
    action: SkillRenameAction,
    state: BootstrapState,
    home: Path,
) -> None:
    """Raise when one frozen successor tree and receipt are not exact.

    Args:
        action: Frozen rename action whose successor must be re-proven.
        state: Ownership snapshot read under the mutation lock.
        home: Validated home root containing the native skill trees.

    Raises:
        SkillRenameBlockedError: If the receipt is missing or any frozen field
            or the on-disk tree disagrees.
    """
    record = state.managed.get(action.successor_resource_id)
    receipt_is_exact = record is not None and (
        record.resource_id == action.successor_resource_id
        and record.destination == action.successor_relative.as_posix()
        and record.source_digest == action.successor_source_digest
        and record.destination_digest == action.successor_destination_digest
    )
    if not receipt_is_exact or not _existing_successor_matches_frozen_tree(
        action=action, home=home
    ):
        raise SkillRenameBlockedError(
            action.from_name,
            action.to_name,
            action.target,
            LegacyRenameState.BLOCKED_UNMANAGED_SUCCESSOR,
        )


def _require_frozen_legacy_proof(
    *,
    action: SkillRenameAction,
    state: BootstrapState,
    home: Path,
) -> RenameTargetClassification:
    """Reclassify one frozen legacy action and require its exact plan state."""
    classification = classify_rename_target(
        from_name=action.from_name,
        to_name=action.to_name,
        target=action.target,
        home=home,
        state=state,
        successor_digest=action.successor_destination_digest,
        enabled=True,
    )
    if (
        classification.legacy_state != action.legacy_state
        or classification.legacy_record != action.legacy_record
    ):
        raise SkillRenameBlockedError(
            action.from_name,
            action.to_name,
            action.target,
            classification.legacy_state,
        )
    return classification


def _live_tree_digest(home: Path, relative: Path) -> str | None:
    """Return the digest of a usable skill tree at a home-relative path.

    Args:
        home: Validated home root holding the native skill trees.
        relative: Home-relative skill tree path.

    Returns:
        The tree digest, or ``None`` when the path is absent, is not a
        directory, or is not a readable skill tree.
    """
    destination = _candidate(home, relative)
    metadata = _metadata(destination)
    if metadata is None or not stat.S_ISDIR(metadata.st_mode):
        return None
    try:
        return hash_skill_tree(destination)
    except ValueError:
        return None


def _existing_successor_matches_frozen_tree(
    *,
    action: SkillRenameAction,
    home: Path,
) -> bool:
    """Return whether an already present successor has the frozen tree digest."""
    return (
        _live_tree_digest(home, action.successor_relative)
        == action.successor_destination_digest
    )


def preflight_skill_rename_cleanups(
    engine: ConfigurationEngine,
    actions: tuple[SkillRenameAction, ...],
) -> None:
    """Prove every frozen legacy cleanup remains safe before any apply.

    Caller holds the outer state mutation lock. Managed-spec planning has already
    validated each successor source and destination feasibility. Every action is
    checked before the caller mutates anything, so one unsafe target blocks the
    whole stage.

    Args:
        engine: Configuration engine that owns paths and the locked state store.
        actions: Frozen accepted rename actions from read-only planning.

    Raises:
        SkillRenameBlockedError: If any legacy target no longer matches its
            frozen classification, or an already present successor tree matches
            the frozen digest without exact receipt proof.
    """
    state = engine.state_store.load()
    for action in sorted(actions, key=_rename_action_order):
        _require_frozen_legacy_proof(
            action=action,
            state=state,
            home=engine.paths.home,
        )
        if _existing_successor_matches_frozen_tree(
            action=action,
            home=engine.paths.home,
        ):
            _require_exact_successor_proof(
                action=action,
                state=state,
                home=engine.paths.home,
            )


def verify_skill_rename_successors(
    engine: ConfigurationEngine,
    actions: tuple[SkillRenameAction, ...],
) -> None:
    """Prove every successor tree and receipt before any legacy cleanup.

    Caller holds the outer state mutation lock after all managed specs apply.
    Verifying every action first keeps cleanup all-or-nothing.

    Args:
        engine: Configuration engine that owns paths and the locked state store.
        actions: Frozen accepted rename actions from read-only planning.

    Raises:
        SkillRenameBlockedError: If any successor tree or receipt is missing or
            does not match the frozen digests.
    """
    state = engine.state_store.load()
    for action in sorted(actions, key=_rename_action_order):
        _require_exact_successor_proof(
            action=action,
            state=state,
            home=engine.paths.home,
        )


def apply_skill_rename_cleanups(
    engine: ConfigurationEngine,
    actions: tuple[SkillRenameAction, ...],
) -> None:
    """Revalidate and remove exact legacy state. Caller holds mutation lock.

    Args:
        engine: Configuration engine whose state store holds the mutation lock.
        actions: Frozen accepted rename actions from planning.

    Raises:
        SkillRenameBlockedError: If live state no longer matches the frozen plan
            or the successor receipt is missing.
    """
    for action in sorted(actions, key=_rename_action_order):
        state = engine.state_store.load()
        _require_exact_successor_proof(
            action=action,
            state=state,
            home=engine.paths.home,
        )
        classification = _require_frozen_legacy_proof(
            action=action,
            state=state,
            home=engine.paths.home,
        )
        if action.legacy_state == LegacyRenameState.CLEAN:
            continue
        if action.legacy_record is None:
            raise SkillRenameBlockedError(
                action.from_name,
                action.to_name,
                action.target,
                classification.legacy_state,
            )
        if action.legacy_state == LegacyRenameState.EXACT_STALE:
            if not engine.state_store.compare_and_remove(action.legacy_record):
                raise SkillRenameBlockedError(
                    action.from_name,
                    action.to_name,
                    action.target,
                    LegacyRenameState.BLOCKED_AMBIGUOUS_RECEIPT,
                )
            continue
        if action.legacy_state == LegacyRenameState.EXACT_LIVE:
            legacy_destination = _candidate(engine.paths.home, action.legacy_relative)
            backup: Path | None = None
            try:
                backup = engine.backup_managed_destination(legacy_destination)
                if not engine.state_store.compare_and_remove(action.legacy_record):
                    raise SkillRenameBlockedError(
                        action.from_name,
                        action.to_name,
                        action.target,
                        LegacyRenameState.BLOCKED_AMBIGUOUS_RECEIPT,
                    )
            except Exception:
                engine.restore_managed_destination(backup, legacy_destination)
                raise
            continue
        raise SkillRenameBlockedError(
            action.from_name,
            action.to_name,
            action.target,
            action.legacy_state,
        )


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
    if source.name != name or declared_skill_name(source) != name:
        raise ValueError("skill name mismatch")

    desired: dict[Path, _DesiredCopy] = {}
    for target in targets:
        relative = _SKILL_ROOTS[target] / name
        destination = _candidate(home, relative)
        resource_id = f"shared-skill-{name}-{target.value}"
        desired[destination] = _DesiredCopy(
            target=target,
            resource_id=resource_id,
            relative=relative,
            record=_matching_record(
                state=state,
                resource_id=resource_id,
                relative_destination=relative,
            ),
        )

    scanned_roots = (
        _CURSOR_SCANNED_ROOTS
        if AgentName.CURSOR in targets
        else tuple(_SKILL_ROOTS[target] for target in targets)
    )
    current_digests: dict[Path, str] = {}
    for relative_root in scanned_roots:
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
        if desired_entry is not None and desired_entry.record is not None:
            continue
        raise SkillCollisionError(name, relative)

    actions: list[SkillCopyAction] = []
    for destination, entry in desired.items():
        destination_digest = current_digests.get(destination)
        if destination_digest == source_digest:
            actions.append(
                SkillCopyAction(
                    source=source,
                    destination=destination,
                    relative_destination=entry.relative,
                    digest=source_digest,
                    state="unchanged",
                    resource_id=entry.resource_id,
                    target=entry.target,
                )
            )
            continue
        if destination_digest is None:
            action_state: Literal["create", "update", "repair"] = "create"
        else:
            if entry.record is None:
                raise SkillCollisionError(name, entry.relative)
            action_state = (
                "update"
                if destination_digest == entry.record.destination_digest
                else "repair"
            )
        actions.append(
            SkillCopyAction(
                source=source,
                destination=destination,
                relative_destination=entry.relative,
                digest=source_digest,
                state=action_state,
                resource_id=entry.resource_id,
                target=entry.target,
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
        expected_source_digest=action.digest,
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
    catalog: SkillCatalog,
    *,
    include_rename_actions: bool = True,
) -> ConfigurationContribution:
    """Resolve every eligible shared skill through core tree primitives.

    Dependencies are validation-only: catalog entries must already be eligible
    under the active profiles, targets, and skips. Planning reads checkout,
    home, and state without creating or mutating any of them.

    Args:
        setup: Fully resolved core component and profile selection.
        paths: Approved checkout, home, state, and backup roots.
        catalog: Validated shared-skill catalog, including rename declarations.
        include_rename_actions: Whether to plan declared rename cleanups. Pass
            ``False`` for diagnostic callers, which then receive no rename
            actions even when the catalog declares them.

    Returns:
        Merged managed-tree specs and structural update/repair plan labels,
        with planned rename cleanups when ``include_rename_actions`` is set.

    Raises:
        ValueError: If a selected dependency is ineligible or a source is not
            canonical and contained.
    """
    if not any(setup.is_enabled(agent) for agent in ("cursor", "claude-code", "codex")):
        return ConfigurationContribution()
    selected = tuple(
        (skill, targets)
        for skill in sorted(catalog.skills, key=lambda item: item.name)
        if (targets := _eligible_targets(skill, setup))
    )
    if not selected and not catalog.renames:
        return ConfigurationContribution()
    state = StateStore(paths).load()
    skill_renames = (
        plan_skill_renames(
            catalog=catalog,
            setup=setup,
            paths=paths,
            state=state,
        )
        if include_rename_actions
        else ()
    )
    if not selected:
        return ConfigurationContribution(skill_renames=skill_renames)
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

    contributions: list[ConfigurationContribution] = [
        ConfigurationContribution(skill_renames=skill_renames)
    ]
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
