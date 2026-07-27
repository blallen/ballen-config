import subprocess
from collections.abc import Sequence
from typing import Protocol, TypedDict


class CommandResult(TypedDict):
    """Captured subprocess result."""

    returncode: int
    stdout: str
    stderr: str


class Runner(Protocol):
    """Subprocess boundary used by installers and diagnostics."""

    def run(self, command: Sequence[str]) -> CommandResult:
        """Run a command without displaying captured output."""


class SubprocessRunner:
    """Production subprocess runner."""

    def run(self, command: Sequence[str]) -> CommandResult:
        """Run a command and capture its result."""
        try:
            completed = subprocess.run(
                list(command),
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            return {"returncode": 127, "stdout": "", "stderr": ""}
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
