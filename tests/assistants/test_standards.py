"""Tests for the canonical, portable engineering standards library."""

from pathlib import Path, PurePosixPath
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
REVIEWED_STANDARD_FILES = {"README.md", *TOPIC_FILES}
PROVENANCE_MANIFEST = (
    "docs/superpowers/specs/2026-07-27-plato-engineering-standards-provenance.yaml"
)
SOURCE_REVISION = "6bb59d00ac01fd3238c091d90f2aea43872934c9"  # pragma: allowlist secret
APPROVED_DECISION = (
    "docs/superpowers/specs/2026-07-27-plato-engineering-standards-migration-design.md"
)
DISPOSITIONS = {"adapted", "corrected"}
TOPIC_KEYS = {
    "source_paths",
    "disposition",
    "source_roles",
    "correction_note",
    "version_review",
}


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


def read_provenance(repo_root: Path) -> ProvenanceManifest:
    """Parse the audit manifest as a trusted, repository-owned asset."""
    text = (repo_root / PROVENANCE_MANIFEST).read_text(encoding="utf-8")
    loaded = yaml.safe_load(text)
    assert isinstance(loaded, dict)
    return cast(ProvenanceManifest, loaded)


def read_topic(path: Path) -> str:
    """Read one canonical topic as normative Markdown."""
    return path.read_text(encoding="utf-8")


def test_standards_directory_contains_only_reviewed_files(
    repo_root: Path,
) -> None:
    """Ship only normative standards; audit metadata lives with the decision."""
    root = standards_root(repo_root)
    assert {path.name for path in root.iterdir() if path.is_file()} == (
        REVIEWED_STANDARD_FILES
    )
    assert {path.name for path in root.iterdir() if path.is_dir()} == {"templates"}
    assert (repo_root / PROVENANCE_MANIFEST).is_file()


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
    """Pin the reviewed revision and enforce per-topic audit invariants."""
    manifest = read_provenance(repo_root)
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
    assert set(provenance) <= TOPIC_KEYS

    source_paths = provenance["source_paths"]
    assert source_paths
    assert len(set(source_paths)) == len(source_paths)
    for source_path in source_paths:
        pure = PurePosixPath(source_path)
        assert not pure.is_absolute()
        assert ".." not in pure.parts

    roles = provenance.get("source_roles", {})
    assert set(roles) <= set(source_paths)
    assert all(role.strip() for role in roles.values())

    disposition = provenance["disposition"]
    assert disposition in DISPOSITIONS
    if disposition == "corrected":
        assert provenance["correction_note"].strip()
    else:
        assert "correction_note" not in provenance
    if topic != "pydantic.md":
        assert "version_review" not in provenance


def test_pydantic_standard_records_supported_version_review(
    repo_root: Path,
) -> None:
    """Record the reviewed stable baseline without making it normative."""
    manifest = read_provenance(repo_root)
    review = manifest["topics"]["pydantic.md"].get("version_review")
    assert review == {
        "product": "Pydantic",
        "version": "2.13.4",
        "primary_source": "https://docs.pydantic.dev/latest/migration/",
        "release_history": "https://pypi.org/project/pydantic/#history",
    }
