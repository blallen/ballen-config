"""Tests for read-only GitHub review-thread normalization."""

from pathlib import PurePosixPath

import pytest
from ballen_review_tools.models import ReviewIdentity
from ballen_review_tools.providers.github import (
    GitHubProviderError,
    normalize_github_comments,
)

IDENTITY = ReviewIdentity(
    provider="github",
    host="github.com",
    repository="acme/ballen-config",
    change_number=17,
    base_revision="a" * 40,
    head_revision="b" * 40,
)


def test_normalization_preserves_root_and_reply_ids() -> None:
    """Keep native review and reply identifiers in chronology."""
    threads = normalize_github_comments(
        identity=IDENTITY,
        head_sha=IDENTITY.head_revision,
        comments=[
            {
                "id": 10,
                "body": "Guard the empty case.",
                "path": "src/example.py",
                "line": 20,
                "side": "RIGHT",
                "user": {"login": "reviewer"},
            },
            {
                "id": 11,
                "body": "I will address this.",
                "in_reply_to_id": 10,
                "user": {"login": "author"},
            },
        ],
    )

    assert len(threads.threads) == 1
    assert threads.threads[0].thread_id == "10"
    assert threads.threads[0].comment_ids == ("10", "11")
    assert threads.threads[0].chronology == ("10", "11")
    assert threads.limitations


def test_normalization_retains_missing_resolution_coverage() -> None:
    """Record REST limitations instead of claiming resolved state."""
    threads = normalize_github_comments(
        identity=IDENTITY,
        head_sha=IDENTITY.head_revision,
        comments=[],
    )

    assert threads.threads == ()
    assert any("resolution" in limitation for limitation in threads.limitations)


def test_outdated_root_comment_normalizes_to_outdated_thread() -> None:
    """Keep outdated comments visible without a stale line position."""
    threads = normalize_github_comments(
        identity=IDENTITY,
        head_sha=IDENTITY.head_revision,
        comments=[
            {
                "id": 20,
                "body": "This line moved.",
                "path": "src/example.py",
                "line": None,
                "original_line": 12,
                "side": "RIGHT",
                "start_line": None,
                "start_side": "RIGHT",
                "user": {"login": "reviewer"},
            }
        ],
    )

    thread = threads.threads[0]
    assert thread.state == "outdated"
    assert thread.path == PurePosixPath("src/example.py")
    assert (thread.line, thread.side, thread.start_line, thread.start_side) == (
        None,
        None,
        None,
        None,
    )
    assert thread.limitations == (
        "Comment no longer maps to a line in the current diff",
    )


def test_normalization_requires_a_github_identity() -> None:
    """Refuse to normalize GitHub comments under another provider's identity."""
    gitlab_identity = IDENTITY.model_copy(update={"provider": "gitlab"})

    with pytest.raises(GitHubProviderError, match="requires a GitHub identity"):
        normalize_github_comments(
            identity=gitlab_identity,
            head_sha=IDENTITY.head_revision,
            comments=[],
        )


def test_file_level_comment_stays_open_without_a_line() -> None:
    """Keep current file-level comments open instead of calling them outdated."""
    threads = normalize_github_comments(
        identity=IDENTITY,
        head_sha=IDENTITY.head_revision,
        comments=[
            {
                "id": 30,
                "body": "Consider splitting this module.",
                "path": "src/example.py",
                "line": None,
                "original_line": None,
                "side": None,
                "subject_type": "file",
                "user": {"login": "reviewer"},
            }
        ],
    )

    thread = threads.threads[0]
    assert thread.state == "open"
    assert thread.path == PurePosixPath("src/example.py")
    assert thread.line is None
    assert thread.limitations == ()
