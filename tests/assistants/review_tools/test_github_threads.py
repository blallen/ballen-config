"""Tests for read-only GitHub review-thread normalization."""

from ballen_review_tools.models import ReviewIdentity
from ballen_review_tools.providers.github import normalize_github_comments

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
