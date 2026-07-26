"""Tests for the redacted tracked-tree portability policy."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from ballen_config.policy import (
    PolicyError,
    Violation,
    main,
    scan_paths,
    scan_tree,
    tracked_paths,
)


def completed(
    command: Sequence[str],
    returncode: int,
    stdout: bytes = b"",
    stderr: bytes = b"",
) -> subprocess.CompletedProcess[bytes]:
    """Build one captured subprocess result."""
    return subprocess.CompletedProcess(command, returncode, stdout, stderr)


def test_violation_is_strict_and_frozen() -> None:
    """Policy findings expose only immutable rule and relative path."""
    with pytest.raises(ValidationError):
        Violation.model_validate(
            {"rule": "private-key", "path": "bad.pem", "content": "secret"}
        )
    violation = Violation(rule="private-key", path="bad.pem")
    with pytest.raises(ValidationError):
        violation.path = "other.pem"


def test_policy_rejects_secret_and_generated_state(tmp_path: Path) -> None:
    """Private-key material and generated state are independently flagged."""
    (tmp_path / "bad.pem").write_text(
        "-----BEGIN " + "OPENSSH PRIVATE KEY-----\nvalue\n"
    )
    (tmp_path / "sessions").mkdir()
    (tmp_path / "sessions/chat.json").write_text("{}")
    violations = scan_paths(
        tmp_path,
        (Path("bad.pem"), Path("sessions/chat.json")),
    )
    assert {(violation.rule, violation.path) for violation in violations} == {
        ("private-key", "bad.pem"),
        ("generated-state", "sessions/chat.json"),
    }


@pytest.mark.parametrize(
    "relative",
    [
        Path("history/item.json"),
        Path("transcripts/item.json"),
        Path("cache/item.json"),
        Path("__pycache__/item.pyc"),
        Path("plugins/cache/item.json"),
        Path("state.sqlite"),
        Path("state.sqlite3"),
        Path("secret.age"),
    ],
)
def test_generated_state_patterns_are_flagged(
    tmp_path: Path,
    relative: Path,
) -> None:
    """Every generated-state path and suffix is rejected."""
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("generated")
    assert scan_paths(tmp_path, (relative,)) == (
        Violation(rule="generated-state", path=relative.as_posix()),
    )


def test_portability_rules_apply_only_to_operational_surfaces(
    tmp_path: Path,
) -> None:
    """Narrative plans may document exclusions that operational files forbid."""
    readme = tmp_path / "README.md"
    readme.write_text("legacy /Users/example/local path")
    plan = tmp_path / "docs/superpowers/plans/example.md"
    plan.parent.mkdir(parents=True)
    plan.write_text("legacy /Users/example/local path and @playwright/mcp")
    violations = scan_paths(
        tmp_path,
        (Path("README.md"), Path("docs/superpowers/plans/example.md")),
    )
    assert violations == (Violation(rule="machine-path", path="README.md"),)


@pytest.mark.parametrize(
    ("relative", "content"),
    [
        ("cursor/mcp.json", "{}"),
        ("assistants/config.json", '{"mcpServers": {}}'),
        ("assistants/config.json", '{"command": "https://mcp.notion.com"}'),
        ("assistants/instructions.md", "import plato"),
        ("assistants/instructions.md", "from avogadro import model"),
        ("assistants/instructions.md", "use this repo-specific helper"),
        ("assistants/config.json", '{"knownMarketplaces": {}}'),
        ("assistants/config.json", '{"trustedFolders": ["/tmp/project"]}'),
    ],
)
def test_core_policy_defers_agent_specific_operational_rules(
    tmp_path: Path,
    relative: str,
    content: str,
) -> None:
    """Leave coding-agent MCP, repository, and trust rules to Agent Task 7."""
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    assert scan_paths(tmp_path, (Path(relative),)) == ()


@pytest.mark.parametrize(
    "content",
    [
        "command: gitlab-mr-mcp",
        "command: @playwright/mcp",
        "token: MR_MCP_GITLAB_TOKEN",
    ],
)
def test_core_policy_rejects_legacy_mcp_strings(
    tmp_path: Path,
    content: str,
) -> None:
    """Keep the legacy MCP exclusions owned by the core bootstrap plan."""
    path = tmp_path / "assistants/config.yaml"
    path.parent.mkdir()
    path.write_text(content)
    assert "forbidden-mcp" in {
        violation.rule
        for violation in scan_paths(tmp_path, (Path("assistants/config.yaml"),))
    }


def test_violations_are_deterministically_sorted(tmp_path: Path) -> None:
    """Violation order is stable regardless of caller path order."""
    (tmp_path / "z.pem").write_text("-----BEGIN " + "RSA PRIVATE KEY-----\nvalue\n")
    (tmp_path / "cache").mkdir()
    (tmp_path / "cache/a").write_text("generated")
    assert scan_paths(
        tmp_path,
        (Path("z.pem"), Path("cache/a")),
    ) == (
        Violation(rule="generated-state", path="cache/a"),
        Violation(rule="private-key", path="z.pem"),
    )


def test_jj_success_enumerates_sorted_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A successful jj listing is authoritative and avoids Git."""
    commands: list[tuple[str, ...]] = []

    def fake_run(
        command: Sequence[str], **_kwargs: Any
    ) -> subprocess.CompletedProcess[bytes]:
        commands.append(tuple(command))
        return completed(command, 0, b"z.txt\na.txt\n", b"native secret")

    monkeypatch.setattr("ballen_config.policy.subprocess.run", fake_run)
    assert tracked_paths(tmp_path) == (Path("a.txt"), Path("z.txt"))
    assert commands == [("jj", "file", "list")]


@pytest.mark.parametrize("jj_mode", ["missing", "failure"])
def test_jj_unavailable_falls_back_to_git(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    jj_mode: str,
) -> None:
    """Missing and failed jj enumeration both use NUL-safe Git fallback."""
    commands: list[tuple[str, ...]] = []

    def fake_run(
        command: Sequence[str], **_kwargs: Any
    ) -> subprocess.CompletedProcess[bytes]:
        normalized = tuple(command)
        commands.append(normalized)
        if normalized[0] == "jj":
            if jj_mode == "missing":
                raise FileNotFoundError
            return completed(command, 1, b"leaked stdout", b"leaked stderr")
        return completed(command, 0, b"z.txt\0a file.txt\0")

    monkeypatch.setattr("ballen_config.policy.subprocess.run", fake_run)
    assert tracked_paths(tmp_path) == (Path("a file.txt"), Path("z.txt"))
    assert commands == [
        ("jj", "file", "list"),
        ("git", "ls-files", "-z"),
    ]


def test_both_enumerators_fail_with_normalized_main_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Enumeration output and exceptions never escape through main."""

    def fake_run(
        command: Sequence[str], **_kwargs: Any
    ) -> subprocess.CompletedProcess[bytes]:
        if command[0] == "jj":
            return completed(command, 1, b"secret stdout", b"secret stderr")
        raise PermissionError("native credential-bearing exception")

    monkeypatch.setattr("ballen_config.policy.subprocess.run", fake_run)
    assert main(tmp_path) == 2
    captured = capsys.readouterr()
    assert captured.out == "policy-error: tracked-tree\n"
    assert captured.err == ""


def test_unsafe_paths_are_refused_without_reading_external_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Absolute, escaping, linked, and special paths fail before any read."""
    root = tmp_path / "checkout"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret"
    secret.write_text("external secret content")
    (root / "parent-link").symlink_to(outside, target_is_directory=True)
    (root / "final-link").symlink_to(secret)
    fifo = root / "pipe"
    os.mkfifo(fifo)

    def forbidden_read(_path: Path) -> bytes:
        raise AssertionError("unsafe path content was read")

    monkeypatch.setattr(Path, "read_bytes", forbidden_read)
    for relative in (
        secret,
        Path("../outside/secret"),
        Path("parent-link/secret"),
        Path("final-link"),
        Path("pipe"),
    ):
        with pytest.raises(PolicyError) as error:
            scan_paths(root, (relative,))
        assert "external secret content" not in str(error.value)


def test_policy_main_reports_rule_and_path_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Return one without echoing matched secret-bearing content."""
    monkeypatch.setattr(
        "ballen_config.policy.scan_tree",
        lambda _root: (Violation(rule="private-key", path="bad.pem"),),
    )
    assert main(tmp_path) == 1
    assert capsys.readouterr().out == "private-key: bad.pem\n"


def test_policy_main_returns_zero_for_clean_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Return zero and print nothing for a clean tracked tree."""
    monkeypatch.setattr("ballen_config.policy.scan_tree", lambda _root: ())
    assert main(tmp_path) == 0
    assert capsys.readouterr().out == ""


def test_repository_passes_policy(repo_root: Path) -> None:
    """The complete working copy satisfies the tracked-tree policy."""
    assert scan_tree(repo_root) == ()


def test_ci_runs_secret_hooks_across_all_files(repo_root: Path) -> None:
    """CI independently enforces both non-mutating credential hooks."""
    workflow = (repo_root / ".github/workflows/ci.yml").read_text()
    for hook in ("detect-secrets", "detect-private-key"):
        assert f"run: uv run --frozen pre-commit run {hook} --all-files" in workflow
