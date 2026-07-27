"""Configure portable Codex settings, instructions, and native plugins."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Never, TypedDict, cast

import tomlkit
import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

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


class CodexSettingsError(ValueError):
    """A normalized failure to read or render Codex settings."""


class CodexPluginInspectionError(RuntimeError):
    """A normalized failure to inspect native Codex plugin state."""


class _CodexJsonError(ValueError):
    """An ambiguous or non-standard JSON document at the native boundary."""


class CodexStableSettings(BaseModel):
    """Repository-owned allowlisted Codex settings."""

    model_config = ConfigDict(extra="forbid", frozen=True, protected_namespaces=())

    model: str
    model_reasoning_effort: str
    service_tier: str


class CodexPluginEntry(TypedDict):
    """One plugin entry returned by Codex's native CLI."""

    id: str


class CodexMarketplaceEntry(TypedDict):
    """One marketplace entry returned by Codex's native CLI."""

    name: str


class CodexPluginSnapshot(TypedDict):
    """The strictly validated Codex plugin-list payload."""

    plugins: list[CodexPluginEntry]
    marketplaces: list[CodexMarketplaceEntry]


def _reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> JsonObject:
    """Decode a JSON object only when its keys are unambiguous.

    Args:
        pairs: Ordered decoded key-value pairs.

    Returns:
        The decoded unique-key object.

    Raises:
        _CodexJsonError: If a JSON object contains a duplicate key.
    """
    result: JsonObject = {}
    for key, value in pairs:
        if key in result:
            raise _CodexJsonError("invalid Codex JSON")
        result[key] = value
    return result


def _reject_non_finite_json_constant(_constant: str) -> Never:
    """Reject JSON constants that are not permitted by the JSON standard.

    Args:
        _constant: Native decoder token such as ``NaN`` or ``Infinity``.

    Raises:
        _CodexJsonError: Always, because non-finite constants are invalid.
    """
    raise _CodexJsonError("invalid Codex JSON")


def _strict_json_loads(source: str | bytes) -> object:
    """Decode JSON while rejecting duplicate keys and non-finite constants."""
    return json.loads(
        source,
        object_pairs_hook=_reject_duplicate_json_keys,
        parse_constant=_reject_non_finite_json_constant,
    )


def _reviewed_source(paths: RuntimePaths, relative: Path) -> Path:
    """Return a resolved, regular, symlink-free reviewed source."""
    source = assert_contained(paths.repo_root / relative, paths.repo_root)
    assert_no_symlink_components(source, stop=paths.repo_root)
    if source.is_symlink() or not source.is_file():
        raise ValueError("Codex source must be a regular file")
    assert_contained(source.resolve(strict=True), paths.repo_root)
    return source


def load_stable_settings(path: Path) -> CodexStableSettings:
    """Load the repository-owned allowlisted Codex settings.

    Args:
        path: Reviewed stable settings TOML source.

    Returns:
        Validated stable settings.

    Raises:
        CodexSettingsError: If the reviewed settings are invalid.
    """
    try:
        return CodexStableSettings.model_validate(tomllib.loads(path.read_text()))
    except (OSError, tomllib.TOMLDecodeError, ValidationError) as error:
        raise CodexSettingsError("invalid Codex settings") from error


def _settings_from_bytes(source: bytes) -> CodexStableSettings:
    """Validate reviewed stable settings supplied by the configuration engine."""
    try:
        return CodexStableSettings.model_validate(tomllib.loads(source.decode("utf-8")))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError, ValidationError) as error:
        raise CodexSettingsError("invalid Codex settings") from error


def codex_settings_renderer() -> Renderer:
    """Build a renderer that changes only portable top-level Codex settings."""

    def render(source: bytes, current: bytes | None) -> bytes:
        stable = _settings_from_bytes(source)
        if current is None:
            document = tomlkit.document()
        else:
            try:
                document = tomlkit.parse(current.decode("utf-8"))
            except (UnicodeDecodeError, tomlkit.exceptions.ParseError) as error:
                raise CodexSettingsError("invalid Codex settings") from error
        document["model"] = stable.model
        document["model_reasoning_effort"] = stable.model_reasoning_effort
        document["service_tier"] = stable.service_tier
        return tomlkit.dumps(document).encode("utf-8")

    return render


def _catalog(path: Path) -> PluginCatalog:
    """Load one reviewed Codex plugin catalog."""
    return PluginCatalog.model_validate(
        yaml.safe_load(path.read_text(encoding="utf-8"))
    )


def plan_codex_plugins(
    catalog_path: Path,
    *,
    profiles: tuple[str, ...],
    installed: frozenset[str],
    known_marketplaces: frozenset[str] = frozenset(),
) -> tuple[InstallAction, ...]:
    """Plan missing Codex marketplace actions followed by plugin actions."""
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
                component_id=f"codex.marketplace.{marketplace.name}",
                argv=(
                    "codex",
                    "plugin",
                    "marketplace",
                    "add",
                    marketplace.source,
                    "--json",
                ),
                required=required,
            )
        )
    for plugin in selected_plugins:
        if plugin.id not in installed:
            actions.append(
                InstallAction(
                    component_id=f"codex.plugin.{plugin.id}",
                    argv=("codex", "plugin", "add", plugin.id, "--json"),
                    required=plugin.required,
                )
            )
    return tuple(actions)


def _plugin_snapshot(result: object) -> CodexPluginSnapshot:
    """Validate the minimal native plugin-list payload used for planning."""
    if not isinstance(result, dict) or set(result) != {"plugins", "marketplaces"}:
        raise CodexPluginInspectionError("Codex plugin inspection failed")
    plugins = result.get("plugins")
    marketplaces = result.get("marketplaces")
    if not isinstance(plugins, list) or not isinstance(marketplaces, list):
        raise CodexPluginInspectionError("Codex plugin inspection failed")
    if not all(
        isinstance(item, dict) and set(item) == {"id"} and isinstance(item["id"], str)
        for item in plugins
    ):
        raise CodexPluginInspectionError("Codex plugin inspection failed")
    if not all(
        isinstance(item, dict)
        and set(item) == {"name"}
        and isinstance(item["name"], str)
        for item in marketplaces
    ):
        raise CodexPluginInspectionError("Codex plugin inspection failed")
    return cast(CodexPluginSnapshot, {"plugins": plugins, "marketplaces": marketplaces})


def install_actions(
    setup: ResolvedSetup, paths: RuntimePaths, runner: Runner
) -> tuple[InstallAction, ...]:
    """Inspect native Codex state and plan only missing plugin actions."""
    if "codex" in setup.skipped or not setup.is_enabled("codex"):
        return ()
    listed = runner.run(("codex", "plugin", "list", "--json"))
    if listed["returncode"] != 0:
        raise CodexPluginInspectionError("Codex plugin inspection failed")
    try:
        snapshot = _plugin_snapshot(_strict_json_loads(listed["stdout"]))
    except (
        CodexPluginInspectionError,
        _CodexJsonError,
        json.JSONDecodeError,
        UnicodeDecodeError,
    ) as error:
        raise CodexPluginInspectionError("Codex plugin inspection failed") from error
    catalog_path = _reviewed_source(paths, Path("assistants/codex/plugins.yaml"))
    return plan_codex_plugins(
        catalog_path,
        profiles=setup.profiles,
        installed=frozenset(plugin["id"] for plugin in snapshot["plugins"]),
        known_marketplaces=frozenset(
            marketplace["name"] for marketplace in snapshot["marketplaces"]
        ),
    )


def codex_instruction_renderer(paths: RuntimePaths) -> Renderer:
    """Build the canonical engineering and Codex instruction renderer."""
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
            rtk_include=paths.home / ".codex/RTK.md",
        ).encode()

    return render


def codex_configuration(
    *, repo_root: Path, home: Path, profiles: tuple[str, ...], enabled: frozenset[str]
) -> ConfigurationContribution:
    """Return the sole portable Codex configuration resource owners."""
    del profiles
    if "codex" not in enabled:
        return ConfigurationContribution()
    paths = RuntimePaths.from_roots(repo_root=repo_root, home=home)
    overlay = _reviewed_source(paths, Path("assistants/codex/config.overlay.toml"))
    instructions = _reviewed_source(paths, Path("assistants/codex/AGENTS.md"))
    rtk = _reviewed_source(paths, Path("assistants/shared/instructions/rtk.md"))
    load_stable_settings(overlay)
    return ConfigurationContribution(
        specs=(
            ManagedFileSpec(
                id="codex-settings",
                source=overlay,
                destination=Path(".codex/config.toml"),
                method=ApplyMethod.RENDER,
                mode=0o600,
                component="codex",
                renderer_id="codex-settings",
                validator_id="toml",
            ),
            ManagedFileSpec(
                id="codex-instructions",
                source=instructions,
                destination=Path(".codex/AGENTS.md"),
                method=ApplyMethod.RENDER,
                mode=0o600,
                component="codex",
                renderer_id="codex-instructions",
            ),
            ManagedFileSpec(
                id="codex-rtk",
                source=rtk,
                destination=Path(".codex/RTK.md"),
                method=ApplyMethod.COPY,
                mode=0o600,
                component="codex",
            ),
        ),
        renderers={
            "codex-settings": codex_settings_renderer(),
            "codex-instructions": codex_instruction_renderer(paths),
        },
    )
