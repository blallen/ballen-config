---
provenance:
  source_repository: plato
  source_revision: 6bb59d00ac01fd3238c091d90f2aea43872934c9
  source_paths:
    - .cursor/rules/104_python_style_guide.mdc
    - .cursor/rules/104_pydantic_style_guide.mdc
    - .cursor/rules/lessons_learned.mdc
    - .cursor/rules/lessons_promoted.mdc
  source_roles:
    .cursor/rules/lessons_promoted.mdc: provenance-only
  approved_decision: docs/superpowers/specs/2026-07-27-plato-engineering-standards-migration-design.md
  disposition: corrected
  portability_result: portable-after-adaptation
  review_date: "2026-07-27"
  correction_note: >-
    Removed repository templates, corrected unsupported class-attribute
    documentation claims, and made public docstring coverage universal to
    match the starter lint policy.
---

# Documentation

## Code documentation

Use Google-style docstrings for every public module, class, function, and
method. Include a concise purpose even when the signature is obvious so missing
documentation remains mechanically detectable. Expand the docstring with
parameters, returns, raised exceptions, side effects, and important invariants
when those details add useful context. Spell out specialized terms and use
specific type or class names instead of vague references.

Name or document intentionally excluded cases, and explain non-obvious
performance choices where a future simplification could change behavior.

Document non-obvious class attributes in the class docstring, generated API
documentation configuration, or supported field metadata. Do not assume that a
string placed after an assignment is displayed by standard interactive help.
For validated fields, keep domain meaning and constraints close to the field
through field descriptions.

## Repository documentation

A README should explain purpose, intended users, supported setup, the shortest
useful example, and where deeper guidance lives. Keep operational details close
to the system that owns them. Do not maintain a duplicated API inventory in
prose when exports or generated reference documentation are authoritative.
Keep configuration discoverable and identify one executable source as the
single source for each setting.

Examples must be runnable or clearly marked as illustrative. Include expected
results and failure behavior when those details affect correct use.

## Visual and decision records

Use diagrams when relationships, sequence, state, or ownership are materially
clearer visually. Prefer Mermaid for maintainable text-native diagrams when it
can express the relationship without sacrificing clarity. Keep labels legible
and provide nearby prose for meaning that cannot be inferred from geometry
alone. Store editable sources when a diagram is expected to evolve.

Record consequential architectural decisions with context, decision, tradeoffs,
and status. Decision records explain why a choice was made; they do not replace
current user or API documentation.

## Quality

Run the repository's configured Markdown lint and link checks. Keep headings
hierarchical, links relative when content moves together, and terminology
consistent. Review documentation changes with the implementation they describe
so neither becomes a stale second source of truth.
