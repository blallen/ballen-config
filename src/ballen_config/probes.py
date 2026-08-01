"""Pure, side-effect-free predicates over native command output.

These helpers isolate assumptions about the output format of external tools
so that a format change only needs updating in one place, and so that the
match rule cannot silently drift between the install, doctor, and CLI
dispatch sites that all need it.
"""


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
