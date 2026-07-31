"""Tests for strict logical review artifacts."""

from pathlib import PurePosixPath

import pytest
from ballen_review_tools.models import (
    ReviewAction,
    ReviewCommentPlan,
    ReviewIdentity,
)
from pydantic import ValidationError


def _identity() -> ReviewIdentity:
    """Return a stable GitHub pull-request identity for model tests."""
    return ReviewIdentity(
        provider="github",
        host="github.com",
        repository="ballen-config",
        change_number=17,
        base_revision="a" * 40,
        head_revision="b" * 40,
    )


def _inline_action(**overrides: object) -> ReviewAction:
    """Build one valid inline action and apply test-specific overrides."""
    values: dict[str, object] = {
        "action_id": "R001",
        "kind": "inline",
        "selected": True,
        "body": "Guard the empty case.",
        "path": PurePosixPath("src/example.py"),
        "line": 20,
        "side": "RIGHT",
        "deduplication_key": "github:R001",
        "validation_state": "valid",
        "intended_action": "create-inline",
        "outcome": "pending",
    }
    values.update(overrides)
    return ReviewAction.model_validate(values)


def test_inline_action_accepts_a_relative_range() -> None:
    """Keep provider-neutral file and line information in the action."""
    action = _inline_action(start_line=18, start_side="RIGHT")

    assert action.path == PurePosixPath("src/example.py")
    assert action.line == 20
    assert action.start_line == 18


def test_inline_action_rejects_an_absolute_path() -> None:
    """Prevent machine-specific paths from entering canonical artifacts."""
    with pytest.raises(ValidationError, match="relative"):
        _inline_action(path="/tmp/example.py")


@pytest.mark.parametrize("path", [".", "src/../example.py", "src\\example.py"])
def test_inline_action_rejects_unsafe_relative_path(path: str) -> None:
    """Reject ambiguous and platform-specific repository paths."""
    with pytest.raises(ValidationError, match="relative"):
        _inline_action(path=path)


def test_inline_action_rejects_missing_location() -> None:
    """Require a logical location for inline review actions."""
    with pytest.raises(ValidationError, match="line"):
        _inline_action(path=None, line=None, side=None)


def test_inline_action_rejects_incomplete_range() -> None:
    """Require both fields when an inline range starts are supplied."""
    with pytest.raises(ValidationError, match="both"):
        _inline_action(start_line=18)


def test_reply_action_rejects_inline_location() -> None:
    """Keep replies addressed to native threads rather than file lines."""
    with pytest.raises(ValidationError, match="location"):
        _inline_action(
            kind="reply",
            thread_id="discussion-1",
            intended_action="reply",
        )


def test_action_rejects_mismatched_intended_action() -> None:
    """Keep the provider action derived from the logical kind."""
    with pytest.raises(ValidationError, match="intended_action"):
        _inline_action(intended_action="create-general")


def test_invalid_action_requires_bounded_reason() -> None:
    """Require evidence when a candidate could not be validated."""
    with pytest.raises(ValidationError, match="validation_reason"):
        _inline_action(
            validation_state="invalid",
            path=None,
            line=None,
            side=None,
        )


def test_invalid_action_can_retain_incomplete_candidate() -> None:
    """Retain malformed known-kind candidates with an explicit reason."""
    action = _inline_action(
        validation_state="invalid",
        validation_reason="missing line",
        path=None,
        line=None,
        side=None,
        outcome="not-attempted",
    )

    assert action.validation_state == "invalid"


def test_plan_rejects_unknown_keys() -> None:
    """Keep artifact contracts closed to accidental authorization fields."""
    with pytest.raises(ValidationError, match="extra_field"):
        ReviewCommentPlan.model_validate(
            {
                "contract_version": "review-comment-plan/v1",
                "identity": _identity(),
                "source_draft_digest": "a" * 64,
                "actions": [_inline_action()],
                "extra_field": "should fail",
            }
        )


def test_plan_rejects_duplicate_action_ids() -> None:
    """Keep action identity unambiguous in direct model construction."""
    with pytest.raises(ValidationError, match="unique"):
        ReviewCommentPlan(
            contract_version="review-comment-plan/v1",
            identity=_identity(),
            source_draft_digest="a" * 64,
            actions=(_inline_action(), _inline_action()),
        )


def test_selected_action_has_no_authorization_field() -> None:
    """Keep selection as candidate state, never publication authority."""
    action = _inline_action()

    assert action.selected is True
    assert "approved" not in type(action).model_fields
    assert "authorized" not in type(action).model_fields
