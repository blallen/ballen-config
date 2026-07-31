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
    def _validate_path(cls, value: str | PurePosixPath | None) -> PurePosixPath | None:
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
