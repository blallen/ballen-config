# Cursor additions

Use Cursor's first-party browser capability rather than a global Playwright
MCP server. Prefer `gh` for GitHub operations; when the remote is GitLab, use
`glab` and the `using-gitlab` skill. Use the official Notion integration; keep
a single Notion connector (prefer a team install when it opens the right
workspace). Never copy authentication, history, worktrees, indexes, caches, or
generated plugin state between machines.
