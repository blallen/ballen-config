"""Tests for installing the shared review-tool tree."""

from pathlib import Path

from ballen_config.assistants.review_tools import review_tools_contribution
from ballen_config.configure import ManagedTreeSpec, digest_tree


def test_review_tools_are_omitted_when_all_agents_are_disabled(tmp_path: Path) -> None:
    """Do not inspect or install review tools without an enabled agent."""
    contribution = review_tools_contribution(
        repo_root=tmp_path,
        enabled=frozenset(),
    )

    assert contribution.specs == ()


def test_review_tools_use_one_shared_managed_tree(repo_root: Path) -> None:
    """Use one digest-bound tree for every selected native agent."""
    source = repo_root / "assistants/shared/tools/review"
    contribution = review_tools_contribution(
        repo_root=repo_root,
        enabled=frozenset({"cursor", "claude-code", "codex"}),
    )

    assert len(contribution.specs) == 1
    spec = contribution.specs[0]
    assert isinstance(spec, ManagedTreeSpec)
    assert spec.id == "shared-review-tools"
    assert spec.destination == Path(".local/share/ballen-config/review-tools")
    assert spec.expected_source_digest == digest_tree(source)
