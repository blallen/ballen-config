"""Structural tests for the guarded GitHub response workflow."""

from pathlib import Path


def test_github_responder_keeps_mutation_boundaries_ordered(repo_root: Path) -> None:
    """Keep local and remote approvals separate and sequential."""
    text = (
        repo_root / "assistants/shared/skills/respond-to-github-review/SKILL.md"
    ).read_text()
    lower = text.lower()
    positions = [
        lower.index("authorize selected local edits"),
        lower.index("focused verification"),
        lower.index("authorize the exact change description and commit"),
        lower.index("authorize push"),
        lower.index("authorize exact remote replies"),
    ]

    assert positions == sorted(positions)
    assert "resolve-change-scope" in lower
    assert "never bundle commit, push, and reply" in lower
    assert "do not claim completion before focused verification passes" in lower
