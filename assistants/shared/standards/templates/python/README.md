# Python tooling starter

## Ownership

These files are copy-once seeds. After copying, each file is a
repository-owned snapshot governed by that repository's instructions and
configuration. In an established repository, inspect the existing file and
merge applicable settings instead of overwriting local decisions.

The files contain no generator tokens or parameter substitution. Copy the
applicable bundle for a new Python repository, or copy and adapt an individual
file by path. Copy `.pre-commit-config.yaml` with `ruff.toml` and
`.markdownlint.json`, because its hooks reference both companion files.

Pre-commit requires Git repository metadata. In a pure-Jujutsu repository
without a colocated `.git/`, omit `.pre-commit-config.yaml` and run Ruff, the selected type checker,
pytest, and Markdownlint through the repository's own task or CI entry. The
individual tool configurations do not depend on Git.

## Required tools

The guidance defaults to Python 3.15, Ruff, ty, pytest, pre-commit, and
Markdownlint for new repositories. The destination repository's configuration
selects the tools and how they are installed and invoked.

The bundled `mypy.ini` is an optional compatibility seed for repositories that
already select mypy. Do not copy it into a ty project; configure ty in that
project's `pyproject.toml` when its defaults need adjustment.

## Adaptation points

Review the supported Python version, source and test paths, pytest markers,
Ruff rule selection, type-checker policy, and repository-specific exclusions.
Retain a setting only when it matches the destination's dependencies and
delivery policy.

The Ruff template applies the same test-specific exceptions to root `tests/`
and colocated `__tests__/` directories. The destination repository selects its
test layout and configures pytest discovery accordingly.

## Optional configuration

ty has built-in Pydantic v2 support. For repositories that retain mypy, enable
its Pydantic plugin only when Pydantic is a declared dependency.
Add a uv-lock hook only when the repository selects uv and tracks its lockfile.
Add conventional commits enforcement only when that repository has adopted
the policy.

## Pin maintenance

Hook revisions are reviewed starting points, not evergreen claims. Check
primary upstream release sources periodically and validate every updated hook
before adopting a new pin.
