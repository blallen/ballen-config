import pytest

from ballen_config.cli import STAGES, parse_args


@pytest.fixture
def repeated_selection_arguments() -> list[str]:
    """Return ordered repeated include and skip arguments."""
    return [
        "plan",
        "--profile",
        "work",
        "--include",
        "mactex",
        "--include",
        "signal",
        "--skip",
        "cursor",
        "--skip",
        "codex",
    ]


def test_cli_accepts_stage_profile_and_repeated_selections(
    repeated_selection_arguments: list[str],
) -> None:
    options = parse_args(repeated_selection_arguments)

    assert options.stage == "plan"
    assert options.request.profile == "work"
    assert options.request.includes == ("mactex", "signal")
    assert options.request.skips == ("cursor", "codex")


def test_cli_defaults_to_all_and_default_profile() -> None:
    options = parse_args([])

    assert STAGES == (
        "all",
        "prepare",
        "plan",
        "install",
        "configure",
        "doctor",
    )
    assert options.stage == "all"
    assert options.request.profile == "default"
    assert options.request.includes == ()
    assert options.request.skips == ()
