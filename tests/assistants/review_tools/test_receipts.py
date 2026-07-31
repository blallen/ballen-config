"""Tests for minimal publication preview and receipt contracts."""

from ballen_review_tools.models import (
    PublicationPreview,
    PublicationReceipt,
    ReviewIdentity,
)


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
    """Keep persisted publication artifacts minimal and redacted."""
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

    assert "headers" not in preview.model_dump()
    assert "response" not in receipt.model_dump()
