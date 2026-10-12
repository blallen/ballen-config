# Publication Preview v1

`publication-preview/v1` binds a validated logical plan to the current
provider identity, observed head, normalized remote-state digest, itemized
deduplication decisions, and exact ephemeral request payloads.

The preview is evidence for one approval. It is not authorization by itself.
Execution must re-fetch state and receive the approved plan digest and expected
head explicitly.
