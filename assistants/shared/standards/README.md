# Engineering standards

## Authority

An always-on shared core supplies concise defaults to each agent's native
configuration. The detailed topic files are normative when their subject
applies; they refine the core without duplicating it. This index is not a second
authority and does not restate their detailed rules. Repository instructions
and executable configuration take precedence when they make a more specific
choice.

## Canonical topics

- [Python](python.md)
- [Pydantic](pydantic.md)
- [Validation](validation.md)
- [API design](api-design.md)
- [Testing](testing.md)
- [Documentation](documentation.md)
- [Source control](source-control.md)
- [Dependency management](dependency-management.md)

## Repository snapshots

The repository-rule starter supports two passive copy modes. Default copies
one concise `AGENTS.md` baseline for Codex, Cursor, and current Claude Code.
An optional `CLAUDE.md` entry supports compatibility cases or Claude-specific
instructions. All adds this index and every canonical topic; tooling remains
a separate opt-in bundle.

ballen-config is the canonical source for reusable guidance. Downstream copies
are vendored snapshots: copy the declared files unchanged and record the source
revision in the downstream guidance commit message. Make generic corrections upstream first;
keep repository-specific instructions and explicit exceptions outside the
vendored topic files. Inspect local changes before refreshing a bundle so
intentional overrides are preserved. Refreshes are deliberate, not automatic.

These files are plain Markdown. Their presence implies no installer, selector,
or runtime loading mechanism.
