"""Tests for the canonical, portable engineering standards library."""

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
REVIEWED_STANDARD_FILES = {"README.md", "provenance.yaml", *TOPIC_FILES}
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


class TopicProvenance(TypedDict):
    """Expected migration provenance for one standards topic."""

    source_paths: list[str]
    disposition: str
    source_roles: NotRequired[dict[str, str]]
    correction_note: NotRequired[str]
    version_review: NotRequired["VersionReview"]


class VersionReview(TypedDict):
    """Expected external-version review mapping in the provenance manifest."""

    product: str
    version: str
    primary_source: str
    release_history: str


class ProvenanceManifest(TypedDict):
    """Expected shared provenance and per-topic migration decisions."""

    source_repository: str
    source_revision: str
    approved_decision: str
    portability_result: str
    review_date: str
    topics: dict[str, TopicProvenance]


def standards_root(repo_root: Path) -> Path:
    """Locate canonical topics independently of repository-rule snapshots."""
    return repo_root / "assistants/shared/standards"


def read_provenance(path: Path) -> ProvenanceManifest:
    """Parse and minimally narrow the standards provenance manifest."""
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)

    topics = loaded.get("topics")
    assert isinstance(topics, dict)
    for topic, provenance in topics.items():
        assert isinstance(topic, str)
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
        version_review = provenance.get("version_review")
        assert version_review is None or isinstance(version_review, dict)
    return cast(ProvenanceManifest, loaded)


def read_topic(path: Path) -> str:
    """Read one canonical topic as normative Markdown."""
    return path.read_text(encoding="utf-8")


def test_standards_directory_contains_only_reviewed_files(
    repo_root: Path,
) -> None:
    """Keep normative standards and their audit record small and explicit."""
    root = standards_root(repo_root)
    assert {path.name for path in root.iterdir() if path.is_file()} == (
        REVIEWED_STANDARD_FILES
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
def test_topic_standard_starts_without_migration_frontmatter(
    repo_root: Path,
    topic: str,
) -> None:
    """Present normative guidance before migration audit metadata."""
    text = read_topic(standards_root(repo_root) / topic)
    assert text.startswith("# ")


@pytest.mark.parametrize("topic", TOPIC_FILES, ids=TOPIC_IDS)
def test_provenance_manifest_records_reviewed_topic_sources(
    repo_root: Path,
    topic: str,
) -> None:
    """Freeze exact reviewed inputs and adaptation decisions per topic."""
    root = standards_root(repo_root)
    manifest = read_provenance(root / "provenance.yaml")
    assert set(manifest) == {
        "source_repository",
        "source_revision",
        "approved_decision",
        "portability_result",
        "review_date",
        "topics",
    }
    assert manifest["source_repository"] == "plato"
    assert manifest["source_revision"] == SOURCE_REVISION
    assert manifest["approved_decision"] == APPROVED_DECISION
    assert manifest["portability_result"] == "portable-after-adaptation"
    assert manifest["review_date"] == "2026-07-27"
    assert set(manifest["topics"]) == set(TOPIC_FILES)

    provenance = manifest["topics"][topic]
    expected_roles = EXPECTED_SOURCE_ROLES.get(topic)
    disposition = "adapted" if topic in ADAPTED_TOPICS else "corrected"
    expected_keys = {"source_paths", "disposition"}
    if expected_roles is not None:
        expected_keys.add("source_roles")
    if disposition == "corrected":
        expected_keys.add("correction_note")
    if topic == "pydantic.md":
        expected_keys.add("version_review")

    assert set(provenance) == expected_keys
    assert tuple(provenance["source_paths"]) == EXPECTED_SOURCE_PATHS[topic]
    assert provenance["disposition"] == disposition
    assert provenance.get("source_roles") == expected_roles
    if disposition == "corrected":
        assert provenance["correction_note"].strip()
    else:
        assert "correction_note" not in provenance


def test_pydantic_standard_records_supported_version_review(
    repo_root: Path,
) -> None:
    """Record the reviewed stable baseline without making it normative."""
    manifest = read_provenance(standards_root(repo_root) / "provenance.yaml")
    review = manifest["topics"]["pydantic.md"].get("version_review")
    assert review == {
        "product": "Pydantic",
        "version": "2.13.4",
        "primary_source": "https://docs.pydantic.dev/latest/migration/",
        "release_history": "https://pypi.org/project/pydantic/#history",
    }
