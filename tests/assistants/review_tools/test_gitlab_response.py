"""Tests for GitLab response preflight gates."""

from ballen_review_tools.gitlab_response import (
    GitLabDiffRefs,
    preflight_gitlab_response,
)
from ballen_review_tools.models import (
    ReviewIdentity,
    ReviewResponseItem,
    ReviewResponsePlan,
)

BASE_SHA = "a" * 40
START_SHA = "b" * 40
HEAD_SHA = "c" * 40
NEW_HEAD = "d" * 40


def _plan() -> ReviewResponsePlan:
    """Return one response plan bound to the current GitLab head."""
    identity = ReviewIdentity(
        provider="gitlab",
        host="gitlab.example.com",
        repository="acme/ballen-config",
        change_number=17,
        base_revision=BASE_SHA,
        head_revision=HEAD_SHA,
    )
    return ReviewResponsePlan(
        contract_version="review-response-plan/v1",
        identity=identity,
        source_threads_digest="e" * 64,
        observed_head=HEAD_SHA,
        items=(
            ReviewResponseItem(
                thread_id="discussion-001",
                classification="actionable",
                evaluation="The concern is valid.",
                evidence="The current branch has the cited path.",
                proposed_changes=("Add the guard.",),
                proposed_response="I will add the guard.",
                verification=("Run the focused test.",),
                selected_action="propose-response",
            ),
        ),
    )


def test_changed_diff_refs_invalidate_reply_preview() -> None:
    """Require a fresh response preview after the MR changes."""
    result = preflight_gitlab_response(
        response_plan=_plan(),
        observed_diff_refs=GitLabDiffRefs(
            base_sha=BASE_SHA,
            start_sha=START_SHA,
            head_sha=NEW_HEAD,
        ),
    )

    assert result.status == "blocked"
    assert "head" in (result.reason or "")


def test_current_diff_refs_allow_response_preview() -> None:
    """Allow response preview only for the plan's current head."""
    result = preflight_gitlab_response(
        response_plan=_plan(),
        observed_diff_refs=GitLabDiffRefs(
            base_sha=BASE_SHA,
            start_sha=START_SHA,
            head_sha=HEAD_SHA,
        ),
    )

    assert result.status == "ready"
