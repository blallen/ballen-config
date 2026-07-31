"""Tests for read-only GitLab merge-request discussion normalization."""

import pytest
from ballen_review_tools.models import ReviewIdentity
from ballen_review_tools.providers.gitlab import (
    GitLabDiffRefs,
    GitLabProviderError,
    normalize_gitlab_threads,
)

BASE_SHA = "a" * 40
START_SHA = "b" * 40
HEAD_SHA = "c" * 40
IDENTITY = ReviewIdentity(
    provider="gitlab",
    host="gitlab.example.com",
    repository="acme/ballen-config",
    change_number=17,
    base_revision=BASE_SHA,
    head_revision=HEAD_SHA,
)
DIFF_REFS = GitLabDiffRefs(
    base_sha=BASE_SHA,
    start_sha=START_SHA,
    head_sha=HEAD_SHA,
)


def _position(
    *, head_sha: str = HEAD_SHA, old_line: int | None = None
) -> dict[str, object]:
    """Build one GitLab text position fixture."""
    position: dict[str, object] = {
        "position_type": "text",
        "base_sha": BASE_SHA,
        "start_sha": START_SHA,
        "head_sha": head_sha,
        "old_path": "src/old_example.py",
        "new_path": "src/example.py",
        "new_line": 42,
    }
    if old_line is not None:
        position["old_line"] = old_line
    return position


DISCUSSIONS = [
    {
        "id": "discussion-012345",
        "individual_note": False,
        "notes": [
            {
                "id": 988,
                "body": "A later reply.",
                "author": {"username": "author"},
                "system": False,
                "created_at": "2026-07-30T12:01:00Z",
            },
            {
                "id": 987,
                "body": "Guard the empty case.",
                "author": {"username": "reviewer"},
                "system": False,
                "created_at": "2026-07-30T12:00:00Z",
                "resolvable": True,
                "resolved": False,
                "position": _position(old_line=41),
            },
        ],
    },
    {
        "id": "discussion-resolved",
        "individual_note": False,
        "resolved": True,
        "notes": [
            {
                "id": 989,
                "body": "Already handled.",
                "author": {"username": "reviewer"},
                "system": False,
                "created_at": "2026-07-30T12:02:00Z",
                "position": _position(),
            }
        ],
    },
    {
        "id": "discussion-outdated",
        "individual_note": False,
        "notes": [
            {
                "id": 990,
                "body": "This moved with the diff.",
                "author": {"username": "reviewer"},
                "system": False,
                "created_at": "2026-07-30T12:03:00Z",
                "position": _position(head_sha="d" * 40),
            }
        ],
    },
    {
        "id": "discussion-system",
        "individual_note": True,
        "notes": [
            {
                "id": 991,
                "body": "A system event.",
                "author": {"username": "bot"},
                "system": True,
                "created_at": "2026-07-30T12:04:00Z",
            }
        ],
    },
]


def test_gitlab_normalization_preserves_discussion_identity_and_position() -> None:
    """Keep GitLab discussion IDs, chronology, and current text locations."""
    threads = normalize_gitlab_threads(
        raw_discussions=DISCUSSIONS,
        identity=IDENTITY,
        revisions=DIFF_REFS,
    )

    assert [thread.thread_id for thread in threads.threads] == [
        "discussion-012345",
        "discussion-resolved",
        "discussion-outdated",
    ]
    assert threads.threads[0].state == "open"
    assert threads.threads[0].comment_ids == ("987", "988")
    assert threads.threads[0].path.as_posix() == "src/example.py"  # type: ignore[union-attr]
    assert threads.threads[0].line == 42
    assert threads.threads[0].side == "RIGHT"
    assert threads.threads[1].state == "resolved"
    assert threads.threads[2].state == "outdated"
    assert any(
        "system notes" in limitation.lower() for limitation in threads.limitations
    )


def test_gitlab_normalization_rejects_incomplete_diff_refs() -> None:
    """Reject snapshots that cannot safely identify the MR diff."""
    with pytest.raises(GitLabProviderError, match="diff refs"):
        normalize_gitlab_threads(
            raw_discussions=DISCUSSIONS,
            identity=IDENTITY,
            revisions=GitLabDiffRefs(
                base_sha=BASE_SHA,
                start_sha=START_SHA,
                head_sha="",
            ),
        )


def test_gitlab_normalization_maps_removed_lines_to_old_side() -> None:
    """Preserve a removed-line discussion using GitLab's old path and line."""
    threads = normalize_gitlab_threads(
        raw_discussions=[
            {
                "id": "removed-line",
                "individual_note": False,
                "notes": [
                    {
                        "id": 992,
                        "body": "This removed branch still matters.",
                        "author": {"username": "reviewer"},
                        "system": False,
                        "position": {
                            "position_type": "text",
                            "base_sha": BASE_SHA,
                            "start_sha": START_SHA,
                            "head_sha": HEAD_SHA,
                            "old_path": "src/removed.py",
                            "new_path": "src/removed.py",
                            "old_line": 9,
                        },
                    }
                ],
            },
            {
                "id": "overview-note",
                "individual_note": True,
                "notes": [
                    {
                        "id": 993,
                        "body": "A general MR note.",
                        "author": {"username": "reviewer"},
                        "system": False,
                    }
                ],
            },
        ],
        identity=IDENTITY,
        revisions=DIFF_REFS,
    )

    assert threads.threads[0].path.as_posix() == "src/removed.py"  # type: ignore[union-attr]
    assert threads.threads[0].line == 9
    assert threads.threads[0].side == "LEFT"
    assert threads.threads[1].path is None
