---
name: writing-pr-descriptions
description: >-
  Use when drafting a pull request title or description, opening a PR, or
  refreshing an existing description after code, scope, or results change.
---

# Writing PR descriptions

A PR description gives a reviewer without the conversation context an entry point into the change. Explain the problem and resulting behavior before implementation details.

## Establish the facts

Read repository instructions, the PR template, applicable PR-workflow guidance, and the actual diff against the intended base. For an existing PR, distinguish its published head from local changes. Use the issue and supplied evidence to establish intent; use the code to establish delivered scope. Identify what remains pending before writing.

## Write the description

Follow the repository's required format. Otherwise, use a short opening and only the supporting sections the change needs; a small fix can be two paragraphs.

1. **Orient the reviewer.** Establish what the affected system or model does, the current problem, and the result of this PR. Introduce domain terms, acronyms, and symbols through their role in that explanation. A cold reader should understand why the change matters before encountering paths or flags.
2. **Explain the change.** Connect the important mechanism to its effect. State relevant defaults, opt-in behavior, affected outputs, and compatibility. For a stack, describe this PR's slice and what its neighbors supply, linking PR numbers. Include a usable configuration example or a short linked review path when it helps someone run or assess the change.
3. **Give meaningful evidence.** Say what ran and what it establishes. Separate current code checks, measured numerical results, and scientific or methodological acceptance. For numerical claims, name the quantity, units, comparison baseline, input/configuration basis, and relevant version. State material gaps beside the claims they limit.

For new, changed, or removed tests, describe the scenarios covered and explain why any removed coverage is safe to drop. For manual verification, state the setup, actions, and observed results.

Keep the main explanation and consequential caveats visible. Use tables for parallel comparisons. Put lengthy diagnostics, reproduction commands, or historical results in a labeled fold or durable linked artifact; explain their relevance in the body. Test-file inventories and pass counts do not explain behavior.

## Refresh without losing clarity

Rewrite around the final change, preserving useful explanations, configuration examples, review links, and evidence. Recheck them when paths, flags, stack boundaries, or methodology change. Adding results should improve the existing explanation rather than replace it with a results dump.

Older measurements belong with their original version/configuration and a clear historical label. When current comparisons have not run, say so; passing regression tests do not make old model results current. Describe the published implementation and remaining work, without recounting local edits or correction chronology.

Preserve repository automation metadata and issue relationships. Use closing keywords only when this PR resolves the issue. Writing a description does not itself authorize publishing it; follow the surrounding task's authorization.

## Final read

**REQUIRED COMPANION:** Use editing-technical-prose for the final wording pass after checking content and evidence.

Keep prose paragraphs on one physical line, with blank lines between them; retain structural breaks in lists, tables, and code. Read the opening without the chat: can the reviewer explain the problem, the result, and what still needs judgment?

For example, replace “Apply the wool parent override on both taxonomy routes” with:

> Sheep-wool production currently inherits purchased inputs from the beef-cattle sector. This change routes wool to the sheep-and-goat sector under either product classification when the correction flag is enabled. The flag remains off by default.
