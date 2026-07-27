# Promoting shared coding-agent skills

A shared skill is portable configuration, not a copy of local agent state.
Promotion requires an individually reviewed source whose name and behavior are
safe for every declared target.

`jujutsu-workflow` is the first reviewed shared skill. `ballen-config` stores
its desired bytes once, then independently copies them to each selected
agent's native skill root. This is desired-state configuration, not a Cursor
third-party auto-import workflow.

## Catalog entry

```yaml
skills:
  - name: example-generic-skill
    source: assistants/shared/skills/example-generic-skill
    targets: [cursor, claude-code, codex]
    profiles: [default]
    dependencies: []
    provenance: Promoted from a reviewed repository skill; change history records the origin.
    portability_status: reviewed-generic
```

1. Remove project names, absolute paths, project import statements, project
   tool prefixes, and repository-specific assumptions.
2. Give the skill a globally unique kebab-case name.
3. Run the portability scanner against the whole skill tree.
4. Add the source directory under `assistants/shared/skills/<name>/`.
5. Add targets and profiles to `catalog.yaml`.
6. Run collision, hash, policy, and integration tests.
7. Promote agent-specific variants only under distinct qualified names.

## Review boundaries

Review every file before promotion. The directory basename, catalog `name`, and
bounded initial YAML frontmatter `name` in `SKILL.md` must agree. Reject
symlinks, special files, generated output, and machine-specific assumptions.

Never promote credentials, API keys, OAuth material, login state, sessions,
transcripts, command history, caches, indexes, trust state, worktrees, or agent
memories. Sources must not contain absolute paths, repository imports,
repository-specific tool prefixes, or instructions to copy authentication
material from another machine.

After review, add the canonical directory and catalog declaration together.
Keep dependencies explicit and eligible for the same profiles, targets, and
skips. Run the focused shared-skill tests, the tracked-tree policy scanner, the
full integration suite, and pre-commit before checkpointing the promotion.
