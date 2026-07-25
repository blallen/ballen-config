import argparse
from collections.abc import Sequence
from dataclasses import dataclass

from ballen_config.models import ResolutionRequest

STAGES = ("all", "prepare", "plan", "install", "configure", "doctor")


@dataclass(frozen=True)
class CliOptions:
    """Parsed bootstrap options."""

    stage: str
    request: ResolutionRequest


def parse_args(arguments: Sequence[str] | None = None) -> CliOptions:
    """Parse bootstrap stage and component selection arguments.

    Args:
        arguments: Arguments to parse, or ``None`` to use process arguments.

    Returns:
        Typed CLI options with ordered include and skip selections.
    """
    parser = argparse.ArgumentParser(prog="bootstrap")
    parser.add_argument("stage", nargs="?", choices=STAGES, default="all")
    parser.add_argument("--profile", default="default")
    parser.add_argument("--include", action="append", default=[])
    parser.add_argument("--skip", action="append", default=[])
    namespace = parser.parse_args(arguments)
    return CliOptions(
        stage=namespace.stage,
        request=ResolutionRequest(
            profile=namespace.profile,
            includes=tuple(namespace.include),
            skips=tuple(namespace.skip),
        ),
    )
