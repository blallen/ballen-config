"""Manage reviewed Cursor settings and curated extensions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict, cast

import yaml
from pydantic import BaseModel, ConfigDict

from ballen_config.assistants.instructions import render_native_instructions
from ballen_config.assistants.json import StrictJsonError, strict_json_loads
from ballen_config.assistants.models import ExtensionCatalog, ExtensionSpec
from ballen_config.assistants.sources import reviewed_regular_file as _reviewed_source
from ballen_config.configure import (
    ApplyMethod,
    ConfigurationContribution,
    ManagedFileSpec,
    Renderer,
)
from ballen_config.install import InstallAction
from ballen_config.models import ResolvedSetup
from ballen_config.runner import Runner
from ballen_config.runtime import RuntimePaths

type JsonObject = dict[str, object]
_DEFAULT_BUNDLED_ROOT = Path(
    "/Applications/Cursor.app/Contents/Resources/app/extensions"
)


class CursorExtensionPackage(TypedDict):
    """Fields read from one bundled Cursor extension package."""

    name: str
    publisher: str


class ExtensionState(BaseModel):
    """Deterministic Cursor extension resolution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    installed: frozenset[str]
    bundled: frozenset[str]
    missing: tuple[str, ...]
    skipped_condition: tuple[str, ...]
    unmanaged_extra: tuple[str, ...]


class CursorExtensionInspectionError(RuntimeError):
    """A normalized failure to inspect installed Cursor extensions."""


def _catalog(path: Path) -> ExtensionCatalog:
    """Load the reviewed extension catalog."""
    return ExtensionCatalog.model_validate(
        yaml.safe_load(path.read_text(encoding="utf-8"))
    )


def _decode_json(source: bytes, *, label: str) -> object:
    """Decode one reviewed JSON document with a normalized error.

    Args:
        source: Reviewed JSON bytes.
        label: Normalized source name for validation errors.

    Returns:
        The decoded JSON value.

    Raises:
        ValueError: If the source is invalid JSON.
    """
    try:
        return strict_json_loads(source)
    except (json.JSONDecodeError, UnicodeDecodeError, StrictJsonError) as error:
        raise ValueError(f"invalid {label} JSON") from error


def _load_json_object(path: Path, *, label: str) -> JsonObject:
    """Load one reviewed JSON object.

    Args:
        path: Reviewed JSON source path.
        label: Normalized source name for validation errors.

    Returns:
        The decoded JSON object.

    Raises:
        ValueError: If the source is invalid JSON or not an object.
    """
    document = _decode_json(path.read_bytes(), label=label)
    if not isinstance(document, dict):
        raise ValueError(f"{label} must be a JSON object")
    return cast(JsonObject, document)


def _load_json_array(path: Path, *, label: str) -> list[object]:
    """Load one reviewed JSON array.

    Args:
        path: Reviewed JSON source path.
        label: Normalized source name for validation errors.

    Returns:
        The decoded JSON array.

    Raises:
        ValueError: If the source is invalid JSON or not an array.
    """
    document = _decode_json(path.read_bytes(), label=label)
    if not isinstance(document, list):
        raise ValueError(f"{label} must be a JSON array")
    return cast(list[object], document)


def deep_merge(base: object, overlay: object) -> object:
    """Recursively merge objects while replacing lists and scalar values.

    Args:
        base: Existing JSON-compatible value.
        overlay: Higher-precedence JSON-compatible value.

    Returns:
        A new merged object, or the overlay for non-object inputs.
    """
    if not isinstance(base, dict) or not isinstance(overlay, dict):
        return overlay
    base_object = cast(JsonObject, base)
    overlay_object = cast(JsonObject, overlay)
    merged: JsonObject = dict(base_object)
    for key, value in overlay_object.items():
        merged[key] = deep_merge(merged[key], value) if key in merged else value
    return merged


def render_settings(
    repo_root: Path,
    *,
    profiles: tuple[str, ...],
) -> JsonObject:
    """Load and merge reviewed Cursor settings for selected profiles.

    Args:
        repo_root: Approved checkout root.
        profiles: Expanded selected profiles.

    Returns:
        Merged Cursor settings.
    """
    cursor_root = repo_root / "assistants/cursor"
    document = _load_json_object(
        cursor_root / "settings.base.json",
        label="Cursor settings base",
    )
    if "work" not in profiles:
        return document
    overlay = _load_json_object(
        cursor_root / "settings.work.json",
        label="Cursor settings work overlay",
    )
    return cast(JsonObject, deep_merge(document, overlay))


def read_bundled_extensions(root: Path) -> frozenset[str]:
    """Read normalized publisher.name IDs from Cursor package manifests.

    Args:
        root: Cursor's packaged extensions directory.

    Returns:
        Lowercase bundled extension identifiers.

    Raises:
        ValueError: If a package manifest lacks string publisher/name fields.
    """
    identifiers: set[str] = set()
    for manifest in sorted(root.glob("*/package.json")):
        raw = _decode_json(
            manifest.read_bytes(), label="bundled Cursor extension manifest"
        )
        if (
            not isinstance(raw, dict)
            or not isinstance(raw.get("publisher"), str)
            or not isinstance(raw.get("name"), str)
        ):
            raise ValueError("invalid bundled Cursor extension manifest")
        package = cast(CursorExtensionPackage, raw)
        identifiers.add(f"{package['publisher']}.{package['name']}".casefold())
    return frozenset(identifiers)


def resolve_extensions(
    catalog_path: Path,
    *,
    enabled_agents: frozenset[str],
    installed: frozenset[str],
    bundled: frozenset[str],
) -> ExtensionState:
    """Resolve desired and diagnostic extension sets independently.

    Args:
        catalog_path: Reviewed extension catalog.
        enabled_agents: Selected coding-agent component identifiers.
        installed: Extensions reported by the Cursor CLI.
        bundled: Extensions packaged with Cursor.

    Returns:
        Deterministic installed, bundled, missing, skipped, and extra sets.
    """
    catalog = _catalog(catalog_path)
    normalized_installed = frozenset(item.casefold() for item in installed)
    normalized_bundled = frozenset(item.casefold() for item in bundled)
    desired = {
        extension.id
        for extension in catalog.extensions
        if extension.condition is None or extension.condition in enabled_agents
    }
    skipped = {
        extension.id
        for extension in catalog.extensions
        if extension.condition is not None and extension.condition not in enabled_agents
    }
    declared = {extension.id for extension in catalog.extensions}
    return ExtensionState(
        installed=normalized_installed,
        bundled=normalized_bundled,
        missing=tuple(sorted(desired - normalized_installed - normalized_bundled)),
        skipped_condition=tuple(sorted(skipped)),
        unmanaged_extra=tuple(sorted(normalized_installed - declared)),
    )


def jj_graph_action(extension: ExtensionSpec) -> InstallAction:
    """Build the core-owned verified JJ Graph VSIX action.

    Args:
        extension: Fully validated optional VSIX declaration.

    Returns:
        A verified-download action using the core artifact placeholder.
    """
    return InstallAction(
        component_id=f"cursor.extension.{extension.id}",
        kind="verified-download",
        argv=("cursor", "--install-extension", "{artifact}"),
        required=extension.required,
        url=extension.url,
        artifact_name="vscode-jj-graph.vsix",
        size_bytes=extension.size_bytes,
        sha256=extension.sha256,
    )


def plan_cursor_extension_actions(
    catalog_path: Path,
    *,
    enabled_agents: frozenset[str],
    installed: frozenset[str],
    bundled: frozenset[str],
) -> tuple[InstallAction, ...]:
    """Translate missing Cursor features into core install actions.

    Args:
        catalog_path: Reviewed extension catalog.
        enabled_agents: Selected coding-agent component identifiers.
        installed: Extensions reported by the Cursor CLI.
        bundled: Extensions packaged with Cursor.

    Returns:
        Deterministic gallery and verified-download actions.
    """
    catalog = _catalog(catalog_path)
    by_id = {extension.id: extension for extension in catalog.extensions}
    state = resolve_extensions(
        catalog_path,
        enabled_agents=enabled_agents,
        installed=installed,
        bundled=bundled,
    )
    actions: list[InstallAction] = []
    for identifier in state.missing:
        extension = by_id[identifier]
        if extension.install_mode == "vsix":
            actions.append(jj_graph_action(extension))
            continue
        actions.append(
            InstallAction(
                component_id=f"cursor.extension.{identifier}",
                argv=("cursor", "--install-extension", identifier),
                required=extension.required,
            )
        )
    return tuple(actions)


def install_actions(
    setup: ResolvedSetup,
    paths: RuntimePaths,
    runner: Runner,
    *,
    bundled_root: Path = _DEFAULT_BUNDLED_ROOT,
) -> tuple[InstallAction, ...]:
    """Inspect enabled Cursor features and return only missing installs.

    Args:
        setup: Fully resolved component and profile selection.
        paths: Approved checkout, home, state, and backup roots.
        runner: Captured native-command boundary.
        bundled_root: Injectable packaged extension root.

    Returns:
        Missing extension installation actions, or empty when Cursor is skipped.
    """
    if not setup.is_enabled("cursor"):
        return ()
    listed = runner.run(("cursor", "--list-extensions"))
    if listed["returncode"] != 0:
        raise CursorExtensionInspectionError("Cursor extension inspection failed")
    installed = frozenset(
        line.strip().casefold()
        for line in listed["stdout"].splitlines()
        if line.strip()
    )
    try:
        bundled = read_bundled_extensions(bundled_root)
    except (OSError, ValueError) as error:
        raise CursorExtensionInspectionError(
            "Cursor extension inspection failed"
        ) from error
    enabled_agents = frozenset(
        identifier
        for identifier in ("cursor", "claude-code", "codex")
        if setup.is_enabled(identifier)
    )
    catalog_path = _reviewed_source(
        paths,
        Path("assistants/cursor/extensions.yaml"),
    )
    return plan_cursor_extension_actions(
        catalog_path,
        enabled_agents=enabled_agents,
        installed=installed,
        bundled=bundled,
    )


def cursor_settings_renderer(
    paths: RuntimePaths,
    *,
    work: bool,
) -> Renderer:
    """Build the profile-aware Cursor settings renderer.

    Args:
        paths: Approved runtime roots.
        work: Whether to apply the reviewed work overlay.

    Returns:
        A deterministic JSON settings renderer.
    """
    overlay = (
        _load_json_object(
            _reviewed_source(
                paths,
                Path("assistants/cursor/settings.work.json"),
            ),
            label="Cursor settings work overlay",
        )
        if work
        else None
    )

    def render(source: bytes, current: bytes | None) -> bytes:
        document = _decode_json(source, label="Cursor settings base")
        if not isinstance(document, dict):
            raise ValueError("Cursor settings base must be a JSON object")
        if overlay is not None:
            document = deep_merge(document, overlay)
        existing = (
            {} if current is None else _decode_json(current, label="Cursor settings")
        )
        if not isinstance(existing, dict):
            raise ValueError("Cursor settings must be a JSON object")
        return (
            json.dumps(
                deep_merge(existing, document), indent=2, sort_keys=True
            ).encode()
            + b"\n"
        )

    return render


def cursor_rules_renderer(paths: RuntimePaths) -> Renderer:
    """Build the canonical shared-plus-Cursor instruction renderer.

    Args:
        paths: Approved runtime roots.

    Returns:
        A deterministic Markdown renderer.
    """
    engineering = _reviewed_source(
        paths,
        Path("assistants/shared/instructions/engineering.md"),
    ).read_text()
    rtk = _reviewed_source(
        paths,
        Path("assistants/shared/instructions/rtk.md"),
    ).read_text()

    def render(source: bytes, _current: bytes | None) -> bytes:
        return render_native_instructions(
            engineering=engineering,
            rtk=rtk,
            agent_suffix=source.decode(),
        ).encode()

    return render


def cursor_keybindings_renderer() -> Renderer:
    """Merge reviewed keybindings while preserving unrelated user bindings."""

    def render(source: bytes, current: bytes | None) -> bytes:
        reviewed = _load_json_array_bytes(source, label="Cursor keybindings")
        existing = (
            []
            if current is None
            else _load_json_array_bytes(current, label="Cursor keybindings")
        )

        def identity(item: object) -> tuple[object, object] | None:
            if not isinstance(item, dict) or not isinstance(item.get("key"), str):
                return None
            return (item["key"], item.get("when"))

        managed = {identity(item) for item in reviewed}
        merged = [item for item in existing if identity(item) not in managed]
        merged.extend(reviewed)
        return json.dumps(merged, indent=2, sort_keys=True).encode() + b"\n"

    return render


def _load_json_array_bytes(source: bytes, *, label: str) -> list[object]:
    """Decode a strict JSON array from renderer input bytes."""
    value = _decode_json(source, label=label)
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a JSON array")
    return value


def configuration(
    setup: ResolvedSetup,
    paths: RuntimePaths,
) -> ConfigurationContribution:
    """Return Cursor-owned settings, keybindings, and manual User Rules.

    Args:
        setup: Fully resolved component and profile selection.
        paths: Approved checkout, home, state, and backup roots.

    Returns:
        Cursor configuration, or an empty contribution when Cursor is skipped.
    """
    if not setup.is_enabled("cursor"):
        return ConfigurationContribution()

    base = _reviewed_source(
        paths,
        Path("assistants/cursor/settings.base.json"),
    )
    work = _reviewed_source(
        paths,
        Path("assistants/cursor/settings.work.json"),
    )
    keybindings = _reviewed_source(
        paths,
        Path("assistants/cursor/keybindings.json"),
    )
    user_rules = _reviewed_source(
        paths,
        Path("assistants/cursor/user-rules.md"),
    )
    _load_json_object(base, label="Cursor settings base")
    _load_json_object(work, label="Cursor settings work overlay")
    _load_json_array(keybindings, label="Cursor keybindings")

    settings_spec = ManagedFileSpec(
        id="cursor-settings",
        source=base,
        destination=Path("Library/Application Support/Cursor/User/settings.json"),
        method=ApplyMethod.RENDER,
        mode=0o600,
        component="cursor",
        renderer_id="cursor-settings",
        validator_id="json",
    )
    keybindings_spec = ManagedFileSpec(
        id="cursor-keybindings",
        source=keybindings,
        destination=Path("Library/Application Support/Cursor/User/keybindings.json"),
        method=ApplyMethod.RENDER,
        mode=0o600,
        component="cursor",
        renderer_id="cursor-keybindings",
        validator_id="json",
    )
    rules_spec = ManagedFileSpec(
        id="cursor-user-rules",
        source=user_rules,
        destination=Path(".local/state/ballen-config/manual/cursor-user-rules.md"),
        method=ApplyMethod.RENDER,
        mode=0o600,
        component="cursor",
        renderer_id="cursor-user-rules",
    )
    return ConfigurationContribution(
        specs=(settings_spec, keybindings_spec, rules_spec),
        renderers={
            "cursor-settings": cursor_settings_renderer(
                paths,
                work="work" in setup.profiles,
            ),
            "cursor-user-rules": cursor_rules_renderer(paths),
            "cursor-keybindings": cursor_keybindings_renderer(),
        },
    )
