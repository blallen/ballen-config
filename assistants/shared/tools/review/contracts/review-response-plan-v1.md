# Review Response Plan v1

`review-response-plan/v1` records a non-mutating evaluation of every
normalized thread, including resolved and informational evidence. It binds the
provider/change target and observed head to the normalized-thread digest and
records evaluation, evidence, proposed changes, proposed response,
verification, and selected or skipped action.

A `propose-response` item requires `proposed_response`, and a `propose-change`
item requires at least one entry in `proposed_changes`.

`source_threads_digest` is the canonical digest of the normalized-threads file
as written, the value `review-plan digest --artifact` prints for that file.

The plan does not authorize local edits, commits, pushes, replies, or thread
resolution.
