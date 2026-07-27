"""Plan safe, native Cursor marketplace and reviewed local plugins."""

from __future__ import annotations

import os
import stat
from pathlib import Path, PurePosixPath
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ballen_config.assistants.json import StrictJsonError, strict_json_loads
from ballen_config.assistants.models import (
    CursorLocalPlugin,
    CursorMarketplacePlugin,
)
from ballen_config.assistants.skills import declared_skill_name
from ballen_config.configure import (
    ConfigurationContribution,
    ManagedTreeSpec,
    digest_tree,
)
from ballen_config.doctor import (
    CheckSeverity,
    DoctorCheck,
    DoctorFinding,
    FindingStatus,
)
from ballen_config.paths import assert_contained, assert_no_symlink_components
from ballen_config.planning import PlanAction

_MAX_DECLARED_SKILL_PATHS: Final[int] = 128


class CursorPluginManifest(BaseModel):
    """The documented Cursor manifest fields needed by this bootstrap."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    name: str = Field(
        min_length=1,
        description="Cursor plugin identifier declared by the reviewed manifest.",
    )
    skills: str | tuple[str, ...] | None = Field(
        default=None,
        description=(
            "Optional relative directories containing plugin Agent Skills. "
            "When omitted, conventional skills/ entries and a root SKILL.md "
            "are reviewed."
        ),
    )


class ValidatedCursorLocalPlugin(BaseModel):
    """One frozen, preflight-validated Cursor local-plugin source snapshot."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    plugin: CursorLocalPlugin = Field(
        description="Original catalog record retained after one successful preflight review."
    )
    source: Path = Field(
        description="Canonical reviewed tree used by later configuration without reparsing its manifest."
    )
    digest: str = Field(
        pattern=r"^[0-9a-f]{64}$",
        description="Complete reviewed-tree digest that the configuration plan must still observe before publishing.",
    )


def _canonical_source(plugin: CursorLocalPlugin, repo_root: Path) -> Path:
    """Return the one permitted repository source for a local plugin.

    Args:
        plugin: Local-plugin declaration to validate.
        repo_root: Repository root containing reviewed plugin sources.

    Returns:
        The contained, non-symlinked source directory.

    Raises:
        ValueError: If the declaration is not the exact canonical source.
    """
    expected = PurePosixPath("assistants/shared/plugins/local") / plugin.id
    if plugin.source != expected:
        raise ValueError(f"cursor local plugin source is not canonical: {plugin.id}")
    source = assert_contained(repo_root / Path(*expected.parts), repo_root)
    assert_no_symlink_components(source, stop=repo_root, include_leaf=True)
    try:
        metadata = os.lstat(source)
    except FileNotFoundError as error:
        raise ValueError(
            f"cursor local plugin source does not exist: {plugin.id}"
        ) from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise ValueError(f"cursor local plugin source is not a directory: {plugin.id}")
    return source


def _manifest(source: Path) -> CursorPluginManifest:
    """Load one strict, regular Cursor plugin manifest.

    Args:
        source: Previously validated plugin source directory.

    Returns:
        A bounded model containing only manifest fields this bootstrap uses.

    Raises:
        ValueError: If the manifest is missing, unsafe, ambiguous, or invalid.
    """
    manifest_path = source / ".cursor-plugin/plugin.json"
    try:
        assert_no_symlink_components(manifest_path, stop=source)
        metadata = os.lstat(manifest_path)
    except FileNotFoundError as error:
        raise ValueError("cursor plugin manifest is missing") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise ValueError("cursor plugin manifest is not a regular file")
    try:
        document = strict_json_loads(manifest_path.read_bytes())
        return CursorPluginManifest.model_validate(document)
    except (StrictJsonError, UnicodeDecodeError, ValidationError, ValueError) as error:
        raise ValueError("cursor plugin manifest is invalid") from error


def _safe_skill_path(raw: str, source: Path) -> Path:
    """Resolve one manifest-declared skill directory within a plugin tree."""
    relative = PurePosixPath(raw)
    if (
        not raw
        or relative.is_absolute()
        or ".." in relative.parts
        or relative == PurePosixPath(".")
    ):
        raise ValueError("cursor plugin skill path is unsafe")
    candidate = assert_contained(source / Path(*relative.parts), source)
    assert_no_symlink_components(candidate, stop=source, include_leaf=True)
    try:
        metadata = os.lstat(candidate)
    except FileNotFoundError as error:
        raise ValueError("cursor plugin skill path is missing") from error
    if not stat.S_ISDIR(metadata.st_mode):
        raise ValueError("cursor plugin skill path is not a directory")
    return candidate


def _default_skill_roots(source: Path) -> tuple[Path, ...]:
    """Discover bounded conventional local plugin skill roots.

    Args:
        source: Validated local plugin root.

    Returns:
        Regular skill directories from ``skills/`` and a root ``SKILL.md``.

    Raises:
        ValueError: If conventional directories are unsafe or unbounded.
    """
    roots: list[Path] = []
    default_root = source / "skills"
    try:
        metadata = os.lstat(default_root)
    except FileNotFoundError:
        metadata = None
    if metadata is not None:
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise ValueError("cursor plugin skills root is not a directory")
        children = tuple(sorted(default_root.iterdir(), key=lambda path: path.name))
        if len(children) > _MAX_DECLARED_SKILL_PATHS:
            raise ValueError("cursor plugin skill paths exceed size limit")
        for child in children:
            child_metadata = os.lstat(child)
            if stat.S_ISLNK(child_metadata.st_mode):
                raise ValueError("cursor plugin skills root contains symlink")
            if stat.S_ISDIR(child_metadata.st_mode) and (child / "SKILL.md").exists():
                roots.append(child)
    if (source / "SKILL.md").exists():
        roots.append(source)
    return tuple(roots)


def _skill_roots(manifest: CursorPluginManifest, source: Path) -> tuple[Path, ...]:
    """Resolve bounded default or explicit skill directories from a manifest."""
    if manifest.skills is None:
        return _default_skill_roots(source)
    raw_paths = (
        (manifest.skills,) if isinstance(manifest.skills, str) else manifest.skills
    )
    if raw_paths is None or len(raw_paths) > _MAX_DECLARED_SKILL_PATHS:
        raise ValueError("cursor plugin skill paths exceed size limit")
    return tuple(_safe_skill_path(raw, source) for raw in raw_paths)


def _validated_cursor_local_plugin(
    plugin: CursorLocalPlugin,
    *,
    repo_root: Path,
    shared_skill_names: frozenset[str],
) -> ValidatedCursorLocalPlugin:
    """Return one frozen, safe canonical Cursor local-plugin snapshot.

    Args:
        plugin: Raw local-plugin declaration from the validated catalog.
        repo_root: Repository checkout that owns all reviewed source trees.
        shared_skill_names: Every shared skill declared for Cursor, regardless
            of the active profile or whole-agent skips.

    Returns:
        A validated source directory and immutable complete-tree digest.

    Raises:
        ValueError: If the plugin tree, manifest, or declared skills are unsafe
            or collide with shared Cursor skills.
    """
    source = _canonical_source(plugin, repo_root)
    digest = digest_tree(source)
    manifest = _manifest(source)
    if manifest.name != plugin.id:
        raise ValueError(f"cursor plugin manifest name mismatch: {plugin.id}")
    for root in _skill_roots(manifest, source):
        name = declared_skill_name(root)
        if name in shared_skill_names:
            raise ValueError(f"cursor local plugin skill collision: {name}")
    return ValidatedCursorLocalPlugin(
        plugin=plugin,
        source=source,
        digest=digest,
    )


def validate_cursor_local_plugin(
    plugin: CursorLocalPlugin,
    *,
    repo_root: Path,
    shared_skill_names: frozenset[str],
) -> Path:
    """Return a safe canonical Cursor local-plugin source tree.

    This compatibility helper validates one plugin outside orchestration. The
    top-level desired-state preflight uses ``validate_cursor_local_plugins()``
    so later configuration consumes the resulting snapshot without repeating
    manifest or skill parsing.

    Args:
        plugin: Raw local-plugin declaration from the validated catalog.
        repo_root: Repository checkout that owns all reviewed source trees.
        shared_skill_names: Every shared skill declared for Cursor.

    Returns:
        The validated canonical plugin source directory.
    """
    return _validated_cursor_local_plugin(
        plugin,
        repo_root=repo_root,
        shared_skill_names=shared_skill_names,
    ).source


def validate_cursor_local_plugins(
    plugins: tuple[CursorLocalPlugin, ...],
    *,
    repo_root: Path,
    shared_skill_names: frozenset[str],
) -> tuple[ValidatedCursorLocalPlugin, ...]:
    """Validate every raw local plugin once before profile filtering.

    Args:
        plugins: All raw Cursor local-plugin declarations from the catalog.
        repo_root: Repository checkout that owns reviewed plugin trees.
        shared_skill_names: Every shared skill declared for Cursor.

    Returns:
        Sorted frozen source snapshots used by later configuration planning.
    """
    return tuple(
        _validated_cursor_local_plugin(
            plugin,
            repo_root=repo_root,
            shared_skill_names=shared_skill_names,
        )
        for plugin in sorted(plugins, key=lambda item: item.id)
    )


def cursor_local_plugin_configuration(
    plugins: tuple[ValidatedCursorLocalPlugin, ...],
) -> ConfigurationContribution:
    """Return atomic native local-plugin tree specifications.

    Args:
        plugins: Profile-eligible snapshots produced by desired-state preflight.

    Returns:
        Deterministically ordered core managed-tree specifications.
    """
    specs = tuple(
        ManagedTreeSpec(
            id=f"cursor-local-plugin-{snapshot.plugin.id}",
            source=snapshot.source,
            destination=Path(".cursor/plugins/local") / snapshot.plugin.id,
            component="cursor",
            expected_source_digest=snapshot.digest,
        )
        for snapshot in sorted(plugins, key=lambda item: item.plugin.id)
    )
    return ConfigurationContribution(specs=specs)


def cursor_marketplace_plan_actions(
    plugins: tuple[CursorMarketplacePlugin, ...],
) -> tuple[PlanAction, ...]:
    """Return deterministic user-scope Customize checklist actions.

    Args:
        plugins: Profile-eligible Cursor marketplace declarations.

    Returns:
        Manual actions without installed-state assertions or runner inputs.
    """
    return tuple(
        PlanAction(
            component_id=f"cursor.plugin.{plugin.id}",
            category="manual",
            action="open-cursor-customize-add-plugin",
            owner="cursor",
            required=plugin.required,
        )
        for plugin in sorted(plugins, key=lambda item: item.id)
    )


def cursor_marketplace_doctor_checks(
    plugins: tuple[CursorMarketplacePlugin, ...],
) -> tuple[DoctorCheck, ...]:
    """Always report Cursor marketplace entries as informational manual work.

    Args:
        plugins: Profile-eligible Cursor marketplace declarations.

    Returns:
        Informational manual checks that never claim a marketplace is installed.
    """
    return tuple(
        DoctorFinding(
            id=f"cursor.plugin.{plugin.id}",
            status=FindingStatus.MANUAL,
            severity=CheckSeverity.INFO,
            message=(
                "required Cursor Customize plugin installation"
                if plugin.required
                else "optional Cursor Customize plugin installation"
            ),
        )
        for plugin in sorted(plugins, key=lambda item: item.id)
    )
