"""Translate one reviewed RTK hook into agent-native registrations."""

from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import Literal, TypedDict

from ballen_config.assistants.json import strict_json_loads
from ballen_config.configure import (
    ApplyMethod,
    ConfigurationContribution,
    ManagedFileSpec,
    Renderer,
)


class CursorHookEntry(TypedDict):
    """One Cursor hook command and tool matcher."""

    command: str
    matcher: str


class CursorHooks(TypedDict):
    """Cursor hook events."""

    preToolUse: list[CursorHookEntry]


class CursorRegistration(TypedDict):
    """Cursor native hooks document."""

    version: int
    hooks: CursorHooks


class ClaudeCommandHook(TypedDict):
    """One Claude command hook."""

    type: str
    command: str


class ClaudeHookEntry(TypedDict):
    """One Claude tool matcher and its commands."""

    matcher: str
    hooks: list[ClaudeCommandHook]


class ClaudeHooks(TypedDict):
    """Claude hook events."""

    PreToolUse: list[ClaudeHookEntry]


class ClaudeHookFragment(TypedDict):
    """Claude settings fragment consumed by its later adapter."""

    hooks: ClaudeHooks


_STATIC_CURSOR_REGISTRATION: CursorRegistration = {
    "version": 1,
    "hooks": {
        "preToolUse": [
            {
                "command": "~/.local/share/ballen-config/hooks/rtk-hook cursor",
                "matcher": "Shell",
            }
        ]
    },
}
_REVIEWED_HOOK_PATH = "~/.local/share/ballen-config/hooks/rtk-hook"
_REVIEWED_HOOK_PATH_BYTES = _REVIEWED_HOOK_PATH.encode()
_HookAgent = Literal["cursor", "claude"]
_ALLOWED_HOOK_AGENTS: frozenset[str] = frozenset({"cursor", "claude"})
_FORBIDDEN_SOURCE_PARTS = frozenset({"cache", "generated", "machine", "plugins"})


def validate_hook_source(source: Path) -> None:
    """Accept only relative, reviewed hook sources in the canonical tree.

    Args:
        source: Candidate repository-relative hook path.

    Raises:
        ValueError: If the path is absolute, traverses, or represents generated
            or machine-local state.
    """
    normalized_parts = tuple(part.casefold() for part in source.parts)
    if (
        source.is_absolute()
        or ".." in source.parts
        or source.parts[:3] != ("assistants", "shared", "hooks")
        or len(source.parts) <= 3
        or _FORBIDDEN_SOURCE_PARTS.intersection(normalized_parts)
    ):
        raise ValueError("hook must use a reviewed source")


def _quoted_hook_path(home: Path) -> str:
    """Return the absolute hook executable as one shell-safe argument."""
    executable = home / ".local/share/ballen-config/hooks/rtk-hook"
    return shlex.quote(executable.as_posix())


def _hook_command(home: Path, agent: _HookAgent) -> str:
    """Return one injected absolute native hook command."""
    if agent not in _ALLOWED_HOOK_AGENTS:
        raise ValueError("unsupported hook agent")
    return f"{_quoted_hook_path(home)} {agent}"


def cursor_registration(home: Path) -> CursorRegistration:
    """Return Cursor's exact native RTK registration.

    Args:
        home: Injected absolute user home.

    Returns:
        Typed Cursor hooks document.
    """
    return {
        "version": 1,
        "hooks": {
            "preToolUse": [
                {
                    "command": _hook_command(home, "cursor"),
                    "matcher": "Shell",
                }
            ]
        },
    }


def claude_hook_fragment(home: Path) -> ClaudeHookFragment:
    """Return the Claude fragment for its sole settings-file owner.

    Args:
        home: Injected absolute user home.

    Returns:
        Typed Claude settings fragment.
    """
    return {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [
                        {
                            "type": "command",
                            "command": _hook_command(home, "claude"),
                        }
                    ],
                }
            ]
        }
    }


def cursor_hook_renderer(home: Path) -> Renderer:
    """Build a pure renderer for the reviewed Cursor registration source.

    Args:
        home: Injected absolute user home.

    Returns:
        Renderer replacing exactly one reviewed command-path token.
    """

    def render(source: bytes, _current: bytes | None) -> bytes:
        if source.count(_REVIEWED_HOOK_PATH_BYTES) != 1:
            raise ValueError("invalid Cursor hook source")
        try:
            payload = strict_json_loads(source)
        except (UnicodeDecodeError, ValueError) as error:
            raise ValueError("invalid Cursor hook source") from error
        if payload != _STATIC_CURSOR_REGISTRATION:
            raise ValueError("invalid Cursor hook source")
        # Preserve the document while escaping the shell word for its JSON string.
        replacement = json.dumps(_quoted_hook_path(home))[1:-1].encode()
        return source.replace(
            _REVIEWED_HOOK_PATH_BYTES,
            replacement,
            1,
        )

    return render


def hook_contribution(
    *,
    repo_root: Path,
    home: Path,
    enabled: frozenset[str],
) -> ConfigurationContribution:
    """Return shared-program and Cursor registration configuration.

    Args:
        repo_root: Approved checkout root.
        home: Injected absolute user home.
        enabled: Resolved enabled component identifiers.

    Returns:
        Core configuration contribution with no Claude settings owner.
    """
    if not enabled.intersection({"cursor", "claude-code"}):
        return ConfigurationContribution()

    source = Path("assistants/shared/hooks/rtk-hook")
    validate_hook_source(source)
    specs = [
        ManagedFileSpec(
            id="shared-rtk-hook",
            source=repo_root / source,
            destination=Path(".local/share/ballen-config/hooks/rtk-hook"),
            method=ApplyMethod.COPY,
            mode=0o700,
            component="shared",
        )
    ]
    renderers: dict[str, Renderer] = {}
    if "cursor" in enabled:
        specs.append(
            ManagedFileSpec(
                id="cursor-hooks",
                source=repo_root / "assistants/cursor/hooks.json",
                destination=Path(".cursor/hooks.json"),
                method=ApplyMethod.RENDER,
                mode=0o600,
                component="cursor",
                renderer_id="cursor-hooks",
            )
        )
        renderers["cursor-hooks"] = cursor_hook_renderer(home)
    return ConfigurationContribution(
        specs=tuple(specs),
        renderers=renderers,
    )
