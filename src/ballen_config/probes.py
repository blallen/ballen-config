"""Shared predicates and presence rules over native command output.

These helpers isolate assumptions about the output format of external tools
so that a format change only needs updating in one place, and so that the
match rule cannot silently drift between the install, doctor, and CLI
dispatch sites that all need it.

The predicates take their effects as arguments rather than performing them,
so the rules stay testable without a subprocess or a filesystem.
"""

import os
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Final

from ballen_config.runner import CommandResult, Runner

CURSOR_EDITOR_CLI: Final = Path(
    "/Applications/Cursor.app/Contents/Resources/app/bin/cursor"
)


def _is_executable_file(path: Path) -> bool:
    """Return whether a path resolves to an executable regular file."""
    return path.is_file() and os.access(path, os.X_OK)


def home_executable_present(
    relative_path: str | None,
    home: Path | None,
    path_is_executable: Callable[[Path], bool] = _is_executable_file,
) -> bool:
    """Return whether a declared home-relative executable is usable."""
    if relative_path is None or home is None:
        return False
    return path_is_executable(home / relative_path)


def run_cursor_editor_command(
    runner: Runner,
    command: Sequence[str],
) -> CommandResult:
    """Run a Cursor editor command with the known app-bundle fallback.

    The PATH command remains authoritative when it resolves, including when
    Cursor itself reports an operation failure. Only shell-style unavailable
    statuses fall back to the executable shipped inside ``Cursor.app``.
    """
    if not command or command[0] != "cursor":
        raise ValueError("Cursor editor command must start with cursor")
    return run_command_with_fallback(runner, command, CURSOR_EDITOR_CLI)


def run_command_with_fallback(
    runner: Runner,
    command: Sequence[str],
    fallback_executable: Path,
) -> CommandResult:
    """Run a command, retrying an unavailable executable at one known path."""
    if not command:
        raise ValueError("command must not be empty")
    result = runner.run(command)
    if result["returncode"] not in {126, 127}:
        return result
    return runner.run((str(fallback_executable), *command[1:]))


def application_paths_present(
    paths: Sequence[str], path_exists: Callable[[Path], bool]
) -> bool:
    """Return whether a component's declared application paths all exist.

    A component with no declared ``application_paths`` cannot be judged
    present by this check: ``all()`` over an empty sequence is vacuously
    ``True``, so without an explicit emptiness guard every such component
    would be reported present regardless of installation state.

    Args:
        paths: A component's declared application paths.
        path_exists: Injected existence check, so this function stays pure.

    Returns:
        Whether ``paths`` is non-empty and every path in it exists.
    """
    return bool(paths) and all(path_exists(Path(path)) for path in paths)


def receipts_match(stdout: str, prefixes: Sequence[str]) -> bool:
    """Return whether every declared receipt prefix has an installed match.

    ``pkgutil --pkgs`` prints one installed receipt identifier per line. A
    component's ``receipt_prefixes`` are satisfied only when each declared
    prefix is a prefix of at least one installed receipt line: ``all()`` over
    the declared prefixes on the outside, ``any()`` over the installed
    receipts on the inside. Swapping the nesting would instead accept a
    single matching receipt as proof that every prefix is installed.

    An empty ``prefixes`` is vacuously satisfied and returns ``True``. That
    is deliberate, and it is the opposite of the emptiness rule in
    :func:`application_paths_present`, so the difference is worth stating.
    The question here is whether every declared prefix is installed; a
    component that declares none has nothing left to prove. Callers treat a
    component without ``receipt_prefixes`` as satisfied for exactly that
    reason, and they short-circuit before calling only to avoid running
    ``pkgutil`` when there is nothing to match. Returning ``False`` instead
    would contradict them and report every receipt-less component missing.

    ``application_paths_present`` differs because a declared path is the
    evidence itself: with no paths declared there is nothing to observe, so
    presence cannot be concluded.

    Args:
        stdout: Captured standard output from ``pkgutil --pkgs``.
        prefixes: A component's declared receipt prefixes.

    Returns:
        Whether every prefix in ``prefixes`` matches at least one line of
        ``stdout`` via ``startswith``. Vacuously ``True`` when ``prefixes``
        is empty.
    """
    installed_receipts = stdout.splitlines()
    return all(
        any(receipt.startswith(prefix) for receipt in installed_receipts)
        for prefix in prefixes
    )


def brew_artifact_present(
    *,
    application_paths: Sequence[str],
    receipt_prefixes: Sequence[str],
    path_exists: Callable[[Path], bool],
    read_receipts: Callable[[], CommandResult],
    home: Path | None = None,
    home_executable: str | None = None,
    path_is_executable: Callable[[Path], bool] = _is_executable_file,
) -> bool:
    """Return whether declared artifacts prove a Homebrew component installed.

    This is the whole declared-artifact rule, not one of its parts. A
    component is proven present when its declared home-relative executable is
    usable, or when every declared application path exists and a readable
    ``pkgutil --pkgs`` matches every declared receipt prefix. Declared paths
    without a matching required receipt are not proof: BasicTeX provides the
    same ``latex`` binary as full MacTeX, so the receipt distinguishes them.

    A negative answer means only that the declared artifacts did not prove
    presence. Callers fall back to their own package query, so the component
    may still be installed.

    ``read_receipts`` is called only when it is needed, so a component that
    declares no prefixes costs no subprocess.

    Arguments are keyword-only because the two sequence parameters share a
    type: passed positionally, transposing them would match declared paths
    against receipts and test prefixes for existence on disk, and no type
    checker would object.

    Args:
        application_paths: A component's declared application paths.
        receipt_prefixes: A component's declared receipt prefixes.
        path_exists: Injected existence check, so this function stays pure.
        read_receipts: Injected ``pkgutil --pkgs`` reader, called at most once.
        home: Home root used to resolve ``home_executable``.
        home_executable: Optional reviewed executable path relative to home.
        path_is_executable: Injected executable-file predicate.

    Returns:
        Whether the declared artifacts prove the component is installed.
    """
    if home_executable_present(home_executable, home, path_is_executable):
        return True
    if not application_paths_present(application_paths, path_exists):
        return False
    if not receipt_prefixes:
        return True
    receipts = read_receipts()
    return receipts["returncode"] == 0 and receipts_match(
        receipts["stdout"], receipt_prefixes
    )


def uv_tool_listed(stdout: str, package: str) -> bool:
    """Return whether ``uv tool list`` output declares a package installed.

    ``uv tool list`` prints one ``name vX.Y.Z`` line per installed tool,
    followed by zero or more indented ``- entrypoint`` lines naming the
    executables it provides. Splitting each line on the first space and
    comparing only the first field matches against the tool name and
    excludes those entrypoint lines, whose first token is always ``-``. A
    naive substring match would instead report a false positive whenever
    one tool's entrypoint name contains or equals another tool's package
    name.

    Args:
        stdout: Captured standard output from ``uv tool list``.
        package: Package name to look for among the listed tools.

    Returns:
        Whether a listed tool's name field equals ``package``.
    """
    return any(line.split(" ", 1)[0] == package for line in stdout.splitlines())
