"""Tests for provider-neutral normalized threads and response plans."""

from pathlib import PurePosixPath

import pytest
from ballen_review_tools.markdown import parse_response_markdown
from ballen_review_tools.models import (
    NormalizedReviewThreads,
    NormalizedThread,
    ReviewIdentity,
    ReviewResponseItem,
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


@pytest.mark.parametrize(
    ("field", "value"),
    [
        pytest.param("thread_id", "", id="empty-thread-id"),
        pytest.param("comment_ids", [], id="no-comment-ids"),
        pytest.param("chronology", [], id="no-chronology"),
        pytest.param("limitations", ["x" * 2001], id="long-limitation"),
    ],
)
def test_normalized_thread_rejects_each_out_of_contract_field(
    field: str, value: object
) -> None:
    """Reject a missing provider ID or an unbounded limitation on its own."""
    payload = {
        "thread_id": "T003",
        "comment_ids": ["C003"],
        "state": "open",
        "author": "reviewer",
        "body": "Feedback.",
        "chronology": ["C003"],
        field: value,
    }

    with pytest.raises(ValidationError, match=field):
        NormalizedThread.model_validate(payload)


def test_normalized_threads_reject_an_unbounded_limitation() -> None:
    """Bound snapshot-level limitations like thread-level ones."""
    with pytest.raises(ValidationError, match="limitations"):
        NormalizedReviewThreads(
            contract_version="normalized-review-threads/v1",
            identity=IDENTITY,
            observed_head=IDENTITY.head_revision,
            limitations=("x" * 2001,),
            threads=(),
        )


def test_response_plan_head_must_match_identity_head() -> None:
    """Reject a plan whose observed head differs from its identity head."""
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


SECTION_TEXT_DRAFT = """### T001: Address the empty case

**Classification:** question
**Selected action:** propose-response
**Evaluation:** The reviewer asks whether the empty case is handled.
**Evidence:** `load_items` returns early when the result is empty.
**Verification:** none

**Note:** the guard already exists.

It returns before the loop, so the empty case never reaches iteration.

### T002: Resolved context

**Classification:** resolved
**Selected action:** skip
**Evaluation:** This thread is already resolved.
**Evidence:** The normalized state is resolved.
"""


def test_section_text_becomes_the_proposed_response() -> None:
    """Keep every paragraph below the fields, including bold-led lines."""
    response = parse_response_markdown(SECTION_TEXT_DRAFT, threads=_threads())

    assert response[0].proposed_response == (
        "**Note:** the guard already exists.\n\n"
        "It returns before the loop, so the empty case never reaches iteration."
    )


def test_section_text_and_proposed_response_field_are_ambiguous() -> None:
    """Reject a section that gives the proposed response twice."""
    draft = SECTION_TEXT_DRAFT.replace(
        "**Verification:** none\n",
        "**Verification:** none\n**Proposed response:** The guard exists.\n",
    )

    with pytest.raises(ValueError, match="T001: Proposed response field and"):
        parse_response_markdown(draft, threads=_threads())


@pytest.mark.parametrize(
    ("selected_action", "reason"),
    [
        pytest.param(
            "propose-response",
            "propose-response requires proposed_response",
            id="response-without-text",
        ),
        pytest.param(
            "propose-change",
            "propose-change requires proposed_changes",
            id="change-without-changes",
        ),
    ],
)
def test_selected_action_requires_its_content(
    selected_action: str, reason: str
) -> None:
    """Reject a proposal that carries nothing to propose."""
    with pytest.raises(ValidationError, match=reason):
        ReviewResponseItem.model_validate(
            {
                "thread_id": "T001",
                "classification": "actionable",
                "evaluation": "The feedback is valid.",
                "evidence": "The empty result is dereferenced.",
                "selected_action": selected_action,
            }
        )


OPEN_THREAD_DRAFT = """### T001: Address the empty case

**Classification:** actionable
**Selected action:** propose-change
**Evaluation:** The feedback is technically valid.
**Evidence:** The current branch still dereferences an empty result.
**Proposed changes:** Guard the empty result before iteration.
**Verification:** focused unit test for the empty result
"""


def test_omitted_resolved_thread_is_kept_as_skipped_evidence() -> None:
    """Retain a resolved thread that has no response section."""
    response = parse_response_markdown(OPEN_THREAD_DRAFT, threads=_threads())

    assert [item.thread_id for item in response] == ["T001", "T002"]
    assert (response[1].classification, response[1].selected_action) == (
        "resolved",
        "skip",
    )


def test_draft_must_answer_every_unresolved_thread() -> None:
    """Name each omitted unresolved thread, but not omitted resolved ones."""
    threads = NormalizedReviewThreads(
        contract_version="normalized-review-threads/v1",
        identity=IDENTITY,
        observed_head=IDENTITY.head_revision,
        threads=(
            *_threads().threads,
            NormalizedThread(
                thread_id="T003",
                comment_ids=("C003",),
                state="open",
                author="reviewer",
                body="Rename the helper.",
                chronology=("C003",),
            ),
        ),
    )

    with pytest.raises(
        ValueError, match=r"^response draft omits unresolved threads: T003$"
    ):
        parse_response_markdown(OPEN_THREAD_DRAFT, threads=threads)
