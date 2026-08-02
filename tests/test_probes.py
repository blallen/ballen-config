"""Tests for the shared uv tool list parsing predicate."""

import pytest

from ballen_config.probes import uv_tool_listed


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
