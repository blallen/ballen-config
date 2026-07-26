"""Contracts for operational bootstrap documentation."""

from pathlib import Path


def test_readme_contains_exact_operating_rationale(repo_root: Path) -> None:
    """README keeps the approved section contract and software rationale."""
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
    for decision in ("Wave", "MacTeX", "libmagic", "glab"):
        assert decision in text
    for link in (
        "docs/manual-steps.md",
        "docs/ssh-transfer.md",
        "docs/superpowers/specs/2026-07-25-laptop-migration-bootstrap-design.md",
    ):
        assert link in text


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


def test_agent_guardrail_is_short_and_operational(repo_root: Path) -> None:
    """CLAUDE delegates canonical guidance and retains core safety rules."""
    text = (repo_root / "CLAUDE.md").read_text(encoding="utf-8")
    for phrase in (
        "README.md",
        "./bootstrap plan",
        "profiles",
        "skips",
        "never copy credentials",
        "never invent MCP configuration",
        "./bootstrap doctor",
    ):
        assert phrase in text
    assert len(text.splitlines()) <= 20


def test_manual_steps_cover_only_core_handoffs(repo_root: Path) -> None:
    """Manual guidance covers authentication and ends with doctor."""
    text = (repo_root / "docs/manual-steps.md").read_text(encoding="utf-8")
    for phrase in (
        "./bootstrap prepare",
        "gh auth login",
        "glab auth login",
        "./bootstrap doctor --profile work",
        "docs/ssh-transfer.md",
        "IT-managed",
        "full MacTeX",
        "status output",
    ):
        assert phrase in text
    lowered = text.lower()
    for excluded in ("browser", "notion", "atlassian"):
        assert excluded not in lowered


def test_ssh_guide_enforces_secure_transfer_and_modes(repo_root: Path) -> None:
    """SSH guidance prefers new keys and defines secure transfer cleanup."""
    text = (repo_root / "docs/ssh-transfer.md").read_text(encoding="utf-8")
    for phrase in (
        "fresh per-machine key",
        "encrypted local medium",
        "trusted direct connection",
        "plaintext cloud",
        "unencrypted",
        "`0700`",
        "`0600`",
        "`0644`",
        "Keychain",
        "out of band",
        "remove the temporary",
        "never commit",
    ):
        assert phrase in text
