"""Structural tests for the read-only GitLab MR review skill."""

from pathlib import Path

import yaml


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
