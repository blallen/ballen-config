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


def test_inline_action_rejects_missing_location() -> None:
    """Require a logical location for inline review actions."""
    with pytest.raises(ValidationError, match="line"):
        _inline_action(path=None, line=None, side=None)


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


def test_selected_action_has_no_authorization_field() -> None:
    """Keep selection as candidate state, never publication authority."""
    action = _inline_action()

    assert action.selected is True
    assert "approved" not in type(action).model_fields
    assert "authorized" not in type(action).model_fields
