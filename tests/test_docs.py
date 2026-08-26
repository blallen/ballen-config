"""Contracts for operational bootstrap documentation structure."""

import re
from pathlib import Path

import pytest

_MARKDOWN_LINK = re.compile(r"\[[^]]+\]\(([^)]+)\)")
_SKIP_LINK_PREFIXES = ("http://", "https://", "mailto:", "#")


def _relative_markdown_targets(text: str) -> tuple[str, ...]:
    """Return in-repo Markdown destinations, ignoring URLs and headings."""
    targets: list[str] = []
    for raw in _MARKDOWN_LINK.findall(text):
        if raw.startswith(_SKIP_LINK_PREFIXES):
            continue
        path = raw.split("#", 1)[0]
        if path:
            targets.append(path)
    return tuple(targets)


def _assert_relative_links_resolve(path: Path, repo_root: Path) -> None:
    """Require every relative Markdown link to stay inside the repository."""
    root = repo_root.resolve()
    for target in _relative_markdown_targets(path.read_text(encoding="utf-8")):
        resolved = (path.parent / target).resolve()
        assert resolved.is_relative_to(root)
        assert resolved.is_file()


def test_readme_keeps_approved_section_headings(repo_root: Path) -> None:
    """README keeps the approved top-level section contract."""
    text = (repo_root / "README.md").read_text(encoding="utf-8")
    assert [line for line in text.splitlines() if line.startswith("## ")] == [
        "## Quick start",
        "## Why this bootstrap is structured this way",
        "## Profiles",
        "## Software choices",
        "## Coding-agent portability",
        "## Security and state boundary",
        "## Manual steps",
    ]


@pytest.mark.parametrize(
    "relative_path",
    (
        pytest.param("README.md", id="readme"),
        pytest.param("docs/manual-steps.md", id="manual-steps"),
        pytest.param("docs/ssh-transfer.md", id="ssh-transfer"),
        pytest.param("AGENTS.md", id="agents"),
        pytest.param("CLAUDE.md", id="claude"),
    ),
)
def test_operational_markdown_links_resolve(
    repo_root: Path, relative_path: str
) -> None:
    """Relative links in live operational Markdown stay in the repository."""
    _assert_relative_links_resolve(repo_root / relative_path, repo_root)


def test_legacy_secret_and_mcp_guidance_is_gone(repo_root: Path) -> None:
    """Operational sources contain no legacy credentials or invented MCP."""
    operational_paths = (
        repo_root / "README.md",
        repo_root / "CLAUDE.md",
        repo_root / "docs/manual-steps.md",
        repo_root / "docs/ssh-transfer.md",
        repo_root / "cursor/extensions.txt",
        repo_root / "cursor/settings.json",
        repo_root / "claude-code/settings.json",
    )
    tracked_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in operational_paths
        if path.exists()
    )
    for forbidden in (
        "<YOUR_GITLAB_TOKEN>",
        "gitlab-mr-mcp",
        "@playwright/mcp",
        "cp ~/.aws",
        "id_ed25519_2025",
    ):
        assert forbidden not in tracked_text
    assert not (repo_root / "cursor/mcp.json").exists()
    assert not (repo_root / "ssh/config").exists()


def test_portable_ssh_config_keeps_public_git_hosts(repo_root: Path) -> None:
    """Keep public Git hosts portable without fixing a machine-specific key."""
    text = (repo_root / "dotfiles/ssh/config").read_text(encoding="utf-8")

    for directive in (
        "Include ~/.ssh/config.local",
        "Host github.com gitlab.com",
        "User git",
        "AddKeysToAgent yes",
        "UseKeychain yes",
    ):
        assert directive in text
    for machine_specific in ("IdentityFile", "HostName", "ProxyJump"):
        assert machine_specific not in text


def test_repository_agents_use_native_instruction_files(repo_root: Path) -> None:
    """Share one native baseline without triple-loading it in Cursor."""
    agents = repo_root / "AGENTS.md"
    claude = repo_root / "CLAUDE.md"
    assert agents.read_text(encoding="utf-8").startswith("# Repository instructions\n")
    assert claude.read_text(encoding="utf-8") == (
        "# Claude Code repository entry\n\n@AGENTS.md\n"
    )
    assert not (repo_root / ".cursor/rules/engineering.mdc").exists()
