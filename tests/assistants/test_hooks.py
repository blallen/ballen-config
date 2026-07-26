"""Tests for portable RTK hook adapters."""

from __future__ import annotations

import json
import os
import shlex
import stat
import subprocess
from pathlib import Path

import pytest

from ballen_config.assistants.hooks import (
    claude_hook_fragment,
    cursor_hook_renderer,
    cursor_registration,
    hook_contribution,
    validate_hook_source,
)
from ballen_config.configure import ApplyMethod, ManagedFileSpec


def test_cursor_registration_uses_exact_native_structure(
    temporary_home: Path,
) -> None:
    """Translate the shared shell event to Cursor preToolUse."""
    assert cursor_registration(temporary_home) == {
        "version": 1,
        "hooks": {
            "preToolUse": [
                {
                    "command": (
                        f"{temporary_home}/.local/share/ballen-config/"
                        "hooks/rtk-hook cursor"
                    ),
                    "matcher": "Shell",
                }
            ]
        },
    }


def test_claude_fragment_uses_exact_native_structure(
    temporary_home: Path,
) -> None:
    """Return a fragment while leaving Claude settings ownership elsewhere."""
    assert claude_hook_fragment(temporary_home) == {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [
                        {
                            "type": "command",
                            "command": (
                                f"{temporary_home}/.local/share/ballen-config/"
                                "hooks/rtk-hook claude"
                            ),
                        }
                    ],
                }
            ]
        }
    }


def test_static_cursor_registration_is_exact_and_renderer_is_literal(
    repo_root: Path,
    temporary_home: Path,
) -> None:
    """Replace only the reviewed path token in the authored source bytes."""
    source = (repo_root / "assistants/cursor/hooks.json").read_bytes()
    reviewed_path = b"~/.local/share/ballen-config/hooks/rtk-hook"
    assert json.loads(source) == {
        "version": 1,
        "hooks": {
            "preToolUse": [
                {
                    "command": ("~/.local/share/ballen-config/hooks/rtk-hook cursor"),
                    "matcher": "Shell",
                }
            ]
        },
    }
    assert source.count(reviewed_path) == 1
    absolute_path = (
        temporary_home / ".local/share/ballen-config/hooks/rtk-hook"
    ).as_posix()
    assert shlex.quote(absolute_path) == absolute_path

    rendered = cursor_hook_renderer(temporary_home)(source, None)
    assert rendered == source.replace(reviewed_path, absolute_path.encode(), 1)


def test_native_hook_commands_quote_a_hostile_home_path(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    """Keep shell metacharacters inside one executable-path argument."""
    hostile_home = tmp_path / "home path;$(printf injected)&'"
    absolute_hook = (
        hostile_home / ".local/share/ballen-config/hooks/rtk-hook"
    ).as_posix()
    cursor_command = cursor_registration(hostile_home)["hooks"]["preToolUse"][0][
        "command"
    ]
    claude_command = claude_hook_fragment(hostile_home)["hooks"]["PreToolUse"][0][
        "hooks"
    ][0]["command"]

    assert shlex.split(cursor_command) == [absolute_hook, "cursor"]
    assert shlex.split(claude_command) == [absolute_hook, "claude"]

    source = (repo_root / "assistants/cursor/hooks.json").read_bytes()
    rendered = cursor_hook_renderer(hostile_home)(source, None)
    assert json.loads(rendered) == cursor_registration(hostile_home)


@pytest.mark.parametrize("token_count", [0, 2])
def test_cursor_renderer_rejects_wrong_reviewed_path_token_count(
    repo_root: Path,
    temporary_home: Path,
    token_count: int,
) -> None:
    """Reject semantically equivalent JSON without exactly one literal token."""
    source = (repo_root / "assistants/cursor/hooks.json").read_bytes()
    reviewed_path = b"~/.local/share/ballen-config/hooks/rtk-hook"
    if token_count == 0:
        source = source.replace(
            reviewed_path, b"\\u007e/.local/share/ballen-config/hooks/rtk-hook"
        )
    else:
        command_line = (
            b'        "command": "~/.local/share/ballen-config/hooks/rtk-hook cursor",'
        )
        source = source.replace(command_line, command_line + b"\n" + command_line)

    assert json.loads(source) == {
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
    assert source.count(reviewed_path) == token_count

    with pytest.raises(ValueError, match="invalid Cursor hook source"):
        cursor_hook_renderer(temporary_home)(source, None)


def test_cursor_renderer_rejects_unreviewed_structure(
    repo_root: Path,
    temporary_home: Path,
) -> None:
    """Reject a source document whose native registration was changed."""
    source = (repo_root / "assistants/cursor/hooks.json").read_bytes()
    changed_source = source.replace(b'"matcher": "Shell"', b'"matcher": "Bash"')

    with pytest.raises(ValueError, match="invalid Cursor hook source"):
        cursor_hook_renderer(temporary_home)(changed_source, None)


@pytest.mark.parametrize(
    "source",
    [
        Path("../assistants/shared/hooks/escape"),
        Path("assistants/shared/hooks/../escape"),
        Path("/Users/example/.claude/hooks/generated.sh"),
        Path("assistants/shared/hooks/plugins/cache/generated.sh"),
        Path("assistants/shared/hooks/generated/hook"),
        Path("assistants/shared/hooks/machine/hook"),
        Path(".claude/plugins/cache/context-mode/hook"),
    ],
)
def test_unreviewed_hook_sources_are_rejected(source: Path) -> None:
    """Accept only relative, reviewed hook programs under the canonical root."""
    with pytest.raises(ValueError, match="reviewed source"):
        validate_hook_source(source)


def test_canonical_hook_source_is_accepted() -> None:
    """Allow one repository-relative authored hook path."""
    validate_hook_source(Path("assistants/shared/hooks/rtk-hook"))


@pytest.mark.parametrize(
    ("enabled", "expected_ids"),
    [
        (
            frozenset({"cursor", "claude-code"}),
            {"shared-rtk-hook", "cursor-hooks"},
        ),
        (frozenset({"cursor"}), {"shared-rtk-hook", "cursor-hooks"}),
        (frozenset({"claude-code"}), {"shared-rtk-hook"}),
        (frozenset(), set()),
        (frozenset({"codex"}), set()),
    ],
)
def test_hook_contribution_follows_supported_agent_selection(
    repo_root: Path,
    temporary_home: Path,
    enabled: frozenset[str],
    expected_ids: set[str],
) -> None:
    """Deploy only the shared program and Cursor-owned registration."""
    contribution = hook_contribution(
        repo_root=repo_root,
        home=temporary_home,
        enabled=enabled,
    )
    assert {spec.id for spec in contribution.specs} == expected_ids
    assert all(not spec.destination.is_absolute() for spec in contribution.specs)


def test_hook_specs_use_core_safe_ownership_and_modes(
    repo_root: Path,
    temporary_home: Path,
) -> None:
    """Build one shared executable and one Cursor render specification."""
    contribution = hook_contribution(
        repo_root=repo_root,
        home=temporary_home,
        enabled=frozenset({"cursor", "claude-code"}),
    )
    by_id = {spec.id: spec for spec in contribution.specs}
    shared = by_id["shared-rtk-hook"]
    cursor = by_id["cursor-hooks"]
    assert isinstance(shared, ManagedFileSpec)
    assert isinstance(cursor, ManagedFileSpec)
    assert shared.source == repo_root / "assistants/shared/hooks/rtk-hook"
    assert shared.destination == Path(".local/share/ballen-config/hooks/rtk-hook")
    assert shared.component == "shared"
    assert shared.method is ApplyMethod.COPY
    assert shared.mode == 0o700
    assert cursor.source == repo_root / "assistants/cursor/hooks.json"
    assert cursor.destination == Path(".cursor/hooks.json")
    assert cursor.component == "cursor"
    assert cursor.method is ApplyMethod.RENDER
    assert cursor.mode == 0o600
    assert cursor.renderer_id == "cursor-hooks"
    assert set(contribution.renderers) == {"cursor-hooks"}


def test_hooks_never_own_claude_settings_or_duplicate_cursor_hooks(
    repo_root: Path,
    temporary_home: Path,
) -> None:
    """Keep exactly one Cursor owner and no Claude settings owner."""
    contribution = hook_contribution(
        repo_root=repo_root,
        home=temporary_home,
        enabled=frozenset({"cursor", "claude-code"}),
    )
    destinations = [spec.destination for spec in contribution.specs]
    assert destinations.count(Path(".cursor/hooks.json")) == 1
    assert Path(".claude/settings.json") not in destinations


def test_rtk_hook_is_executable_and_has_valid_zsh_syntax(
    repo_root: Path,
) -> None:
    """Track the authored adapter as an executable, valid Zsh program."""
    hook = repo_root / "assistants/shared/hooks/rtk-hook"
    assert stat.S_IMODE(hook.stat().st_mode) & stat.S_IXUSR
    result = subprocess.run(
        ("zsh", "-n", str(hook)),
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""


@pytest.mark.parametrize("agent", ["cursor", "claude"])
def test_rtk_hook_executes_exact_argv(
    repo_root: Path,
    tmp_path: Path,
    agent: str,
) -> None:
    """Pass only the normalized hook subcommand and selected adapter name."""
    binary_root = tmp_path / "bin"
    binary_root.mkdir()
    fake_rtk = binary_root / "rtk"
    fake_rtk.write_text('#!/bin/zsh\nprint -r -- "$@"\n')
    fake_rtk.chmod(0o700)
    environment = {
        **os.environ,
        "PATH": f"{binary_root}:{os.environ.get('PATH', '')}",
    }
    result = subprocess.run(
        (str(repo_root / "assistants/shared/hooks/rtk-hook"), agent),
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert result.returncode == 0
    assert result.stdout == f"hook {agent}\n"
    assert result.stderr == ""


@pytest.mark.parametrize("arguments", [(), ("codex",), ("cursor", "extra")])
def test_rtk_hook_rejects_invalid_usage(
    repo_root: Path,
    arguments: tuple[str, ...],
) -> None:
    """Return sysexits usage without echoing untrusted arguments."""
    result = subprocess.run(
        (str(repo_root / "assistants/shared/hooks/rtk-hook"), *arguments),
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 64
    assert result.stdout == ""
    assert result.stderr == "usage: rtk-hook cursor|claude\n"
