"""Configure reviewed Claude Code preferences and native plugins."""

from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import Never, NotRequired, TypedDict, cast

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from ballen_config.assistants.hooks import claude_hook_fragment
from ballen_config.assistants.instructions import render_native_instructions
from ballen_config.assistants.models import PluginCatalog
from ballen_config.configure import (
    ApplyMethod,
    ConfigurationContribution,
    ManagedFileSpec,
    Renderer,
)
from ballen_config.install import InstallAction
from ballen_config.models import ResolvedSetup
from ballen_config.paths import assert_contained, assert_no_symlink_components
from ballen_config.runner import Runner
from ballen_config.runtime import RuntimePaths

type JsonObject = dict[str, object]


class ClaudeSettingsError(ValueError):
    """A normalized failure to read or render Claude settings."""


class ClaudePluginInspectionError(RuntimeError):
    """A normalized failure to inspect native Claude plugin state."""


class _ClaudeJsonError(ValueError):
    """An ambiguous or non-standard JSON document at the native boundary."""


class ClaudeStableSettings(BaseModel):
    """Repository-owned allowlisted Claude settings."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model: str


class ClaudePluginEntry(TypedDict):
    """One plugin entry returned by Claude's native CLI."""

    id: str


class ClaudeMarketplaceEntry(TypedDict):
    """One marketplace entry returned by Claude's native CLI."""

    name: str


class ClaudePluginSnapshot(TypedDict):
    """The subset of Claude's plugin list response used by this adapter."""

    plugins: list[ClaudePluginEntry]
    marketplaces: NotRequired[list[ClaudeMarketplaceEntry]]


def _reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> JsonObject:
    """Decode a JSON object only when its keys are unambiguous.

    Args:
        pairs: Ordered decoded key-value pairs.

    Returns:
        The decoded unique-key object.

    Raises:
        _ClaudeJsonError: If a JSON object contains a duplicate key.
    """
    result: JsonObject = {}
    for key, value in pairs:
        if key in result:
            raise _ClaudeJsonError("invalid Claude JSON")
        result[key] = value
    return result


def _reject_non_finite_json_constant(_constant: str) -> Never:
    """Reject JSON constants that are not permitted by the JSON standard.

    Args:
        _constant: Native decoder token such as ``NaN`` or ``Infinity``.

    Raises:
        _ClaudeJsonError: Always, because non-finite constants are invalid.
    """
    raise _ClaudeJsonError("invalid Claude JSON")


def _strict_json_loads(source: str | bytes) -> object:
    """Decode JSON while rejecting duplicate keys and non-finite constants.

    Args:
        source: Native JSON text or bytes.

    Returns:
        Decoded JSON value.

    Raises:
        _ClaudeJsonError: If JSON uses duplicate keys or non-standard constants.
        json.JSONDecodeError: If JSON syntax is invalid.
        UnicodeDecodeError: If JSON bytes are not valid UTF-8.
    """
    return json.loads(
        source,
        object_pairs_hook=_reject_duplicate_json_keys,
        parse_constant=_reject_non_finite_json_constant,
    )


def _json_object(source: bytes) -> JsonObject:
    """Decode one local Claude settings object without lossy coercion.

    Args:
        source: Native settings bytes.

    Returns:
        The decoded settings object.

    Raises:
        ClaudeSettingsError: If settings are invalid JSON or not an object.
    """
    try:
        document = _strict_json_loads(source)
    except (json.JSONDecodeError, UnicodeDecodeError, _ClaudeJsonError) as error:
        raise ClaudeSettingsError("invalid Claude settings") from error
    if not isinstance(document, dict):
        raise ClaudeSettingsError("invalid Claude settings")
    return cast(JsonObject, document)


def _reviewed_source(paths: RuntimePaths, relative: Path) -> Path:
    """Return a resolved, regular, symlink-free reviewed source.

    Args:
        paths: Approved runtime roots.
        relative: Repository-relative reviewed source.

    Returns:
        Absolute source path contained by the checkout.
    """
    source = assert_contained(paths.repo_root / relative, paths.repo_root)
    assert_no_symlink_components(source, stop=paths.repo_root)
    if source.is_symlink() or not source.is_file():
        raise ValueError("Claude source must be a regular file")
    assert_contained(source.resolve(strict=True), paths.repo_root)
    return source


def load_stable_settings(path: Path) -> ClaudeStableSettings:
    """Load the repository-owned allowlisted Claude settings.

    Args:
        path: Reviewed stable settings JSON source.

    Returns:
        Validated stable settings.

    Raises:
        ClaudeSettingsError: If the reviewed settings are invalid.
    """
    try:
        return ClaudeStableSettings.model_validate_json(path.read_bytes())
    except (OSError, ValidationError) as error:
        raise ClaudeSettingsError("invalid Claude settings") from error


def _is_managed_rtk_hook(value: object, *, home: Path) -> bool:
    """Return whether an entry contains this adapter's managed RTK hook.

    Args:
        value: Candidate Claude PreToolUse entry.
        home: Approved user home used to identify the canonical command.

    Returns:
        True only for the exact adapter-owned ``rtk-hook claude`` entry.
    """
    if not isinstance(value, dict) or set(value) != {"matcher", "hooks"}:
        return False
    if value.get("matcher") != "Bash":
        return False
    hooks = value.get("hooks")
    if not isinstance(hooks, list) or len(hooks) != 1:
        return False
    hook = hooks[0]
    if not isinstance(hook, dict) or set(hook) != {"type", "command"}:
        return False
    if hook.get("type") != "command" or not isinstance(hook.get("command"), str):
        return False
    try:
        arguments = shlex.split(hook["command"])
    except ValueError:
        return False
    expected = home / ".local/share/ballen-config/hooks/rtk-hook"
    return arguments == [expected.as_posix(), "claude"]


def claude_settings_renderer(home: Path) -> Renderer:
    """Build a renderer that preserves Claude-native plugin and local state.

    Args:
        home: Approved user home used for the injected RTK hook command.

    Returns:
        A settings renderer that updates only ``model`` and the RTK hook.
    """
    managed_hook = claude_hook_fragment(home)["hooks"]["PreToolUse"][0]

    def render(source: bytes, current: bytes | None) -> bytes:
        stable = load_stable_settings_bytes(source)
        existing = {} if current is None else _json_object(current)
        existing_hooks = existing.get("hooks", {})
        if not isinstance(existing_hooks, dict):
            raise ClaudeSettingsError("invalid Claude settings")
        hooks = cast(JsonObject, dict(existing_hooks))
        pre_tool_use = hooks.get("PreToolUse", [])
        if not isinstance(pre_tool_use, list):
            raise ClaudeSettingsError("invalid Claude settings")
        hooks["PreToolUse"] = [
            item for item in pre_tool_use if not _is_managed_rtk_hook(item, home=home)
        ] + [managed_hook]
        result = dict(existing)
        result["model"] = stable.model
        result["hooks"] = hooks
        return json.dumps(result, indent=2, sort_keys=True).encode() + b"\n"

    return render


def load_stable_settings_bytes(source: bytes) -> ClaudeStableSettings:
    """Validate settings bytes supplied by the configuration engine.

    Args:
        source: Reviewed stable settings bytes.

    Returns:
        Validated stable settings.

    Raises:
        ClaudeSettingsError: If the reviewed settings are invalid.
    """
    try:
        return ClaudeStableSettings.model_validate_json(source)
    except ValidationError as error:
        raise ClaudeSettingsError("invalid Claude settings") from error


def _catalog(path: Path) -> PluginCatalog:
    """Load one reviewed Claude plugin catalog.

    Args:
        path: Reviewed plugin catalog path.

    Returns:
        Validated plugin catalog.
    """
    return PluginCatalog.model_validate(
        yaml.safe_load(path.read_text(encoding="utf-8"))
    )


def plan_claude_plugins(
    catalog_path: Path,
    *,
    profiles: tuple[str, ...],
    installed: frozenset[str],
    known_marketplaces: frozenset[str] = frozenset(),
) -> tuple[InstallAction, ...]:
    """Plan missing scoped Claude marketplace and plugin actions.

    Args:
        catalog_path: Reviewed marketplace and plugin catalog.
        profiles: Selected expanded profile names.
        installed: Plugin IDs reported by the native CLI.
        known_marketplaces: Marketplace names reported by the native CLI.

    Returns:
        Deterministically ordered marketplace actions followed by plugins.
    """
    catalog = _catalog(catalog_path)
    active_profiles = set(profiles)
    selected_plugins = tuple(
        plugin
        for plugin in catalog.plugins
        if active_profiles.intersection(plugin.profiles)
    )
    selected_marketplaces = {plugin.marketplace for plugin in selected_plugins}
    actions: list[InstallAction] = []
    for marketplace in catalog.marketplaces:
        if (
            marketplace.name not in selected_marketplaces
            or marketplace.name in known_marketplaces
            or not active_profiles.intersection(marketplace.profiles)
        ):
            continue
        required = any(
            plugin.required
            for plugin in selected_plugins
            if plugin.marketplace == marketplace.name
        )
        actions.append(
            InstallAction(
                component_id=f"claude.marketplace.{marketplace.name}",
                argv=(
                    "claude",
                    "plugin",
                    "marketplace",
                    "add",
                    "--scope",
                    "user",
                    marketplace.source,
                ),
                required=required,
            )
        )
    for plugin in sorted(selected_plugins, key=lambda item: item.id):
        if plugin.id not in installed:
            actions.append(
                InstallAction(
                    component_id=f"claude.plugin.{plugin.id}",
                    argv=("claude", "plugin", "install", "--scope", "user", plugin.id),
                    required=plugin.required,
                )
            )
    return tuple(actions)


def _plugin_snapshot(result: object) -> ClaudePluginSnapshot:
    """Validate the minimal native plugin-list payload used for planning.

    Args:
        result: JSON-decoded native command output.

    Returns:
        Validated plugin snapshot.

    Raises:
        ClaudePluginInspectionError: If native output is malformed.
    """
    if not isinstance(result, dict):
        raise ClaudePluginInspectionError("Claude plugin inspection failed")
    plugins = result.get("plugins")
    marketplaces = result.get("marketplaces", [])
    if not isinstance(plugins, list) or not isinstance(marketplaces, list):
        raise ClaudePluginInspectionError("Claude plugin inspection failed")
    if not all(
        isinstance(item, dict) and isinstance(item.get("id"), str) for item in plugins
    ):
        raise ClaudePluginInspectionError("Claude plugin inspection failed")
    if not all(
        isinstance(item, dict) and isinstance(item.get("name"), str)
        for item in marketplaces
    ):
        raise ClaudePluginInspectionError("Claude plugin inspection failed")
    return cast(
        ClaudePluginSnapshot, {"plugins": plugins, "marketplaces": marketplaces}
    )


def install_actions(
    setup: ResolvedSetup,
    paths: RuntimePaths,
    runner: Runner,
) -> tuple[InstallAction, ...]:
    """Inspect native Claude state and plan only missing plugin actions.

    Args:
        setup: Resolved components and profiles.
        paths: Approved runtime roots.
        runner: Native command boundary.

    Returns:
        Missing marketplace and plugin actions, or none when skipped.

    Raises:
        ClaudePluginInspectionError: If the native inspection cannot be trusted.
    """
    if "claude-code" in setup.skipped or not setup.is_enabled("claude-code"):
        return ()
    listed = runner.run(("claude", "plugin", "list", "--json"))
    if listed["returncode"] != 0:
        raise ClaudePluginInspectionError("Claude plugin inspection failed")
    try:
        snapshot = _plugin_snapshot(_strict_json_loads(listed["stdout"]))
    except (
        ClaudePluginInspectionError,
        _ClaudeJsonError,
        json.JSONDecodeError,
        UnicodeDecodeError,
    ) as error:
        raise ClaudePluginInspectionError("Claude plugin inspection failed") from error
    catalog_path = _reviewed_source(paths, Path("assistants/claude/plugins.yaml"))
    return plan_claude_plugins(
        catalog_path,
        profiles=setup.profiles,
        installed=frozenset(plugin["id"] for plugin in snapshot["plugins"]),
        known_marketplaces=frozenset(
            marketplace["name"] for marketplace in snapshot["marketplaces"]
        ),
    )


def claude_instruction_renderer(paths: RuntimePaths) -> Renderer:
    """Build the canonical engineering and Claude instruction renderer.

    Args:
        paths: Approved runtime roots.

    Returns:
        A pure Claude instruction renderer.
    """
    engineering = _reviewed_source(
        paths, Path("assistants/shared/instructions/engineering.md")
    ).read_text(encoding="utf-8")
    rtk = _reviewed_source(
        paths, Path("assistants/shared/instructions/rtk.md")
    ).read_text(encoding="utf-8")

    def render(source: bytes, _current: bytes | None) -> bytes:
        return render_native_instructions(
            engineering=engineering,
            rtk=rtk,
            agent_suffix=source.decode("utf-8"),
        ).encode()

    return render


def claude_configuration(
    *,
    repo_root: Path,
    home: Path,
    profiles: tuple[str, ...],
    enabled: frozenset[str],
) -> ConfigurationContribution:
    """Return the sole Claude settings and instruction resource owners.

    Args:
        repo_root: Approved checkout root.
        home: Approved user home.
        profiles: Selected expanded profile names.
        enabled: Enabled agent component IDs.

    Returns:
        Empty when skipped, otherwise Claude's rendered file contribution.
    """
    del profiles
    if "claude-code" not in enabled:
        return ConfigurationContribution()
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=home)
    settings = _reviewed_source(paths, Path("assistants/claude/settings.json"))
    instructions = _reviewed_source(paths, Path("assistants/claude/CLAUDE.md"))
    load_stable_settings(settings)
    return ConfigurationContribution(
        specs=(
            ManagedFileSpec(
                id="claude-settings",
                source=settings,
                destination=Path(".claude/settings.json"),
                method=ApplyMethod.RENDER,
                mode=0o600,
                component="claude-code",
                renderer_id="claude-settings",
                validator_id="json",
            ),
            ManagedFileSpec(
                id="claude-instructions",
                source=instructions,
                destination=Path(".claude/CLAUDE.md"),
                method=ApplyMethod.RENDER,
                mode=0o600,
                component="claude-code",
                renderer_id="claude-instructions",
            ),
        ),
        renderers={
            "claude-settings": claude_settings_renderer(home),
            "claude-instructions": claude_instruction_renderer(paths),
        },
    )
