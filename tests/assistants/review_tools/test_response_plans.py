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
