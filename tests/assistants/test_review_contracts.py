"""Structural tests for portable review-foundation contract fixtures."""

import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any, Final
from urllib.parse import urlsplit

import pytest

_SHA256_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")
_EXAMPLE_TOP_LEVEL_KEYS: Final[frozenset[str]] = frozenset(
    {
        "contract_version",
        "status",
        "source",
        "request",
        "repository_identity",
        "comparison",
        "workspace_fingerprint",
        "changes",
        "reviewable_diff",
        "coverage",
        "diagnostics",
        "scope_identity",
    }
)
_REVIEW_RESULT_TOP_LEVEL_KEYS: Final[frozenset[str]] = frozenset(
    {
        "contract_version",
        "reviewer",
        "scope_identity",
        "standards_inventory_ref",
        "applicability",
        "outcome",
        "coverage",
        "findings",
        "skips",
        "commands",
        "summary",
    }
)
_REMOTE_CASE_NAMES: Final[frozenset[str]] = frozenset(
    {
        "single_remote",
        "tracked_upstream",
        "origin_fallback",
        "ambiguous_multi_remote",
        "ambiguous_tracked_remotes",
        "no_remote",
    }
)
_CHANGE_TYPES: Final[frozenset[str]] = frozenset({"add", "modify", "delete", "rename"})
_CONTENT_KINDS: Final[frozenset[str]] = frozenset(
    {"text", "binary", "symlink", "submodule", "conflict", "unknown"}
)
_DIFF_STATES: Final[frozenset[str]] = frozenset(
    {"complete", "binary-marker", "unavailable"}
)
_COVERAGE_STATES: Final[frozenset[str]] = frozenset(
    {"complete", "partial", "unavailable"}
)
_PROHIBITED_KEY_TERMS: Final[frozenset[str]] = frozenset(
    {
        "absolute_path",
        "credential",
        "credentials",
        "raw_diff",
        "raw_output",
        "command_output",
        "session",
        "sessions",
        "token",
        "trust",
    }
)


@pytest.fixture
def change_scope_reference_root(repo_root: Path) -> Path:
    """Return the canonical change-scope reference directory."""
    return repo_root / "assistants/shared/skills/resolve-change-scope/references"


def _load_json(path: Path) -> dict[str, Any]:
    """Load a JSON object from a contract fixture."""
    loaded = json.loads(path.read_text())
    assert isinstance(loaded, dict)
    return loaded


def _canonical_sha256(material: object) -> str:
    """Hash canonical UTF-8 JSON with the contract's stable encoding."""
    encoded = json.dumps(
        _normalize_canonical_value(material),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _normalize_canonical_value(value: object) -> object:
    """Normalize strings recursively before canonical JSON serialization."""
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, Mapping):
        return {
            unicodedata.normalize("NFC", key): _normalize_canonical_value(nested)
            for key, nested in value.items()
        }
    if isinstance(value, list):
        return [_normalize_canonical_value(nested) for nested in value]
    return value


def _assert_sha256(value: object) -> None:
    """Require a lowercase hexadecimal SHA-256 value."""
    assert isinstance(value, str)
    assert _SHA256_PATTERN.fullmatch(value)


def _assert_repository_relative_path(value: object) -> None:
    """Require an NFC-normalized repository-relative POSIX path."""
    assert isinstance(value, str)
    assert value == unicodedata.normalize("NFC", value)
    assert "\\" not in value
    path = PurePosixPath(value)
    assert value not in {"", "."}
    assert not path.is_absolute()
    assert ".." not in path.parts


def _assert_comparison_identity(value: object) -> None:
    """Require the exact comparison-identity shape and state coupling."""
    assert isinstance(value, dict)
    assert set(value) == {"state", "value"}
    assert value["state"] in {"resolved", "unavailable"}
    if value["state"] == "resolved":
        assert isinstance(value["value"], str)
        assert value["value"]
    else:
        assert value["value"] is None


def _walk_key_values(value: object) -> list[tuple[str, object]]:
    """Flatten nested mapping keys without interpreting contract prose."""
    pairs: list[tuple[str, object]] = []
    if isinstance(value, Mapping):
        for key, nested in value.items():
            assert isinstance(key, str)
            pairs.append((key, nested))
            pairs.extend(_walk_key_values(nested))
    elif isinstance(value, list):
        for nested in value:
            pairs.extend(_walk_key_values(nested))
    return pairs


def _walk_strings(value: object) -> list[str]:
    """Collect nested string values for portable-value validation."""
    strings: list[str] = []
    if isinstance(value, str):
        strings.append(value)
    elif isinstance(value, Mapping):
        for key, nested in value.items():
            strings.append(key)
            strings.extend(_walk_strings(nested))
    elif isinstance(value, list):
        for nested in value:
            strings.extend(_walk_strings(nested))
    return strings


def _assert_portable_string(value: str) -> None:
    """Reject absolute paths and remote URLs in portable contract values."""
    assert re.search(r"(?<![A-Za-z0-9._~-])/[^\s]+", value) is None
    assert re.search(r"\b[A-Za-z]:[\\/][^\s]*", value) is None
    assert re.search(r"\b[A-Za-z][A-Za-z0-9+.-]*://", value) is None
    assert re.search(r"\b[^@\s]+@[^:\s]+:[^\s]+", value) is None


def _finding_identity_material(
    reviewer: str,
    finding: dict[str, Any],
) -> dict[str, object]:
    """Build the semantic material for a stable finding identity."""
    location = (
        None
        if finding["path"] is None
        else {
            "path": finding["path"],
            "start_line": (
                finding["location"]["start_line"]
                if finding["location"] is not None
                else None
            ),
            "end_line": (
                finding["location"]["end_line"]
                if finding["location"] is not None
                else None
            ),
        }
    )
    evidence = unicodedata.normalize(
        "NFC",
        finding["evidence"].replace("\r\n", "\n").replace("\r", "\n"),
    )
    evidence_digest = hashlib.sha256(evidence.encode()).hexdigest()
    return {
        "reviewer": reviewer,
        "category": finding["category"],
        "rule": finding["rule"],
        "location": location,
        "evidence_digest": evidence_digest,
    }


def _select_remote(case: dict[str, Any]) -> tuple[str | None, str | None]:
    """Apply the contract's non-guessing remote-selection precedence."""
    remotes = case["remotes"]
    remote_names = {remote["name"] for remote in remotes}
    tracked = set(case["tracked_remote_candidates"])
    assert tracked.issubset(remote_names)
    if len(tracked) > 1:
        return None, "repository_identity_ambiguous"
    if tracked:
        return tracked.pop(), None
    if "origin" in remote_names:
        return "origin", None
    if len(remote_names) == 1:
        return next(iter(remote_names)), None
    if not remote_names:
        return None, "repository_identity_no_remote"
    return None, "repository_identity_ambiguous"


def _normalized_remote_material(url: str) -> dict[str, str]:
    """Normalize a credential-free Git URL into path-free identity material."""
    parsed = urlsplit(url)
    assert parsed.scheme in {"http", "https", "ssh"}
    assert parsed.username is None
    assert parsed.password is None
    assert parsed.query == ""
    assert parsed.fragment == ""
    host = parsed.hostname
    assert host is not None
    port = parsed.port
    if port is not None and not (
        (parsed.scheme == "http" and port == 80)
        or (parsed.scheme == "https" and port == 443)
        or (parsed.scheme == "ssh" and port == 22)
    ):
        host = f"{host}:{port}"
    namespace = unicodedata.normalize("NFC", parsed.path.strip("/"))
    if namespace.endswith(".git"):
        namespace = namespace[:-4]
    assert namespace
    return {
        "host": host.lower(),
        "namespace": namespace,
        "vcs": "git",
    }


@pytest.mark.parametrize(
    "value",
    [
        "/tmp/review",
        "output=/tmp/review",
        "see(/tmp/review)",
        r"C:\review\result.json",
        "https://example.invalid/repository",
        "git@example.invalid:owner/repository.git",
    ],
)
def test_portable_string_rejects_absolute_paths_and_remote_urls(value: str) -> None:
    """Reject portable-result leaks regardless of surrounding punctuation."""
    with pytest.raises(AssertionError):
        _assert_portable_string(value)


def test_change_scope_example_is_portable_persisted_projection(
    change_scope_reference_root: Path,
) -> None:
    """Validate the persisted example without pinning human-authored prose."""
    example = _load_json(change_scope_reference_root / "change-scope.example.json")

    assert set(example) == _EXAMPLE_TOP_LEVEL_KEYS
    assert example["contract_version"] == "v1"
    assert example["status"] in {"resolved", "empty", "partial", "blocked"}
    assert example["source"] in {"git", "jujutsu", "supplied"}
    assert set(example["request"]) == {"mode", "selector"}
    assert example["request"]["mode"] in {"current", "explicit", "supplied"}
    assert set(example["repository_identity"]) == {"state", "vcs", "value", "code"}
    assert example["repository_identity"]["state"] in {
        "complete",
        "unavailable",
    }
    assert example["repository_identity"]["vcs"] in {
        "git",
        "jujutsu",
        "supplied",
    }
    if example["repository_identity"]["state"] == "complete":
        _assert_sha256(example["repository_identity"]["value"])
        assert example["repository_identity"]["code"] is None
    else:
        assert example["repository_identity"]["value"] is None
        assert example["repository_identity"]["code"] in {
            "repository_identity_unparseable",
            "repository_identity_ambiguous",
            "repository_identity_no_remote",
        }
    assert set(example["comparison"]) == {
        "kind",
        "base_identities",
        "target_identity",
        "resolved_selector",
    }
    for identity in example["comparison"]["base_identities"]:
        _assert_comparison_identity(identity)
    _assert_comparison_identity(example["comparison"]["target_identity"])
    if example["workspace_fingerprint"] is not None:
        _assert_sha256(example["workspace_fingerprint"])
    _assert_sha256(example["scope_identity"])
    assert set(example["reviewable_diff"]) == {
        "state",
        "format",
        "content",
        "digest",
        "unavailable_paths",
    }
    assert example["reviewable_diff"]["state"] in _COVERAGE_STATES
    assert example["reviewable_diff"]["format"] in {
        "unified",
        "supplied-unified",
        "none",
    }
    if example["reviewable_diff"]["digest"] is not None:
        _assert_sha256(example["reviewable_diff"]["digest"])
    assert example["reviewable_diff"]["content"] is None

    for change in example["changes"]:
        assert set(change) == {
            "path",
            "change_type",
            "previous_path",
            "content_kind",
            "diff_state",
            "content_digest",
        }
        _assert_repository_relative_path(change["path"])
        assert change["change_type"] in _CHANGE_TYPES
        assert change["content_kind"] in _CONTENT_KINDS
        assert change["diff_state"] in _DIFF_STATES
        if change["previous_path"] is not None:
            _assert_repository_relative_path(change["previous_path"])
        if change["content_digest"] is not None:
            _assert_sha256(change["content_digest"])
    for path in example["reviewable_diff"]["unavailable_paths"]:
        _assert_repository_relative_path(path)
    for path in example["coverage"]["unreviewable_paths"]:
        _assert_repository_relative_path(path)
    assert set(example["coverage"]) == {
        "entries",
        "textual_diff",
        "overall",
        "unreviewable_paths",
    }
    assert {
        example["coverage"]["entries"],
        example["coverage"]["textual_diff"],
        example["coverage"]["overall"],
    }.issubset(_COVERAGE_STATES)
    for diagnostic in example["diagnostics"]:
        assert set(diagnostic) == {"code", "path", "detail"}
        assert isinstance(diagnostic["code"], str)
        assert diagnostic["code"]
        assert isinstance(diagnostic["detail"], str)
        assert diagnostic["detail"]
        if diagnostic["path"] is not None:
            _assert_repository_relative_path(diagnostic["path"])

    serialized = json.dumps(example, sort_keys=True)
    assert "/Users/" not in serialized
    assert "\\\\Users\\\\" not in serialized
    assert not {key.casefold() for key, _ in _walk_key_values(example)}.intersection(
        _PROHIBITED_KEY_TERMS
    )


def test_change_scope_vectors_freeze_canonical_identities_and_filename_prefix(
    change_scope_reference_root: Path,
) -> None:
    """Recompute canonical hashes and the shortest unique scope prefix."""
    fixture = _load_json(change_scope_reference_root / "change-scope-vectors.json")
    assert fixture["canonicalization"] == {
        "encoding": "utf-8",
        "ensure_ascii": False,
        "sort_keys": True,
        "separators": [",", ":"],
        "path_normalization": "NFC repository-relative POSIX",
        "digest": "sha256-lowercase-hex",
    }
    vectors = fixture["vectors"]
    assert {vector["purpose"] for vector in vectors} == {
        "workspace_fingerprint",
        "scope_identity",
    }
    for vector in vectors:
        _assert_sha256(vector["expected_sha256"])
        assert _canonical_sha256(vector["material"]) == vector["expected_sha256"]

    unicode_vector = next(
        vector for vector in vectors if vector["name"] == "unicode_path_normalization"
    )
    unicode_path = unicode_vector["material"]["changes"][0]["path"]
    assert unicode_path != unicodedata.normalize("NFC", unicode_path)
    raw_encoded = json.dumps(
        unicode_vector["material"],
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    assert hashlib.sha256(raw_encoded).hexdigest() != unicode_vector["expected_sha256"]

    scope_vector = next(
        vector for vector in vectors if vector["purpose"] == "scope_identity"
    )
    scope_id = scope_vector["expected_sha256"]
    existing_scope_ids = fixture["existing_scope_ids"]
    assert scope_id in existing_scope_ids
    assert all(_SHA256_PATTERN.fullmatch(value) for value in existing_scope_ids)
    expected_prefix = fixture["expected_filename_prefix"]
    assert len(expected_prefix) >= 12
    assert [
        value for value in existing_scope_ids if value.startswith(expected_prefix)
    ] == [scope_id]
    assert (
        len(expected_prefix) == 12
        or len(
            [
                value
                for value in existing_scope_ids
                if value.startswith(expected_prefix[:-1])
            ]
        )
        != 1
    )


def test_change_scope_vectors_freeze_remote_selection_and_identity(
    change_scope_reference_root: Path,
) -> None:
    """Validate remote precedence without falling through ambiguous choices."""
    fixture = _load_json(change_scope_reference_root / "change-scope-vectors.json")
    cases = fixture["repository_identity_cases"]
    assert {case["name"] for case in cases} == _REMOTE_CASE_NAMES

    for case in cases:
        selected_name, diagnostic_code = _select_remote(case)
        assert selected_name == case["expected_selected_name"]
        assert diagnostic_code == case["diagnostic_code"]
        if selected_name is None:
            assert case["expected_state"] == "unavailable"
            assert case["expected_material"] is None
            assert case["expected_identity_digest"] is None
            continue

        assert case["expected_state"] == "complete"
        remote = next(
            remote for remote in case["remotes"] if remote["name"] == selected_name
        )
        material = _normalized_remote_material(remote["url"])
        assert material == case["expected_material"]
        assert _canonical_sha256(material) == case["expected_identity_digest"]


def test_review_result_example_is_portable_and_internally_consistent(
    change_scope_reference_root: Path,
) -> None:
    """Validate the common result envelope without judging review prose."""
    result = _load_json(change_scope_reference_root / "review-result.example.json")

    assert set(result) == _REVIEW_RESULT_TOP_LEVEL_KEYS
    assert result["contract_version"] == "v1"
    assert result["reviewer"] == "review-project-quality"
    _assert_sha256(result["scope_identity"])
    _assert_sha256(result["standards_inventory_ref"])
    assert result["applicability"] in {
        "applicable",
        "not_applicable",
        "unknown",
    }
    assert result["outcome"] in {
        "completed",
        "incomplete",
        "unavailable",
        "blocked",
    }

    coverage = result["coverage"]
    assert set(coverage) == {"scope", "inputs", "checks"}
    assert coverage["scope"] in _COVERAGE_STATES
    assert coverage["inputs"] in _COVERAGE_STATES
    for check in coverage["checks"]:
        assert set(check) == {"check", "required", "selected_scope", "completion"}
        assert isinstance(check["check"], str)
        assert isinstance(check["required"], bool)
        assert check["selected_scope"] in {"changed", "full", "none"}
        assert check["completion"] in {
            "completed",
            "incomplete",
            "unavailable",
            "skipped",
        }

    for finding in result["findings"]:
        assert set(finding) == {
            "finding_id",
            "category",
            "severity",
            "source_severity",
            "path",
            "location",
            "rule",
            "evidence",
            "remediation",
            "contributors",
        }
        _assert_sha256(finding["finding_id"])
        assert finding["severity"] in {"blocker", "actionable", "advisory"}
        if finding["path"] is not None:
            _assert_repository_relative_path(finding["path"])
        else:
            assert finding["location"] is None
        if finding["location"] is not None:
            assert set(finding["location"]) == {"start_line", "end_line"}
            assert finding["location"]["start_line"] >= 1
            assert finding["location"]["start_line"] <= finding["location"]["end_line"]
        assert finding["contributors"] == sorted(set(finding["contributors"]))
        assert finding["contributors"]
        material = _finding_identity_material(result["reviewer"], finding)
        assert _canonical_sha256(material) == finding["finding_id"]

    for skip in result["skips"]:
        assert set(skip) == {"check", "reason", "effect"}
        assert skip["effect"] in {"none", "incomplete", "unavailable", "blocked"}

    for command in result["commands"]:
        assert set(command) == {
            "invocation_id",
            "provenance",
            "selected_scope",
            "completion",
            "exit_status",
            "evidence",
            "unrun_reason",
        }
        _assert_sha256(command["invocation_id"])
        assert command["selected_scope"] in {"changed", "full", "none"}
        provenance_path = command["provenance"].split(":", maxsplit=1)[0]
        _assert_repository_relative_path(provenance_path)
        assert command["completion"] in {
            "completed",
            "incomplete",
            "unavailable",
            "skipped",
        }
        assert command["exit_status"] is None or isinstance(command["exit_status"], int)
        assert "\n" not in command["evidence"]
        if command["completion"] == "completed":
            assert command["exit_status"] is not None
            assert command["unrun_reason"] is None
        else:
            assert command["unrun_reason"] is not None

    counts = result["summary"]["counts"]
    assert set(counts) == {"blocker", "actionable", "advisory"}
    assert counts == {
        severity: sum(finding["severity"] == severity for finding in result["findings"])
        for severity in ("blocker", "actionable", "advisory")
    }
    assert result["summary"]["verdict"] in {
        "blocked",
        "unavailable",
        "incomplete",
        "blockers_found",
        "needs_attention",
        "advisories",
        "clean",
    }
    assert result["summary"]["verdict"] == "needs_attention"

    serialized = json.dumps(result, sort_keys=True)
    assert "/Users/" not in serialized
    assert "\\\\Users\\\\" not in serialized
    for value in _walk_strings(result):
        _assert_portable_string(value)
    assert not {key.casefold() for key, _ in _walk_key_values(result)}.intersection(
        _PROHIBITED_KEY_TERMS
    )


def test_review_result_vectors_freeze_finding_identity(
    change_scope_reference_root: Path,
) -> None:
    """Recompute every stable finding ID from canonical semantic material."""
    fixture = _load_json(change_scope_reference_root / "review-result-vectors.json")

    assert fixture["contract_version"] == "v1"
    assert fixture["vectors"]
    for vector in fixture["vectors"]:
        assert set(vector) == {"name", "material", "expected_sha256"}
        _assert_sha256(vector["expected_sha256"])
        assert _canonical_sha256(vector["material"]) == vector["expected_sha256"]


def test_review_result_vectors_freeze_verdict_precedence(
    change_scope_reference_root: Path,
) -> None:
    """Freeze named precedence cases without implementing a second evaluator."""
    fixture = _load_json(change_scope_reference_root / "review-result-vectors.json")

    vectors = fixture["verdict_vectors"]
    by_name = {vector["name"]: vector for vector in vectors}
    assert {name: vector["expected_verdict"] for name, vector in by_name.items()} == {
        "blocked_precedes_findings": "blocked",
        "unavailable_precedes_blockers": "unavailable",
        "unknown_applicability_is_incomplete": "incomplete",
        "partial_scope_is_incomplete": "incomplete",
        "skip_prevents_clean": "incomplete",
        "unavailable_check_prevents_clean": "unavailable",
        "blocker_finding": "blockers_found",
        "actionable_finding": "needs_attention",
        "advisory_finding": "advisories",
        "clean_requires_complete_coverage": "clean",
    }
    for vector in vectors:
        assert set(vector) == {
            "name",
            "applicability",
            "outcome",
            "coverage",
            "skips",
            "counts",
            "expected_verdict",
        }

    assert by_name["blocked_precedes_findings"]["outcome"] == "blocked"
    assert by_name["blocked_precedes_findings"]["counts"]["actionable"] == 1
    assert by_name["unavailable_precedes_blockers"]["outcome"] == "unavailable"
    assert by_name["unavailable_precedes_blockers"]["counts"]["blocker"] == 1

    clean = by_name["clean_requires_complete_coverage"]
    assert clean["applicability"] == "applicable"
    assert clean["outcome"] == "completed"
    assert clean["coverage"]["scope"] == "complete"
    assert clean["coverage"]["inputs"] == "complete"
    assert all(
        check["completion"] == "completed" for check in clean["coverage"]["checks"]
    )
    assert clean["skips"] == []
    assert clean["counts"] == {"blocker": 0, "actionable": 0, "advisory": 0}
