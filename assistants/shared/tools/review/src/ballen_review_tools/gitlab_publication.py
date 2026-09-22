"""Approval-bound GitLab publication preview and execution gates."""

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
from ballen_review_tools.providers.gitlab import (
    GitLabProvider,
    GitLabProviderError,
    GitLabRemoteState,
)


@dataclass(frozen=True)
class GitLabPublicationExecutionResult:
    """Bounded execution result and optional minimal receipt."""

    status: PublicationStatus
    receipt: PublicationReceipt | None = None
    reason: str | None = None


def plan_digest(plan: ReviewCommentPlan) -> str:
    """Return the canonical digest of one validated logical plan."""
    return canonical_digest(plan.model_dump(mode="json"))


def _remote_state_digest(state: GitLabRemoteState) -> str:
    """Digest only normalized GitLab observations needed for preview."""
    return canonical_digest(asdict(state))


def _remote_id(value: object) -> str | None:
    """Extract one minimal native GitLab identifier."""
    if not isinstance(value, dict):
        return None
    identifier = value.get("id")
    if isinstance(identifier, (int, str)) and str(identifier):
        return str(identifier)
    return None


def _remote_duplicate(action: ReviewAction, state: GitLabRemoteState) -> bool:
    """Return whether the exact logical action is already remote."""
    if action.kind == "inline":
        if action.path is None or action.line is None or action.side is None:
            return False
        expected = (action.path.as_posix(), action.line, action.side)
        for discussion in state.discussions:
            for note in discussion.notes[:1]:
                if (
                    not note.system
                    and note.body == action.body
                    and _note_location(note, state) == expected
                ):
                    return True
        return False
    if action.kind == "general":
        return any(not note.system and note.body == action.body for note in state.notes)
    if not action.thread_id:
        return False
    return any(
        discussion.discussion_id == action.thread_id
        and any(
            not note.system and note.body == action.body
            for note in discussion.notes[1:]
        )
        for discussion in state.discussions
    )


def _note_location(
    note: object,
    state: GitLabRemoteState,
) -> tuple[str, int, str] | None:
    """Return one current normalized location from a native note."""
    position = getattr(note, "position", None)
    if position is None:
        return None
    if (
        position.position_type != "text"
        or position.base_sha != state.diff_refs.base_sha
        or position.start_sha != state.diff_refs.start_sha
        or position.head_sha != state.diff_refs.head_sha
    ):
        return None
    if position.new_line is not None and position.new_path is not None:
        return position.new_path, position.new_line, "RIGHT"
    if position.old_line is not None and position.old_path is not None:
        return position.old_path, position.old_line, "LEFT"
    return None


def _preview_payload(
    provider: GitLabProvider,
    action: ReviewAction,
    state: GitLabRemoteState,
) -> dict[str, object] | None:
    """Build one exact ephemeral GitLab payload."""
    if action.kind == "inline":
        return dict(provider.discussion_payload(action, state.diff_refs))
    if action.kind == "general":
        return dict(provider.note_payload(action))
    return dict(provider.reply_payload(action))


def _preview_gitlab_publication_with_state(
    plan: ReviewCommentPlan,
    provider: GitLabProvider,
    state: GitLabRemoteState,
) -> PublicationPreview:
    """Build a non-mutating GitLab preview from one captured state."""
    if provider.identity != plan.identity:
        raise GitLabProviderError("provider identity does not match plan identity")
    expected_head = plan.identity.head_revision
    head_matches = (
        state.diff_refs.head_sha == expected_head
        and state.diff_refs.base_sha == plan.identity.base_revision
    )
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
                    reason="GitLab diff refs do not match plan head",
                )
            )
            continue
        if action.kind == "inline" and not provider.location_is_current(action, state):
            items.append(
                PublicationItemPreview(
                    action_id=action.action_id,
                    deduplication_key=action.deduplication_key,
                    state="blocked",
                    reason="inline location is not present in the current GitLab diff",
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
        try:
            payload = _preview_payload(provider, action, state)
        except GitLabProviderError as error:
            items.append(
                PublicationItemPreview(
                    action_id=action.action_id,
                    deduplication_key=action.deduplication_key,
                    state="blocked",
                    reason=str(error),
                )
            )
            continue
        items.append(
            PublicationItemPreview(
                action_id=action.action_id,
                deduplication_key=action.deduplication_key,
                state="eligible",
                payload=payload,
            )
        )
    return PublicationPreview(
        contract_version="publication-preview/v1",
        plan_digest=plan_digest(plan),
        identity=plan.identity,
        expected_head=expected_head,
        observed_head=state.diff_refs.head_sha,
        remote_state_digest=_remote_state_digest(state),
        status="ready" if head_matches else "blocked",
        items=tuple(items),
    )


def preview_gitlab_publication(
    plan: ReviewCommentPlan,
    provider: GitLabProvider,
) -> PublicationPreview:
    """Fetch current state and produce a non-mutating GitLab preview."""
    return _preview_gitlab_publication_with_state(
        plan,
        provider,
        provider.fetch_remote_state(),
    )


def execute_gitlab_publication(
    *,
    plan: ReviewCommentPlan,
    approved_plan_digest: str,
    expected_head: str,
    provider: GitLabProvider,
) -> GitLabPublicationExecutionResult:
    """Revalidate state and publish only an exactly approved current plan."""
    current_digest = plan_digest(plan)
    if approved_plan_digest != current_digest:
        return GitLabPublicationExecutionResult(
            status="blocked",
            reason="approved plan digest does not match current plan",
        )
    if expected_head != plan.identity.head_revision:
        return GitLabPublicationExecutionResult(
            status="blocked",
            reason="expected head does not match current plan",
        )
    try:
        state = provider.fetch_remote_state()
        preview = _preview_gitlab_publication_with_state(plan, provider, state)
    except GitLabProviderError as error:
        return GitLabPublicationExecutionResult(status="blocked", reason=str(error))
    if preview.observed_head != expected_head:
        return GitLabPublicationExecutionResult(
            status="blocked",
            reason="GitLab head changed after approval",
        )
    if preview.status != "ready":
        return GitLabPublicationExecutionResult(
            status="blocked",
            reason="current GitLab preview is not ready for execution",
        )
    preview_by_id = {item.action_id: item for item in preview.items}
    receipt_items: list[PublicationReceiptItem] = []
    posted_any = False
    failed = False
    halted = False
    for action in sorted(plan.actions, key=lambda item: item.action_id):
        item = preview_by_id[action.action_id]
        if item.state != "eligible" or halted:
            continue
        try:
            if action.kind == "inline":
                response = provider.post_discussion(action, state.diff_refs)
            elif action.kind == "general":
                response = provider.post_note(action)
            else:
                response = provider.post_reply(action)
            receipt_items.append(
                PublicationReceiptItem(
                    action_id=action.action_id,
                    deduplication_key=action.deduplication_key,
                    outcome="posted",
                    remote_id=_remote_id(response),
                )
            )
            posted_any = True
        except GitLabProviderError:
            failed = True
            halted = True
            receipt_items.append(
                PublicationReceiptItem(
                    action_id=action.action_id,
                    deduplication_key=action.deduplication_key,
                    outcome="failed",
                    reason="GitLab publication request failed",
                )
            )

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
    if failed and posted_any:
        status: PublicationStatus = "partial"
    elif failed:
        status = "failed"
    elif posted_any:
        status = "posted"
    else:
        status = "blocked"
    return GitLabPublicationExecutionResult(
        status=status,
        receipt=PublicationReceipt(
            contract_version="publication-receipt/v1",
            plan_digest=current_digest,
            identity=plan.identity,
            expected_head=expected_head,
            observed_head=preview.observed_head,
            status=status,
            items=tuple(receipt_items),
        ),
    )
