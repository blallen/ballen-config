"""Shared predicates and presence rules over native command output.

These helpers isolate assumptions about the output format of external tools
so that a format change only needs updating in one place, and so that the
match rule cannot silently drift between the install, doctor, and CLI
dispatch sites that all need it.

The predicates take their effects as arguments rather than performing them,
so the rules stay testable without a subprocess or a filesystem.
"""

from collections.abc import Callable, Sequence
from pathlib import Path

from ballen_config.runner import CommandResult


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
    application_paths: Sequence[str],
    receipt_prefixes: Sequence[str],
    path_exists: Callable[[Path], bool],
    read_receipts: Callable[[], CommandResult],
) -> bool:
    """Return whether declared artifacts prove a Homebrew component installed.

    This is the whole declared-artifact rule, not one of its parts. A
    component is proven present when every declared application path exists
    and, when it also declares ``receipt_prefixes``, a readable
    ``pkgutil --pkgs`` matches all of them. Declared paths without a matching
    receipt are not proof: BasicTeX provides the same ``latex`` binary as full
    MacTeX, so the receipt is what distinguishes them.

    A negative answer means only that the declared artifacts did not prove
    presence. Callers fall back to their own package query, so the component
    may still be installed.

    ``read_receipts`` is called only when it is needed, so a component that
    declares no prefixes costs no subprocess.

    Args:
        application_paths: A component's declared application paths.
        receipt_prefixes: A component's declared receipt prefixes.
        path_exists: Injected existence check, so this function stays pure.
        read_receipts: Injected ``pkgutil --pkgs`` reader, called at most once.

    Returns:
        Whether the declared artifacts prove the component is installed.
    """
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
