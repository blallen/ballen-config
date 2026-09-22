"""Strict provider-neutral models for review artifacts."""

from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Provider = Literal["github", "gitlab"]
ReviewKind = Literal["inline", "general", "reply"]
ReviewSide = Literal["LEFT", "RIGHT"]
ValidationState = Literal["valid", "invalid", "stale", "duplicate"]
ActionOutcome = Literal[
    "pending",
    "posted",
    "failed",
    "blocked",
    "duplicate",
    "skipped",
    "not-attempted",
]
IntendedAction = Literal["create-inline", "create-general", "reply"]
PublicationItemState = Literal["eligible", "duplicate", "blocked", "skipped"]
PublicationStatus = Literal["ready", "blocked", "posted", "partial", "failed"]
NormalizedThreadState = Literal["open", "resolved", "outdated", "missing"]
ResponseClassification = Literal[
    "actionable",
    "question",
    "discussion",
    "resolved",
    "informational",
]
ResponseAction = Literal["skip", "propose-change", "propose-response"]


class ReviewIdentity(BaseModel):
    """Canonical provider and change identity."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: Provider
    host: str = Field(min_length=1)
    repository: str = Field(min_length=1)
    change_number: int = Field(gt=0)
    base_revision: str = Field(min_length=1)
    head_revision: str = Field(min_length=1)

    @field_validator("host", "repository", "base_revision", "head_revision")
    @classmethod
    def _reject_machine_paths(cls, value: str) -> str:
        """Reject absolute, backslash-bearing, or whitespace values."""
        if (
            value.startswith("/")
            or "\\" in value
            or any(char.isspace() for char in value)
        ):
            raise ValueError("identity must not contain a machine path")
        return value


class ReviewAction(BaseModel):
    """One retained review candidate, including skipped evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action_id: str = Field(
        min_length=1,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    )
    kind: ReviewKind
    selected: bool
    body: str = Field(min_length=1)
    path: PurePosixPath | None = None
    line: int | None = Field(default=None, gt=0)
    side: ReviewSide | None = None
    start_line: int | None = Field(default=None, gt=0)
    start_side: ReviewSide | None = None
    thread_id: str | None = None
    deduplication_key: str = Field(min_length=1)
    validation_state: ValidationState
    validation_reason: str | None = None
    intended_action: IntendedAction
    outcome: ActionOutcome

    @field_validator("path", mode="before")
    @classmethod
    def _validate_path(cls, value: object) -> PurePosixPath | None:
        """Require repository-relative POSIX paths when present."""
        if value is None:
            return None
        if isinstance(value, str):
            raw = value
        elif isinstance(value, PurePosixPath):
            raw = value.as_posix()
        else:
            raise ValueError("path must be a string or POSIX path")
        if (
            not raw
            or raw == "."
            or raw.startswith("/")
            or "\\" in raw
            or any(part in {".", ".."} for part in raw.split("/"))
        ):
            raise ValueError("path must be repository-relative")
        return PurePosixPath(raw)

    @model_validator(mode="after")
    def _validate_kind(self) -> "ReviewAction":
        """Require location and thread fields appropriate to the action kind."""
        expected_intended = {
            "inline": "create-inline",
            "general": "create-general",
            "reply": "reply",
        }[self.kind]
        if self.intended_action != expected_intended:
            raise ValueError("intended_action does not match kind")
        if self.validation_state != "valid" and not self.validation_reason:
            raise ValueError("invalid action state requires validation_reason")
        if self.kind == "inline":
            if self.validation_state == "valid" and (
                self.path is None or self.line is None or self.side is None
            ):
                raise ValueError("inline action requires path, line, and side")
            if self.thread_id is not None:
                raise ValueError("inline action must not contain thread_id")
        elif self.kind == "general":
            if self.validation_state == "valid" and any(
                value is not None
                for value in (
                    self.path,
                    self.line,
                    self.side,
                    self.start_line,
                    self.start_side,
                    self.thread_id,
                )
            ):
                raise ValueError("general action must not contain a location")
        elif self.validation_state == "valid" and not self.thread_id:
            raise ValueError("reply action requires thread_id")
        elif self.kind == "reply" and any(
            value is not None
            for value in (
                self.path,
                self.line,
                self.side,
                self.start_line,
                self.start_side,
            )
        ):
            raise ValueError("reply action must not contain a location")
        if (self.start_line is None) != (self.start_side is None):
            raise ValueError("range requires both start_line and start_side")
        if self.start_line is not None and (
            self.line is None or self.start_line > self.line
        ):
            raise ValueError("start_line must not exceed line")
        return self


class ReviewDiagnostic(BaseModel):
    """One bounded parse diagnostic retained beside a logical plan."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action_id: str = Field(min_length=1)
    validation_state: Literal["invalid"] = "invalid"
    reason: str = Field(min_length=1)


class ReviewCommentPlan(BaseModel):
    """Logical review plan compiled from a human-editable draft."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal["review-comment-plan/v1"]
    identity: ReviewIdentity
    source_draft_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    actions: tuple[ReviewAction, ...] = ()
    diagnostics: tuple[ReviewDiagnostic, ...] = ()

    @model_validator(mode="after")
    def _validate_actions(self) -> "ReviewCommentPlan":
        """Require retained actions or bounded parse diagnostics."""
        action_ids = [action.action_id for action in self.actions]
        if len(action_ids) != len(set(action_ids)):
            raise ValueError("action IDs must be unique")
        if not self.actions and not self.diagnostics:
            raise ValueError("plan must contain actions or diagnostics")
        return self


class NormalizedThread(BaseModel):
    """Provider-neutral view of one native review thread."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    thread_id: str = Field(min_length=1, max_length=256)
    comment_ids: tuple[str, ...] = Field(min_length=1)
    state: NormalizedThreadState
    path: PurePosixPath | None = None
    line: int | None = Field(default=None, gt=0)
    side: ReviewSide | None = None
    start_line: int | None = Field(default=None, gt=0)
    start_side: ReviewSide | None = None
    author: str = Field(min_length=1, max_length=256)
    body: str = Field(min_length=1, max_length=10000)
    chronology: tuple[str, ...] = Field(min_length=1)
    limitations: tuple[str, ...] = ()

    @field_validator("path", mode="before")
    @classmethod
    def _validate_thread_path(
        cls, value: str | PurePosixPath | None
    ) -> PurePosixPath | None:
        """Require repository-relative POSIX paths when present."""
        if value is None:
            return None
        raw = value if isinstance(value, str) else value.as_posix()
        if (
            not raw
            or raw == "."
            or raw.startswith("/")
            or "\\" in raw
            or any(part in {".", ".."} for part in raw.split("/"))
        ):
            raise ValueError("path must be repository-relative")
        return PurePosixPath(raw)

    @model_validator(mode="after")
    def _validate_thread(self) -> "NormalizedThread":
        """Keep location pairs and bounded normalization evidence coherent."""
        if self.path is None and any(
            value is not None
            for value in (self.line, self.side, self.start_line, self.start_side)
        ):
            raise ValueError("thread location requires path")
        if self.path is not None and (self.line is None) != (self.side is None):
            raise ValueError("thread location requires line and side")
        if (self.start_line is None) != (self.start_side is None):
            raise ValueError("thread range requires both start fields")
        if any(len(limitation) > 2000 for limitation in self.limitations):
            raise ValueError("limitations are too long")
        return self


class NormalizedReviewThreads(BaseModel):
    """Validated provider-neutral native thread observations."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal["normalized-review-threads/v1"]
    identity: ReviewIdentity
    observed_head: str = Field(min_length=1)
    limitations: tuple[str, ...] = ()
    threads: tuple[NormalizedThread, ...] = ()

    @model_validator(mode="after")
    def _validate_source(self) -> "NormalizedReviewThreads":
        """Bind the normalized source to its provider/change head."""
        if self.observed_head != self.identity.head_revision:
            raise ValueError("normalized thread head does not match identity head")
        if any(len(limitation) > 2000 for limitation in self.limitations):
            raise ValueError("limitations are too long")
        thread_ids = [thread.thread_id for thread in self.threads]
        if len(thread_ids) != len(set(thread_ids)):
            raise ValueError("thread IDs must be unique")
        return self


class ReviewResponseItem(BaseModel):
    """One evaluated thread, including selected or skipped next action."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    thread_id: str = Field(min_length=1, max_length=256)
    classification: ResponseClassification
    evaluation: str = Field(min_length=1, max_length=4000)
    evidence: str = Field(min_length=1, max_length=4000)
    proposed_changes: tuple[str, ...] = ()
    proposed_response: str | None = Field(default=None, max_length=4000)
    verification: tuple[str, ...] = ()
    selected_action: ResponseAction


class ReviewResponsePlan(BaseModel):
    """Non-mutating response plan bound to normalized thread observations."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal["review-response-plan/v1"]
    identity: ReviewIdentity
    source_threads_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    observed_head: str = Field(min_length=1)
    items: tuple[ReviewResponseItem, ...] = ()

    @model_validator(mode="after")
    def _validate_response_source(self) -> "ReviewResponsePlan":
        """Keep the response target and observed head immutable."""
        if self.observed_head != self.identity.head_revision:
            raise ValueError("response plan head does not match identity head")
        item_ids = [item.thread_id for item in self.items]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("response thread IDs must be unique")
        return self


class PublicationItemPreview(BaseModel):
    """One current publication decision and ephemeral request payload."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action_id: str = Field(min_length=1)
    deduplication_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    state: PublicationItemState
    reason: str | None = None
    payload: dict[str, object] | None = None


class PublicationPreview(BaseModel):
    """Approval-bound GitHub publication preview."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal["publication-preview/v1"]
    plan_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    identity: ReviewIdentity
    expected_head: str = Field(min_length=1)
    observed_head: str = Field(min_length=1)
    remote_state_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: Literal["ready", "blocked"]
    items: tuple[PublicationItemPreview, ...] = ()


class PublicationReceiptItem(BaseModel):
    """One minimal publication outcome."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action_id: str = Field(min_length=1)
    deduplication_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    outcome: ActionOutcome
    reason: str | None = None
    remote_id: int | None = Field(default=None, gt=0)
    remote_url: str | None = None


class PublicationReceipt(BaseModel):
    """Minimal persisted publication outcomes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal["publication-receipt/v1"]
    plan_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    identity: ReviewIdentity
    expected_head: str = Field(min_length=1)
    observed_head: str = Field(min_length=1)
    status: PublicationStatus
    items: tuple[PublicationReceiptItem, ...] = ()
