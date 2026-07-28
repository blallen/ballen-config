"""Shared assertions for coding-agent adapter tests."""


def assert_canonical_instruction_contract(
    *,
    rendered: str,
    engineering: str,
    suffix: str,
) -> None:
    """Verify one canonical core and no precedence duplicate in the suffix."""
    precedence = "Repository instructions and executable configuration take precedence."
    core_count = rendered.count(engineering.rstrip())
    precedence_count = " ".join(rendered.split()).count(precedence)
    suffix_has_precedence = precedence in " ".join(suffix.split())
    assert core_count == 1, f"expected one canonical core, found {core_count}"
    assert precedence_count == 1, (
        f"expected one precedence rule, found {precedence_count}"
    )
    assert not suffix_has_precedence, "agent suffix duplicates the precedence rule"
