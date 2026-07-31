"""Contract tests for the shared mechanistic-modeling reference library."""

from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Literal, NotRequired, TypedDict, cast

import yaml

SOURCE_REVISION = "0fa63b144251ca6b5c6fa99b49151c7e5d5ae276"  # pragma: allowlist secret
REVIEW_DATE = "2026-07-31"
APPROVED_DESIGN = (
    "docs/superpowers/specs/2026-07-31-plato-mechanistic-modeling-design.md"
)
PROVENANCE_MANIFEST = Path(
    "docs/superpowers/specs/2026-07-31-plato-mechanistic-modeling-provenance.yaml"
)
LIBRARY_ROOT = Path("assistants/shared/mechanistic-modeling")

SourceKind = Literal["repository_document", "design_page"]
SourceAuthority = Literal["target_design", "package_contract", "corroboration"]
Disposition = Literal["adapt", "qualify", "exclude", "verify_only"]
DocumentKind = Literal["index", "layer", "validation"]
SourceRole = Literal["primary", "supporting"]
ReviewStatus = Literal["pending", "passed"]


class SourceRepository(TypedDict):
    """One pinned source repository."""

    id: str
    revision: str
    reviewed_on: str


class DesignSource(TypedDict):
    """One privacy-reviewed internal design source."""

    id: str
    title: str
    retrieved_on: str
    locator: str


class SourceRecord(TypedDict):
    """One prose source and its extraction disposition."""

    id: str
    kind: SourceKind
    repository: NotRequired[str]
    path: NotRequired[str]
    locator: NotRequired[str]
    authority: SourceAuthority
    disposition: Disposition
    destinations: list[str]
    notes: str


class RepositoryEvidence(TypedDict):
    """One pinned repository file used only for verification."""

    id: str
    kind: Literal["repository_file"]
    repository: str
    path: str
    revision: str
    claim: str


class WorkItemEvidence(TypedDict):
    """One reviewed work item used only for status verification."""

    id: str
    kind: Literal["work_item"]
    locator: str
    reviewed_on: str
    claim: str


VerificationEvidence = RepositoryEvidence | WorkItemEvidence


class DestinationSource(TypedDict):
    """One source's role in one destination."""

    id: str
    role: SourceRole


class DestinationRecord(TypedDict):
    """Audit metadata for one reader-facing document."""

    id: str
    path: str
    kind: DocumentKind
    authority: Literal["conceptual_contract"]
    sources: list[DestinationSource]
    transformation: str
    exclusions: list[str]
    semantic_review: ReviewStatus
    privacy_review: ReviewStatus


class ReviewRecord(TypedDict):
    """Program-level review result."""

    portability: Literal["portable_after_adaptation"]
    semantic: ReviewStatus
    privacy: ReviewStatus
    approved_on: str | None


class ProvenanceManifest(TypedDict):
    """Complete extraction provenance manifest."""

    schema_version: int
    design: str
    source_repositories: list[SourceRepository]
    design_sources: list[DesignSource]
    sources: list[SourceRecord]
    verification_evidence: list[VerificationEvidence]
    destinations: list[DestinationRecord]
    review: ReviewRecord


EXPECTED_DESIGN_SOURCES = {
    "mechanistic-model-overview": (
        "QSP Wizard Meets Mechanistic Model",
        "notion:364043d22fe38182b0c6c602c82079ae",
    ),
    "mechanistic-model-data-layer": (
        "Data Layer",
        "notion:364043d22fe381c18c90eefe537031b0",
    ),
    "mechanistic-model-runtime-layer": (
        "Runtime Layer",
        "notion:364043d22fe381f39e66d15b7fb143b0",
    ),
    "mechanistic-model-composition-layer": (
        "Composition Layer",
        "notion:364043d22fe381b09129fdb76ff3c818",
    ),
}

SOURCE_DESTINATIONS = {
    "overview-design": {
        "index",
        "data-layer",
        "runtime-layer",
        "composition-layer",
        "validation-boundaries",
    },
    "data-layer-design": {"data-layer", "validation-boundaries"},
    "runtime-layer-design": {"runtime-layer", "validation-boundaries"},
    "composition-layer-design": {
        "composition-layer",
        "validation-boundaries",
    },
    "package-readme": {
        "index",
        "data-layer",
        "runtime-layer",
        "composition-layer",
        "validation-boundaries",
    },
    "crate-readme": {"index", "composition-layer"},
}

EXPECTED_DESTINATIONS = {
    "index": "assistants/shared/mechanistic-modeling/README.md",
    "data-layer": "assistants/shared/mechanistic-modeling/data-layer.md",
    "runtime-layer": "assistants/shared/mechanistic-modeling/runtime-layer.md",
    "composition-layer": "assistants/shared/mechanistic-modeling/composition-layer.md",
    "validation-boundaries": (
        "assistants/shared/mechanistic-modeling/validation-boundaries.md"
    ),
}

DESTINATION_SOURCE_ROLES = {
    "index": {
        "overview-design": "primary",
        "package-readme": "supporting",
        "crate-readme": "supporting",
    },
    "data-layer": {
        "data-layer-design": "primary",
        "overview-design": "supporting",
        "package-readme": "supporting",
    },
    "runtime-layer": {
        "runtime-layer-design": "primary",
        "overview-design": "supporting",
        "package-readme": "supporting",
    },
    "composition-layer": {
        "composition-layer-design": "primary",
        "overview-design": "supporting",
        "package-readme": "supporting",
        "crate-readme": "supporting",
    },
    "validation-boundaries": {
        "overview-design": "primary",
        "data-layer-design": "supporting",
        "runtime-layer-design": "supporting",
        "composition-layer-design": "supporting",
        "package-readme": "supporting",
    },
}


def load_provenance(repo_root: Path) -> ProvenanceManifest:
    """Load the repository-owned audit manifest."""
    loaded = yaml.safe_load(
        (repo_root / PROVENANCE_MANIFEST).read_text(encoding="utf-8")
    )
    assert isinstance(loaded, dict)
    return cast(ProvenanceManifest, loaded)


def assert_relative_posix_path(value: str) -> None:
    """Assert that a manifest path is normalized and repository-relative."""
    pure = PurePosixPath(value)
    assert value
    assert "\\" not in value
    assert not pure.is_absolute()
    assert all(segment not in {"", ".", ".."} for segment in value.split("/"))
    assert value == pure.as_posix()


def index_by_id(
    records: Sequence[Mapping[str, object]],
) -> dict[str, Mapping[str, object]]:
    """Index manifest records while rejecting duplicate IDs."""
    ids = [record.get("id") for record in records]
    assert all(isinstance(record_id, str) and record_id for record_id in ids)
    typed_ids = cast(list[str], ids)
    assert len(typed_ids) == len(set(typed_ids))
    return dict(zip(typed_ids, records, strict=True))


def test_provenance_records_fixed_program_metadata(repo_root: Path) -> None:
    """Pin the approved design and reviewed source snapshot."""
    manifest = load_provenance(repo_root)
    assert list(manifest) == [
        "schema_version",
        "design",
        "source_repositories",
        "design_sources",
        "sources",
        "verification_evidence",
        "destinations",
        "review",
    ]
    assert manifest["schema_version"] == 1
    assert manifest["design"] == APPROVED_DESIGN
    assert manifest["source_repositories"] == [
        {
            "id": "plato",
            "revision": SOURCE_REVISION,
            "reviewed_on": REVIEW_DATE,
        }
    ]
    assert manifest["review"] == {
        "portability": "portable_after_adaptation",
        "semantic": "pending",
        "privacy": "pending",
        "approved_on": None,
    }
    assert_relative_posix_path(manifest["design"])


def test_provenance_records_design_and_verification_sources(repo_root: Path) -> None:
    """Separate prose sources from verification-only evidence."""
    manifest = load_provenance(repo_root)
    design_sources = index_by_id(manifest["design_sources"])
    assert set(design_sources) == set(EXPECTED_DESIGN_SOURCES)
    for source_id, (title, locator) in EXPECTED_DESIGN_SOURCES.items():
        record = design_sources[source_id]
        assert record["title"] == title
        assert record["retrieved_on"] == REVIEW_DATE
        assert record["locator"] == locator

    sources = index_by_id(manifest["sources"])
    assert set(sources) == set(SOURCE_DESTINATIONS)
    for source_id, record in sources.items():
        assert record["destinations"] == sorted(SOURCE_DESTINATIONS[source_id])
        assert isinstance(record["notes"], str) and record["notes"]
        if record["kind"] == "design_page":
            assert set(record) == {
                "id",
                "kind",
                "locator",
                "authority",
                "disposition",
                "destinations",
                "notes",
            }
            assert str(record["locator"]).startswith("notion:")
        else:
            assert set(record) == {
                "id",
                "kind",
                "repository",
                "path",
                "authority",
                "disposition",
                "destinations",
                "notes",
            }
            assert record["repository"] == "plato"
            assert_relative_posix_path(cast(str, record["path"]))

    evidence = index_by_id(manifest["verification_evidence"])
    assert set(evidence) == {"integration-status", "agtc-1038-status"}
    repository_evidence = evidence["integration-status"]
    assert repository_evidence["kind"] == "repository_file"
    assert repository_evidence["repository"] == "plato"
    assert repository_evidence["revision"] == SOURCE_REVISION
    assert_relative_posix_path(cast(str, repository_evidence["path"]))
    work_item_evidence = evidence["agtc-1038-status"]
    assert work_item_evidence["kind"] == "work_item"
    assert work_item_evidence["locator"] == "jira:AGTC-1038"
    assert work_item_evidence["reviewed_on"] == REVIEW_DATE
    for record in evidence.values():
        assert isinstance(record["claim"], str) and record["claim"]


def test_provenance_accounts_for_every_destination(repo_root: Path) -> None:
    """Give every reader document one complete provenance record."""
    manifest = load_provenance(repo_root)
    destinations = index_by_id(manifest["destinations"])
    assert set(destinations) == set(EXPECTED_DESTINATIONS)
    for destination_id, expected_path in EXPECTED_DESTINATIONS.items():
        record = destinations[destination_id]
        assert record["path"] == expected_path
        assert_relative_posix_path(cast(str, record["path"]))
        assert record["authority"] == "conceptual_contract"
        assert record["semantic_review"] == "pending"
        assert record["privacy_review"] == "pending"
        assert isinstance(record["transformation"], str) and record["transformation"]
        assert isinstance(record["exclusions"], list) and record["exclusions"]
        actual_roles = {
            source["id"]: source["role"]
            for source in cast(list[DestinationSource], record["sources"])
        }
        assert actual_roles == DESTINATION_SOURCE_ROLES[destination_id]
        assert list(actual_roles.values()).count("primary") == 1


def test_provenance_source_and_destination_links_are_bidirectional(
    repo_root: Path,
) -> None:
    """Keep source dispositions and destination roles synchronized."""
    manifest = load_provenance(repo_root)
    destinations = index_by_id(manifest["destinations"])
    for source_id, destination_ids in SOURCE_DESTINATIONS.items():
        destinations_naming_source = {
            destination_id
            for destination_id, record in destinations.items()
            if source_id
            in {
                source["id"]
                for source in cast(list[DestinationSource], record["sources"])
            }
        }
        assert destinations_naming_source == destination_ids
