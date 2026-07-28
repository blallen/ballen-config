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
without a colocated `.git/`, omit `.pre-commit-config.yaml` and run Ruff, mypy,
pytest, and Markdownlint through the repository's own task or CI entry. The
individual tool configurations do not depend on Git.

## Required tools

The baseline assumes Python 3.12, Ruff, mypy, pytest, pre-commit, and
Markdownlint. The destination repository chooses how those tools are installed
and invoked.

## Adaptation points

Review the supported Python version, source and test paths, pytest markers,
Ruff rule selection, mypy strictness, and repository-specific exclusions.
Retain a setting only when it matches the destination's dependencies and
delivery policy.

## Optional configuration

Enable the Pydantic mypy plugin only when Pydantic is a declared dependency.
Add a uv-lock hook only when the repository selects uv and tracks its lockfile.
Add conventional commits enforcement only when that repository has adopted
the policy.

## Pin maintenance

Hook revisions are reviewed starting points, not evergreen claims. Check
primary upstream release sources periodically and validate every updated hook
before adopting a new pin.
