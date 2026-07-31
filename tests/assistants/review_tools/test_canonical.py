"""Tests for deterministic review-artifact digests."""

from pathlib import Path

from ballen_review_tools.canonical import (
    canonical_digest,
    deduplication_key,
    source_digest,
)


def test_canonical_digest_ignores_mapping_insertion_order() -> None:
    """Bind equivalent logical JSON to one digest."""
    first = canonical_digest({"b": 2, "a": 1})
    second = canonical_digest({"a": 1, "b": 2})

    assert first == second
    assert len(first) == 64


def test_source_digest_changes_when_draft_bytes_change(tmp_path: Path) -> None:
    """Bind the plan to the exact current Markdown bytes."""
    draft = tmp_path / "review.md"
    draft.write_bytes(b"draft\n")
    first = source_digest(draft)

    draft.write_bytes(b"draft changed\n")

    assert source_digest(draft) != first


def test_deduplication_key_binds_provider_target_and_location() -> None:
    """Avoid treating a comment at a different location as a duplicate."""
    first = deduplication_key(
        provider="github",
        repository="ballen-config",
        change_number=17,
        kind="inline",
        body="Guard the empty case.",
        path="src/example.py",
        line=20,
    )
    second = deduplication_key(
        provider="github",
        repository="ballen-config",
        change_number=17,
        kind="inline",
        body="Guard the empty case.",
        path="src/example.py",
        line=21,
    )

    assert first != second
