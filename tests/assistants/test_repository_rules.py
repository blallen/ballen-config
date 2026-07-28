"""Tests for passive repository-rule starter templates."""

from __future__ import annotations

import shutil
from pathlib import Path

ENTRY_FILES = {
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
    ".cursor/rules/engineering.mdc",
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
    """Return the passive repository-rule template root."""
    return repo_root / "assistants/shared/standards/templates/repository-rules"


def test_repository_rule_templates_share_the_canonical_baseline(
    repo_root: Path,
) -> None:
    """Keep all native repository entries aligned with the shared core."""
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
    cursor = (root / ".cursor/rules/engineering.mdc").read_text(encoding="utf-8")
    opening, frontmatter, cursor_body = cursor.split("---", 2)

    assert opening == ""
    assert "alwaysApply: true" in frontmatter
    assert "globs:" in frontmatter
    assert agents == claude == cursor_body.lstrip() == expected
    assert "Pydantic v2" in expected
    assert "Pydantic 2.8" not in expected


def test_repository_rule_readme_defines_passive_copy_modes(
    repo_root: Path,
) -> None:
    """Keep Default, All, and direct-copy behavior explicit and separate."""
    root = repository_rules_root(repo_root)
    text = (root / "README.md").read_text(encoding="utf-8")
    default = text.partition("## Default")[2].partition("## All")[0]
    all_mode = text.partition("## All")[2].partition("## Narrower migrations")[0]

    for path in ("AGENTS.md", "CLAUDE.md", ".cursor/rules/engineering.mdc"):
        assert path in default
    for topic in TOPICS:
        destination = f"docs/engineering-standards/{topic}"
        assert destination not in default
        assert destination in all_mode
    for tooling in TOOLING_FILES:
        assert tooling not in all_mode

    assert "repository-owned snapshot" in text
    assert "merge" in text.casefold()
    assert "There is no installer or file-selector command." in text
    inventory = (repo_root / "assistants/inventory.yaml").read_text(encoding="utf-8")
    assert "templates/repository-rules" not in inventory


def _materialize_repository_rules(
    *,
    repo_root: Path,
    target: Path,
    include_standards: bool,
) -> None:
    """Copy real passive assets without introducing a production installer."""
    template_root = repository_rules_root(repo_root)
    for relative_path in ENTRY_FILES - {"README.md"}:
        destination = target / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(template_root / relative_path, destination)

    if not include_standards:
        return

    standards_root = template_root.parents[1]
    for topic in TOPICS:
        destination = target / "docs/engineering-standards" / topic
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(standards_root / topic, destination)


def test_repository_rule_copy_modes_materialize_expected_layout(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    """Smoke-test Default and All as passive copies of real assets."""
    default_target = tmp_path / "default"
    all_target = tmp_path / "all"
    _materialize_repository_rules(
        repo_root=repo_root,
        target=default_target,
        include_standards=False,
    )
    _materialize_repository_rules(
        repo_root=repo_root,
        target=all_target,
        include_standards=True,
    )

    default_files = {
        path.relative_to(default_target).as_posix()
        for path in default_target.rglob("*")
        if path.is_file()
    }
    expected_default = ENTRY_FILES - {"README.md"}
    assert default_files == expected_default

    all_files = {
        path.relative_to(all_target).as_posix()
        for path in all_target.rglob("*")
        if path.is_file()
    }
    expected_standards = {f"docs/engineering-standards/{topic}" for topic in TOPICS}
    assert all_files == expected_default | expected_standards
    assert {path.name for path in all_target.rglob("*")} & set(TOOLING_FILES) == set()
