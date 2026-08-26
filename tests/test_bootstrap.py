import hashlib
import os
import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import TypedDict

import pytest


class FakeStageZeroTools(TypedDict):
    """Paths and environment for isolated stage-zero tool doubles."""

    command_log: Path
    environment: dict[str, str]
    root: Path


def write_executable(path: Path, contents: str) -> None:
    """Write a private executable test command.

    Args:
        path: Destination for the executable.
        contents: Complete command contents, including the shebang.
    """
    path.write_text(contents, encoding="utf-8")
    path.chmod(0o700)


def lock_fingerprint(root: Path) -> str:
    """Return the SHA-256 fingerprint of an isolated checkout lock file."""
    return hashlib.sha256((root / "uv.lock").read_bytes()).hexdigest()


def runtime_marker(root: Path) -> Path:
    """Return the isolated runtime readiness marker path."""
    return root / ".venv/.ballen-config-lock.sha256"


@pytest.fixture
def fake_stage_zero_tools(
    repo_root: Path,
    tmp_path: Path,
) -> FakeStageZeroTools:
    """Provide deterministic private substitutes for stage-zero commands."""
    tools_root = tmp_path / "tools"
    tools_root.mkdir(mode=0o700)
    command_log = tmp_path / "command.log"

    write_executable(
        tools_root / "uname",
        """#!/bin/zsh
set -eu
umask 077
print -r -- "uname $*" >> "$COMMAND_LOG"
print -r -- "${FAKE_UNAME_OUTPUT:-Darwin}"
""",
    )
    write_executable(
        tools_root / "xcode-select",
        """#!/bin/zsh
set -eu
umask 077
print -r -- "xcode-select $*" >> "$COMMAND_LOG"
if [[ "${1:-}" == "-p" ]]; then
  [[ "${FAKE_XCODE_READY:-1}" == "1" ]]
  exit
fi
if [[ "${1:-}" == "--install" ]]; then
  exit 0
fi
exit 2
""",
    )
    write_executable(
        tools_root / "curl",
        """#!/bin/zsh
set -eu
umask 077
print -r -- "curl $*" >> "$COMMAND_LOG"
local output=""
while (( $# > 0 )); do
  if [[ "$1" == "-o" ]]; then
    output="$2"
    shift 2
  else
    shift
  fi
done
if [[ -n "$output" ]]; then
  print -r -- "${FAKE_INSTALLER_CONTENT:-exit 0}" > "$output"
else
  print -r -- "${FAKE_INSTALLER_CONTENT:-exit 0}"
fi
""",
    )
    write_executable(
        tools_root / "bash",
        """#!/bin/zsh
set -eu
umask 077
print -r -- "bash $*" >> "$COMMAND_LOG"
""",
    )
    write_executable(
        tools_root / "brew",
        """#!/bin/zsh
set -eu
umask 077
print -r -- "brew $*" >> "$COMMAND_LOG"
if [[ "${1:-}" == "--prefix" ]]; then
  print -r -- "$FAKE_BREW_PREFIX"
fi
""",
    )
    write_executable(
        tools_root / "shasum",
        """#!/bin/zsh
set -eu
umask 077
print -r -- "shasum $*" >> "$COMMAND_LOG"
[[ "${1:-}" == "-a" && "${2:-}" == "256" ]] || exit 2
if [[ "${3:-}" == *uv.lock ]]; then
  print -r -- "$FAKE_LOCK_HASH  ${3:-}"
else
  print -r -- "$FAKE_INSTALLER_HASH  ${3:-}"
fi
""",
    )
    write_executable(
        tools_root / "uv",
        """#!/bin/zsh
set -eu
umask 077
print -r -- "uv $*" >> "$COMMAND_LOG"
if [[ "${1:-}" == "sync" ]]; then
  if [[ "${FAKE_UV_SYNC_STATUS:-0}" != "0" ]]; then
    exit "$FAKE_UV_SYNC_STATUS"
  fi
  /bin/mkdir -p "$PWD/.venv/bin"
  {
    print -r -- '#!/bin/zsh'
    print -r -- 'set -eu'
    print -r -- 'if [[ "${1:-}" == "--version" ]]; then'
    print -r -- '  print -r -- "Python 3.12.9"'
    print -r -- '  exit 0'
    print -r -- 'fi'
    print -r -- 'if [[ "${1:-}" == "-B" && "${2:-}" == "-c" ]]; then'
    print -r -- '  [[ "${3:-}" == "import ballen_config, pydantic, yaml, tomlkit" ]] || exit 2'
    print -r -- '  [[ "${FAKE_RUNTIME_IMPORTS_READY:-1}" == "1" ]]'
    print -r -- '  exit'
    print -r -- 'fi'
    print -r -- 'exit 2'
  } > "$PWD/.venv/bin/python"
  /bin/chmod 700 "$PWD/.venv/bin/python"
fi
""",
    )
    return {
        "command_log": command_log,
        "environment": {
            "BALLEN_BOOTSTRAP_TOOL_ROOT": str(tools_root),
            "COMMAND_LOG": str(command_log),
            "FAKE_BREW_PREFIX": str(tools_root),
            "FAKE_INSTALLER_HASH": hashlib.sha256(b"exit 0\n").hexdigest(),
            "FAKE_LOCK_HASH": lock_fingerprint(repo_root),
            "PATH": f"{tools_root}:/usr/bin:/bin",
        },
        "root": tools_root,
    }


def copy_stage_zero(repo_root: Path, tmp_path: Path) -> Path:
    """Copy the stage-zero interface into an isolated checkout."""
    root = tmp_path / "checkout"
    (root / "manifests").mkdir(parents=True)
    shutil.copy2(repo_root / "bootstrap", root / "bootstrap")
    shutil.copy2(
        repo_root / "manifests/component-ids.txt",
        root / "manifests/component-ids.txt",
    )
    shutil.copy2(repo_root / "uv.lock", root / "uv.lock")
    return root


def run_bootstrap(
    root: Path,
    *arguments: str,
    environment: Mapping[str, str] | None = None,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the isolated stage-zero shim.

    Args:
        root: Isolated checkout root.
        *arguments: Original arguments to forward to the shim.
        environment: Optional controlled environment overrides.
        input_text: Optional confirmation response.

    Returns:
        The completed Zsh process.
    """
    process_environment = {**os.environ, "PATH": "/usr/bin:/bin"}
    if environment is not None:
        process_environment.update(environment)
    return subprocess.run(
        ["/bin/zsh", str(root / "bootstrap"), *arguments],
        cwd=root,
        env=process_environment,
        check=False,
        capture_output=True,
        input=input_text,
        text=True,
    )


def snapshot_checkout(root: Path) -> dict[Path, tuple[int, bytes | None]]:
    """Capture checkout paths, permissions, and file contents."""
    return {
        path.relative_to(root): (
            path.stat().st_mode,
            path.read_bytes() if path.is_file() else None,
        )
        for path in root.rglob("*")
    }


def write_runtime(root: Path, version: str = "Python 3.12.9") -> None:
    """Create a marked runtime reporting a chosen version and import status."""
    python = root / ".venv/bin/python"
    python.parent.mkdir(parents=True)
    write_executable(
        python,
        f"""#!/bin/zsh
set -eu
if [[ "${{1:-}}" == "--version" ]]; then
  print -r -- "{version}"
  exit 0
fi
if [[ "${{1:-}}" == "-B" && "${{2:-}}" == "-c" ]]; then
  [[ "${{3:-}}" == "import ballen_config, pydantic, yaml, tomlkit" ]] || exit 2
  [[ "${{FAKE_RUNTIME_IMPORTS_READY:-1}}" == "1" ]]
  exit
fi
exit 2
""",
    )
    marker = runtime_marker(root)
    marker.write_text(f"{lock_fingerprint(root)}\n", encoding="utf-8")
    marker.chmod(0o600)


def read_command_log(tools: FakeStageZeroTools) -> str:
    """Read fake command invocations, or return an empty log."""
    command_log = tools["command_log"]
    if not command_log.exists():
        return ""
    return command_log.read_text(encoding="utf-8")


def assert_no_uv_dispatch(command_log: str) -> None:
    """Assert that readiness failure neither synchronizes nor dispatches."""
    assert not any(
        line.startswith(("uv run ", "uv sync ")) for line in command_log.splitlines()
    )


def test_unknown_component_fails_before_preparation(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    """Validate component selection before probing or creating a runtime."""
    root = copy_stage_zero(repo_root, tmp_path)

    result = run_bootstrap(root, "install", "--include", "unknown")

    assert result.returncode == 2
    assert "unknown include: unknown" in result.stderr
    assert not (root / ".venv").exists()


def test_prepare_synchronizes_frozen_python_312_environment(
    repo_root: Path,
    tmp_path: Path,
    fake_stage_zero_tools: FakeStageZeroTools,
) -> None:
    """Prepare installs the reviewed interpreter and records its lock state."""
    root = copy_stage_zero(repo_root, tmp_path)

    result = run_bootstrap(
        root,
        "prepare",
        environment=fake_stage_zero_tools["environment"],
        input_text="y\n",
    )

    assert result.returncode == 0
    assert (
        "Prepare Command Line Tools, Homebrew, uv, Python 3.12, "
        "and the frozen environment?"
    ) in result.stdout
    command_log = read_command_log(fake_stage_zero_tools)
    assert "uv python install 3.12" in command_log
    assert "uv sync --frozen --python 3.12" in command_log
    assert (root / ".venv/bin/python").stat().st_mode & 0o777 == 0o700
    marker = runtime_marker(root)
    assert marker.read_text(encoding="utf-8") == f"{lock_fingerprint(root)}\n"
    assert marker.stat().st_mode & 0o777 == 0o600


def test_prepare_rejects_unverified_homebrew_installer_before_execution(
    repo_root: Path,
    tmp_path: Path,
    fake_stage_zero_tools: FakeStageZeroTools,
) -> None:
    """Never execute downloaded Homebrew bytes whose reviewed digest changed."""
    root = copy_stage_zero(repo_root, tmp_path)
    fake_stage_zero_tools["root"].joinpath("brew").unlink()
    environment = {
        **fake_stage_zero_tools["environment"],
        "FAKE_INSTALLER_HASH": "0" * 64,
    }

    result = run_bootstrap(
        root,
        "prepare",
        environment=environment,
        input_text="y\n",
    )

    assert result.returncode == 2
    assert "Homebrew installer checksum mismatch" in result.stderr
    assert not any(
        line.startswith("bash ") for line in read_command_log(fake_stage_zero_tools)
    )


def test_prepared_plan_preserves_original_arguments_without_sync(
    repo_root: Path,
    tmp_path: Path,
    fake_stage_zero_tools: FakeStageZeroTools,
) -> None:
    """Dispatch a prepared read-only request without changing its arguments."""
    root = copy_stage_zero(repo_root, tmp_path)
    write_runtime(root)

    result = run_bootstrap(
        root,
        "plan",
        "--profile",
        "wsh",
        "--include",
        "signal",
        "--skip",
        "cursor",
        environment=fake_stage_zero_tools["environment"],
    )

    assert result.returncode == 0
    command_log = read_command_log(fake_stage_zero_tools)
    assert (
        "uv run --frozen --no-sync python -m ballen_config "
        "plan --profile wsh --include signal --skip cursor"
    ) in command_log
    assert "uv sync " not in command_log


@pytest.mark.parametrize(
    "arguments",
    [
        pytest.param(("--help",), id="top-level"),
        pytest.param(("install", "--help"), id="stage-specific"),
    ],
)
def test_help_requests_are_available_before_runtime_preparation(
    repo_root: Path,
    tmp_path: Path,
    fake_stage_zero_tools: FakeStageZeroTools,
    arguments: tuple[str, ...],
) -> None:
    """Show stage-zero help without preparing or synchronizing a runtime."""
    root = copy_stage_zero(repo_root, tmp_path)

    result = run_bootstrap(
        root,
        *arguments,
        environment=fake_stage_zero_tools["environment"],
    )

    assert result.returncode == 0
    assert "usage: ./bootstrap" in result.stdout
    command_log = read_command_log(fake_stage_zero_tools)
    assert "uv run " not in command_log
    assert "uv sync " not in command_log


@pytest.mark.parametrize(
    "stage",
    [
        pytest.param("plan", id="plan"),
        pytest.param("doctor", id="doctor"),
        pytest.param("configure", id="configure"),
    ],
)
def test_prepared_read_only_stages_never_synchronize(
    repo_root: Path,
    tmp_path: Path,
    fake_stage_zero_tools: FakeStageZeroTools,
    stage: str,
) -> None:
    """Prepared read-only stages dispatch without triggering environment sync."""
    root = copy_stage_zero(repo_root, tmp_path)
    write_runtime(root)

    result = run_bootstrap(
        root,
        stage,
        environment=fake_stage_zero_tools["environment"],
    )

    assert result.returncode == 0
    command_log = read_command_log(fake_stage_zero_tools)
    assert f"python -m ballen_config {stage}" in command_log
    assert not any(line.startswith("uv sync ") for line in command_log.splitlines())


@pytest.mark.parametrize(
    "stage",
    [
        pytest.param("plan", id="plan"),
        pytest.param("doctor", id="doctor"),
        pytest.param("configure", id="configure"),
    ],
)
def test_unprepared_read_only_stages_call_no_tools_and_write_nothing(
    repo_root: Path,
    tmp_path: Path,
    fake_stage_zero_tools: FakeStageZeroTools,
    stage: str,
) -> None:
    """An unprepared read-only request leaves tools and checkout untouched."""
    root = copy_stage_zero(repo_root, tmp_path)
    before = snapshot_checkout(root)

    result = run_bootstrap(
        root,
        stage,
        environment=fake_stage_zero_tools["environment"],
    )

    assert result.returncode == 20
    assert "run ./bootstrap prepare" in result.stderr
    assert read_command_log(fake_stage_zero_tools) == ""
    assert snapshot_checkout(root) == before


def test_prepare_always_synchronizes_an_existing_valid_runtime(
    repo_root: Path,
    tmp_path: Path,
    fake_stage_zero_tools: FakeStageZeroTools,
) -> None:
    """An explicit prepare refreshes even a runtime that is already valid."""
    root = copy_stage_zero(repo_root, tmp_path)
    write_runtime(root)

    result = run_bootstrap(
        root,
        "prepare",
        environment=fake_stage_zero_tools["environment"],
        input_text="y\n",
    )

    assert result.returncode == 0
    assert "uv sync --frozen --python 3.12" in read_command_log(fake_stage_zero_tools)


def test_declined_prepare_calls_no_tools_and_writes_nothing(
    repo_root: Path,
    tmp_path: Path,
    fake_stage_zero_tools: FakeStageZeroTools,
) -> None:
    """Declining explicit preparation is a no-op for commands and checkout."""
    root = copy_stage_zero(repo_root, tmp_path)
    before = snapshot_checkout(root)

    result = run_bootstrap(
        root,
        "prepare",
        environment=fake_stage_zero_tools["environment"],
        input_text="n\n",
    )

    assert result.returncode == 0
    assert "Continue? [y/N]" in result.stderr
    assert read_command_log(fake_stage_zero_tools) == ""
    assert snapshot_checkout(root) == before


def test_declined_missing_runtime_all_calls_no_tools_and_writes_nothing(
    repo_root: Path,
    tmp_path: Path,
    fake_stage_zero_tools: FakeStageZeroTools,
) -> None:
    """Declining implicit runtime preparation leaves the checkout unchanged."""
    root = copy_stage_zero(repo_root, tmp_path)
    before = snapshot_checkout(root)

    result = run_bootstrap(
        root,
        environment=fake_stage_zero_tools["environment"],
        input_text="n\n",
    )

    assert result.returncode == 0
    assert "The runtime is missing. Run the reviewed prepare step now?" in result.stdout
    assert "Continue? [y/N]" in result.stderr
    assert read_command_log(fake_stage_zero_tools) == ""
    assert snapshot_checkout(root) == before


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        pytest.param(("unknown",), "unknown stage: unknown", id="unknown-stage"),
        pytest.param(
            ("prepare", "--unknown"),
            "unknown option: --unknown",
            id="unknown-option",
        ),
        pytest.param(
            ("prepare", "--profile"),
            "missing value for --profile",
            id="missing-profile-value",
        ),
        pytest.param(
            ("prepare", "--profile", "unknown"),
            "unknown profile: unknown",
            id="unknown-profile",
        ),
        pytest.param(
            ("install", "--skip", "unknown"),
            "unknown skip: unknown",
            id="unknown-skip",
        ),
    ],
)
def test_argument_validation_precedes_tool_calls_and_writes(
    repo_root: Path,
    tmp_path: Path,
    fake_stage_zero_tools: FakeStageZeroTools,
    arguments: tuple[str, ...],
    message: str,
) -> None:
    """Reject malformed input before any prerequisite command or write."""
    root = copy_stage_zero(repo_root, tmp_path)
    before = snapshot_checkout(root)

    result = run_bootstrap(
        root,
        *arguments,
        environment=fake_stage_zero_tools["environment"],
        input_text="y\n",
    )

    assert result.returncode == 2
    assert message in result.stderr
    assert read_command_log(fake_stage_zero_tools) == ""
    assert snapshot_checkout(root) == before


def test_install_can_prepare_missing_runtime_after_confirmation(
    repo_root: Path,
    tmp_path: Path,
    fake_stage_zero_tools: FakeStageZeroTools,
) -> None:
    """A confirmed install may prepare and then dispatch the original request."""
    root = copy_stage_zero(repo_root, tmp_path)

    result = run_bootstrap(
        root,
        "install",
        "--include",
        "signal",
        environment=fake_stage_zero_tools["environment"],
        input_text="Y\n",
    )

    assert result.returncode == 0
    assert "The runtime is missing. Run the reviewed prepare step now?" in result.stdout
    command_log = read_command_log(fake_stage_zero_tools)
    assert "uv sync --frozen --python 3.12" in command_log
    assert (
        "uv run --frozen --no-sync python -m ballen_config install --include signal"
    ) in command_log


def test_only_single_letter_confirmation_is_accepted(
    repo_root: Path,
    tmp_path: Path,
    fake_stage_zero_tools: FakeStageZeroTools,
) -> None:
    """Only the reviewed one-character confirmation opts into preparation."""
    root = copy_stage_zero(repo_root, tmp_path)
    before = snapshot_checkout(root)

    result = run_bootstrap(
        root,
        "prepare",
        environment=fake_stage_zero_tools["environment"],
        input_text="yes\n",
    )

    assert result.returncode == 0
    assert read_command_log(fake_stage_zero_tools) == ""
    assert snapshot_checkout(root) == before


def test_non_darwin_prepare_fails_without_other_prerequisite_calls(
    repo_root: Path,
    tmp_path: Path,
    fake_stage_zero_tools: FakeStageZeroTools,
) -> None:
    """Platform rejection stops before any non-platform prerequisite check."""
    root = copy_stage_zero(repo_root, tmp_path)
    environment = {
        **fake_stage_zero_tools["environment"],
        "FAKE_UNAME_OUTPUT": "Linux",
    }

    result = run_bootstrap(
        root,
        "prepare",
        environment=environment,
        input_text="y\n",
    )

    assert result.returncode == 2
    assert "macOS is required" in result.stderr
    assert read_command_log(fake_stage_zero_tools).splitlines() == ["uname -s"]


def test_missing_command_line_tools_start_install_and_require_rerun(
    repo_root: Path,
    tmp_path: Path,
    fake_stage_zero_tools: FakeStageZeroTools,
) -> None:
    """Missing Command Line Tools request installation and a later rerun."""
    root = copy_stage_zero(repo_root, tmp_path)
    environment = {
        **fake_stage_zero_tools["environment"],
        "FAKE_XCODE_READY": "0",
    }

    result = run_bootstrap(
        root,
        "prepare",
        environment=environment,
        input_text="y\n",
    )

    assert result.returncode == 20
    assert "rerun ./bootstrap prepare when it completes" in result.stderr
    assert read_command_log(fake_stage_zero_tools).splitlines() == [
        "uname -s",
        "xcode-select -p",
        "xcode-select --install",
    ]


def test_stale_lock_fingerprint_refuses_plan_without_mutation(
    repo_root: Path,
    tmp_path: Path,
    fake_stage_zero_tools: FakeStageZeroTools,
) -> None:
    """A runtime marker tied to an old lock cannot dispatch a plan."""
    root = copy_stage_zero(repo_root, tmp_path)
    write_runtime(root)
    lock_file = root / "uv.lock"
    lock_file.write_bytes(lock_file.read_bytes() + b"\n# changed after prepare\n")
    environment = {
        **fake_stage_zero_tools["environment"],
        "FAKE_LOCK_HASH": lock_fingerprint(root),
    }
    before = snapshot_checkout(root)

    result = run_bootstrap(root, "plan", environment=environment)

    assert result.returncode == 20
    assert "run ./bootstrap prepare" in result.stderr
    assert_no_uv_dispatch(read_command_log(fake_stage_zero_tools))
    assert snapshot_checkout(root) == before


def test_missing_runtime_import_refuses_plan_without_mutation(
    repo_root: Path,
    tmp_path: Path,
    fake_stage_zero_tools: FakeStageZeroTools,
) -> None:
    """A runtime without required imports cannot dispatch a plan."""
    root = copy_stage_zero(repo_root, tmp_path)
    write_runtime(root)
    environment = {
        **fake_stage_zero_tools["environment"],
        "FAKE_RUNTIME_IMPORTS_READY": "0",
    }
    before = snapshot_checkout(root)

    result = run_bootstrap(root, "plan", environment=environment)

    assert result.returncode == 20
    assert "run ./bootstrap prepare" in result.stderr
    assert_no_uv_dispatch(read_command_log(fake_stage_zero_tools))
    assert snapshot_checkout(root) == before


@pytest.mark.parametrize(
    "arguments",
    [
        pytest.param(("install",), id="install"),
        pytest.param(("configure",), id="configure"),
        pytest.param((), id="default-all"),
    ],
)
def test_prepared_non_darwin_mutating_stage_never_dispatches(
    repo_root: Path,
    tmp_path: Path,
    fake_stage_zero_tools: FakeStageZeroTools,
    arguments: tuple[str, ...],
) -> None:
    """Mutating dispatch remains unavailable when the host is not macOS."""
    root = copy_stage_zero(repo_root, tmp_path)
    write_runtime(root)
    environment = {
        **fake_stage_zero_tools["environment"],
        "FAKE_UNAME_OUTPUT": "Linux",
    }
    before = snapshot_checkout(root)

    result = run_bootstrap(root, *arguments, environment=environment)

    assert result.returncode == 2
    assert "macOS is required" in result.stderr
    command_log = read_command_log(fake_stage_zero_tools)
    assert "uname -s" in command_log
    assert not any(line.startswith("uv run ") for line in command_log.splitlines())
    assert snapshot_checkout(root) == before


def test_failed_frozen_sync_does_not_leave_runtime_marker(
    repo_root: Path,
    tmp_path: Path,
    fake_stage_zero_tools: FakeStageZeroTools,
) -> None:
    """A failed frozen sync removes readiness evidence before returning."""
    root = copy_stage_zero(repo_root, tmp_path)
    write_runtime(root)
    environment = {
        **fake_stage_zero_tools["environment"],
        "FAKE_UV_SYNC_STATUS": "9",
    }

    result = run_bootstrap(
        root,
        "prepare",
        environment=environment,
        input_text="y\n",
    )

    assert result.returncode == 9
    assert "uv sync --frozen --python 3.12" in read_command_log(fake_stage_zero_tools)
    assert not runtime_marker(root).exists()
