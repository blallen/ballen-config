# Repository instructions

Repository instructions and executable configuration take precedence.

Use staff-level judgment and choose the simplest sufficient solution. Optimize
for readability and maintainability. Avoid unrelated scope, and run fresh
verification before claiming completion.

For Python repositories unless their own configuration says otherwise:

- Use Python 3.12.
- Use type hints, `TypedDict` for controlled mapping shapes, and Pydantic v2 for
  validated models.
- Use Google-style docstrings and pytest fixtures.

Use Jujutsu when `.jj/` is present; otherwise use the repository's selected
source-control system.

Before relevant implementation or review work, read the
[engineering standards](assistants/shared/standards/README.md) index and
applicable topic documents.

## Bootstrap workflow

Read [README.md](README.md) before changing bootstrap behavior or managed
configuration. Its manifests and security/state boundary are authoritative.

- Run `./bootstrap plan` before any bootstrap mutation, preserving selected
  profile, include, and skip choices across every stage.
- Run `./bootstrap doctor` with the same selections after bootstrap or managed
  configuration changes.
- Never copy, migrate, or commit credentials, tokens, private keys,
  authentication or trust state, sessions, histories, local state,
  machine-specific project paths, or generated plugin state.
- Do not invent MCP configuration or commit machine-specific integrations.
