"""Tests for the shared GitHub review skill's provider boundary."""

from pathlib import Path


def test_using_github_owns_transport_but_not_review_contracts(repo_root: Path) -> None:
    """Keep provider selection separate from the shared review tool contract."""
    text = (repo_root / "assistants/shared/skills/using-github/SKILL.md").read_text()

    assert "review-plan" in text
    assert "connected provider" in text
    assert "managed `review-plan` command" in text
    assert "credentials" in text
