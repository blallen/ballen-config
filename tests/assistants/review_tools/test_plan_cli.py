"""Tests for the read-only review-plan command."""

from pathlib import Path

from ballen_review_tools.plan_cli import main


def test_digest_command_prints_canonical_artifact_digest(
    tmp_path: Path,
    capsys: object,
) -> None:
    """Expose one stable digest without a provider call."""
    artifact = tmp_path / "plan.json"
    artifact.write_text('{"b": 2, "a": 1}\n')

    assert main(["digest", "--artifact", str(artifact)]) == 0
    assert len(capsys.readouterr().out.strip()) == 64  # type: ignore[attr-defined]
