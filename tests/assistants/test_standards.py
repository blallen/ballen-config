"""Tests for the canonical, portable engineering standards library."""

from __future__ import annotations

import re
from pathlib import Path
from typing import NotRequired, TypedDict, cast

import pytest
import yaml

TOPIC_FILES = (
    "python.md",
    "pydantic.md",
    "validation.md",
    "api-design.md",
    "testing.md",
    "documentation.md",
    "source-control.md",
    "dependency-management.md",
)
TOPIC_IDS = tuple(Path(topic).stem for topic in TOPIC_FILES)
CANONICAL_DOCUMENTS = {"README.md", *TOPIC_FILES}
SOURCE_REVISION = "6bb59d00ac01fd3238c091d90f2aea43872934c9"  # pragma: allowlist secret
APPROVED_DECISION = (
    "docs/superpowers/specs/2026-07-27-plato-engineering-standards-migration-design.md"
)
LESSONS = (
    ".cursor/rules/lessons_learned.mdc",
    ".cursor/rules/lessons_promoted.mdc",
)
EXPECTED_SOURCE_PATHS = {
    "python.md": (
        "AGENTS.md",
        ".cursor/rules/104_python_style_guide.mdc",
        *LESSONS,
    ),
    "pydantic.md": (
        "AGENTS.md",
        ".cursor/rules/104_pydantic_style_guide.mdc",
        *LESSONS,
    ),
    "validation.md": (
        ".cursor/rules/104_data_validation.mdc",
        ".cursor/rules/104_pydantic_style_guide.mdc",
        *LESSONS,
    ),
    "api-design.md": (
        ".cursor/rules/104_pythonic_apis.mdc",
        *LESSONS,
    ),
    "testing.md": (
        ".cursor/rules/test_rules_macro.mdc",
        ".cursor/rules/test_rules_micro.mdc",
        *LESSONS,
    ),
    "documentation.md": (
        ".cursor/rules/104_python_style_guide.mdc",
        ".cursor/rules/104_pydantic_style_guide.mdc",
        *LESSONS,
    ),
    "source-control.md": (
        "AGENTS.md",
        "skills/jujutsu-workflow/SKILL.md",
        "skills/jujutsu-workflow/reference.md",
    ),
    "dependency-management.md": (
        "AGENTS.md",
        ".cursor/rules/uv.mdc",
        "docs/tooling/uv_workspace_guide.md",
    ),
}
EXPECTED_SOURCE_ROLES = {
    topic: {".cursor/rules/lessons_promoted.mdc": "provenance-only"}
    for topic in (
        "python.md",
        "pydantic.md",
        "validation.md",
        "api-design.md",
        "testing.md",
        "documentation.md",
    )
}
EXPECTED_SOURCE_ROLES["dependency-management.md"] = {
    "docs/tooling/uv_workspace_guide.md": "evidence-after-correction"
}
ADAPTED_TOPICS = {"validation.md"}


class Provenance(TypedDict):
    """Expected provenance mapping parsed from one standards topic."""

    source_repository: str
    source_revision: str
    source_paths: list[str]
    approved_decision: str
    disposition: str
    portability_result: str
    review_date: str
    source_roles: NotRequired[dict[str, str]]
    correction_note: NotRequired[str]


class VersionReview(TypedDict):
    """Expected external-version review mapping in topic frontmatter."""

    product: str
    version: str
    primary_source: str
    release_history: str


class TopicMetadata(TypedDict):
    """Expected frontmatter mapping for one standards topic."""

    provenance: Provenance
    version_review: NotRequired[VersionReview]


PROHIBITED_BODY_PATTERNS = (
    ("stale Pydantic pin", re.compile(r"\bPydantic 2\.8\b", re.IGNORECASE)),
    ("user-specific path", re.compile(r"/Users/")),
    ("Plato import", re.compile(r"\b(?:from|import)\s+plato\b")),
    (
        "internal product or project",
        re.compile(
            r"\b(?:Plato|Autopilot|Avogadro|MechanisticModel|QSP|AMI-\d+|GitLab)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "internal issue or review",
        re.compile(r"\b(?:AGTC-\d+|MR\s*[#!]\d+)\b", re.IGNORECASE),
    ),
    (
        "internal infrastructure",
        re.compile(
            r"\b(?:1Password|AWS Secrets Manager|src/plato)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "agent-charter or skill coupling",
        re.compile(r"(?:docs/agent_charter|plato:skill|plugins/cache)"),
    ),
    (
        "generated assistant state",
        re.compile(
            r"(?:trust_level|"
            r"\.(?:claude|codex|cursor)/(?:sessions|history)|mcp\.json)"
        ),
    ),
    (
        "token-shaped sample",
        re.compile(r"\b(?:sk-|ghp_|glpat-)[A-Za-z0-9_-]{8,}\b"),
    ),
    ("placeholder marker", re.compile(r"\b(?:TODO|TBD|FIXME)\b")),
)


def standards_root(repo_root: Path) -> Path:
    """Locate canonical topics independently of repository-rule snapshots."""
    return repo_root / "assistants/shared/standards"


def read_topic(path: Path) -> tuple[TopicMetadata, str]:
    """Parse and minimally narrow a topic's frontmatter and body."""
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    _, raw_metadata, body = text.split("---", 2)
    loaded = yaml.safe_load(raw_metadata)
    assert isinstance(loaded, dict)

    provenance = loaded.get("provenance")
    assert isinstance(provenance, dict)
    source_paths = provenance.get("source_paths")
    assert isinstance(source_paths, list)
    assert all(isinstance(source_path, str) for source_path in source_paths)
    source_roles = provenance.get("source_roles")
    assert source_roles is None or (
        isinstance(source_roles, dict)
        and all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in source_roles.items()
        )
    )
    version_review = loaded.get("version_review")
    assert version_review is None or isinstance(version_review, dict)
    return cast(TopicMetadata, loaded), body.lstrip()


def test_standards_directory_contains_only_canonical_documents(
    repo_root: Path,
) -> None:
    """Keep the direct standards surface small and explicit."""
    root = standards_root(repo_root)
    assert {path.name for path in root.iterdir() if path.is_file()} == (
        CANONICAL_DOCUMENTS
    )
    assert {path.name for path in root.iterdir() if path.is_dir()} == {"templates"}


@pytest.mark.parametrize("topic", TOPIC_FILES, ids=TOPIC_IDS)
def test_standards_index_links_every_canonical_topic_once(
    repo_root: Path,
    topic: str,
) -> None:
    """Link each normative topic exactly once from the index."""
    text = (standards_root(repo_root) / "README.md").read_text(encoding="utf-8")
    assert text.count(f"]({topic})") == 1


@pytest.mark.parametrize("topic", TOPIC_FILES, ids=TOPIC_IDS)
def test_topic_standard_has_structured_provenance(
    repo_root: Path,
    topic: str,
) -> None:
    """Freeze exact reviewed inputs and adaptation decisions per topic."""
    root = standards_root(repo_root)
    base_keys = {
        "source_repository",
        "source_revision",
        "source_paths",
        "approved_decision",
        "disposition",
        "portability_result",
        "review_date",
    }
    metadata, _ = read_topic(root / topic)
    provenance = metadata["provenance"]
    expected_roles = EXPECTED_SOURCE_ROLES.get(topic)
    disposition = "adapted" if topic in ADAPTED_TOPICS else "corrected"
    expected_keys = set(base_keys)
    if expected_roles is not None:
        expected_keys.add("source_roles")
    if disposition == "corrected":
        expected_keys.add("correction_note")

    assert set(provenance) == expected_keys
    assert provenance["source_repository"] == "plato"
    assert provenance["source_revision"] == SOURCE_REVISION
    assert tuple(provenance["source_paths"]) == EXPECTED_SOURCE_PATHS[topic]
    assert provenance["approved_decision"] == APPROVED_DECISION
    assert provenance["disposition"] == disposition
    assert provenance["portability_result"] == "portable-after-adaptation"
    assert provenance["review_date"] == "2026-07-27"
    assert provenance.get("source_roles") == expected_roles
    if disposition == "corrected":
        assert provenance["correction_note"].strip()
    else:
        assert "correction_note" not in provenance


@pytest.mark.parametrize("topic", TOPIC_FILES, ids=TOPIC_IDS)
def test_topic_standard_body_is_portable(repo_root: Path, topic: str) -> None:
    """Reject stale pins, internal coupling, state, tokens, and placeholders."""
    _, body = read_topic(standards_root(repo_root) / topic)
    for label, pattern in PROHIBITED_BODY_PATTERNS:
        assert pattern.search(body) is None, f"{topic}: {label}"


def test_pydantic_standard_records_supported_version_review(
    repo_root: Path,
) -> None:
    """Record the reviewed stable baseline without making it normative."""
    metadata, _ = read_topic(standards_root(repo_root) / "pydantic.md")
    review = metadata.get("version_review")
    assert review == {
        "product": "Pydantic",
        "version": "2.13.4",
        "primary_source": "https://docs.pydantic.dev/latest/migration/",
        "release_history": "https://pypi.org/project/pydantic/#history",
    }


@pytest.mark.parametrize(
    "topic",
    ("source-control.md", "dependency-management.md"),
    ids=("source-control", "dependency-management"),
)
def test_procedural_standards_do_not_embed_command_recipes(
    repo_root: Path,
    topic: str,
) -> None:
    """Keep tool command recipes for the future skills migration."""
    root = standards_root(repo_root)
    command_fragment = (
        r"(?:jj|git|uv)\s+"
        r"(?:status|diff|log|show|new|bookmark|workspace|run|sync|lock|add|"
        r"remove|commit|checkout|switch|rebase|worktree|branch|stage|push|"
        r"pull|fetch|restore|reset|clean)\b"
    )
    line_recipe = re.compile(
        r"^\s*(?:(?:[-*+]|>|\d+[.)])\s*)*(?:\$\s*)?" + command_fragment,
        re.IGNORECASE | re.MULTILINE,
    )
    inline_recipe = re.compile(
        r"`(?:\$\s*)?" + command_fragment + r"[^`]*`",
        re.IGNORECASE,
    )
    prose_recipe = re.compile(
        r"\b(?:run|execute|invoke|use|try)\s+`?(?:\$\s*)?" + command_fragment,
        re.IGNORECASE,
    )
    shell_fence = re.compile(r"```(?:bash|console|sh|shell|zsh)", re.IGNORECASE)
    _, body = read_topic(root / topic)
    assert shell_fence.search(body) is None
    assert line_recipe.search(body) is None
    assert inline_recipe.search(body) is None
    assert prose_recipe.search(body) is None
