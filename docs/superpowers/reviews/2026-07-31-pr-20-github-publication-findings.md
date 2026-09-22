# PR #20 GitHub publication review handoff

## Status

- Branch: `forge-review-github-publish`
- Source artifact: `20260731T163443Z-a83752411b53.md`
- Result ID: `ecbcaf5bbf4716fd08139ed6dbfd20d749407b18726744faf16b121544e7ebfe`
- Scope identity: `a83752411b531ebc8cc1724ff95d12c3cb2f2241e35ea30023d1d6d05d9e275d`
- Original verdict: incomplete, with 4 actionable findings and no blockers

This handoff preserves findings from the original self-review. The stack has
since been rewritten, and this document changes the reviewed branch again.
Revalidate every item against the current diff before remediation; paths and
line numbers below describe the original review scope.

## Deferred findings

- [ ] Add direct CLI coverage for preview and execute success, blocking, and
  error paths in
  `assistants/shared/tools/review/src/ballen_review_tools/github_cli.py`
  (original lines 40-89). Assert output, receipt writes, and exit status without
  invoking a real provider.
- [ ] Replace the broad `dict[str, object]` publication payload in
  `assistants/shared/tools/review/src/ballen_review_tools/models.py` (original
  line 187) with typed mappings or a named union for the controlled request
  shapes.
- [ ] Annotate the set-once `API_VERSION`, `_ACCEPT`, and `_HUNK` bindings in
  `assistants/shared/tools/review/src/ballen_review_tools/providers/github.py`
  (original lines 12-14) with precise `Final` types.
- [ ] Add a multi-page GitHub response test for
  `assistants/shared/tools/review/src/ballen_review_tools/providers/github.py`
  (original lines 116-130) and validate the selected `gh --paginate` output
  shape before decoding it.

## Verification limitation

The root mypy configuration did not cover the changed `ballen_review_tools`
package, so the original type review was incomplete.
