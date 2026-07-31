"""Contract tests for the shared agent-architecture reference library."""

import re
from pathlib import Path, PurePosixPath
from typing import Literal, NotRequired, TypedDict, cast

import pytest
import yaml

SOURCE_REVISION = "0d7699bb0cae3025097718126fcb8e413b6a49e0"  # pragma: allowlist secret
APPROVED_DECISION = (
    "docs/superpowers/specs/2026-07-31-plato-agent-architecture-design.md"
)
PROVENANCE_MANIFEST = Path(
    "docs/superpowers/specs/2026-07-31-plato-agent-architecture-provenance.yaml"
)
LIBRARY_ROOT = Path("assistants/shared/agent-architecture")

SourceDisposition = Literal[
    "extracted",
    "split",
    "profile",
    "template",
    "stub",
    "excluded",
]
DocumentKind = Literal[
    "core",
    "orchestration",
    "delegation",
    "reference-profile",
    "template",
    "stub",
]
Authority = Literal[
    "normative",
    "conditional",
    "informative",
    "non-normative-draft",
]
SourceRole = Literal["primary", "supporting"]


class VersionReview(TypedDict):
    """One dated review of a version-sensitive external product."""

    product: str
    package: str
    version: str
    primary_source: str
    release_history: str
    reviewed_on: str


class SourceRecord(TypedDict):
    """Disposition of one source document."""

    disposition: SourceDisposition
    destinations: NotRequired[list[str]]
    reason: NotRequired[str]


class DestinationRecord(TypedDict):
    """Audit metadata for one destination document."""

    kind: DocumentKind
    authority: Authority
    source_paths: list[str]
    source_roles: dict[str, SourceRole]
    transformation_note: str
    evidence_paths: NotRequired[list[str]]
    version_reviews: NotRequired[list[VersionReview]]


class ProvenanceManifest(TypedDict):
    """Complete source and destination provenance manifest."""

    source_repository: str
    source_revision: str
    approved_decision: str
    portability_result: str
    review_date: str
    source_documents: dict[str, SourceRecord]
    documents: dict[str, DestinationRecord]


SOURCE_DESTINATIONS: dict[str, tuple[SourceDisposition, tuple[str, ...]]] = {
    "docs/agent_charter/README.md": (
        "split",
        ("core/architecture-levels.md", "core/agent-layers.md"),
    ),
    "docs/agent_charter/agent_construction_standard.md": (
        "profile",
        ("reference-profiles/pydantic-ai/construction.md",),
    ),
    "docs/agent_charter/agent_service_pattern.md": (
        "split",
        (
            "core/agent-layers.md",
            "delegation/agent-as-tool.md",
            "reference-profiles/pydantic-ai/services-and-dependencies.md",
        ),
    ),
    "docs/agent_charter/capabilities.md": (
        "split",
        (
            "core/tools-and-capabilities.md",
            "reference-profiles/pydantic-ai/tools-and-capabilities.md",
        ),
    ),
    "docs/agent_charter/demo_apps.md": (
        "profile",
        ("reference-profiles/streamlit-demo-apps.md",),
    ),
    "docs/agent_charter/evals.md": ("extracted", ("core/evaluation.md",)),
    "docs/agent_charter/file_organization.md": (
        "extracted",
        ("core/agent-layers.md",),
    ),
    "docs/agent_charter/maturity_tiers.md": (
        "stub",
        ("stubs/maturity-tiers.md",),
    ),
    "docs/agent_charter/mcp.md": ("extracted", ("core/mcp.md",)),
    "docs/agent_charter/models_exceptions.md": (
        "split",
        (
            "core/models-and-errors.md",
            "reference-profiles/pydantic-ai/construction.md",
        ),
    ),
    "docs/agent_charter/observability_logfire.md": (
        "profile",
        ("reference-profiles/logfire.md",),
    ),
    "docs/agent_charter/readme_templates.md": (
        "template",
        ("templates/readme-templates.md",),
    ),
    "docs/agent_charter/testing.md": ("stub", ("stubs/testing.md",)),
    "docs/agent_charter/tool_design_guidelines.md": (
        "split",
        (
            "core/tools-and-capabilities.md",
            "reference-profiles/pydantic-ai/tools-and-capabilities.md",
        ),
    ),
    "docs/agentic_workflows/README.md": (
        "extracted",
        ("orchestration/director-act-scene.md",),
    ),
    "docs/agentic_workflows/contracts.md": (
        "extracted",
        ("orchestration/handoff-contracts.md",),
    ),
    "docs/agentic_workflows/transitions.md": (
        "split",
        (
            "orchestration/transitions.md",
            "orchestration/persistence-and-resume.md",
        ),
    ),
    "docs/agentic_workflows/anti_patterns.md": (
        "extracted",
        ("orchestration/anti-patterns.md",),
    ),
}

EXCLUDED_SOURCES = {
    "docs/agent_charter/auth_flow.md": (
        "Authentication and internal request flow are outside the portable "
        "reference-library scope."
    ),
    "docs/agent_charter/credentials_config.md": (
        "Credential storage and local configuration are explicitly prohibited "
        "migration material."
    ),
    "docs/agent_charter/todos.md": (
        "Project-specific work tracking is not reference documentation."
    ),
}

CORE_DOCUMENTS = {
    "README.md",
    "core/architecture-levels.md",
    "core/agent-layers.md",
    "core/models-and-errors.md",
    "core/tools-and-capabilities.md",
    "core/mcp.md",
    "core/evaluation.md",
}
ORCHESTRATION_DOCUMENTS = {
    "orchestration/director-act-scene.md",
    "orchestration/handoff-contracts.md",
    "orchestration/transitions.md",
    "orchestration/persistence-and-resume.md",
    "orchestration/anti-patterns.md",
}
DELEGATION_DOCUMENTS = {
    "delegation/agent-as-tool.md",
    "delegation/dynamic-subagents.md",
    "delegation/isolation-matrix.md",
}
PROFILE_DOCUMENTS = {
    "reference-profiles/README.md",
    "reference-profiles/pydantic-ai/README.md",
    "reference-profiles/pydantic-ai/construction.md",
    "reference-profiles/pydantic-ai/services-and-dependencies.md",
    "reference-profiles/pydantic-ai/tools-and-capabilities.md",
    "reference-profiles/logfire.md",
    "reference-profiles/streamlit-demo-apps.md",
}
TEMPLATE_DOCUMENTS = {"templates/readme-templates.md"}
STUB_DOCUMENTS = {"stubs/testing.md", "stubs/maturity-tiers.md"}
ALL_DOCUMENTS = (
    CORE_DOCUMENTS
    | ORCHESTRATION_DOCUMENTS
    | DELEGATION_DOCUMENTS
    | PROFILE_DOCUMENTS
    | TEMPLATE_DOCUMENTS
    | STUB_DOCUMENTS
)

KIND_AND_AUTHORITY = {
    **{path: ("core", "normative") for path in CORE_DOCUMENTS},
    **{
        path: ("orchestration", "normative")
        for path in ORCHESTRATION_DOCUMENTS
    },
    **{path: ("delegation", "normative") for path in DELEGATION_DOCUMENTS},
    **{
        path: ("reference-profile", "conditional") for path in PROFILE_DOCUMENTS
    },
    **{path: ("template", "informative") for path in TEMPLATE_DOCUMENTS},
    **{path: ("stub", "non-normative-draft") for path in STUB_DOCUMENTS},
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
    assert "." not in pure.parts
    assert ".." not in pure.parts
    assert value == pure.as_posix()


def read_document(repo_root: Path, relative_path: str) -> str:
    """Read one canonical library document."""
    return (repo_root / LIBRARY_ROOT / relative_path).read_text(encoding="utf-8")


def assert_document_shape(text: str) -> None:
    """Require one visible title and no migration frontmatter."""
    assert text.startswith("# ")
    assert not text.startswith("---")
    assert sum(line.startswith("# ") for line in text.splitlines()) == 1


def assert_explained_normative_rules(text: str) -> None:
    """Require rationale, scope, and exceptions for each normative rule."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not re.search(r"\b(?:MUST|SHOULD)\b", line):
            continue
        assert line.startswith("Requirement:")
        section_end = len(lines)
        for candidate in range(index + 1, len(lines)):
            if lines[candidate].startswith("#"):
                section_end = candidate
                break
        section = lines[index:section_end]
        assert any(item.startswith("Rationale:") for item in section)
        assert any(item.startswith("Scope:") for item in section)
        assert any(item.startswith("Exceptions:") for item in section)


def test_provenance_records_fixed_program_metadata(repo_root: Path) -> None:
    """Pin the source snapshot and approved portability decision."""
    manifest = load_provenance(repo_root)
    assert list(manifest) == [
        "source_repository",
        "source_revision",
        "approved_decision",
        "portability_result",
        "review_date",
        "source_documents",
        "documents",
    ]
    assert manifest["source_repository"] == "plato"
    assert manifest["source_revision"] == SOURCE_REVISION
    assert manifest["approved_decision"] == APPROVED_DECISION
    assert manifest["portability_result"] == "portable-after-adaptation"
    assert manifest["review_date"] == "2026-07-31"
    assert_relative_posix_path(manifest["approved_decision"])


def test_provenance_accounts_for_every_source_document(repo_root: Path) -> None:
    """Give every source exactly one explicit disposition."""
    manifest = load_provenance(repo_root)
    records = manifest["source_documents"]
    assert set(records) == set(SOURCE_DESTINATIONS) | set(EXCLUDED_SOURCES)

    for source_path, (disposition, destinations) in SOURCE_DESTINATIONS.items():
        assert_relative_posix_path(source_path)
        record = records[source_path]
        assert record == {
            "disposition": disposition,
            "destinations": list(destinations),
        }
        for destination in destinations:
            assert_relative_posix_path(destination)

    for source_path, reason in EXCLUDED_SOURCES.items():
        assert_relative_posix_path(source_path)
        assert records[source_path] == {"disposition": "excluded", "reason": reason}


def test_provenance_accounts_for_every_destination_document(repo_root: Path) -> None:
    """Record one authority and source mapping for every planned document."""
    manifest = load_provenance(repo_root)
    documents = manifest["documents"]
    assert len(ALL_DOCUMENTS) == 25
    assert set(documents) == ALL_DOCUMENTS

    for destination, record in documents.items():
        assert_relative_posix_path(destination)
        assert (record["kind"], record["authority"]) == KIND_AND_AUTHORITY[
            destination
        ]
        assert record["source_paths"]
        assert set(record["source_roles"]) == set(record["source_paths"])
        assert set(record["source_roles"].values()) <= {"primary", "supporting"}
        assert record["transformation_note"].strip()
        for source_path in record["source_paths"]:
            assert_relative_posix_path(source_path)
            assert source_path in manifest["source_documents"]
        for evidence_path in record.get("evidence_paths", []):
            assert_relative_posix_path(evidence_path)


def test_architecture_foundations_define_responsibility_categories(
    repo_root: Path,
) -> None:
    """Replace numeric shorthand with three responsibility categories."""
    text = read_document(repo_root, "core/architecture-levels.md")
    assert_document_shape(text)
    assert_explained_normative_rules(text)
    assert "## Workflow" in text
    assert "## Agent" in text
    assert "## Orchestrator" in text
    assert "fixed specialist" in text
    assert "does not make the parent an Orchestrator" in text
    assert not re.search(r"\bP[0-3]\b", text)


def test_agent_layers_define_inward_dependency_direction(repo_root: Path) -> None:
    """Keep framework mechanics behind stable service boundaries."""
    text = read_document(repo_root, "core/agent-layers.md")
    assert_document_shape(text)
    assert_explained_normative_rules(text)
    for heading in (
        "## Construction",
        "## Models and expected errors",
        "## Tools and capabilities",
        "## Service entry points",
        "## External adapters",
        "## Dependency direction",
        "## Public API",
    ):
        assert heading in text
    assert "validated boundary data" in text
    assert "runtime resources" in text


@pytest.mark.parametrize(
    "relative_path",
    (
        "core/models-and-errors.md",
        "core/tools-and-capabilities.md",
        "core/mcp.md",
        "core/evaluation.md",
    ),
)
def test_remaining_core_documents_are_normative(
    repo_root: Path,
    relative_path: str,
) -> None:
    """Require each framework-neutral core contract and explained rules."""
    text = read_document(repo_root, relative_path)
    assert_document_shape(text)
    assert_explained_normative_rules(text)


def test_models_and_errors_separate_expected_outcomes(repo_root: Path) -> None:
    """Distinguish boundary data, non-completion, and exceptional faults."""
    text = read_document(repo_root, "core/models-and-errors.md")
    for phrase in (
        "validated boundary models",
        "runtime dependency containers",
        "expected non-completion",
        "exceptional faults",
        "partial failure",
        "exception translation",
    ):
        assert phrase in text


def test_tools_and_capabilities_name_effect_and_recovery_contracts(
    repo_root: Path,
) -> None:
    """Make capability grants and consequential effects inspectable."""
    text = read_document(repo_root, "core/tools-and-capabilities.md")
    for phrase in (
        "thin tool wrappers",
        "Read",
        "Write",
        "External message",
        "Destructive",
        "Idempotency",
        "Timeout",
        "Cancellation",
        "Approval",
    ):
        assert phrase in text


def test_mcp_core_remains_framework_neutral(repo_root: Path) -> None:
    """Keep MCP lifecycle and error guidance independent of one SDK."""
    text = read_document(repo_root, "core/mcp.md")
    for phrase in (
        "typed request and response",
        "Capability discovery",
        "registration",
        "transport faults",
        "cancellation",
    ):
        assert phrase in text
    for forbidden in ("RunContext", "Agent(", "MCPServerStdio"):
        assert forbidden not in text


def test_evaluation_separates_quality_dimensions_and_modes(repo_root: Path) -> None:
    """Cover portable evaluation dimensions without fixed thresholds."""
    text = read_document(repo_root, "core/evaluation.md")
    for phrase in (
        "Task success",
        "Structural validity",
        "Factual support",
        "Safety",
        "Latency",
        "Cost",
        "Golden sets",
        "Offline",
        "Pre-release",
        "Production",
        "Judge calibration",
    ):
        assert phrase in text


@pytest.mark.parametrize(
    "relative_path",
    (
        "orchestration/director-act-scene.md",
        "orchestration/handoff-contracts.md",
    ),
)
def test_orchestration_foundations_are_normative(
    repo_root: Path,
    relative_path: str,
) -> None:
    """Require explained contracts for orchestration roles and handoffs."""
    text = read_document(repo_root, relative_path)
    assert_document_shape(text)
    assert_explained_normative_rules(text)


def test_director_act_scene_keeps_primary_metaphor_and_translation(
    repo_root: Path,
) -> None:
    """Translate the metaphor without replacing its primary vocabulary."""
    text = read_document(repo_root, "orchestration/director-act-scene.md")
    for row in (
        "| Director | Control plane or scheduler |",
        "| Act | Bounded stage or handoff boundary |",
        "| Scene | Retryable step or checkpoint |",
    ):
        assert row in text
    assert "orchestration responsibilities" in text
    assert "not three independent model Agents" in text
    assert "Capability confinement" in text
    assert "Resumability" in text
    assert "Gated progress" in text
    assert "Context isolation" in text


def test_handoff_contracts_preserve_typed_status_and_capability_boundaries(
    repo_root: Path,
) -> None:
    """Require explicit entry points, envelopes, and dependencies."""
    text = read_document(repo_root, "orchestration/handoff-contracts.md")
    for phrase in (
        "explicit entry point",
        "Succeeded",
        "Blocked",
        "Failed",
        "summary",
        "artifact references",
        "typed payload",
        "explicitly scoped dependencies",
        "compatibility",
    ):
        assert phrase in text


@pytest.mark.parametrize(
    "relative_path",
    (
        "orchestration/transitions.md",
        "orchestration/persistence-and-resume.md",
        "orchestration/anti-patterns.md",
    ),
)
def test_orchestration_lifecycle_documents_are_normative(
    repo_root: Path,
    relative_path: str,
) -> None:
    """Require explained transition, recovery, and review guidance."""
    text = read_document(repo_root, relative_path)
    assert_document_shape(text)
    assert_explained_normative_rules(text)


def test_transitions_separate_policy_from_mechanism(repo_root: Path) -> None:
    """Define portable outcomes without claiming implementation symbols."""
    text = read_document(repo_root, "orchestration/transitions.md")
    for outcome in ("Advance", "Retry", "Escalate", "Stop"):
        assert f"| {outcome} |" in text
    assert "conceptual outcomes, not required code symbols" in text
    assert "intent, target, and reason" in text
    assert "Policy computes" in text
    assert "mechanism applies" in text


def test_persistence_resumes_through_the_same_control_loop(repo_root: Path) -> None:
    """Persist durable state without serializing live dependencies."""
    text = read_document(repo_root, "orchestration/persistence-and-resume.md")
    for phrase in (
        "durable workflow position",
        "Scene completion",
        "same control loop",
        "stale resume target",
        "attempt identity",
        "Idempotent replay",
        "live dependency objects",
    ):
        assert phrase in text


def test_anti_patterns_pair_symptoms_with_reasons_and_remedies(
    repo_root: Path,
) -> None:
    """Make common orchestration failures actionable."""
    text = read_document(repo_root, "orchestration/anti-patterns.md")
    expected_patterns = (
        "Ambient capabilities",
        "Implicit workspace handoffs",
        "Hidden history sharing",
        "Mixed policy and mechanism",
        "Untyped handoffs",
        "Unbounded retries",
        "Persisted live resources",
        "Agent for every layer",
    )
    for pattern in expected_patterns:
        assert f"## {pattern}" in text
    assert text.count("Symptom:") == len(expected_patterns)
    assert text.count("Why it fails:") == len(expected_patterns)
    assert text.count("Remedy:") == len(expected_patterns)


@pytest.mark.parametrize(
    "relative_path",
    (
        "delegation/agent-as-tool.md",
        "delegation/dynamic-subagents.md",
        "delegation/isolation-matrix.md",
    ),
)
def test_delegation_documents_are_normative(
    repo_root: Path,
    relative_path: str,
) -> None:
    """Require explained static, dynamic, and isolation contracts."""
    text = read_document(repo_root, relative_path)
    assert_document_shape(text)
    assert_explained_normative_rules(text)


@pytest.mark.parametrize(
    "relative_path",
    ("delegation/agent-as-tool.md", "delegation/dynamic-subagents.md"),
)
def test_delegation_requires_explicit_context_and_authority_mapping(
    repo_root: Path,
    relative_path: str,
) -> None:
    """Prevent implicit inheritance across delegated runs."""
    text = read_document(repo_root, relative_path)
    assert "message history is not inherited" in text
    assert "dependencies are not inherited" in text
    assert "resources are not inherited" in text
    assert "permissions are not inherited" in text


def test_agent_as_tool_keeps_static_specialist_boundary(repo_root: Path) -> None:
    """Define fixed typed delegation without inflating architecture level."""
    text = read_document(repo_root, "delegation/agent-as-tool.md")
    for phrase in (
        "predeclared specialist",
        "typed tool boundary",
        "structured output",
        "timeout",
        "cancellation",
        "error translation",
        "does not make the parent an Orchestrator",
    ):
        assert phrase in text


def test_dynamic_subagents_define_runtime_lifecycle(repo_root: Path) -> None:
    """Define runtime worker creation independently of one package."""
    text = read_document(repo_root, "delegation/dynamic-subagents.md")
    for phrase in (
        "runtime creation or selection",
        "independent run identity",
        "context mapping",
        "capability grants",
        "Concurrency",
        "Cancellation",
        "Retry",
        "Persistence",
    ):
        assert phrase in text


def test_isolation_matrix_covers_every_delegation_dimension(repo_root: Path) -> None:
    """Compare explicit defaults for static and dynamic delegation."""
    text = read_document(repo_root, "delegation/isolation-matrix.md")
    for dimension in (
        "Instructions",
        "Message history",
        "Input",
        "Output",
        "Dependencies",
        "Shared resources",
        "Tools",
        "Permissions",
        "Lifecycle",
        "Persistence",
        "Cancellation",
        "Errors",
    ):
        assert f"| {dimension} |" in text
    assert "orthogonal choices" in text
    assert "Director/Act/Scene placement" in text
