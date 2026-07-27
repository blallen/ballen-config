# CLAUDE.md

[README.md](README.md) and `./bootstrap` are the portable operating guides for
this repository.

- Run `./bootstrap plan` before any mutation.
- Honor the selected profiles and skips across every stage.
- Follow the reviewed manifests; do not add undeclared machine setup.
- never copy credentials, tokens, private keys, sessions, or local state.
- never invent MCP configuration or commit machine-specific integrations.
- Run `./bootstrap doctor` with the appropriate profile after changes.
