---
name: writing-pr-descriptions
description: >-
  Use when drafting a pull request title or description, opening a PR, or
  refreshing an existing description after code, scope, or results change.
---

# Writing PR descriptions

A PR description introduces the change to a reviewer without the conversation context. Explain the problem and resulting behavior first. When the title and body become the squash commit message, write them for permanent history too.

## Establish the facts

Read repository instructions, the PR template, PR-workflow guidance, and the diff against the intended base. Check commit conventions and how squash merges use the title and body. Distinguish the published head from local changes. Establish intent from the issue and supplied evidence, delivered scope from the code, and what remains pending.

## Write the title for the commit

Follow the repository's commit convention. Otherwise, use [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/): `<type>[optional scope][!]: <description>`.

Use `feat` for a new feature, `fix` for a bug fix, and repository-supported types such as `docs`, `refactor`, or `test` for other changes. Put an optional subsystem scope in parentheses, as in `fix(parser): handle empty input`. Summarize the final change with a concise verb phrase.

Mark breaking changes with `!` immediately before the colon or an uppercase `BREAKING CHANGE: <description>` footer. Explain incompatibility and migration visibly. Separate title, body, and footers with blank lines.

## Write the description

Follow the repository's required format. Otherwise, lead with a short, carefully selected explanation of what deserves the reviewer's attention. Add only the supporting sections the change needs; a small fix can be two paragraphs.

1. **Orient the reviewer.** Establish what the affected system or model does, the current problem, and the result of this PR. Introduce domain terms, acronyms, and symbols through their role in that explanation. A cold reader should understand why the change matters before encountering paths or flags.
2. **Explain the change.** Connect the important mechanism to its effect. State relevant defaults, opt-in behavior, affected outputs, and compatibility. For a stack, describe this PR's slice and what its neighbors supply, linking PR numbers. Include a usable configuration example or a short linked review path when it helps someone run or assess the change.
3. **Give meaningful evidence.** Say what ran and what it establishes. Separate current code checks, measured numerical results, and scientific or methodological acceptance. For numerical claims, name the quantity, units, comparison baseline, input/configuration basis, and relevant version. State material gaps beside the claims they limit.

Arrange that content in this order:

1. **Visible overview.** Open with one or two short paragraphs explaining the problem and resulting behavior. Follow with a brief validation outcome, evidence link, and any defaults, compatibility or migration requirements, consequential caveats, and pending decisions the reviewer needs before expanding anything.
2. **Collapsed supporting detail.** When retaining case-by-case lists, module or function inventories, detailed flag/configuration tables, reproduction commands, or expanded test-coverage explanations, put them inside one or more `<details>` blocks. Use a descriptive `<summary>`, blank lines around Markdown content, a closing `</details>`, and no `open` attribute. Retaining this detail requires a fold; choosing to omit the detail can remove the need for one. A small PR containing only the visible overview needs no fold.
3. **Visible metadata and footers.** Keep issue relationships, automation metadata, and breaking-change footers outside the folds.

Describe test scenarios and why removed coverage is safe in the supporting detail; manual verification includes setup, actions, and observations. The visible overview states what verification establishes and its material gaps. Test-file inventories and pass counts do not explain behavior. Folded text still enters a squash commit when the body is copied verbatim, so keep it concise and useful in permanent history.

## Give results a maintained home

Always give substantive results and analysis a maintained home outside the PR description: repository Markdown, a Google Doc, a GitHub issue discussion, Notion, or another durable location accessible to reviewers. Keep benchmark measurements, model comparisons, experiment results, tables, run histories, diagnostics, and interpretation there.

Reuse the existing record. If none exists, choose a destination and create it within the task's authorization. If blocked, identify the missing record instead of storing results in the PR. Preserve version, configuration, provenance, and reproduction instructions in that record.

For results, include only a link, the takeaway needed to assess the change, and consequential caveats. Result dumps stay out of the description, including folds, so they do not flood the squash commit. Routine code-check summaries need no separate report.

## Refresh without losing clarity

Rewrite the title and body around the final change. Preserve useful explanations, configuration examples, review links, and evidence links; recheck them when paths, flags, stack boundaries, or methodology change. Update the maintained record and linked takeaway as evidence changes.

Older measurements belong with their original version/configuration and a clear historical label. When current comparisons have not run, say so; passing regression tests do not make old model results current. Describe the published implementation and remaining work, without recounting local edits or correction chronology.

Preserve repository automation metadata and issue relationships. Use closing keywords only when this PR resolves the issue. Writing a description does not itself authorize publishing it; follow the surrounding task's authorization.

## Final read

**REQUIRED COMPANION:** Use editing-technical-prose for the final wording pass after checking content and evidence.

Keep prose paragraphs on one physical line, with blank lines between them; retain structural breaks in lists, tables, and code. Read only the visible overview: can a reviewer explain the problem, result, and pending judgment? If supporting detail is retained, verify that a collapsed `<details>` block exists and contains it; balanced tags alone do not establish this. Check that consequential caveats, migration requirements, and footers remain visible and results remain linked elsewhere. Read the whole body, including folds, as the eventual squash commit.

For example, replace “Apply the wool parent override on both taxonomy routes” with:

> Sheep-wool production currently inherits purchased inputs from the beef-cattle sector. This change routes wool to the sheep-and-goat sector under either product classification when the correction flag is enabled. The flag remains off by default.
