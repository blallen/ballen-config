"""Tests for normalized subprocess execution failures."""

import errno
import os
from pathlib import Path

import pytest

from ballen_config.runner import SubprocessRunner


def test_non_executable_command_returns_shell_unavailable_status(
    tmp_path: Path,
) -> None:
    """Normalize a real permission failure so executable fallback can proceed."""
    command = tmp_path / "not-executable"
    command.write_text("#!/bin/sh\nexit 0\n")
    command.chmod(0o600)

    assert SubprocessRunner().run((str(command),)) == {
        "returncode": 126,
        "stdout": "",
        "stderr": "",
    }


def test_exec_format_error_returns_shell_unavailable_status(tmp_path: Path) -> None:
    """Normalize a real executable file whose format the OS cannot execute."""
    command = tmp_path / "invalid-executable"
    command.write_text("not an executable format\n")
    command.chmod(0o700)

    assert SubprocessRunner().run((str(command),)) == {
        "returncode": 126,
        "stdout": "",
        "stderr": "",
    }


def test_unrelated_os_error_is_not_normalized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Preserve unexpected operating-system failures for the caller to handle."""

    def fail(*_args: object, **_kwargs: object) -> None:
        raise OSError(errno.EIO, os.strerror(errno.EIO))

    monkeypatch.setattr("ballen_config.runner.subprocess.run", fail)

    with pytest.raises(OSError) as error:
        SubprocessRunner().run(("ignored",))

    assert error.value.errno == errno.EIO
