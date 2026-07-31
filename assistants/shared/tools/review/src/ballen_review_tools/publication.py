"""Approval-bound GitHub publication preview and execution gates."""

from dataclasses import asdict, dataclass
from typing import Literal

from ballen_review_tools.canonical import canonical_digest
from ballen_review_tools.models import (
    PublicationItemPreview,
    PublicationPreview,
    PublicationReceipt,
    PublicationReceiptItem,
    PublicationStatus,
    ReviewAction,
    ReviewCommentPlan,
)
from ballen_review_tools.providers.github import (
    GitHubProvider,
    GitHubProviderError,
    GitHubRemoteState,
)


@dataclass(frozen=True)
class PublicationExecutionResult:
    """Bounded execution result and optional minimal receipt."""

    status: PublicationStatus
    receipt: PublicationReceipt | None = None
    reason: str | None = None


def plan_digest(plan: ReviewCommentPlan) -> str:
    """Return the canonical digest of one validated logical plan."""
    return canonical_digest(plan.model_dump(mode="json"))


def _remote_state_digest(state: GitHubRemoteState) -> str:
    """Digest only normalized remote observations needed for preview."""
    return canonical_digest(
        {
            "head_sha": state.head_sha,
            "review_comments": [asdict(item) for item in state.review_comments],
            "issue_comments": [asdict(item) for item in state.issue_comments],
        }
    )


def _remote_duplicate(action: ReviewAction, state: GitHubRemoteState) -> bool:
    """Return whether the exact logical action is already remote."""
    if action.kind == "inline":
        return any(
            comment.in_reply_to is None
            and comment.body == action.body
            and comment.path == (action.path.as_posix() if action.path else None)
            and comment.line == action.line
            and comment.side == action.side
            and comment.start_line == action.start_line
            and comment.start_side == action.start_side
            for comment in state.review_comments
        )
    if action.kind == "general":
        return any(comment.body == action.body for comment in state.issue_comments)
    try:
        thread_id = int(action.thread_id or "")
    except ValueError:
        return False
    return any(
        comment.in_reply_to == thread_id and comment.body == action.body
        for comment in state.review_comments
    )


def _preview_payload(
    provider: GitHubProvider,
    action: ReviewAction,
    observed_head: str,
) -> dict[str, object] | None:
    """Build one exact ephemeral payload for a valid selected action."""
    if action.kind == "inline":
        payload = provider.review_payload(
            plan=ReviewCommentPlan(
                contract_version="review-comment-plan/v1",
                identity=provider.identity,
                source_draft_digest="0" * 64,
                actions=(action,),
            ),
            observed_head=observed_head,
        )
        comments = payload["comments"]
        return dict(comments[0]) if comments else None
    if action.kind == "general":
        return dict(provider.issue_comment_payload(action))
    return dict(provider.reply_payload(action))


def preview_github_publication(
    plan: ReviewCommentPlan,
    provider: GitHubProvider,
) -> PublicationPreview:
    """Fetch current state and produce a non-mutating GitHub preview."""
    if provider.identity != plan.identity:
        raise GitHubProviderError("provider identity does not match plan identity")
    state = provider.fetch_remote_state()
    expected_head = plan.identity.head_revision
    head_matches = state.head_sha == expected_head
    items: list[PublicationItemPreview] = []
    for action in sorted(plan.actions, key=lambda item: item.action_id):
        if not action.selected:
            items.append(
                PublicationItemPreview(
                    action_id=action.action_id,
                    deduplication_key=action.deduplication_key,
                    state="skipped",
                    reason="not selected for preview",
                )
            )
            continue
        if action.validation_state != "valid":
            items.append(
                PublicationItemPreview(
                    action_id=action.action_id,
                    deduplication_key=action.deduplication_key,
                    state="blocked",
                    reason=action.validation_reason or "action is not valid",
                )
            )
            continue
        if not head_matches:
            items.append(
                PublicationItemPreview(
                    action_id=action.action_id,
                    deduplication_key=action.deduplication_key,
                    state="blocked",
                    reason="remote head does not match plan head",
                )
            )
            continue
        if _remote_duplicate(action, state):
            items.append(
                PublicationItemPreview(
                    action_id=action.action_id,
                    deduplication_key=action.deduplication_key,
                    state="duplicate",
                    reason="exact logical action already exists remotely",
                )
            )
            continue
        items.append(
            PublicationItemPreview(
                action_id=action.action_id,
                deduplication_key=action.deduplication_key,
                state="eligible",
                payload=_preview_payload(provider, action, state.head_sha),
            )
        )
    return PublicationPreview(
        contract_version="publication-preview/v1",
        plan_digest=plan_digest(plan),
        identity=plan.identity,
        expected_head=expected_head,
        observed_head=state.head_sha,
        remote_state_digest=_remote_state_digest(state),
        status="ready" if head_matches else "blocked",
        items=tuple(items),
    )


def _remote_id(value: object) -> int | None:
    """Extract only a positive provider ID from a mutation result."""
    if not isinstance(value, dict):
        return None
    identifier = value.get("id")
    return identifier if isinstance(identifier, int) and identifier > 0 else None


def execute_github_publication(
    *,
    plan: ReviewCommentPlan,
    approved_plan_digest: str,
    expected_head: str,
    provider: GitHubProvider,
) -> PublicationExecutionResult:
    """Revalidate state and publish only an exactly approved current plan."""
    current_digest = plan_digest(plan)
    if approved_plan_digest != current_digest:
        return PublicationExecutionResult(
            status="blocked",
            reason="approved plan digest does not match current plan",
        )
    if expected_head != plan.identity.head_revision:
        return PublicationExecutionResult(
            status="blocked",
            reason="expected head does not match current plan",
        )
    try:
        preview = preview_github_publication(plan, provider)
    except GitHubProviderError as error:
        return PublicationExecutionResult(status="blocked", reason=str(error))
    if preview.observed_head != expected_head:
        return PublicationExecutionResult(
            status="blocked",
            reason="remote head changed after approval",
        )
    if preview.status != "ready":
        return PublicationExecutionResult(
            status="blocked",
            reason="current preview is not ready for execution",
        )
    preview_by_id = {item.action_id: item for item in preview.items}
    receipt_items: list[PublicationReceiptItem] = []
    posted_any = False
    failed = False
    halted = False

    inline_actions = [
        action
        for action in sorted(plan.actions, key=lambda item: item.action_id)
        if action.kind == "inline"
        and preview_by_id[action.action_id].state == "eligible"
    ]
    if inline_actions:
        inline_plan = plan.model_copy(update={"actions": tuple(inline_actions)})
        try:
            response = provider.post_review(
                provider.review_payload(plan=inline_plan, observed_head=expected_head)
            )
            remote_id = _remote_id(response)
            for action in inline_actions:
                receipt_items.append(
                    PublicationReceiptItem(
                        action_id=action.action_id,
                        deduplication_key=action.deduplication_key,
                        outcome="posted",
                        remote_id=remote_id,
                    )
                )
            posted_any = True
        except GitHubProviderError:
            failed = True
            halted = True
            for action in inline_actions:
                receipt_items.append(
                    PublicationReceiptItem(
                        action_id=action.action_id,
                        deduplication_key=action.deduplication_key,
                        outcome="failed",
                        reason="GitHub inline review request failed",
                    )
                )

    for action in sorted(plan.actions, key=lambda item: item.action_id):
        if (
            halted
            or action.kind == "inline"
            or preview_by_id[action.action_id].state != "eligible"
        ):
            continue
        try:
            response = (
                provider.post_issue_comment(action)
                if action.kind == "general"
                else provider.post_reply(action)
            )
            receipt_items.append(
                PublicationReceiptItem(
                    action_id=action.action_id,
                    deduplication_key=action.deduplication_key,
                    outcome="posted",
                    remote_id=_remote_id(response),
                )
            )
            posted_any = True
        except GitHubProviderError:
            failed = True
            halted = True
            receipt_items.append(
                PublicationReceiptItem(
                    action_id=action.action_id,
                    deduplication_key=action.deduplication_key,
                    outcome="failed",
                    reason="GitHub publication request failed",
                )
            )
            break

    for action in sorted(plan.actions, key=lambda item: item.action_id):
        if action.action_id in {item.action_id for item in receipt_items}:
            continue
        item = preview_by_id[action.action_id]
        if item.state == "duplicate":
            outcome: Literal["duplicate", "skipped", "blocked", "not-attempted"] = (
                "duplicate"
            )
        elif item.state == "blocked":
            outcome = "blocked"
        elif item.state == "eligible" and failed:
            outcome = "not-attempted"
        else:
            outcome = "skipped"
        receipt_items.append(
            PublicationReceiptItem(
                action_id=action.action_id,
                deduplication_key=action.deduplication_key,
                outcome=outcome,
                reason=item.reason,
            )
        )
    receipt_items.sort(key=lambda item: item.action_id)
    status: PublicationStatus
    if failed and posted_any:
        status = "partial"
    elif failed:
        status = "failed"
    elif posted_any:
        status = "posted"
    else:
        status = "blocked"
    receipt = PublicationReceipt(
        contract_version="publication-receipt/v1",
        plan_digest=current_digest,
        identity=plan.identity,
        expected_head=expected_head,
        observed_head=preview.observed_head,
        status=status,
        items=tuple(receipt_items),
    )
    return PublicationExecutionResult(status=status, receipt=receipt)
