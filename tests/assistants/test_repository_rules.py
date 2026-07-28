"""Tests for passive repository-rule starter templates."""

import re
from pathlib import Path

ENTRY_FILES = {
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
}
ROUTE = (
    "If `docs/engineering-standards/` exists, read the applicable topic "
    "documents before relevant implementation or review work."
)
TOPICS = (
    "README.md",
    "python.md",
    "pydantic.md",
    "validation.md",
    "api-design.md",
    "testing.md",
    "documentation.md",
    "source-control.md",
    "dependency-management.md",
)
TOOLING_FILES = (
    "ruff.toml",
    "mypy.ini",
    "pytest.ini",
    ".pre-commit-config.yaml",
    ".markdownlint.json",
)


def repository_rules_root(repo_root: Path) -> Path:
    """Locate passive native-rule snapshots within the canonical standards tree."""
    return repo_root / "assistants/shared/standards/templates/repository-rules"


def test_repository_rule_templates_share_the_canonical_baseline(
    repo_root: Path,
) -> None:
    """Keep one canonical baseline and a concise Claude Code delegation."""
    root = repository_rules_root(repo_root)
    assert {
        path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()
    } == ENTRY_FILES

    core = (repo_root / "assistants/shared/instructions/core.md").read_text(
        encoding="utf-8"
    )
    expected = f"{core.rstrip()}\n\n{ROUTE}\n"
    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    claude = (root / "CLAUDE.md").read_text(encoding="utf-8")

    assert agents == expected
    assert claude == "# Claude Code repository entry\n\n@AGENTS.md\n"


def test_repository_rule_readme_separates_default_and_all_paths(
    repo_root: Path,
) -> None:
    """Keep Default and All path inventories distinct."""
    root = repository_rules_root(repo_root)
    text = (root / "README.md").read_text(encoding="utf-8")
    default = text.partition("## Default")[2].partition("## All")[0]
    all_mode = text.partition("## All")[2].partition("## Narrower migrations")[0]

    for path in ("AGENTS.md", "CLAUDE.md"):
        assert path in default
    for topic in TOPICS:
        destination = f"docs/engineering-standards/{topic}"
        assert destination not in default
        assert destination in all_mode
    for tooling in TOOLING_FILES:
        assert tooling not in all_mode

    inventory = (repo_root / "assistants/inventory.yaml").read_text(encoding="utf-8")
    assert "templates/repository-rules" not in inventory


def test_all_snapshot_index_links_only_copied_topics(repo_root: Path) -> None:
    """Keep links in the copied standards index within the All inventory."""
    index = (repo_root / "assistants/shared/standards/README.md").read_text(
        encoding="utf-8"
    )
    linked_files = set(re.findall(r"\]\(([^)]+)\)", index))

    assert linked_files == set(TOPICS[1:])
