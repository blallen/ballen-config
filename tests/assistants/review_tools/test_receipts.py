"""Tests for minimal publication preview and receipt contracts."""

import pytest
from ballen_review_tools.models import (
    PublicationPreview,
    PublicationReceipt,
    ReviewIdentity,
)
from pydantic import ValidationError


def _identity() -> ReviewIdentity:
    """Return one stable provider identity."""
    return ReviewIdentity(
        provider="github",
        host="github.com",
        repository="acme/ballen-config",
        change_number=17,
        base_revision="a" * 40,
        head_revision="b" * 40,
    )


def test_preview_and_receipt_forbid_raw_provider_material() -> None:
    """Reject raw provider material in persisted publication artifacts."""
    preview = PublicationPreview(
        contract_version="publication-preview/v1",
        plan_digest="c" * 64,
        identity=_identity(),
        expected_head="b" * 40,
        observed_head="b" * 40,
        remote_state_digest="d" * 64,
        status="ready",
        items=(),
    )
    receipt = PublicationReceipt(
        contract_version="publication-receipt/v1",
        plan_digest="c" * 64,
        identity=_identity(),
        expected_head="b" * 40,
        observed_head="b" * 40,
        status="blocked",
        items=(),
    )

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PublicationPreview.model_validate({**preview.model_dump(), "headers": {}})
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PublicationReceipt.model_validate({**receipt.model_dump(), "response": {}})
