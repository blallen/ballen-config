"""Tests for read-only GitLab merge-request discussion normalization."""

from pathlib import PurePosixPath
from typing import Final

import pytest
from ballen_review_tools.models import ReviewIdentity
from ballen_review_tools.providers.gitlab import (
    GitLabDiffRefs,
    GitLabProviderError,
    normalize_gitlab_threads,
)

BASE_SHA: Final[str] = "a" * 40
START_SHA: Final[str] = "b" * 40
HEAD_SHA: Final[str] = "c" * 40
IDENTITY: Final[ReviewIdentity] = ReviewIdentity(
    provider="gitlab",
    host="gitlab.example.com",
    repository="acme/ballen-config",
    change_number=17,
    base_revision=BASE_SHA,
    head_revision=HEAD_SHA,
)
DIFF_REFS: Final[GitLabDiffRefs] = GitLabDiffRefs(
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


def _discussions() -> list[object]:
    """Return fresh GitLab discussions covering each normalization case."""
    return [
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
            "notes": [
                {
                    "id": 989,
                    "body": "Already handled.",
                    "author": {"username": "reviewer"},
                    "system": False,
                    "created_at": "2026-07-30T12:02:00Z",
                    "resolvable": True,
                    "resolved": True,
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
        raw_discussions=_discussions(),
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
    assert threads.threads[0].path == PurePosixPath("src/example.py")
    assert threads.threads[0].line == 42
    assert threads.threads[0].side == "RIGHT"
    assert threads.threads[1].state == "resolved"
    assert threads.threads[2].state == "outdated"
    assert any(
        "system notes" in limitation.lower() for limitation in threads.limitations
    )


def test_gitlab_diff_refs_reject_an_empty_sha() -> None:
    """Reject diff refs that cannot identify the MR diff."""
    with pytest.raises(GitLabProviderError, match="GitLab diff refs are incomplete"):
        GitLabDiffRefs(base_sha=BASE_SHA, start_sha=START_SHA, head_sha="")


@pytest.mark.parametrize(
    "revisions",
    [
        pytest.param(
            GitLabDiffRefs(base_sha="d" * 40, start_sha=START_SHA, head_sha=HEAD_SHA),
            id="base",
        ),
        pytest.param(
            GitLabDiffRefs(base_sha=BASE_SHA, start_sha=START_SHA, head_sha="d" * 40),
            id="head",
        ),
    ],
)
def test_gitlab_normalization_rejects_diff_refs_that_differ_from_identity(
    revisions: GitLabDiffRefs,
) -> None:
    """Reject complete diff refs whose base or head is not the identity's."""
    with pytest.raises(
        GitLabProviderError, match="GitLab diff refs do not match review identity"
    ):
        normalize_gitlab_threads(
            raw_discussions=_discussions(),
            identity=IDENTITY,
            revisions=revisions,
        )


def test_gitlab_normalization_rejects_non_gitlab_identity() -> None:
    """Reject an identity from another provider."""
    with pytest.raises(
        GitLabProviderError, match="GitLab normalization requires a GitLab identity"
    ):
        normalize_gitlab_threads(
            raw_discussions=_discussions(),
            identity=IDENTITY.model_copy(update={"provider": "github"}),
            revisions=DIFF_REFS,
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

    assert threads.threads[0].path == PurePosixPath("src/removed.py")
    assert threads.threads[0].line == 9
    assert threads.threads[0].side == "LEFT"
    assert threads.threads[1].path is None


def test_gitlab_normalization_truncates_long_note_bodies() -> None:
    """Truncate an oversized root note instead of aborting the snapshot."""
    long_discussion = {
        "id": "discussion-long",
        "individual_note": True,
        "notes": [
            {
                "id": 994,
                "body": "x" * 10_001,
                "author": {"username": "reviewer"},
                "system": False,
            }
        ],
    }

    threads = normalize_gitlab_threads(
        raw_discussions=[*_discussions(), long_discussion],
        identity=IDENTITY,
        revisions=DIFF_REFS,
    )

    assert [thread.thread_id for thread in threads.threads] == [
        "discussion-012345",
        "discussion-resolved",
        "discussion-outdated",
        "discussion-long",
    ]
    assert threads.threads[3].body == "x" * 10_000
    assert threads.threads[3].limitations == ("Body truncated to 10000 characters",)


def test_gitlab_normalization_keeps_state_of_image_and_file_discussions() -> None:
    """Keep current image and file discussions open or resolved without a line."""
    threads = normalize_gitlab_threads(
        raw_discussions=[
            {
                "id": "image-discussion",
                "individual_note": False,
                "notes": [
                    {
                        "id": 995,
                        "body": "The screenshot is cropped.",
                        "author": {"username": "reviewer"},
                        "system": False,
                        "position": {**_position(), "position_type": "image"},
                    }
                ],
            },
            {
                "id": "file-discussion",
                "individual_note": False,
                "notes": [
                    {
                        "id": 996,
                        "body": "This file should be generated.",
                        "author": {"username": "reviewer"},
                        "system": False,
                        "resolvable": True,
                        "resolved": True,
                        "position": {**_position(), "position_type": "file"},
                    }
                ],
            },
        ],
        identity=IDENTITY,
        revisions=DIFF_REFS,
    )

    assert [thread.state for thread in threads.threads] == ["open", "resolved"]
    for thread in threads.threads:
        assert (thread.path, thread.line, thread.side) == (None, None, None)
        assert thread.limitations == (
            "GitLab image or file discussion has no line position",
        )
