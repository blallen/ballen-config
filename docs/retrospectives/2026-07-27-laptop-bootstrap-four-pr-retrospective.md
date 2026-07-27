# `ballen-config` Four-PR Retrospective

Date: 2026-07-27

Scope: [`ballen-config`](https://github.com/blallen/ballen-config) PRs
[#1](https://github.com/blallen/ballen-config/pull/1),
[#2](https://github.com/blallen/ballen-config/pull/2),
[#3](https://github.com/blallen/ballen-config/pull/3), and
[#4](https://github.com/blallen/ballen-config/pull/4)

## Executive conclusion

The stacked-PR mechanism was not the source of the delay. Creating the first
three PRs took about 2.4 minutes, and merging PRs #2, #3, and #4 in order took
2 minutes 29 seconds. The PRs were useful: the review surface caught the SSH
template regression, experimental Piste declarations, and the missing shared
desired-state architecture.

The primary avoidable technical cause was committing to plan and execute the
core bootstrap and coding-agent portability together before the agent half of
the design had converged. The core boundary was comparatively clear, but the
agent work still had unresolved ownership questions: what should be shared,
what each agent should manage natively, how plugins and skills interact, and
which declaration wins when capabilities overlap. The detailed implementation
plan converted those open architectural questions into apparently executable
tasks instead of forcing a second design checkpoint.

The largest engineering delay was the first implementation phase. It occupied
20.31 hours of wall time, with at least one subagent turn open for 19.10 hours.
It was effectively serial despite using many agents. One reused worker,
`core_task6`, accumulated 17 active segments and 788.9 minutes of open-agent
time. Its largest segment was the 435.6-minute implementation of portable
shared-skill infrastructure.

That 7-hour-16-minute `nrx` to `mzw` interval was mostly real productive
complexity, not a silent hang. The resulting `mzw` commit changed six files
with 1,547 insertions, including 380 lines of implementation and 1,039 lines
of tests. It finished with 79 focused tests, the 287-test full suite, static
checks, policy checks, and all pre-commit hooks passing. It was nevertheless
too large for one uncheckpointed agent turn and sat directly on the critical
path.

The second major avoidable cost was planning scale. The two initial
implementation plans contain 10,698 lines, and the elapsed interval from “write
the implementation plan” to the final blocker-fix commit was about 5 hours
3 minutes. Across the six design and plan documents created for this work,
there are 14,659 lines. That level of detail increased authoring time, review
time, context load, and the cost of every agent handoff.

The user’s intuition about targeted implementers was directionally correct.
Across the task, initial `gpt-5.6-sol`/ultra agent turns had a 4.4-minute median
and 13.9-minute mean, while Terra/low turns had a 1.1-minute median and
1.9-minute mean, and Terra/medium turns had a 2.1-minute median and 3.5-minute
mean. The task mix was not controlled, so this is correlation rather than a
model benchmark. The largest outlier was still Terra/medium because the work
itself was large.

## Method and confidence

The audit used three independent sources:

- GitHub PR metadata, review comments, changed-file statistics, and merge
  timestamps.
- Local Jujutsu commit history, commit descriptions, and diff statistics.
- The source Codex task JSONL, including root-turn durations,
  `sub_agent_activity`, agent final messages, interrupts, follow-ups, and
  coordination calls.

Timing definitions:

- **Wall time** is elapsed clock time between phase boundaries.
- **Agent-open time** is spawn or follow-up to final answer or interrupt. It
  includes model reasoning, commands, tests, and any internal waiting; it is
  not CPU time.
- **Agent sum** adds overlapping agent segments.
- **Any-agent time** is the union of those segments and approximates the
  subagent critical path.

Confidence:

- **High:** PR timestamps, commit statistics, task durations, agent segment
  boundaries, coordination-call counts, and user-response gaps.
- **Medium:** whether a long agent segment was dominated by reasoning, editing,
  or tests. The parent log records the final evidence but not every internal
  subagent action.
- **Medium:** the performance effect of model and reasoning changes, because
  task difficulty differed across groups.
- **Low:** attributing stale UI state to one particular compaction or app bug.
  The evidence proves the agents had ended, but not the exact UI failure mode.

## Overall timeline

The full interval from the first audit turn to the PR #4 merge was about
49 hours 27 minutes. From explicit authorization to execute the plans to the
PR #4 merge was about 41 hours 18 minutes.

| Phase | Wall time | Agent sum | Any-agent time | Max concurrency | Interpretation |
|---|---:|---:|---:|---:|---|
| Initial PR #1/#2 implementation | 20.31 h | 19.83 h | 19.10 h | 3 | Almost continuously active, but effectively serial |
| PR #3 review and local validation | 3.39 h | 1.31 h | 0.65 h | 3 | Review work used parallelism effectively |
| PR #4 implementation | 7.33 h | 5.95 h | 5.60 h | 3 | Again effectively serial |
| PR #4 self-review and cleanup | 2.67 h | 2.04 h | 1.84 h | 3 | Mostly serial remediation |

The effective overlap ratio was only 1.04 for the initial implementation and
1.06 for PR #4 implementation. A maximum concurrency of three therefore
overstates the practical parallelism. PR #3’s review phase reached an effective
overlap ratio of about 2.0 and is the strongest example of useful parallel
delegation in the stack.

## PR-level evidence

| PR | Purpose | Commits | Files | Diff | Authored span | Open on GitHub |
|---|---|---:|---:|---:|---:|---:|
| #1 | Portable laptop bootstrap | 20 | 60 | +18,770 / -442 | 30.33 h | 0.39 h |
| #2 | Coding-agent portability | 30 | 57 | +10,235 / -95 | 20.73 h | 16.89 h |
| #3 | Hardening and validation | 20 | 50 | +1,958 / -840 | 3.25 h | 16.91 h |
| #4 | Shared desired-state consolidation | 14 | 38 | +7,289 / -1,035 | 15.61 h | 8.42 h |

The authored spans are not additive. They include rebases, deliberate waiting,
and work performed on later stacked branches.

PRs #2 and #3 were open for about 17 hours because they were stack-gated and
held for the follow-on architecture and next-day review. That is not 17 hours
of implementation. After merge approval, PRs #2, #3, and #4 merged at
15:22:05Z, 15:23:15Z, and 15:24:34Z.

## Ranked delay intervals

### 1. Initial implementation: 20.31 hours

**Cause:** productive implementation plus an almost completely serial agent
pipeline.

**Confidence:** high.

At least one agent turn was open for 19.10 of the 20.31 hours, so this was not
mostly an unattended user gap. However, 19.83 summed agent-hours compressed to
19.10 any-agent hours: only 0.73 hours of work overlapped.

The phase used:

- 38 spawned agents
- 97 follow-up triggers
- 112 inter-agent messages
- 580 waits
- 24 status listings
- 7 interrupts
- 858 total coordination calls

The high agent count created the appearance of parallelism without shortening
the critical path. Most work advanced as implement → spec review → quality
review → remediation → verification, one slice at a time in a shared working
copy.

### 2. Portable shared-skill infrastructure: 7 hours 16 minutes

**Cause:** a genuinely large feature placed in one agent turn, with extensive
test generation and final verification.

**Confidence:** high for size and timing; medium for the internal time split.

This is the `nrx` → `mzw` gap visible in the Jujutsu graph.

| Change | Agent-open time | Diff |
|---|---:|---:|
| Define coding-agent inventory | 81.9 m | 11 files, +1,361 / -0 |
| Reject ambiguous inventory state | 123.6 m | 3 files, +363 / -10 |
| Add portable shared-skill infrastructure | 435.6 m | 6 files, +1,547 / -12 |

The shared-skill commit alone added:

- 380 lines in `assistants/skills.py`
- 873 lines in `test_skills.py`
- 166 lines in `test_configure.py`
- 44 lines of promotion documentation

The parent spent long intervals waiting for this one worker, including a
250.6-minute interval between visible coordination events. The final result
was substantial and verified, so the evidence does not support calling it a
dead hang. It does support calling the task oversized and insufficiently
checkpointed.

### 3. PR #4 implementation: 7 hours 20 minutes

**Cause:** late architectural consolidation prompted by valid PR #2 review
feedback.

**Confidence:** high.

PR #2 received ten inline comments:

- Six requested removal of abandoned Piste/Fieldkit declarations.
- One questioned duplicated per-agent desired state.
- One clarified the role of the shared-skill catalog.
- Two documented the follow-up implementation.

The shared desired-state comment was not a small fix. PR #4 introduced a
target-aware shared plugin catalog, shared preflight orchestration, native
Cursor plugin planning, updated docs, and later cleanup. Representative
changes were:

- Target-aware catalog: 10 files, +861 / -23
- Native Cursor plugin planning: 12 files, +1,297 / -7
- Shared preflight: a cross-cutting refactor across adapters, models,
  orchestration, CLI behavior, and tests

This was useful scope, not ordinary review rework. It could have been avoided
as a late change only by deciding the ownership model before PR #2
implementation.

PR #4 used 42 spawned agents and 427 coordination calls but achieved only
5.95 summed agent-hours versus 5.60 any-agent hours. Again, orchestration was
mostly serial.

### 4. User review interval after PR #4 was green: 5 hours 27 minutes

**Cause:** human review availability.

**Confidence:** high.

The implementation turn reported the complete, green PR #4 stack at
07:02:00Z. The next user turn began at 12:28:44Z. This is the largest
non-engineering interval and should not be attributed to the agents or PR
mechanics.

There was another 32-minute interval between the PR #4 self-review report and
authorization to apply every cleanup suggestion. That is a normal approval
boundary.

### 5. Initial implementation planning: about 5 hours

**Cause:** over-detailed planning artifacts and repeated plan audits.

**Confidence:** high.

From “write the implementation plan” to the final blocker-fix commit was about
5 hours 3 minutes. The two initial plans contain:

- `2026-07-25-laptop-bootstrap-core.md`: 4,973 lines
- `2026-07-25-coding-agent-portability.md`: 5,725 lines

The associated plan agents each took about 46 minutes for their initial turns,
and the final plan auditor took 47 minutes. Those agents then received more
follow-ups and interruptions.

The plan detail reduced ambiguity, but 10,698 lines exceeded what a bootstrap
project needed. It also made every implementer and reviewer pay a large context
loading cost.

### 6. PR #3 review and live validation: 3 hours 23 minutes

**Cause:** intentional quality work that caught substantive issues.

**Confidence:** high.

PR #3 added 20 commits in a 3.25-hour authored span. It consolidated tests and
runtime boundaries, pinned external installers and repositories, corrected
native Cursor/Claude behavior, and performed local bootstrap validation.

This was mostly high-value review rather than delay. Its agent work also had
the best parallelism of the four phases. The lesson is to move selected live
validation earlier, not to remove the review.

### 7. PR #4 self-review and cleanup: 2 hours 40 minutes

**Cause:** explicitly requested polish using Plato standards and Ponytail
review.

**Confidence:** high.

The review reported no blockers or correctness failures. It produced four
cleanup commits covering desired-state types, plugin fixtures, explicit
parameter IDs, and remediation documentation. This was discretionary quality
work and should be budgeted as such.

## The long-lived `core_task6` worker

`core_task6` was the single largest operational smell:

- 17 active segments
- 788.9 minutes of total open-agent time
- 13.78 hours from first spawn to last final answer
- No segment remained open after 2026-07-26T15:33:57Z

After its original task it was reused for configuration, diagnostics,
documentation, CI, agent inventory, shared skills, hooks, Cursor support, and
multiple fixes. The name stopped describing its responsibility, its context
grew continuously, and it became a serial bottleneck.

The 435.6-minute shared-skill segment was the largest individual segment,
followed by 123.6 minutes for ambiguous inventory-state handling and
81.9 minutes for the inventory feature.

Future workers should be retired after one logical feature or PR checkpoint.
The shared-skill work should have been a new `shared_skill_infrastructure`
worker with explicit intermediate checkpoints.

## Model and reasoning choice

Before the user requested more targeted implementers, ten implementation
agents inherited the root’s Sol/ultra configuration. After the request, 28 new
implementation/review agents were explicitly dispatched as:

- 15 Terra/low
- 11 Terra/medium
- 2 Sol/medium

Across the whole task:

| Configuration | Initial turns | Median | Mean | Largest |
|---|---:|---:|---:|---:|
| Terra/low | 20 | 1.1 m | 1.9 m | 5.2 m |
| Terra/medium | 46 | 2.1 m | 3.5 m | 47.7 m |
| Sol/ultra | 26 | 4.4 m | 13.9 m | 82.4 m |
| Terra/high | 25 | 3.5 m | 9.7 m | 82.1 m |
| Sol/high | 14 | 4.6 m | 7.5 m | 37.4 m |

These samples are not task-matched. The safe conclusion is:

- Terra/low was effective for bounded implementation, fixtures, and focused
  test changes.
- Terra/medium was effective for normal implementation.
- High/ultra reasoning belonged on architecture and defect review, not every
  implementer.
- A genuinely oversized task remains slow regardless of model.

## Verification and review churn

Testing was thorough, but verification was repeatedly performed at
micro-commit granularity:

- 55.7% of PR #2’s added lines were test lines.
- 52.2% of PR #3’s added lines were test lines.
- The reused `core_task6` worker reported a focused suite, full suite, type
  checks, formatting, policy checks, and pre-commit checks after most of its
  follow-up commits.
- PR #3 then consolidated and parameterized tests, and PR #4 performed another
  self-review and cleanup pass.

The quality outcome was strong. The avoidable part was applying every expensive
gate after small two- to ten-minute fixes and then repeating full-stack review.
Focused tests should run per commit; the full suite and all hooks should run at
phase or PR boundaries.

The layered review pattern also created redundancy:

1. Per-task spec reviewer
2. Per-task quality reviewer
3. PR #3 full-stack review
4. PR #4 self-review and Ponytail review
5. Final cleanup review

A stronger design/invariant review before implementation plus one full PR
review would likely have found the same issues with fewer agent turns.

## Small but avoidable rework

### SSH template regression

The implementation correctly excluded SSH keys and machine-specific key paths
but over-applied that policy by deleting stable GitHub/GitLab host defaults.
The chat review found it, and the fix took 7.2 minutes.

Future portability reviews should distinguish:

- secrets and local identity material: exclude
- stable public service host configuration: retain
- machine-specific overrides: route through an ignored local include

### Remote checkpoint delay

The user requested branch labels and a remote push at 03:07Z. The final
two-branch checkpoint was not reported until 18:26Z, after implementation
continued for more than 15 hours.

This did not slow the code, but it increased recovery risk and made progress
harder to inspect. Bookmarks and remote branches should be created before
implementation and pushed after every meaningful checkpoint.

### Late shared ownership decision

The desired-state ownership model was not settled early enough. PR #2 encoded
more per-agent state than the user ultimately wanted, and PR #4 consolidated
it.

A one-page ownership matrix before coding should have answered:

| Concern | Shared declaration? | Native adapter? |
|---|---|---|
| Generic skills | Yes, with explicit targets | Yes |
| Plugins | Shared intent when IDs align | Yes |
| Native settings | No | Yes |
| Authentication/session state | Never | Never migrate |
| Cursor marketplace/local plugins | Cursor-specific capability | Yes |

## Primary causal lesson: execution began before agent design converged

The decision to “plan core + agents” bundled two areas with different levels
of design readiness. The core bootstrap was ready to become an implementation
plan. The coding-agent layer still needed another design pass. Combining them
made implementation feel authorized for both and allowed the more uncertain
agent work to become the critical path.

This matters especially for unattended execution. The user intentionally left
the work running for hours at a time and overnight. That was a reasonable use
of autonomous implementation once the contracts were stable, but it amplified
the cost of a premature stage transition: there was no natural human pause at
which to notice that “shared skills” had expanded into a cross-agent ownership
system. The absence of the user was not itself a delay; the workflow should
have made the agent design safe to leave unattended before execution began.

A better sequence would have been:

1. Finish the core design, plan, and implementation independently.
2. Keep the agent work in design mode.
3. Inventory Codex, Claude, and Cursor native capabilities and configuration
   boundaries.
4. Approve a one-page ownership and precedence matrix.
5. Prototype one generic skill end to end across all intended targets.
6. Only then write the agent implementation plan and authorize unattended
   execution.

The agent design gate should answer all of these before planning:

- What is the source of truth for each capability?
- Which state is shared intent, and which is agent-native configuration?
- How do native plugins, imported skills, and local adapters coexist?
- What are the precedence and conflict rules?
- Which secrets, sessions, trust, generated state, and project paths are
  excluded?
- Is configuration idempotent and reversible enough for repeated bootstrap
  runs?
- Has one representative vertical path been proven against every target?

If any answer is still architectural rather than mechanical, stop after the
design artifact. Do not produce the full implementation plan or dispatch an
unattended worker yet.

## Superpowers fit and wrapper opportunities

The Superpowers workflow does not fundamentally require parallel execution.
Its subagent-driven development gate says tasks must be mostly independent and
routes tightly coupled work back to manual execution or brainstorming. Its
parallel-agent guidance similarly requires no shared state. The shared
agent-capability foundation therefore should not have been treated as a set of
independent subagent tasks until its contracts were stable.

Several audit recommendations already align with Superpowers:

- critically review the plan before execution
- use the most capable model for architecture and cheaper models for mechanical
  implementation
- isolate genuinely parallel writers in separate workspaces
- use focused agents with explicit context

Two Superpowers defaults create tension for work of this shape:

1. Comprehensive plans made of 2–5-minute actions can create false precision
   and very large documents when architecture is unsettled.
2. A fresh implementer plus task review, fix review, and final review for every
   task can generate more coordination and verification than a tightly coupled
   feature benefits from.

A local wrapper or companion skill could preserve the useful discipline while
adding the missing control points:

| Control point | Wrapper behavior |
|---|---|
| Readiness classifier | Choose `design`, `inline`, `serial-subagent`, or `parallel-workspace` before planning. |
| Architecture gate | Require the ownership matrix, precedence rules, exclusions, and one vertical prototype for cross-agent work. |
| Mixed-readiness split | Refuse a combined plan when one subsystem is implementation-ready and another still has architectural questions. |
| Plan budget | Warn at 800 lines and require explicit justification above 1,200 lines. |
| Task sizing | Give one worker a meaningful 30–60-minute feature slice, not a microscopic plan action. |
| Runtime checkpoint | Require a report at 30–45 minutes; split or escalate at 60 minutes. |
| Review policy | Use focused review at feature boundaries and one full review per PR instead of a reviewer for every mechanical step. |
| Fix-loop breaker | After two unsuccessful follow-ups, rescope, replace the worker, or return to design. |
| Durability | Create and push bookmarks before long execution and after each meaningful checkpoint. |
| Lifecycle | Retire workers at task and PR boundaries; do not reuse generic names such as `core_task6`. |

For unattended or overnight work, the wrapper should expose an explicit
`unattended-ready` result. It should be false whenever ownership, precedence,
scope, or target behavior remains open. “Wait and design again tomorrow” is a
successful workflow outcome when the alternative is several hours of
autonomous implementation against unstable assumptions.

## What was not a real delay

### Stale “Working” subagent cards

The later UI showed six agents as active for roughly two days. The event log
proves all six had ended:

| UI label | Actual active time | Last end |
|---|---:|---|
| Agent plan outline | 73.7 m across 3 segments | Jul 25 20:15Z |
| Core plan outline | 73.8 m across 3 segments | Jul 25 20:15Z |
| Final plan audit | 64.0 m across 5 segments | Jul 25 22:28Z |
| Core task2 quality | 6.2 m | Jul 25 23:47Z |
| Core task3 quality | 4.5 m | Jul 25 23:59Z |
| Core task6 | 788.9 m across 17 segments | Jul 26 15:33Z |

No selected segment was open when the UI was audited. Those cards were
orphaned UI/thread state, not ongoing model work. Their histories were later
archived without deletion.

### PR creation and merge mechanics

- Three PRs created: 2.4 minutes
- PR #1 review/fix/merge window: about 23 minutes
- PRs #2 → #4 sequential merges: 2 minutes 29 seconds
- Root merge-and-cleanup turn: 9.6 minutes

The stacked PRs added little operational delay and produced useful review
boundaries.

## Recommended operating model

### Priority 1: Bound tasks and retire workers

1. One worker owns one logical feature or review.
2. Require a checkpoint after 30–45 minutes.
3. At 60 minutes without a checkpoint, split the task or request an explicit
   blocker/progress report.
4. Do not reuse a worker across unrelated features.
5. Interrupt and archive all workers at each PR boundary.

Expected effect: eliminates `core_task6`-style context growth, misleading
labels, and multi-hour unobservable turns.

### Priority 2: Reduce plan size

1. Cap a design at roughly 500–800 lines.
2. Cap an implementation plan at roughly 800–1,200 lines per PR.
3. Use acceptance tables, invariants, and file-level tasks instead of embedding
   large code/test bodies.
4. Put shared-vs-native ownership in the design before implementation.
5. Let implementation details live in typed interfaces and tests.

Expected effect: saves hours of plan authoring and reduces every agent’s
context-loading cost.

### Priority 3: Use real parallelism or intentionally stay serial

For a shared working copy, designate one writer and parallelize read-only
review. For genuinely independent implementation, use separate Jujutsu
workspaces or separate clones and integrate at explicit checkpoints.

Track effective concurrency as `agent sum / any-agent time`. If it remains near
1.0, stop paying multi-agent coordination overhead and run a simpler serial
pipeline.

### Priority 4: Match model to role

- Terra/low: bounded mechanical implementation, fixtures, catalog edits,
  focused tests.
- Terra/medium: normal feature implementation and integration fixes.
- Sol/high: architecture, security, ambiguous failures, and final review.
- Root/highest setting: coordination and decisions, not routine code.

Use a higher setting only when the task’s uncertainty justifies it.

### Priority 5: Stage verification

Per commit:

- focused tests
- focused lint/type checks

Per PR checkpoint:

- full suite
- full mypy/Ruff
- policy tests
- pre-commit

Before merge:

- clean checkout/bootstrap smoke
- one final full suite
- stack/base verification

This retains the quality bar while avoiding full-suite repetition after every
microfix.

### Priority 6: Shift live validation left

- After core PR: run stage-zero and a dry-run profile.
- After agent PR: run agent doctor and inspect native schemas.
- After review PR: run the full work profile on the local machine.
- After stack merge: perform only a short smoke, not the first full live test.

This would catch SSH/Cursor/native-state issues before the late hardening pass.

### Priority 7: Make progress durable and observable

1. Create and push stack bookmarks before implementation begins.
2. Push every meaningful checkpoint, especially before a long agent run.
3. Maintain a compact status table:
   `worker | task | started | last checkpoint | next expected output`.
4. Use longer event-driven waits instead of frequent polling.
5. Record agent thread IDs and close them before compaction or phase
   completion.

## Suggested future stacked-PR playbook

1. **Design gate:** one concise architecture/ownership matrix.
2. **Stack setup:** create and push all intended bookmarks immediately.
3. **PR 1 implementation:** one Terra/medium writer; focused tests per commit;
   one Sol/high review; full gate once.
4. **PR 2 implementation:** new writer with fresh context; independent read-only
   review in parallel.
5. **Integration PR:** live bootstrap/doctor validation and only the fixes it
   reveals.
6. **Optional architecture follow-up:** create only for genuinely new scope,
   as PR #4 was.
7. **Final review:** one full-stack standards/test/security pass.
8. **Merge:** verify bases, merge in order, fetch, and confirm local/remote
   bookmarks.
9. **Cleanup:** close every worker and remove temporary workspaces/bookmarks.

Practical guardrails:

- At most three live workers.
- At most two follow-ups per worker before replacing it with a fresh,
  better-scoped worker.
- No implementation turn longer than 60 minutes without a checkpoint.
- No plan over 1,200 lines without explicit justification.
- Full verification only at PR boundaries.
- Remote checkpoint at least every 30–60 minutes of active implementation.

## Bottom line

Keep the PRs and logical commits. They made the work safer and improved the
design. Change the execution model around them:

- smaller plans
- fresh, role-specific workers
- fewer micro-review agents
- real workspace isolation when parallel writing is worthwhile
- phase-level verification
- immediate remote checkpoints
- explicit cleanup of agent state

The most important single change is to avoid combining an implementation-ready
subsystem with an underdesigned subsystem in one plan and execution
authorization. For long unattended runs, require an explicit architecture
readiness gate first. The next change is to prevent another `core_task6`: no
worker should remain the critical path for 17 successive tasks and more than
13 hours.
