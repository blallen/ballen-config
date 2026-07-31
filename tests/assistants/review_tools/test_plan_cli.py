"""Tests for the read-only review-plan command."""

import json
import subprocess
from pathlib import Path

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


def _git_repository(repo: Path) -> str:
    """Create one committed repository with the expected origin."""
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "remote", "add", "origin", "git@github.com:ballen/ballen-config.git")
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
    capsys: object,
) -> None:
    """Expose one stable digest without a provider call."""
    artifact = tmp_path / "plan.json"
    artifact.write_text('{"b": 2, "a": 1}\n')

    assert main(["digest", "--artifact", str(artifact)]) == 0
    assert len(capsys.readouterr().out.strip()) == 64  # type: ignore[attr-defined]


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


def test_compile_response_writes_only_a_validated_plan(tmp_path: Path) -> None:
    """Compile normalized feedback without constructing mutation tooling."""
    repo = tmp_path / "repo"
    head = _git_repository(repo)
    workspace = repo / ".reviews"
    workspace.mkdir()
    threads = repo / "threads.json"
    threads.write_text(
        json.dumps(
            {
                "contract_version": "normalized-review-threads/v1",
                "identity": {
                    "provider": "github",
                    "host": "github.com",
                    "repository": "ballen-config",
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
    draft.write_text(
        """### T001: Guard the empty case

**Classification:** actionable
**Selected action:** propose-change
**Evaluation:** The feedback is valid.
**Evidence:** The empty result is dereferenced.
**Proposed changes:** Add a guard.
**Proposed response:** I will add the guard.
**Verification:** focused test
"""
    )
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
