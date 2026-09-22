"""Structural tests for the read-only GitLab MR review skill."""

from pathlib import Path

import yaml


def test_gitlab_reviewer_keeps_native_read_only_boundaries(repo_root: Path) -> None:
    """Require GitLab-native terms and the shared normalization boundary."""
    skill = (
        repo_root / "assistants/shared/skills/review-gitlab-merge-request/SKILL.md"
    ).read_text()
    lower = skill.lower()

    assert "starts read-only" in lower
    assert "merge request" in lower
    assert "discussion" in lower
    assert "diff_refs" in skill
    assert "review-plan normalize-threads" in lower
    assert "ignored workspace" in lower
    assert "no remote write" in lower
    assert "using-gitlab" in lower
    assert "discover-project-standards" in lower
    assert "publish-github-review" not in lower
    assert "review-github-pull-request" not in lower


def test_using_gitlab_documents_shared_normalization_boundary(repo_root: Path) -> None:
    """Keep transport ownership in using-gitlab and planning in review-plan."""
    text = (repo_root / "assistants/shared/skills/using-gitlab/SKILL.md").read_text()
    lower = text.lower()

    assert "read-only" in lower
    assert "review-plan normalize-threads" in lower
    assert "never migrate authentication" in lower


def test_gitlab_review_skill_has_no_github_dependency(repo_root: Path) -> None:
    """Keep the GitLab review closure independent from GitHub publication."""
    catalog = yaml.safe_load(
        (repo_root / "assistants/shared/skills/catalog.yaml").read_text()
    )
    by_name = {item["name"]: item for item in catalog["skills"]}

    def closure(name: str) -> set[str]:
        """Return the transitive dependency names for one catalog entry."""
        dependencies = set(by_name[name]["dependencies"])
        for dependency in tuple(dependencies):
            dependencies.update(closure(dependency))
        return dependencies

    projected_dependency_closure = closure("review-gitlab-merge-request")

    assert "using-gitlab" in projected_dependency_closure
    assert "publish-github-review" not in projected_dependency_closure
    assert "review-github-pull-request" not in projected_dependency_closure
