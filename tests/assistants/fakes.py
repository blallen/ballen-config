"""Stateful external-boundary fakes for coding-agent tests."""

import json
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from ballen_config.runner import CommandResult


class StatefulAssistantFake:
    """Stateful runner and downloader for assistant integration tests."""

    def __init__(self, home: Path) -> None:
        """Initialize isolated observable command and download state.

        Args:
            home: Temporary home used for modeled agent-native state.
        """
        self.home = home
        self.results: dict[tuple[str, ...], CommandResult] = {}
        self.commands: list[tuple[str, ...]] = []
        self.downloads: list[tuple[str, Path]] = []
        self.cursor_extensions: set[str] = set()
        self.claude_marketplaces: set[str] = set()
        self.claude_plugins: set[str] = set()
        self.codex_marketplaces: set[str] = set()
        self.codex_plugins: set[str] = set()
        self.payloads: dict[str, bytes] = {}
        self.downloaded_extension_ids: dict[Path, str] = {}
        self.allow_unmodeled_core_commands = False
        self.marketplace_names: dict[str, str] = {
            "anthropics/claude-plugins-official": "claude-plugins-official",
            "obra/superpowers-marketplace": "superpowers-marketplace",
            "mksglu/claude-context-mode": "claude-context-mode",
            "bigspinai/toolkit": "bigspinai",
            "prime-radiant-inc/prime-radiant-marketplace": (
                "prime-radiant-marketplace"
            ),
            "DietrichGebert/ponytail": "ponytail",
            "context-mode": "context-mode",
        }

    def add(
        self,
        command: tuple[str, ...],
        *,
        returncode: int,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        """Register one exact command result.

        Args:
            command: Exact command tuple to match.
            returncode: Captured process status.
            stdout: Captured standard output.
            stderr: Captured standard error.
        """
        self.results[command] = {
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr,
        }

    def add_vsix(
        self,
        *,
        url: str,
        payload: bytes,
        extension_id: str,
        artifact_name: str = "vscode-jj-graph.vsix",
    ) -> None:
        """Register verified bytes and their installed extension identity.

        Args:
            url: Exact HTTPS URL expected by the downloader.
            payload: Bytes returned for the registered URL.
            extension_id: Extension ID installed from the artifact.
            artifact_name: Reviewed local artifact filename.
        """
        self.payloads[url] = payload
        self.downloaded_extension_ids[Path(artifact_name)] = extension_id

    def satisfy_core_commands(self) -> None:
        """Let already-tested core commands succeed without running them."""
        self.allow_unmodeled_core_commands = True

    def add_git_checkout(self, path: Path, *, origin: str, revision: str) -> None:
        """Model one clean checkout already converged to its reviewed revision."""
        (path / ".git").mkdir(parents=True, exist_ok=True)
        prefix = ("git", "-C", str(path))
        self.add(
            (*prefix, "remote", "get-url", "origin"),
            returncode=0,
            stdout=f"{origin}\n",
        )
        self.add((*prefix, "status", "--porcelain"), returncode=0)
        self.add(
            (*prefix, "rev-parse", "HEAD"),
            returncode=0,
            stdout=f"{revision}\n",
        )

    def download(
        self,
        *,
        url: str,
        destination: Path,
        maximum_bytes: int,
    ) -> None:
        """Write only explicitly registered bytes without network access.

        Args:
            url: Exact registered URL.
            destination: Temporary artifact destination.
            maximum_bytes: Maximum accepted payload length.

        Raises:
            KeyError: If the URL or artifact name was not registered.
            ValueError: If the registered payload exceeds the limit.
        """
        payload = self.payloads[url]
        if len(payload) > maximum_bytes:
            raise ValueError("payload exceeds maximum_bytes")
        destination.write_bytes(payload)
        extension_id = self.downloaded_extension_ids[Path(destination.name)]
        self.downloaded_extension_ids[destination] = extension_id
        self.downloads.append((url, destination))

    def _update_claude_settings(
        self,
        *,
        marketplace: tuple[str, str] | None = None,
        plugin: str | None = None,
    ) -> None:
        """Model only the Claude CLI fields future tests must observe."""
        path = self.home / ".claude/settings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = json.loads(path.read_text()) if path.exists() else {}
        if not isinstance(raw, dict):
            raise ValueError("modeled Claude settings must be an object")
        document = cast(dict[str, object], raw)
        if marketplace is not None:
            name, source = marketplace
            raw_marketplaces = document.setdefault("extraKnownMarketplaces", {})
            if not isinstance(raw_marketplaces, dict):
                raise ValueError("modeled marketplaces must be an object")
            marketplaces = cast(dict[str, object], raw_marketplaces)
            marketplaces[name] = {"source": source}
        if plugin is not None:
            raw_plugins = document.setdefault("enabledPlugins", {})
            if not isinstance(raw_plugins, dict):
                raise ValueError("modeled plugins must be an object")
            plugins = cast(dict[str, object], raw_plugins)
            plugins[plugin] = True
        path.write_text(json.dumps(document, indent=2) + "\n")

    def run(self, command: Sequence[str]) -> CommandResult:
        """Run one modeled command and update observable fake state.

        Args:
            command: Captured command and arguments.

        Returns:
            A normalized captured command result.
        """
        normalized = tuple(command)
        self.commands.append(normalized)
        if normalized in self.results:
            return self.results[normalized]
        if normalized == ("cursor", "--list-extensions"):
            return {
                "returncode": 0,
                "stdout": "\n".join(sorted(self.cursor_extensions)),
                "stderr": "",
            }
        if normalized[:2] == ("cursor", "--install-extension"):
            operand = normalized[2]
            extension_id = self.downloaded_extension_ids.get(Path(operand), operand)
            self.cursor_extensions.add(extension_id)
            return {"returncode": 0, "stdout": "", "stderr": ""}
        if normalized == ("claude", "plugin", "list", "--json"):
            payload = [
                {"id": plugin, "scope": "user"}
                for plugin in sorted(self.claude_plugins)
            ]
            return {
                "returncode": 0,
                "stdout": json.dumps(payload),
                "stderr": "",
            }
        if normalized == ("claude", "plugin", "marketplace", "list", "--json"):
            payload = [
                {"name": marketplace}
                for marketplace in sorted(self.claude_marketplaces)
            ]
            return {
                "returncode": 0,
                "stdout": json.dumps(payload),
                "stderr": "",
            }
        if normalized[:4] == ("claude", "plugin", "marketplace", "add"):
            source = normalized[-1]
            name = self.marketplace_names.get(
                source,
                source.rsplit("/", maxsplit=1)[-1].removesuffix(".git"),
            )
            self.claude_marketplaces.add(name)
            self._update_claude_settings(marketplace=(name, source))
            return {"returncode": 0, "stdout": "", "stderr": ""}
        if normalized[:3] == ("claude", "plugin", "install"):
            plugin = normalized[-1]
            self.claude_plugins.add(plugin)
            self._update_claude_settings(plugin=plugin)
            return {"returncode": 0, "stdout": "", "stderr": ""}
        if normalized == ("codex", "plugin", "list", "--json"):
            payload = {
                "installed": [
                    {"pluginId": plugin} for plugin in sorted(self.codex_plugins)
                ],
                "available": [],
            }
            return {
                "returncode": 0,
                "stdout": json.dumps(payload),
                "stderr": "",
            }
        if normalized == ("codex", "plugin", "marketplace", "list", "--json"):
            payload = {
                "marketplaces": [
                    {"name": marketplace}
                    for marketplace in sorted(self.codex_marketplaces)
                ]
            }
            return {
                "returncode": 0,
                "stdout": json.dumps(payload),
                "stderr": "",
            }
        if normalized[:4] == ("codex", "plugin", "marketplace", "add"):
            source = normalized[4]
            codex_names = {
                **self.marketplace_names,
                "mksglu/claude-context-mode": "context-mode",
            }
            name = codex_names.get(
                source,
                source.rsplit("/", maxsplit=1)[-1].removesuffix(".git"),
            )
            self.codex_marketplaces.add(name)
            return {"returncode": 0, "stdout": "{}", "stderr": ""}
        if normalized[:3] == ("codex", "plugin", "add"):
            self.codex_plugins.add(normalized[3])
            return {"returncode": 0, "stdout": "{}", "stderr": ""}
        return {
            "returncode": 0 if self.allow_unmodeled_core_commands else 127,
            "stdout": "",
            "stderr": "",
        }
