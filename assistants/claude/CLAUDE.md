# Claude Code additions

Do not copy credentials, sessions, project trust, or generated plugin state
between machines.

## Auto memory

Save `user`, `feedback`, and `reference` memories only. Do not save
`project` memories: plan status, milestones, open work, decisions under
discussion. That state changes in meetings and Notion between sessions,
and a stale memory reads as authoritative.

When something project-shaped is worth keeping, write it where a human
reviews it and Claude reads it deliberately: repository docs when it
describes the code, the relevant Notion page when it describes the plan.
Read it fresh from there each session instead of caching it in memory.
