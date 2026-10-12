"""Tests for GitLab payloads and fixed transport vectors."""

import json
from typing import Final

import pytest
from ballen_review_tools.models import (
    ReviewAction,
    ReviewCommentPlan,
    ReviewIdentity,
    ReviewSide,
)
from ballen_review_tools.providers.base import CompletedCommand
from ballen_review_tools.providers.gitlab import (
    DiffLine,
    DiffLineKey,
    GitLabDiffRefs,
    GitLabProvider,
    GitLabProviderError,
    GitLabRemoteState,
)

from tests.assistants.review_tools.doubles import RecordingRunner

BASE_SHA: Final[str] = "a" * 40
START_SHA: Final[str] = "b" * 40
HEAD_SHA: Final[str] = "c" * 40


def _identity() -> ReviewIdentity:
    """Return one GitLab identity with a namespaced repository."""
    return ReviewIdentity(
        provider="gitlab",
        host="gitlab.example.com",
        repository="acme/ballen-config",
        change_number=17,
        base_revision=BASE_SHA,
        head_revision=HEAD_SHA,
    )


def _refs() -> GitLabDiffRefs:
    """Return one complete GitLab diff-ref tuple."""
    return GitLabDiffRefs(
        base_sha=BASE_SHA,
        start_sha=START_SHA,
        head_sha=HEAD_SHA,
    )


def _state(
    line_numbers: dict[DiffLineKey, tuple[int | None, int | None]],
) -> GitLabRemoteState:
    """Return current GitLab state whose MR diff holds only the given lines."""
    return GitLabRemoteState(
        diff_refs=_refs(),
        discussions=(),
        notes=(),
        diff_lines={
            key: DiffLine(key[0], key[0], *numbers)
            for key, numbers in line_numbers.items()
        },
    )


def _merge_request() -> CompletedCommand:
    """Return the current MR response with complete diff refs."""
    return CompletedCommand(
        0,
        json.dumps(
            {
                "iid": 17,
                "diff_refs": {
                    "base_sha": BASE_SHA,
                    "start_sha": START_SHA,
                    "head_sha": HEAD_SHA,
                },
            }
        ),
        "",
    )


def _inline_plan(
    *, side: ReviewSide = "RIGHT", path: str = "src/example.py"
) -> ReviewCommentPlan:
    """Return one selected single-line GitLab action."""
    action = ReviewAction(
        action_id="R001",
        kind="inline",
        selected=True,
        body="Guard the empty case.",
        path=path,
        line=42,
        side=side,
        deduplication_key="d" * 64,
        validation_state="valid",
        intended_action="create-inline",
        outcome="pending",
    )
    return ReviewCommentPlan(
        contract_version="review-comment-plan/v1",
        identity=_identity(),
        source_draft_digest="e" * 64,
        actions=(action,),
    )


def test_gitlab_discussion_payload_uses_current_text_position() -> None:
    """Build the exact new-line position with all three current SHAs."""
    provider = GitLabProvider(identity=_identity(), runner=RecordingRunner())

    payload = provider.discussion_payload(
        _inline_plan().actions[0],
        _state({("src/example.py", 42, "RIGHT"): (None, 42)}),
    )

    assert payload == {
        "body": "Guard the empty case.",
        "position": {
            "position_type": "text",
            "base_sha": BASE_SHA,
            "head_sha": HEAD_SHA,
            "start_sha": START_SHA,
            "old_path": "src/example.py",
            "new_path": "src/example.py",
            "new_line": 42,
        },
    }


def test_gitlab_discussion_payload_maps_removed_line_to_old_side() -> None:
    """Use old_line for a removed line and retain both paths."""
    provider = GitLabProvider(identity=_identity(), runner=RecordingRunner())

    payload = provider.discussion_payload(
        _inline_plan(side="LEFT", path="src/old_example.py").actions[0],
        _state({("src/old_example.py", 42, "LEFT"): (42, None)}),
    )

    assert payload["position"]["old_path"] == "src/old_example.py"
    assert payload["position"]["new_path"] == "src/old_example.py"
    assert payload["position"]["old_line"] == 42
    assert "new_line" not in payload["position"]


def test_gitlab_read_vectors_encode_namespace_and_use_pagination() -> None:
    """Use exact no-shell glab vectors for MR, discussions, notes, and diffs."""
    runner = RecordingRunner(
        responses=[
            _merge_request(),
            CompletedCommand(0, "[]", ""),
            CompletedCommand(0, "[]", ""),
            CompletedCommand(0, "[]", ""),
        ]
    )
    provider = GitLabProvider(identity=_identity(), runner=runner)

    state = provider.fetch_remote_state()

    assert state.diff_refs.head_sha == HEAD_SHA
    assert [call[0] for call in runner.calls] == [
        ("glab", "api", "projects/acme%2Fballen-config/merge_requests/17"),
        (
            "glab",
            "api",
            "projects/acme%2Fballen-config/merge_requests/17/discussions",
            "--paginate",
        ),
        (
            "glab",
            "api",
            "projects/acme%2Fballen-config/merge_requests/17/notes",
            "--paginate",
        ),
        (
            "glab",
            "api",
            "projects/acme%2Fballen-config/merge_requests/17/diffs",
            "--paginate",
        ),
    ]


def test_gitlab_post_vectors_use_json_stdin() -> None:
    """Post exact JSON through glab without shell interpolation."""
    runner = RecordingRunner([CompletedCommand(0, '{"id": "D001"}', "")])
    provider = GitLabProvider(identity=_identity(), runner=runner)

    provider.post_discussion(
        _inline_plan().actions[0],
        _state({("src/example.py", 42, "RIGHT"): (None, 42)}),
    )

    assert runner.calls == [
        (
            (
                "glab",
                "api",
                "--method",
                "POST",
                "projects/acme%2Fballen-config/merge_requests/17/discussions",
                "--header",
                "Content-Type: application/json",
                "--input",
                "-",
            ),
            json.dumps(
                {
                    "body": "Guard the empty case.",
                    "position": {
                        "position_type": "text",
                        "base_sha": BASE_SHA,
                        "head_sha": HEAD_SHA,
                        "start_sha": START_SHA,
                        "old_path": "src/example.py",
                        "new_path": "src/example.py",
                        "new_line": 42,
                    },
                },
                sort_keys=True,
            ),
        )
    ]


def test_gitlab_discussion_payload_sends_both_lines_for_context_line() -> None:
    """Send old_line and new_line for an unchanged line, as GitLab requires."""
    provider = GitLabProvider(identity=_identity(), runner=RecordingRunner())

    payload = provider.discussion_payload(
        _inline_plan().actions[0],
        _state({("src/example.py", 42, "RIGHT"): (40, 42)}),
    )

    assert payload["position"]["old_line"] == 40
    assert payload["position"]["new_line"] == 42


def test_gitlab_discussion_payload_rejects_line_outside_current_diff() -> None:
    """Refuse a position for a path, line, and side the MR diff lacks."""
    provider = GitLabProvider(identity=_identity(), runner=RecordingRunner())

    with pytest.raises(GitLabProviderError, match="not present in the current"):
        provider.discussion_payload(
            _inline_plan().actions[0],
            _state({("src/example.py", 42, "LEFT"): (42, None)}),
        )


def test_gitlab_diff_lines_map_renamed_file_and_skip_missing_diff_text() -> None:
    """Map renamed-file hunks per side and give omitted diff text no lines."""
    renamed = {
        "old_path": "src/old_name.py",
        "new_path": "src/new_name.py",
        "diff": (
            "@@ -2,2 +2,3 @@ class Example:\n"
            " two\n"
            "-three\n"
            "+THREE\n"
            "+four\n"
            "@@ -9,2 +10,3 @@\n"
            " nine\n"
            "-ten\n"
            "\\ No newline at end of file\n"
            "+ten\n"
            "+eleven\n"
        ),
    }
    too_large = {
        "old_path": "src/large.py",
        "new_path": "src/large.py",
        "diff": "",
        "too_large": True,
    }
    runner = RecordingRunner(
        responses=[
            _merge_request(),
            CompletedCommand(0, "[]", ""),
            CompletedCommand(0, "[]", ""),
            CompletedCommand(0, json.dumps([renamed, too_large]), ""),
        ]
    )

    state = GitLabProvider(identity=_identity(), runner=runner).fetch_remote_state()

    paths = ("src/old_name.py", "src/new_name.py")
    assert state.diff_lines == {
        ("src/new_name.py", 2, "RIGHT"): (*paths, 2, 2),
        ("src/old_name.py", 2, "LEFT"): (*paths, 2, 2),
        ("src/old_name.py", 3, "LEFT"): (*paths, 3, None),
        ("src/new_name.py", 3, "RIGHT"): (*paths, None, 3),
        ("src/new_name.py", 4, "RIGHT"): (*paths, None, 4),
        ("src/new_name.py", 10, "RIGHT"): (*paths, 9, 10),
        ("src/old_name.py", 9, "LEFT"): (*paths, 9, 10),
        ("src/old_name.py", 10, "LEFT"): (*paths, 10, None),
        ("src/new_name.py", 11, "RIGHT"): (*paths, None, 11),
        ("src/new_name.py", 12, "RIGHT"): (*paths, None, 12),
    }


def test_gitlab_discussion_payload_sends_both_paths_for_renamed_file() -> None:
    """Send a renamed file's old and new path, as GitLab requires."""
    provider = GitLabProvider(identity=_identity(), runner=RecordingRunner())
    state = GitLabRemoteState(
        diff_refs=_refs(),
        discussions=(),
        notes=(),
        diff_lines={
            ("src/new_name.py", 42, "RIGHT"): DiffLine(
                "src/old_name.py", "src/new_name.py", 40, 42
            )
        },
    )

    payload = provider.discussion_payload(
        _inline_plan(path="src/new_name.py").actions[0], state
    )

    position = payload["position"]
    assert (position["old_path"], position["new_path"]) == (
        "src/old_name.py",
        "src/new_name.py",
    )
    assert (position["old_line"], position["new_line"]) == (40, 42)
