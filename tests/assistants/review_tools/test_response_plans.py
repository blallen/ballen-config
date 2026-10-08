"""Tests for provider-neutral normalized threads and response plans."""

from pathlib import PurePosixPath

import pytest
from ballen_review_tools.markdown import parse_response_markdown
from ballen_review_tools.models import (
    NormalizedReviewThreads,
    NormalizedThread,
    ReviewIdentity,
    ReviewResponsePlan,
)
from pydantic import ValidationError

IDENTITY = ReviewIdentity(
    provider="github",
    host="github.com",
    repository="acme/ballen-config",
    change_number=17,
    base_revision="a" * 40,
    head_revision="b" * 40,
)


def _threads() -> NormalizedReviewThreads:
    """Return actionable and resolved evidence from one current head."""
    return NormalizedReviewThreads(
        contract_version="normalized-review-threads/v1",
        identity=IDENTITY,
        observed_head=IDENTITY.head_revision,
        limitations=("REST input does not expose GraphQL resolution reason",),
        threads=(
            NormalizedThread(
                thread_id="T001",
                comment_ids=("C001",),
                state="open",
                path=PurePosixPath("src/example.py"),
                line=20,
                side="RIGHT",
                author="reviewer",
                body="Guard the empty case.",
                chronology=("C001",),
            ),
            NormalizedThread(
                thread_id="T002",
                comment_ids=("C002",),
                state="resolved",
                author="reviewer",
                body="Looks good now.",
                chronology=("C002",),
            ),
        ),
    )


RESPONSE_DRAFT = """### T001: Address the empty case

**Classification:** actionable
**Selected action:** propose-change
**Evaluation:** The feedback is technically valid.
**Evidence:** The current branch still dereferences an empty result.
**Proposed changes:** Guard the empty result before iteration.
**Proposed response:** I will add the guard and run the focused tests.
**Verification:** focused unit test for the empty result

### T002: Resolved context

**Classification:** informational
**Selected action:** skip
**Evaluation:** This thread is already resolved.
**Evidence:** The normalized state is resolved.
**Verification:** none
"""


def test_resolved_and_informational_threads_remain_visible() -> None:
    """Keep skipped evidence instead of dropping completed feedback."""
    response = parse_response_markdown(RESPONSE_DRAFT, threads=_threads())

    assert [item.thread_id for item in response] == ["T001", "T002"]
    assert response[1].classification == "informational"
    assert response[1].selected_action == "skip"


def test_normalized_thread_rejects_absolute_path() -> None:
    """Keep machine paths out of normalized provider artifacts."""
    with pytest.raises(ValidationError, match="relative"):
        NormalizedThread(
            thread_id="T003",
            comment_ids=("C003",),
            state="open",
            path="/tmp/example.py",
            line=1,
            side="RIGHT",
            author="reviewer",
            body="Unsafe path.",
            chronology=("C003",),
        )


def test_normalized_thread_requires_native_ids_and_bounded_text() -> None:
    """Reject missing provider IDs and unbounded diagnostics."""
    with pytest.raises(ValidationError):
        NormalizedThread(
            thread_id="",
            comment_ids=(),
            state="open",
            author="reviewer",
            body="Feedback.",
            chronology=(),
        )
    with pytest.raises(ValidationError, match="limitations"):
        NormalizedReviewThreads(
            contract_version="normalized-review-threads/v1",
            identity=IDENTITY,
            observed_head=IDENTITY.head_revision,
            limitations=("x" * 2001,),
            threads=(),
        )


def test_response_plan_binds_identity_and_head_to_normalized_source() -> None:
    """Prevent response plans from changing their normalized target."""
    response = parse_response_markdown(RESPONSE_DRAFT, threads=_threads())
    with pytest.raises(ValidationError, match="head"):
        ReviewResponsePlan(
            contract_version="review-response-plan/v1",
            identity=IDENTITY,
            source_threads_digest="c" * 64,
            observed_head="d" * 40,
            items=tuple(response),
        )


def test_normalized_thread_rejects_non_string_path() -> None:
    """Report malformed provider paths as validation errors, not crashes."""
    with pytest.raises(ValidationError, match="string or POSIX path"):
        NormalizedThread.model_validate(
            {
                "thread_id": "T004",
                "comment_ids": ["C004"],
                "state": "open",
                "path": 42,
                "line": 1,
                "side": "RIGHT",
                "author": "reviewer",
                "body": "Malformed path.",
                "chronology": ["C004"],
            }
        )


@pytest.mark.parametrize(
    ("line", "side"),
    [(None, None), (2, "RIGHT")],
)
def test_normalized_thread_rejects_incoherent_ranges(
    line: int | None, side: str | None
) -> None:
    """Apply the review-action range rule to normalized threads."""
    with pytest.raises(ValidationError, match="start_line must not exceed line"):
        NormalizedThread.model_validate(
            {
                "thread_id": "T005",
                "comment_ids": ["C005"],
                "state": "open",
                "path": "src/example.py",
                "line": line,
                "side": side,
                "start_line": 3,
                "start_side": "RIGHT",
                "author": "reviewer",
                "body": "Range check.",
                "chronology": ["C005"],
            }
        )


def test_normalized_thread_accepts_cross_side_ranges() -> None:
    """Allow GitHub ranges that start on a deleted line and end on an added one."""
    thread = NormalizedThread.model_validate(
        {
            "thread_id": "T006",
            "comment_ids": ["C006"],
            "state": "open",
            "path": "src/example.py",
            "line": 10,
            "side": "RIGHT",
            "start_line": 11,
            "start_side": "LEFT",
            "author": "reviewer",
            "body": "Cross-side range.",
            "chronology": ["C006"],
        }
    )

    assert (thread.start_line, thread.start_side, thread.line, thread.side) == (
        11,
        "LEFT",
        10,
        "RIGHT",
    )
