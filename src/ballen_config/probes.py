"""Pure, side-effect-free predicates over native command output.

These helpers isolate assumptions about the output format of external tools
so that a format change only needs updating in one place, and so that the
match rule cannot silently drift between the install, doctor, and CLI
dispatch sites that all need it.
"""

from collections.abc import Callable, Sequence
from pathlib import Path


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

    Args:
        stdout: Captured standard output from ``pkgutil --pkgs``.
        prefixes: A component's declared receipt prefixes.

    Returns:
        Whether every prefix in ``prefixes`` matches at least one line of
        ``stdout`` via ``startswith``.
    """
    installed_receipts = stdout.splitlines()
    return all(
        any(receipt.startswith(prefix) for receipt in installed_receipts)
        for prefix in prefixes
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
