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

The repository-rule template supports two passive copy modes. Default copies
only the concise native entries. All adds this index and every canonical topic;
tooling remains a separate opt-in bundle. Copied files become repository-owned
snapshots. Maintainers inspect and merge future upstream changes rather than
assuming automatic synchronization.

## Future progressive loading

Future skills may load the canonical topics progressively for the work at hand.
No resolver exists in this migration, and the presence of these files does not
imply an installer, selector, or runtime loading mechanism.
