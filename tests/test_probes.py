"""Tests for the shared uv tool list parsing predicate."""

import pytest

from ballen_config.probes import (
    application_paths_present,
    receipts_match,
    uv_tool_listed,
)


@pytest.mark.parametrize(
    ("stdout", "package", "expected"),
    [
        pytest.param(
            "pre-commit v4.6.0\n- pre-commit\n",
            "pre-commit",
            True,
            id="listed-package-matches",
        ),
        pytest.param(
            "ruff v0.6.0\n- ruff\n",
            "pre-commit",
            False,
            id="absent-package-does-not-match",
        ),
        pytest.param(
            "ruff v0.6.0\n- ruff\n- pre-commit\n",
            "pre-commit",
            False,
            id="entrypoint-line-does-not-match-package",
        ),
        pytest.param(
            "",
            "pre-commit",
            False,
            id="empty-stdout-does-not-match",
        ),
        pytest.param(
            "\n\npre-commit v4.6.0\n\n- pre-commit\n\n",
            "pre-commit",
            True,
            id="blank-lines-are-handled",
        ),
        pytest.param(
            "ruff-lsp v1.0.0\n- ruff-lsp\n",
            "ruff",
            False,
            id="strict-prefix-package-does-not-false-positive",
        ),
        pytest.param(
            " pre-commit v4.6.0\n",
            "pre-commit",
            False,
            id="leading-whitespace-does-not-match",
        ),
    ],
)
def test_uv_tool_listed(stdout: str, package: str, expected: bool) -> None:
    """The predicate matches only an exact leading-field tool name."""
    assert uv_tool_listed(stdout, package) is expected


@pytest.mark.parametrize(
    ("paths", "existing", "expected"),
    [
        pytest.param(
            ("/Applications/Brave Browser.app",),
            {"/Applications/Brave Browser.app"},
            True,
            id="single-declared-path-exists",
        ),
        pytest.param(
            ("/Applications/Brave Browser.app", "/usr/local/bin/brave"),
            {"/Applications/Brave Browser.app"},
            False,
            id="not-every-declared-path-exists",
        ),
        pytest.param(
            (),
            {"/Applications/Brave Browser.app"},
            False,
            id="no-declared-paths-is-never-present",
        ),
    ],
)
def test_application_paths_present(
    paths: tuple[str, ...], existing: set[str], expected: bool
) -> None:
    """Presence requires at least one declared path and all of them to exist."""
    assert application_paths_present(paths, lambda p: str(p) in existing) is expected


def test_application_paths_present_rejects_vacuous_truth_on_empty_paths() -> None:
    """An empty ``paths`` must not short-circuit to ``all([]) is True``.

    This is the specific trap the emptiness guard exists to catch: a
    ``path_exists`` that always returns ``True`` must still yield ``False``
    for a component that declares no application paths at all.
    """
    assert application_paths_present((), lambda _p: True) is False


@pytest.mark.parametrize(
    ("stdout", "prefixes", "expected"),
    [
        pytest.param(
            "org.tug.mactex.gui2025\norg.tug.texlive2025\n",
            ("org.tug.mactex.gui",),
            True,
            id="single-prefix-matches-installed-receipt",
        ),
        pytest.param(
            "org.tug.mactex.gui2025\norg.tug.texlive2025\n",
            ("org.tug.mactex.gui", "org.tug.texlive"),
            True,
            id="every-declared-prefix-has-a-match",
        ),
        pytest.param(
            "org.tug.mactex.gui2025\n",
            ("org.tug.mactex.gui", "org.tug.texlive"),
            False,
            id="one-unmatched-prefix-fails-the-whole-check",
        ),
        pytest.param(
            "",
            ("org.tug.mactex.gui",),
            False,
            id="empty-receipts-do-not-match",
        ),
    ],
)
def test_receipts_match(stdout: str, prefixes: tuple[str, ...], expected: bool) -> None:
    """Every declared prefix must be matched by some installed receipt."""
    assert receipts_match(stdout, prefixes) is expected


def test_receipts_match_is_vacuously_true_for_no_declared_prefixes() -> None:
    """No declared prefixes means nothing left to prove, so ``True``.

    This is deliberately the opposite of
    ``test_application_paths_present_rejects_vacuous_truth_on_empty_paths``.
    A declared application path is the evidence itself, so declaring none
    proves nothing; a declared receipt prefix is an extra condition on top
    of that evidence, so declaring none leaves the condition satisfied.
    Callers rely on this: they treat a component without
    ``receipt_prefixes`` as present. Inverting it here would report every
    receipt-less component missing.
    """
    assert receipts_match("", ()) is True
    assert receipts_match("org.tug.texlive2025\n", ()) is True


def test_receipts_match_nesting_direction_is_all_prefixes_any_receipts() -> None:
    """Catch the ``any(all(...))`` nesting-inversion trap directly.

    Two receipts, two prefixes, and each receipt matches a different
    prefix: no single receipt line starts with every prefix, and no single
    prefix is a prefix of every receipt. The correct nesting -- every
    declared prefix (``all``) matched by some installed receipt (``any``)
    -- is satisfied, so this must be ``True``. The inverted nesting
    (``any(all(...))``, "some prefix matches every receipt") would instead
    find no such prefix and return ``False``, so this case fails under the
    inverted nesting while every case above it passes coincidentally.
    """
    stdout = "org.tug.mactex.gui2025\norg.tug.texlive2025\n"
    prefixes = ("org.tug.mactex.gui", "org.tug.texlive")
    assert receipts_match(stdout, prefixes) is True
