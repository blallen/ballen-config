"""Provider-specific response preflight gates for GitLab merge requests."""

from dataclasses import dataclass
from typing import Literal

from ballen_review_tools.models import ReviewResponsePlan
from ballen_review_tools.providers.gitlab import GitLabDiffRefs


@dataclass(frozen=True)
class GitLabResponsePreflight:
    """Result of binding a response plan to current GitLab diff refs."""

    status: Literal["ready", "blocked"]
    reason: str | None = None


def preflight_gitlab_response(
    *,
    response_plan: ReviewResponsePlan,
    observed_diff_refs: GitLabDiffRefs,
) -> GitLabResponsePreflight:
    """Reject response work when the MR head or base changed."""
    if response_plan.identity.provider != "gitlab":
        return GitLabResponsePreflight(
            status="blocked",
            reason="response plan is not a GitLab plan",
        )
    if observed_diff_refs.base_sha != response_plan.identity.base_revision:
        return GitLabResponsePreflight(
            status="blocked",
            reason="GitLab base changed after response planning",
        )
    if observed_diff_refs.head_sha != response_plan.observed_head:
        return GitLabResponsePreflight(
            status="blocked",
            reason="GitLab head changed after response planning",
        )
    return GitLabResponsePreflight(status="ready")
