"""Contract tests for the shared mechanistic-modeling reference library."""

import re
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Literal, NotRequired, TypedDict, cast

import pytest
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
AGENT_ARCHITECTURE_INDEX = Path("assistants/shared/agent-architecture/README.md")

EXPECTED_DOCUMENTS = {
    "README.md",
    "data-layer.md",
    "runtime-layer.md",
    "composition-layer.md",
    "validation-boundaries.md",
}

TERMINOLOGY_DEFINITIONS = (
    "a `MechanisticModel` is the complete structured artifact;",
    "an `Interaction` is a named process;",
    "a `Variable` is a quantity that may be changed, read, or observed;",
    "a `MathTerm` is one atomic contribution to one target equation;",
    "a `Block` groups related model content;",
    "a `Parameter` supplies a named quantity used by the mathematics;",
    "a `ConservationLaw` declares a conserved relationship;",
    "a `MechanisticModelComposer` assembles models and scenario data into one "
    "runnable system; and",
    "a `ModelSolution` carries named simulation results and derived diagnostics.",
)

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


def read_document(repo_root: Path, relative_path: str) -> str:
    """Read one canonical mechanistic-modeling document."""
    return (repo_root / LIBRARY_ROOT / relative_path).read_text(encoding="utf-8")


def local_markdown_targets(text: str) -> list[str]:
    """Extract non-web Markdown link targets from a document."""
    targets: list[str] = []
    for match in re.finditer(r"(?<!!)\[[^]]+\]\(([^)]+)\)", text):
        target = match.group(1).strip()
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        target = target.split("#", maxsplit=1)[0]
        if target:
            targets.append(target)
    return targets


def assert_document_shape(text: str) -> None:
    """Require one visible title and no migration frontmatter."""
    assert not text.startswith("---\n")
    assert len(re.findall(r"^# [^#].+$", text, flags=re.MULTILINE)) == 1


def normalize_whitespace(value: str) -> str:
    """Collapse layout whitespace for exact prose-contract checks."""
    return " ".join(value.split())


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


def test_library_tree_contains_only_expected_regular_files(repo_root: Path) -> None:
    """Keep the passive library small and free of special files."""
    root = repo_root / LIBRARY_ROOT
    actual_paths = {
        path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()
    }
    assert actual_paths == EXPECTED_DOCUMENTS
    for path in root.rglob("*"):
        assert not path.is_symlink()
        assert path.is_file()


def test_every_document_has_one_title_and_no_frontmatter(repo_root: Path) -> None:
    """Keep the library directly readable as ordinary Markdown."""
    for relative_path in EXPECTED_DOCUMENTS:
        assert_document_shape(read_document(repo_root, relative_path))


def test_root_index_links_every_child_exactly_once(repo_root: Path) -> None:
    """Make the root document a complete, unambiguous index."""
    targets = local_markdown_targets(read_document(repo_root, "README.md"))
    for relative_path in EXPECTED_DOCUMENTS - {"README.md"}:
        assert targets.count(relative_path) == 1


def test_all_reader_relative_links_resolve(repo_root: Path) -> None:
    """Require every local reader-facing link to resolve to a regular file."""
    reader_paths = [repo_root / LIBRARY_ROOT / path for path in EXPECTED_DOCUMENTS]
    reader_paths.append(repo_root / AGENT_ARCHITECTURE_INDEX)
    for document_path in reader_paths:
        text = document_path.read_text(encoding="utf-8")
        for target in local_markdown_targets(text):
            resolved = (document_path.parent / target).resolve()
            assert resolved.is_file(), f"broken link in {document_path}: {target}"


@pytest.mark.parametrize("definition", TERMINOLOGY_DEFINITIONS)
def test_root_preserves_exact_terminology(repo_root: Path, definition: str) -> None:
    """Keep approved terms and definitions stable across line wrapping."""
    text = normalize_whitespace(read_document(repo_root, "README.md"))
    assert definition in text


def test_root_explains_scope_layers_and_package_mechanics(repo_root: Path) -> None:
    """Expose the complete conceptual map from the library entry point."""
    text = read_document(repo_root, "README.md")
    for heading in (
        "## Authority and Scope",
        "## Terminology",
        "## Layer Map",
        "## Package Mechanics",
        "## Relationship to Agent Architecture",
        "## Reading Order",
    ):
        assert heading in text


def test_reference_libraries_cross_link_without_nesting_authority(
    repo_root: Path,
) -> None:
    """Keep orchestration and mechanistic semantics as sibling contracts."""
    model_index = read_document(repo_root, "README.md")
    agent_index = (repo_root / AGENT_ARCHITECTURE_INDEX).read_text(encoding="utf-8")
    assert model_index.count("../agent-architecture/README.md") == 1
    assert agent_index.count("../mechanistic-modeling/README.md") == 1
    assert "agent architecture owns orchestration" in model_index.lower()
    assert "mechanistic modeling owns model semantics" in agent_index.lower()


def test_data_layer_preserves_model_semantics(repo_root: Path) -> None:
    """Keep persistent entities and variable roles explicit."""
    text = read_document(repo_root, "data-layer.md")
    for heading in (
        "## Process-Centered Model",
        "## Targeted and External Variables",
        "## Atomic `MathTerm` Contributions",
        "## `Block`, `Parameter`, and `ConservationLaw`",
        "## Entity Provenance",
        "## Derived Views",
        "## Serialization",
        "## Construction Boundary",
    ):
        assert heading in text

    for term in (
        "`MechanisticModel`",
        "`Interaction`",
        "`Variable`",
        "`MathTerm`",
        "`Block`",
        "`Parameter`",
        "`ConservationLaw`",
    ):
        assert term in text

    lowered = text.lower()
    for concept in (
        "targeted variables",
        "external variables",
        "derived equations",
        "variable registry",
        "parameter registry",
        "schema version",
        "entity provenance",
        "extraction provenance",
    ):
        assert concept in lowered


def test_runtime_layer_defines_deterministic_evaluation(repo_root: Path) -> None:
    """Keep evaluator responsibilities and transient state explicit."""
    text = read_document(repo_root, "runtime-layer.md")
    for heading in (
        "## Evaluator Responsibility",
        "## Restricted Mathematical Expressions",
        "## Determinism and Identity",
        "## Rate Accumulation and Ledger",
        "## Runtime Failures",
        "## Transient Runtime State",
    ):
        assert heading in text

    for term in ("`MechanisticModel`", "`MathTerm`", "`Variable`"):
        assert term in text

    lowered = normalize_whitespace(text).lower()
    for concept in (
        "one point in time",
        "per-variable change map",
        "named rate ledger",
        "restricted mathematical expressions",
        "topology weights",
        "transient runtime state",
    ):
        assert concept in lowered
