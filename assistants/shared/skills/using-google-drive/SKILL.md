---
name: using-google-drive
description: >-
  Use when searching, reading, or writing Google Drive files from an agent
  session — through a Drive MCP connector, a Drive for desktop mount under
  ~/Library/CloudStorage, or both — including multiple Google accounts,
  shared drives, "file not found" conclusions, and Permission denied errors
  on locally synced Drive paths.
---

# Using Google Drive

Pick the surface per operation, and never conclude "not found" from a single
surface.

## Surface selection

| Operation | Surface |
| --- | --- |
| Full-text or metadata search | Connector `search_files` (`fullText contains`, `title contains`, `mimeType =`) |
| List a folder | Connector `search_files` with `parentId = '<folder-id>'` |
| Read Google Docs/Sheets/Slides | Connector (the mount holds only `.gdoc`/`.gsheet` pointer stubs) |
| Read binaries (PDF, xlsx) | Mount `~/Library/CloudStorage/GoogleDrive-<email>/` (hydrates on first open; bulk reads are slow) |
| Write or upload binaries | Mount if the role allows (see below), else Drive web UI; connector `create_file` needs inline base64 and is impractical past ~100KB |

## Multiple accounts

- A connector authenticates to exactly one account at a time (switchable in
  the assistant's connector settings). Before concluding a file does not
  exist, confirm which account the connector is on.
- Mounts exist per signed-in account and are all usable simultaneously.
- A connected Notion workspace's AI search can span its own linked Drive
  account — a distinct search surface with different coverage.
- Shared-with-me items appear in neither mounts nor `parentId` listings
  unless the user added shortcuts.

## Shared-drive writes

`Permission denied` writing to `Shared drives/...` on the mount, while
My Drive writes and web-UI uploads both succeed, usually means the user's
shared-drive role is Contributor (API role `writer`) or lower. Drive for
desktop requires Content Manager (`fileOrganizer`) to write. Confirm the
actual role with `get_file_permissions` before diagnosing; remediate by
having a drive Manager (`organizer`) raise the role, or hand the upload to
the user to do in the Drive web UI.

## Verify writes

A successful copy onto the mount proves nothing until synced. Confirm the
file appears via connector `search_files` on the destination folder (allow
sync latency; re-check rather than fail immediately). Verification requires
the connector to be on the same account as the mount written to.
