# Review Response Plan v1

`review-response-plan/v1` records a non-mutating evaluation of every
normalized thread, including resolved and informational evidence. It binds the
provider/change target and observed head to the normalized-thread digest and
records evaluation, evidence, proposed changes, proposed response,
verification, and selected or skipped action.

A `propose-response` item requires `proposed_response`, and a `propose-change`
item requires at least one entry in `proposed_changes`.

The plan does not authorize local edits, commits, pushes, replies, or thread
resolution.
