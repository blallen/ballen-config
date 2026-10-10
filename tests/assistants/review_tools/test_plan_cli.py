"""Tests for the read-only review-plan command."""

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Final

import pytest
from ballen_review_tools.canonical import source_digest_bytes
from ballen_review_tools.models import ReviewIdentity
from ballen_review_tools.plan_cli import GitWorkspaceProbe, main


def _git(repo: Path, *arguments: str) -> str:
    """Run one fixed Git command for a temporary repository."""
    result = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def _git_repository(
    repo: Path,
    remote: str = "git@github.com:ballen/ballen-config.git",
) -> str:
    """Create one committed repository with the expected origin."""
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "remote", "add", "origin", remote)
    (repo / ".gitignore").write_text(".reviews/\n")
    (repo / "tracked.txt").write_text("tracked\n")
    _git(repo, "add", ".gitignore", "tracked.txt")
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.email=test@example.com",
            "-c",
            "user.name=Test",
            "commit",
            "-qm",
            "initial",
        ],
        check=True,
    )
    return _git(repo, "rev-parse", "HEAD")


def test_digest_command_prints_canonical_artifact_digest(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Print the digest of the canonical JSON, not of the file bytes."""
    artifact = tmp_path / "plan.json"
    artifact.write_text('{"b": 2, "a": 1}\n')
    canonical = b'{"a":1,"b":2}\n'

    assert main(["digest", "--artifact", str(artifact)]) == 0
    assert capsys.readouterr().out == f"{hashlib.sha256(canonical).hexdigest()}\n"


def test_identity_binds_origin_and_current_head(tmp_path: Path) -> None:
    """Require the local checkout to match the supplied review identity."""
    repo = tmp_path / "repo"
    head = _git_repository(repo)
    identity = ReviewIdentity(
        provider="github",
        host="github.com",
        repository="ballen-config",
        change_number=17,
        base_revision="a" * 40,
        head_revision=head,
    )

    assert GitWorkspaceProbe(repo).identity_matches(identity) == (True, "")


def test_compile_review_rejects_an_origin_host_mismatch(tmp_path: Path) -> None:
    """Refuse to compile a plan for the same repository on another forge host."""
    repo = tmp_path / "repo"
    head = _git_repository(repo)
    (repo / ".reviews").mkdir()
    draft = repo / "review.md"
    draft.write_text(
        "### R001: General note\n\n**Type:** general\n**POST:** NO\n\nContext.\n"
    )
    identity_path = repo / "identity.json"
    identity_path.write_text(
        json.dumps(
            {
                "provider": "github",
                "host": "github.example.com",
                "repository": "ballen/ballen-config",
                "change_number": 17,
                "base_revision": "a" * 40,
                "head_revision": head,
            }
        )
    )
    output = repo / ".reviews" / "review-plan.json"

    with pytest.raises(ValueError, match="origin does not match"):
        main(
            [
                "compile-review",
                "--draft",
                str(draft),
                "--identity",
                str(identity_path),
                "--output",
                str(output),
                "--repo-root",
                str(repo),
            ]
        )
    assert not output.exists()


def test_compile_review_binds_one_draft_byte_snapshot(tmp_path: Path) -> None:
    """Persist the digest of the exact draft bytes parsed for the plan."""
    repo = tmp_path / "repo"
    head = _git_repository(repo)
    workspace = repo / ".reviews"
    workspace.mkdir()
    draft = repo / "review.md"
    draft_bytes = b"""### R001: General note\n\n**Type:** general\n**POST:** NO\n\nKeep this in context.\n"""
    draft.write_bytes(draft_bytes)
    identity_path = repo / "identity.json"
    identity_path.write_text(
        json.dumps(
            {
                "provider": "github",
                "host": "github.com",
                "repository": "ballen-config",
                "change_number": 17,
                "base_revision": "a" * 40,
                "head_revision": head,
            }
        )
    )
    output = workspace / "review-plan.json"

    assert (
        main(
            [
                "compile-review",
                "--draft",
                str(draft),
                "--identity",
                str(identity_path),
                "--output",
                str(output),
                "--repo-root",
                str(repo),
            ]
        )
        == 0
    )
    artifact = json.loads(output.read_text())

    assert artifact["source_draft_digest"] == source_digest_bytes(draft_bytes)
    assert artifact["diagnostics"] == []


RESPONSE_DRAFT: Final[str] = """### T001: Guard the empty case

**Classification:** actionable
**Selected action:** propose-change
**Evaluation:** The feedback is valid.
**Evidence:** The empty result is dereferenced.
**Proposed changes:** Add a guard.
**Proposed response:** I will add the guard.
**Verification:** focused test
"""


def _write_response_inputs(
    repo: Path, *, repository: str, head: str
) -> tuple[Path, Path]:
    """Write one open-thread snapshot and a response draft that answers it.

    Args:
        repo: Repository root that receives `threads.json` and `response.md`.
        repository: Repository named by the snapshot identity.
        head: Head revision the snapshot identity and observed head carry.

    Returns:
        The threads file and the draft file.
    """
    threads = repo / "threads.json"
    threads.write_text(
        json.dumps(
            {
                "contract_version": "normalized-review-threads/v1",
                "identity": {
                    "provider": "github",
                    "host": "github.com",
                    "repository": repository,
                    "change_number": 17,
                    "base_revision": "a" * 40,
                    "head_revision": head,
                },
                "observed_head": head,
                "limitations": [],
                "threads": [
                    {
                        "thread_id": "T001",
                        "comment_ids": ["C001"],
                        "state": "open",
                        "author": "reviewer",
                        "body": "Guard the empty case.",
                        "chronology": ["C001"],
                    }
                ],
            }
        )
    )
    draft = repo / "response.md"
    draft.write_text(RESPONSE_DRAFT)
    return threads, draft


def test_compile_response_writes_a_plan_bound_to_the_threads_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Write the parsed plan with the digest `digest` prints for the threads."""
    repo = tmp_path / "repo"
    head = _git_repository(repo)
    workspace = repo / ".reviews"
    workspace.mkdir()
    threads, draft = _write_response_inputs(repo, repository="ballen-config", head=head)
    output = workspace / "response-plan.json"

    assert (
        main(
            [
                "compile-response",
                "--threads",
                str(threads),
                "--draft",
                str(draft),
                "--output",
                str(output),
                "--repo-root",
                str(repo),
            ]
        )
        == 0
    )
    artifact = json.loads(output.read_text())

    assert artifact["contract_version"] == "review-response-plan/v1"
    assert artifact["items"][0]["selected_action"] == "propose-change"
    assert main(["digest", "--artifact", str(threads)]) == 0
    assert artifact["source_threads_digest"] == capsys.readouterr().out.strip()


@pytest.mark.parametrize(
    ("repository", "head_override", "reason"),
    [
        ("ballen-config", "f" * 40, "head does not match"),
        ("other-repository", None, "origin does not match"),
    ],
)
def test_compile_response_rejects_a_mismatched_identity(
    tmp_path: Path,
    repository: str,
    head_override: str | None,
    reason: str,
) -> None:
    """Refuse to compile a response plan for a different checkout."""
    repo = tmp_path / "repo"
    head = _git_repository(repo)
    workspace = repo / ".reviews"
    workspace.mkdir()
    observed = head_override or head
    threads, draft = _write_response_inputs(repo, repository=repository, head=observed)
    output = workspace / "response-plan.json"

    with pytest.raises(ValueError, match=reason):
        main(
            [
                "compile-response",
                "--threads",
                str(threads),
                "--draft",
                str(draft),
                "--output",
                str(output),
                "--repo-root",
                str(repo),
            ]
        )
    assert not output.exists()


@pytest.mark.parametrize(
    ("payload", "output_directory", "reason"),
    [
        pytest.param(
            ["not", "an", "object"],
            ".reviews",
            "thread input must be a JSON object",
            id="non-object-payload",
        ),
        pytest.param(
            {"review_comments": []},
            ".reviews",
            "thread input must contain head_sha and review_comments",
            id="missing-head-sha",
        ),
        pytest.param(
            {"head_sha": "b" * 40},
            ".reviews",
            "thread input must contain head_sha and review_comments",
            id="missing-review-comments",
        ),
        pytest.param(
            {"head_sha": "b" * 40, "review_comments": []},
            "notes",
            "workspace path is not ignored",
            id="unignored-output-directory",
        ),
    ],
)
def test_normalize_threads_command_rejects_unsafe_input_or_output(
    tmp_path: Path,
    payload: object,
    output_directory: str,
    reason: str,
) -> None:
    """Refuse malformed captures and unsafe destinations before writing."""
    repo = tmp_path / "repo"
    _git_repository(repo)
    (repo / output_directory).mkdir()
    identity = repo / "identity.json"
    identity.write_text(
        json.dumps(
            {
                "provider": "github",
                "host": "github.com",
                "repository": "ballen-config",
                "change_number": 17,
                "base_revision": "a" * 40,
                "head_revision": "b" * 40,
            }
        )
    )
    source = repo / "github-comments.json"
    source.write_text(json.dumps(payload))
    output = repo / output_directory / "threads.json"

    with pytest.raises(ValueError, match=reason):
        main(
            [
                "normalize-threads",
                "--provider",
                "github",
                "--identity",
                str(identity),
                "--input",
                str(source),
                "--output",
                str(output),
                "--repo-root",
                str(repo),
            ]
        )
    assert not output.exists()


def test_normalize_threads_command_writes_provider_neutral_snapshot(
    tmp_path: Path,
) -> None:
    """Normalize supplied GitHub observations without provider mutation."""
    repo = tmp_path / "repo"
    head = _git_repository(repo)
    workspace = repo / ".reviews"
    workspace.mkdir()
    identity = repo / "identity.json"
    identity.write_text(
        json.dumps(
            {
                "provider": "github",
                "host": "github.com",
                "repository": "ballen-config",
                "change_number": 17,
                "base_revision": "a" * 40,
                "head_revision": head,
            }
        )
    )
    source = repo / "github-comments.json"
    source.write_text(
        json.dumps(
            {
                "head_sha": head,
                "review_comments": [
                    {
                        "id": 10,
                        "body": "Guard the empty case.",
                        "user": {"login": "reviewer"},
                    }
                ],
            }
        )
    )
    output = workspace / "threads.json"

    assert (
        main(
            [
                "normalize-threads",
                "--provider",
                "github",
                "--identity",
                str(identity),
                "--input",
                str(source),
                "--output",
                str(output),
                "--repo-root",
                str(repo),
            ]
        )
        == 0
    )
    artifact = json.loads(output.read_text())

    assert artifact["contract_version"] == "normalized-review-threads/v1"
    assert artifact["threads"][0]["thread_id"] == "10"


def test_normalize_gitlab_threads_command_writes_provider_neutral_snapshot(
    tmp_path: Path,
) -> None:
    """Normalize captured GitLab discussions without remote access."""
    repo = tmp_path / "repo"
    head = _git_repository(
        repo,
        "git@gitlab.example.com:acme/ballen-config.git",
    )
    workspace = repo / ".reviews"
    workspace.mkdir()
    identity = repo / "identity.json"
    base = "a" * 40
    start = "b" * 40
    identity.write_text(
        json.dumps(
            {
                "provider": "gitlab",
                "host": "gitlab.example.com",
                "repository": "acme/ballen-config",
                "change_number": 17,
                "base_revision": base,
                "head_revision": head,
            }
        )
    )
    source = repo / "gitlab-discussions.json"
    source.write_text(
        json.dumps(
            {
                "diff_refs": {
                    "base_sha": base,
                    "start_sha": start,
                    "head_sha": head,
                },
                "discussions": [
                    {
                        "id": "discussion-012345",
                        "individual_note": False,
                        "notes": [
                            {
                                "id": 987,
                                "body": "Guard the empty case.",
                                "author": {"username": "reviewer"},
                                "system": False,
                                "position": {
                                    "position_type": "text",
                                    "base_sha": base,
                                    "start_sha": start,
                                    "head_sha": head,
                                    "old_path": "src/example.py",
                                    "new_path": "src/example.py",
                                    "new_line": 42,
                                },
                            }
                        ],
                    }
                ],
            }
        )
    )
    output = workspace / "threads.json"

    assert (
        main(
            [
                "normalize-threads",
                "--provider",
                "gitlab",
                "--identity",
                str(identity),
                "--input",
                str(source),
                "--output",
                str(output),
                "--repo-root",
                str(repo),
            ]
        )
        == 0
    )
    artifact = json.loads(output.read_text())

    assert artifact["identity"]["provider"] == "gitlab"
    assert artifact["threads"][0]["thread_id"] == "discussion-012345"
