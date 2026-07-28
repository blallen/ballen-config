"""Configure portable Codex settings, instructions, and native plugins."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import TypedDict, cast

import tomlkit
from pydantic import BaseModel, ConfigDict, ValidationError

from ballen_config.assistants.desired_state import PluginCatalogProjection
from ballen_config.assistants.instructions import render_native_instructions
from ballen_config.assistants.json import StrictJsonError, strict_json_loads
from ballen_config.assistants.models import AgentName
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


class CodexSettingsError(ValueError):
    """A normalized failure to read or render Codex settings."""


class CodexPluginInspectionError(RuntimeError):
    """A normalized failure to inspect native Codex plugin state."""


class CodexStableSettings(BaseModel):
    """Repository-owned allowlisted Codex settings."""

    model_config = ConfigDict(extra="forbid", frozen=True, protected_namespaces=())

    model: str
    model_reasoning_effort: str
    service_tier: str


class CodexNativePluginEntry(TypedDict):
    """The installed-plugin fields consumed from Codex's native CLI."""

    pluginId: str


class CodexNativeMarketplaceEntry(TypedDict):
    """The marketplace fields consumed from Codex's native CLI."""

    name: str


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


def plan_codex_plugins(
    catalog: PluginCatalogProjection,
    *,
    installed: frozenset[str],
    known_marketplaces: frozenset[str] = frozenset(),
) -> tuple[InstallAction, ...]:
    """Plan missing Codex marketplace actions followed by plugin actions."""
    if catalog.target is not AgentName.CODEX:
        raise ValueError("Codex plugin catalog must target codex")
    selected_plugins = catalog.native_plugins
    selected_marketplaces = {plugin.marketplace for plugin in selected_plugins}
    actions: list[InstallAction] = []
    for marketplace in catalog.marketplaces:
        if (
            marketplace.name not in selected_marketplaces
            or marketplace.name in known_marketplaces
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


def _installed_plugin_ids(result: object) -> frozenset[str]:
    """Validate native plugin-list payload and return installed IDs."""
    if not isinstance(result, dict):
        raise CodexPluginInspectionError("Codex plugin inspection failed")
    installed = result.get("installed")
    if not isinstance(installed, list):
        raise CodexPluginInspectionError("Codex plugin inspection failed")
    if not all(
        isinstance(item, dict) and isinstance(item.get("pluginId"), str)
        for item in installed
    ):
        raise CodexPluginInspectionError("Codex plugin inspection failed")
    return frozenset(
        cast(CodexNativePluginEntry, item)["pluginId"] for item in installed
    )


def _marketplace_names(result: object) -> frozenset[str]:
    """Validate native marketplace-list payload and return marketplace names."""
    if not isinstance(result, dict):
        raise CodexPluginInspectionError("Codex plugin inspection failed")
    marketplaces = result.get("marketplaces")
    if not isinstance(marketplaces, list):
        raise CodexPluginInspectionError("Codex plugin inspection failed")
    if not all(
        isinstance(item, dict) and isinstance(item.get("name"), str)
        for item in marketplaces
    ):
        raise CodexPluginInspectionError("Codex plugin inspection failed")
    return frozenset(
        cast(CodexNativeMarketplaceEntry, item)["name"] for item in marketplaces
    )


def install_actions(
    setup: ResolvedSetup, catalog: PluginCatalogProjection, runner: Runner
) -> tuple[InstallAction, ...]:
    """Inspect native Codex state and plan only missing plugin actions."""
    if "codex" in setup.skipped or not setup.is_enabled("codex"):
        return ()
    listed = runner.run(("codex", "plugin", "list", "--json"))
    if listed["returncode"] != 0:
        raise CodexPluginInspectionError("Codex plugin inspection failed")
    try:
        installed = _installed_plugin_ids(strict_json_loads(listed["stdout"]))
    except (
        CodexPluginInspectionError,
        StrictJsonError,
        json.JSONDecodeError,
        UnicodeDecodeError,
    ) as error:
        raise CodexPluginInspectionError("Codex plugin inspection failed") from error
    marketplaces = runner.run(("codex", "plugin", "marketplace", "list", "--json"))
    if marketplaces["returncode"] != 0:
        raise CodexPluginInspectionError("Codex plugin inspection failed")
    try:
        known_marketplaces = _marketplace_names(
            strict_json_loads(marketplaces["stdout"])
        )
    except (
        CodexPluginInspectionError,
        StrictJsonError,
        json.JSONDecodeError,
        UnicodeDecodeError,
    ) as error:
        raise CodexPluginInspectionError("Codex plugin inspection failed") from error
    return plan_codex_plugins(
        catalog,
        installed=installed,
        known_marketplaces=known_marketplaces,
    )


def codex_instruction_renderer(paths: RuntimePaths) -> Renderer:
    """Build the canonical engineering and Codex instruction renderer."""
    engineering = _reviewed_source(
        paths, Path("assistants/shared/instructions/core.md")
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
