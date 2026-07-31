"""Structural tests for the guarded GitLab response workflow."""

from pathlib import Path


def test_gitlab_responder_keeps_local_and_remote_gates_ordered(
    repo_root: Path,
) -> None:
    """Require five independent gates and GitLab-native response terms."""
    text = (
        repo_root / "assistants/shared/skills/respond-to-gitlab-review/SKILL.md"
    ).read_text()
    lower = text.lower()
    positions = [
        lower.index("authorize selected local edits"),
        lower.index("focused verification"),
        lower.index("authorize the exact change description and commit"),
        lower.index("authorize push"),
        lower.index("preview exact remote replies"),
    ]

    assert positions == sorted(positions)
    assert "using-gitlab" in lower
    assert "publish-gitlab-review" in lower
    assert "never infer remote resolution" in lower
    assert "receipt outcomes" in lower
    assert "do not claim completion before focused verification passes" in lower
    assert "publish-github-review" not in lower
    assert "review-github-pull-request" not in lower
