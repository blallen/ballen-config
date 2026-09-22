"""Structural tests for the guarded GitLab publication skill."""

from pathlib import Path


def test_gitlab_publisher_keeps_preview_and_execute_gates_separate(
    repo_root: Path,
) -> None:
    """Require GitLab-native approval, head, and receipt boundaries."""
    skill = (
        repo_root / "assistants/shared/skills/publish-gitlab-review/SKILL.md"
    ).read_text()
    lower = skill.lower()

    assert lower.index("preview") < lower.index("execute")
    assert "using-gitlab" in lower
    assert "review-gitlab-merge-request" in lower
    assert "diff refs" in lower
    assert "approved plan digest" in lower
    assert "expected head" in lower
    assert "publication receipt" in lower
    assert "partial" in lower
    assert "never resolve" in lower
    assert "publish-github-review" not in lower
