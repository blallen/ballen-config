"""Tests for deterministic review-artifact digests."""

import json
from pathlib import Path

from ballen_review_tools.canonical import canonical_digest, deduplication_key


def test_canonical_digest_ignores_mapping_insertion_order() -> None:
    """Bind equivalent logical JSON to one digest."""
    first = canonical_digest({"b": 2, "a": 1})
    second = canonical_digest({"a": 1, "b": 2})

    assert first == second
    assert len(first) == 64


def test_deduplication_key_binds_provider_target_and_location() -> None:
    """Avoid treating a comment at a different location as a duplicate."""
    first = deduplication_key(
        provider="github",
        host="github.com",
        repository="ballen-config",
        change_number=17,
        kind="inline",
        body="Guard the empty case.",
        path="src/example.py",
        line=20,
    )
    second = deduplication_key(
        provider="github",
        host="github.com",
        repository="ballen-config",
        change_number=17,
        kind="inline",
        body="Guard the empty case.",
        path="src/example.py",
        line=21,
    )

    assert first != second


def test_checked_in_canonical_vectors_are_stable() -> None:
    """Keep canonical JSON behavior locked by concrete artifact vectors."""
    vector_path = (
        Path(__file__).parents[3]
        / "assistants/shared/tools/review/contracts/review-comment-plan-vectors.json"
    )
    vectors = json.loads(vector_path.read_text(encoding="utf-8"))["vectors"]

    assert vectors
    for vector in vectors:
        expected = bytes(vector["sha256_bytes"]).hex()
        assert canonical_digest(vector["payload"]) == expected
