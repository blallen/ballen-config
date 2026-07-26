"""Translate one reviewed RTK hook into agent-native registrations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

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


def _hook_command(home: Path, agent: str) -> str:
    """Return one injected absolute native hook command."""
    executable = home / ".local/share/ballen-config/hooks/rtk-hook"
    return f"{executable.as_posix()} {agent}"


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
        Renderer replacing only the reviewed command's leading ``~/``.
    """

    def render(source: bytes, _current: bytes | None) -> bytes:
        try:
            payload = json.loads(source)
        except json.JSONDecodeError as error:
            raise ValueError("invalid Cursor hook source") from error
        if payload != _STATIC_CURSOR_REGISTRATION:
            raise ValueError("invalid Cursor hook source")
        return (
            json.dumps(
                cursor_registration(home),
                indent=2,
                sort_keys=True,
            ).encode()
            + b"\n"
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
