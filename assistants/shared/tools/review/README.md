# Ballen Review Tools

This locked Python project provides deterministic local review planning and
provider-specific publication commands. The canonical source is installed by
`ballen-config`; credentials and provider authentication remain owned by the
existing `gh`, `glab`, or connected provider environment.

The `review-plan digest`, `validate`, and `workspace-check` commands are
read-only. `review-plan compile-review` writes the requested local JSON plan
artifact after validating its repository-local workspace. Publication commands
are added by their respective provider capability slices and require a current
approved preview.

The same locked project validates normalized thread snapshots and compiles
provider-neutral response plans. These commands do not construct provider
mutation clients:

```text
review-plan validate-threads --threads PATH
review-plan compile-response --threads PATH --draft PATH --output PATH --repo-root PATH
```
