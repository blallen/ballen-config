# Self-Review Artifact Split and Test Review Taxonomy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist each self-review as a readable Markdown file plus an
authoritative sibling JSON file, and give test review a fixed, enforced
vocabulary that explicitly covers test theatre, TDD residue, consolidation,
and parameterization.

**Architecture:** Every change is skill prose, contract references, JSON
fixtures, or contract tests. There is no runtime code. Agents render the
Markdown from a fixed template in the artifact contract. A line-for-line test
oracle keeps the canonical example pair honest, and updated remediation
vectors freeze the new `address-self-review` input rules.

**Tech Stack:** Markdown skills, JSON fixtures, pytest, Ruff, pre-commit,
Jujutsu, uv.

**Spec:** `docs/superpowers/specs/2026-09-24-self-review-artifact-split-design.md`

## Global Constraints

- The top-level JSON object keeps `contract_version: "v1"`, its exact key set,
  finding identity material, and hash rules.
- No compatibility with existing single-file artifacts; do not read or migrate
  them.
- No committed renderer script or packaged tooling. The one-off scripts in
  Tasks 1 and 3 run from `/tmp` and are not committed.
- Tests must not pin skill prose, rule tables, or check names.
- After Task 1, contract fixture JSON under
  `assistants/shared/skills/*/references/` is excluded from detect-secrets.
  Write hashes and hex prefixes in those files plain; never escape them.
  Everywhere else, keep using `# pragma: allowlist secret` where comments are
  allowed.
- Prefix every agent-run shell command with `rtk`. Run Python tools through
  `uv run --frozen`.
- Use Jujutsu (`jj`), not Git. Work lands on bookmark
  `self-review-artifact-split`, whose first commit is the spec.
- Wrap Markdown prose near 80 columns to match the surrounding files. Tables
  and template lines are exempt.
- Commit messages end with
  `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`.

## Review Focus

1. A pathless, repository-wide finding must render as `repository` instead of
   crashing or printing `None`. Pinned in Task 3 by the example's `222222222222`
   advisory.
2. Single-line and range locations must render differently
   (`src/review.py:18` versus `...:40-46`), and deduplicated contributors must
   all appear. Pinned in Task 3 by the `555555555555` and `111111111111`
   findings.
3. An optional skip with effect `none` does not change the verdict but must
   still appear under Limitations. Pinned in Task 3 by the `opt-in-evaluation`
   skip.
4. A user may pass the `.md` path of a pair whose JSON write succeeded but
   whose Markdown write failed. Remediation must block with
   `artifact_path_invalid` rather than act on an incomplete review. Pinned in
   Task 4 by the `missing_sibling` vector.
5. A user may type an 8- to 11-character prefix from memory. It must block with
   `selected_finding_unknown` rather than be guessed. Pinned in Task 4 by the
   `short_prefix_selection` vector.

---

## File Map

| File | Change | Task |
| --- | --- | --- |
| `.pre-commit-config.yaml` | Exclude contract fixture JSON from detect-secrets | 1 |
| `assistants/shared/skills/*/references/*.json` | Decode existing hex escapes | 1 |
| `assistants/shared/skills/review-project-tests/SKILL.md` | Declared checks, categories, rules, breaking-change probe, TDD residue | 2 |
| `assistants/shared/standards/testing.md` | Two sentences under "Avoid test theatre" | 2 |
| `assistants/shared/skills/conduct-self-review/SKILL.md` | Stem, pair persistence, Markdown verification, required-check enforcement | 3 |
| `assistants/shared/skills/conduct-self-review/references/self-review-artifact-v1.md` | Pair layout, Markdown template, rendering rules, upgrade note | 3 |
| `assistants/shared/skills/conduct-self-review/references/self-review-result.example.json` | Create: authoritative example JSON | 3 |
| `assistants/shared/skills/conduct-self-review/references/self-review-result.example.md` | Replace: rendered example Markdown | 3 |
| `tests/assistants/test_review_contracts.py` | Example-pair fixture and oracle test; vector harness | 3, 4 |
| `assistants/shared/skills/address-self-review/SKILL.md` | Pair input, JSON-only reads, prefix selection | 4 |
| `assistants/shared/skills/address-self-review/references/remediation-vectors.json` | Pair and prefix vectors | 1, 4 |

---

### Task 1: Stop secret-scanning contract fixtures

**Files:**
- Modify: `.pre-commit-config.yaml`
- Modify: every `assistants/shared/skills/*/references/*.json` that contains
  hex escapes

**Interfaces:**
- Produces: plain hex values in all contract fixture JSON, and a
  detect-secrets hook that skips
  `^assistants/shared/skills/[^/]+/references/[^/]+\.json$`. Tasks 3 and 4
  write new hashes and prefixes plain.

- [ ] **Step 1: Confirm the baseline**

Run: `rtk uv run --frozen pytest tests/assistants/test_review_contracts.py -q`
Expected: all tests pass.

- [ ] **Step 2: Decode the hex escapes**

Write this one-off script to `/tmp/decode_fixture_hex.py`. Do not add it to
the repository. It rewrites only JSON string literals that decode to pure
lowercase hex of 11 to 64 characters. Any other `\u` escape, such as a
Unicode normalization case, is left untouched.

```python
"""One-off: decode every-eighth-character hex escapes in contract fixtures."""

import re
from pathlib import Path

STRING = re.compile(r'"((?:[0-9a-f]|\\u00[0-9a-f]{2})+)"')
ESCAPE = re.compile(r"\\u00([0-9a-f]{2})")
HEX = re.compile(r"[0-9a-f]{11,64}")


def decode(match: re.Match[str]) -> str:
    raw = match.group(1)
    if "\\u" not in raw:
        return match.group(0)
    value = ESCAPE.sub(lambda escape: chr(int(escape.group(1), 16)), raw)
    return f'"{value}"' if HEX.fullmatch(value) else match.group(0)


for path in sorted(Path("assistants/shared/skills").glob("*/references/*.json")):
    text = path.read_text(encoding="utf-8")
    decoded = STRING.sub(decode, text)
    if decoded != text:
        path.write_text(decoded, encoding="utf-8")
        print(path)
```

Run: `rtk uv run --frozen python /tmp/decode_fixture_hex.py`
Expected: it prints these five paths:

```text
assistants/shared/skills/address-self-review/references/remediation-vectors.json
assistants/shared/skills/resolve-change-scope/references/change-scope-vectors.json
assistants/shared/skills/resolve-change-scope/references/change-scope.example.json
assistants/shared/skills/resolve-change-scope/references/review-result-vectors.json
assistants/shared/skills/resolve-change-scope/references/review-result.example.json
```

Then run
`rtk grep -rn '\\u00[0-9a-f][0-9a-f]' assistants/shared/skills --include='*.json'`
and confirm that every remaining match, if any, is a non-hex Unicode case.

- [ ] **Step 3: Prove the decode is lossless**

Run: `rtk uv run --frozen pytest tests/assistants/test_review_contracts.py -q`
Expected: all tests pass. The tests recompute every result, finding, scope,
and workspace hash from the decoded values.

- [ ] **Step 4: Run detect-secrets to verify it fails without the exclusion**

Run: `rtk uv run --frozen pre-commit run detect-secrets --all-files`
Expected: FAIL with `Hex High Entropy String` findings in the decoded
fixture files.

- [ ] **Step 5: Exclude contract fixtures from detect-secrets**

In `.pre-commit-config.yaml`, replace:

```yaml
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
```

with:

```yaml
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        # Contract fixtures are SHA-256 identities by design; the contract tests
        # check them for credential-like keys and non-portable values instead.
        exclude: ^assistants/shared/skills/[^/]+/references/[^/]+\.json$
```

- [ ] **Step 6: Run detect-secrets to verify it passes**

Run: `rtk uv run --frozen pre-commit run detect-secrets --all-files`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
rtk jj commit -m "chore: stop secret-scanning review contract fixtures

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Test review taxonomy

**Files:**
- Modify: `assistants/shared/skills/review-project-tests/SKILL.md`
- Modify: `assistants/shared/standards/testing.md`

**Interfaces:**
- Produces: the eight required check names, used verbatim by Task 3's example
  and generator: `behavioral-coverage`, `assertions`, `fixtures-doubles`,
  `execution-policy`, `theatre`, `consolidation`, `generated-output`,
  `test-documentation`. Task 3's `conduct-self-review` text refers to "every
  required check that skill declares".

This task is prose only. Its verification is the existing assistant suite
plus a checklist review against the spec. Per the testing standard, no test
pins the new prose.

- [ ] **Step 1: Confirm the baseline suite passes**

Run: `rtk uv run --frozen pytest tests/assistants -q`
Expected: all tests pass.

- [ ] **Step 2: Retitle workflow step 4**

In `review-project-tests/SKILL.md`, replace:

```markdown
### 4. Review assertions, fixtures, and doubles
```

with:

```markdown
### 4. Review assertions, fixtures, doubles, and execution policy
```

- [ ] **Step 3: Add the probe, residue, rewrite, and precedence rules to step 5**

Replace:

```markdown
Do not misclassify repository-owned Pydantic validators, transformations,
serialization, custom methods, or consumer-facing representations as
dependency guarantees. Name the exact owned behavior a useful replacement
test would protect.
```

with:

```markdown
Do not misclassify repository-owned Pydantic validators, transformations,
serialization, custom methods, or consumer-facing representations as
dependency guarantees. Name the exact owned behavior a useful replacement
test would protect.

Apply the breaking-change probe to every added or changed test: name the
smallest plausible repository-owned production change that would make it
fail, such as removing a guard, flipping a branch, or returning a stub value.
When no such change exists, report a `theatre` finding whose evidence explains
why no owned change fails the test. The probe is reasoning only; do not run
mutation tools or undeclared commands, and do not edit code.

Report `tdd-residue` for tests left behind by red-green steps:

- existence, import, callable, signature, or return-type tests; and
- tests pinned to a stub or intermediate value.

A test is residue when every owned change that fails it also fails a retained
test. Recommend deleting it or folding its case into the behavioral test.
Incremental tests that differ only in inputs are `parameterize-matrix`
findings instead.

Report `expectation-rewritten` when a changed test's expected value was edited
to match new output and the change does not intend that behavior change.

When the probe finds no failing owned change, report the test only as
`theatre`, even when a mock or weak assertion is the cause. Use the specific
theatre rule when one applies and `test-cannot-fail` otherwise. Tautological
assertions and tests that execute code without asserting use
`test-cannot-fail`.
```

- [ ] **Step 4: Name the consolidation rules in step 6**

Replace:

```markdown
Keep tests separate when they communicate different failure stories, recovery
paths, side effects, user-visible contracts, or diagnostic obligations.
Similar syntax is not sufficient reason to merge them. Do not optimize for the
fewest test functions at the expense of behavioral clarity.

Distinguish:

- duplicate implementation that should be consolidated;
- repeated data that should be parameterized; and
- distinct scenarios that should remain separate.
```

with:

```markdown
Keep tests separate when they communicate different failure stories, recovery
paths, side effects, user-visible contracts, or diagnostic obligations.
Similar syntax is not sufficient reason to merge them. Do not optimize for the
fewest test functions at the expense of behavioral clarity.

Distinguish:

- duplicate implementation that should be consolidated
  (`consolidate-duplicate`);
- repeated data that should be parameterized (`parameterize-matrix`), with
  explicit case identifiers (`missing-case-ids` when absent); and
- distinct scenarios that should remain separate (`over-consolidated` when a
  merged or parameterized test hides them).
```

- [ ] **Step 5: Replace the recommended-categories sentence in step 9 with the declared tables**

Replace:

```markdown
Use tight repository-relative locations and concise evidence. Recommended
categories include behavioral coverage, assertion, theatre, double,
snapshot, duplication, parameterization, and test documentation. Use blocker
only when the review boundary or evidence is untrustworthy, actionable for
material corrections, and advisory for optional clarity or maintainability.
```

with:

```markdown
Record every required check below in coverage whenever this specialist is
applicable. A missing or non-completed required check makes the result
`incomplete`. An evidence-backed `not_applicable` result requires no checks.
Test command evidence follows the command rules instead.

Each check name is also the finding category for the findings it produces:

| Check and category | Workflow step | Covers |
| --- | --- | --- |
| `behavioral-coverage` | 2 and 3 | Changed behavior without a meaningful test, removed sole protection, defect fix without a reproducer |
| `assertions` | 4 | Weak, existence-only, or status-only assertions; implementation-step assertions; exception-message contracts |
| `fixtures-doubles` | 4 | Fixture ownership and visibility, shared mutable state, patch site, sync and async doubles, mocked subject, overbuilt fakes |
| `execution-policy` | 4 | Default-suite determinism and speed, opt-in expensive checks, strict xfail, explainable skips, heavy optional imports, typed signatures, plain functions |
| `theatre` | 5 | Tests that cannot fail for a meaningful owned regression |
| `consolidation` | 6 | Near-duplicates, input matrices, case identifiers, over-merged scenarios |
| `generated-output` | 7 | Snapshots and generated-output contracts |
| `test-documentation` | 8 | Behavioral meaning of test names and docstrings |

Every finding uses one rule from its category:

| Category | Rules |
| --- | --- |
| `behavioral-coverage` | `coverage-gap`, `protection-removed`, `missing-reproducer` |
| `assertions` | `weak-assertion`, `implementation-coupled`, `exception-contract` |
| `fixtures-doubles` | `hidden-fixture`, `shared-mutable-state`, `wrong-patch-target`, `async-mismatch`, `mocked-subject`, `overbuilt-double` |
| `execution-policy` | `nondeterministic-default`, `expensive-not-opt-in`, `non-strict-xfail`, `unexplained-skip`, `heavy-import`, `untyped-test`, `unneeded-test-class` |
| `theatre` | `test-cannot-fail`, `tdd-residue`, `expectation-rewritten`, `mock-manufactured`, `framework-guarantee`, `configuration-reasserted`, `prose-pinned` |
| `consolidation` | `consolidate-duplicate`, `parameterize-matrix`, `missing-case-ids`, `over-consolidated` |
| `generated-output` | `unreviewed-snapshot`, `volatile-snapshot`, `oversized-snapshot`, `brittle-prose` |
| `test-documentation` | `test-name-meaning`, `docstring-meaning` |

When no rule fits, use `unlisted` and name the pattern in the evidence.

Use tight repository-relative locations and concise evidence. Use blocker only
when the review boundary or evidence is untrustworthy, actionable for material
corrections, and advisory for optional clarity or maintainability.
```

- [ ] **Step 6: Add Quick Reference rows**

Replace:

```markdown
| Pydantic field-population assertion | Theatre unless repository-owned behavior is also proved |
```

with:

```markdown
| Pydantic field-population assertion | Theatre unless repository-owned behavior is also proved |
| Added or changed test | Name the smallest owned change that fails it; none means theatre |
| Stepping-stone test subsumed by a behavioral test | `tdd-residue`; delete or fold it |
| Expected value edited to match new output | `expectation-rewritten` unless the change intends the behavior change |
| Pattern outside the rule table | `unlisted`, with the pattern named in evidence |
```

- [ ] **Step 7: Add Common Mistakes bullets**

Replace:

```markdown
- Returning an informal approval without scope identity, coverage, findings,
  and limitations.
```

with:

```markdown
- Returning an informal approval without scope identity, coverage, findings,
  and limitations.
- Leaving red-green stepping-stone tests beside the behavioral tests that
  subsume them. Report `tdd-residue`.
- Reporting a test that cannot fail under assertions or doubles as well as
  theatre. Theatre takes precedence.
- Inventing check names or rules. Use the declared tables and `unlisted`.
```

- [ ] **Step 8: Extend the testing standard**

In `assistants/shared/standards/testing.md`, replace:

```markdown
Reject test theatre: do not re-test framework guarantees, assert configuration
that existing behavior tests already cover, or create mocks whose assertions
can pass without exercising production control flow. Every test should be able
to fail for a meaningful regression in code the repository owns.
```

with:

```markdown
Reject test theatre: do not re-test framework guarantees, assert configuration
that existing behavior tests already cover, or create mocks whose assertions
can pass without exercising production control flow. Every test should be able
to fail for a meaningful regression in code the repository owns. Name the
plausible owned change that would make a new test fail; if none exists, the
test is theatre. Delete or fold stepping-stone tests from red-green cycles once
behavioral tests subsume them.
```

- [ ] **Step 9: Verify**

Run: `rtk uv run --frozen pytest tests/assistants -q`
Expected: all tests pass.

Then re-read the edited sections of `review-project-tests/SKILL.md` against
spec sections "Checks and categories", "Rules", "Breaking-change probe", "TDD
residue", "Expectation rewrites", and "Precedence". Confirm that every check,
category, and rule name matches the spec exactly and that `unlisted` is
present.

- [ ] **Step 10: Commit**

```bash
rtk jj commit -m "feat: declare test review checks and theatre rules

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Artifact pair contract and example

**Files:**
- Create: `assistants/shared/skills/conduct-self-review/references/self-review-result.example.json`
- Replace: `assistants/shared/skills/conduct-self-review/references/self-review-result.example.md`
- Modify: `assistants/shared/skills/conduct-self-review/references/self-review-artifact-v1.md`
- Modify: `assistants/shared/skills/conduct-self-review/SKILL.md`
- Test: `tests/assistants/test_review_contracts.py`

**Interfaces:**
- Consumes: the eight check names from Task 2, and the plain-hex fixture
  convention from Task 1.
- Produces: the pytest fixture `self_review_example_path(repo_root: Path) ->
  Path`, pointing at `self-review-result.example.json`. Also the diagnostic code
  `reviewer_check_missing`, the rendered finding-prefix convention (first 12
  hex characters), and the pair layout that Task 4's `address-self-review`
  text relies on.

- [ ] **Step 1: Point the integrity test at the JSON and add the Markdown oracle test**

In `tests/assistants/test_review_contracts.py`:

1a. Insert a severity-heading constant directly above `_UTC_RFC3339_PATTERN`.
Replace:

```python
_UTC_RFC3339_PATTERN: Final[re.Pattern[str]] = re.compile(
```

with:

```python
_SELF_REVIEW_SEVERITY_HEADINGS: Final[dict[str, str]] = {
    "blocker": "Blockers",
    "actionable": "Actionable",
    "advisory": "Advisories",
}
_UTC_RFC3339_PATTERN: Final[re.Pattern[str]] = re.compile(
```

1b. Add the example fixture after `change_scope_reference_root`. Replace:

```python
    return repo_root / "assistants/shared/skills/resolve-change-scope/references"
```

with:

```python
    return repo_root / "assistants/shared/skills/resolve-change-scope/references"


@pytest.fixture
def self_review_example_path(repo_root: Path) -> Path:
    """Return the canonical self-review example JSON path."""
    return (
        repo_root
        / "assistants/shared/skills/conduct-self-review/references"
        / "self-review-result.example.json"
    )
```

1c. Replace the whole `_load_self_review_artifact` function:

```python
def _load_self_review_artifact(path: Path) -> tuple[dict[str, Any], str]:
    """Parse the marked JSON block and trailing human summary."""
    lines = path.read_text().splitlines()
    assert lines[0] == "<!-- ballen-config:self-review-result:v1 -->"
    assert lines[1] == "```json"
    closing_fence = lines.index("```", 2)
    loaded = json.loads("\n".join(lines[2:closing_fence]))
    assert isinstance(loaded, dict)
    summary = "\n".join(lines[closing_fence + 1 :]).strip()
    assert summary
    return loaded, summary
```

with the template oracle:

```python
def _render_finding_location(finding: dict[str, Any]) -> str:
    """Render the contract's human location for one finding."""
    if finding["path"] is None:
        return "repository"
    start = finding["location"]["start_line"]
    end = finding["location"]["end_line"]
    return f"{finding['path']}:{start}" + ("" if start == end else f"-{end}")


def _render_self_review_markdown(result: dict[str, Any], json_name: str) -> list[str]:
    """Render the artifact contract's Markdown template for the example's cases."""
    assert result["diagnostics"] == []
    assert all(reviewer["outcome"] == "completed" for reviewer in result["reviewers"])
    counts = result["summary"]["counts"]
    scope = result["scope"]
    lines = [
        f"# Self-review: {result['summary']['verdict']}",
        "",
        f"- Findings: {counts['blocker']} blocker, "
        f"{counts['actionable']} actionable, {counts['advisory']} advisory",
        f"- Scope: {scope['status']}, {scope['source']}, "
        f"{len(scope['changed_paths'])} changed paths, "
        f"scope `{scope['scope_identity'][:12]}`",
        f"- Result: `{result['result_id'][:12]}` ([machine result]({json_name}))",
        "",
        "## Limitations",
        "",
        *(
            [
                f"- `{skip['check']}` ({skip['effect']}): {skip['reason']}"
                for skip in result["skips"]
            ]
            or ["None."]
        ),
    ]
    for severity, heading in _SELF_REVIEW_SEVERITY_HEADINGS.items():
        findings = [
            finding for finding in result["findings"] if finding["severity"] == severity
        ]
        if not findings:
            continue
        lines += ["", f"## {heading}", ""]
        for finding in findings:
            lines += [
                f"- `{finding['finding_id'][:12]}` "
                f"`{_render_finding_location(finding)}` "
                f"· {finding['category']}/`{finding['rule']}` "
                f"· {', '.join(finding['contributors'])}",
                f"  - Evidence: {finding['evidence']}",
                f"  - Remediation: {finding['remediation']}",
            ]
    lines += [
        "",
        "## Coverage",
        "",
        "| Reviewer | Applicability | Outcome | Checks |",
        "| --- | --- | --- | --- |",
    ]
    for reviewer in result["reviewers"]:
        checks = ", ".join(
            f"{check['check']}: {check['completion']}"
            for check in reviewer["coverage"]["checks"]
        )
        lines.append(
            f"| {reviewer['reviewer']} | {reviewer['applicability']} "
            f"| {reviewer['outcome']} | {checks} |"
        )
    return lines
```

The two leading `assert` lines are deliberate. The oracle implements only the
cases the example contains, and it fails loudly if the example grows a
diagnostic or an incomplete reviewer without the oracle growing too.

1d. Switch the integrity test to the JSON file. Replace:

```python
def test_self_review_artifact_example_is_portable_and_internally_consistent(
    repo_root: Path,
) -> None:
    """Validate persisted review integrity without pinning summary prose."""
    artifact_path = (
        repo_root
        / "assistants/shared/skills/conduct-self-review/references"
        / "self-review-result.example.md"
    )
    result, summary = _load_self_review_artifact(artifact_path)
```

with:

```python
def test_self_review_artifact_example_is_portable_and_internally_consistent(
    self_review_example_path: Path,
) -> None:
    """Validate persisted review integrity without pinning summary prose."""
    result = _load_json(self_review_example_path)
```

and, in the same test, delete the line:

```python
    assert summary.startswith("## ")
```

1e. Append the oracle test at the end of the file:

```python


def test_self_review_example_markdown_renders_its_json_result(
    self_review_example_path: Path,
) -> None:
    """Keep the human Markdown a faithful, complete rendering of its JSON."""
    result = _load_json(self_review_example_path)
    markdown = self_review_example_path.with_suffix(".md").read_text(encoding="utf-8")

    assert markdown.splitlines() == _render_self_review_markdown(
        result, self_review_example_path.name
    )
```

- [ ] **Step 2: Run the example tests to verify they fail**

Run: `rtk uv run --frozen pytest tests/assistants/test_review_contracts.py -q -k self_review_example`
Expected: FAIL. Both tests raise `FileNotFoundError` for
`self-review-result.example.json`.

- [ ] **Step 3: Generate the example JSON**

Write this one-off script to `/tmp/generate_self_review_example.py`. Do not
add it to the repository. It reads the legacy single-file example, which
still exists at this point.

```python
"""One-off: build the self-review example JSON from the legacy example."""

import hashlib
import json
import re
import unicodedata
from pathlib import Path

REFERENCES = Path("assistants/shared/skills/conduct-self-review/references")
TEST_CHECKS = (
    "behavioral-coverage",
    "assertions",
    "fixtures-doubles",
    "execution-policy",
    "theatre",
    "consolidation",
    "generated-output",
    "test-documentation",
)


def nfc(value):
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, dict):
        return {nfc(key): nfc(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [nfc(nested) for nested in value]
    return value


def canonical_sha256(material):
    encoded = json.dumps(
        nfc(material), ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


legacy = (REFERENCES / "self-review-result.example.md").read_text(encoding="utf-8")
result = json.loads(re.search(r"```json\n(.*?)\n```\n", legacy, re.S).group(1))
reviewers = {reviewer["reviewer"]: reviewer for reviewer in result["reviewers"]}

residue = {
    "finding_id": "1" * 64,
    "category": "theatre",
    "severity": "actionable",
    "source_severity": None,
    "path": "tests/assistants/test_review_contracts.py",
    "location": {"start_line": 40, "end_line": 46},
    "rule": "tdd-residue",
    "evidence": (
        "The import-only test detects no owned regression that the behavioral "
        "contract tests would not also catch."
    ),
    "remediation": (
        "Delete the import-only test; the behavioral contract tests already "
        "fail for every regression it detects."
    ),
    "contributors": ["review-project-tests"],
}
undocumented = {
    "finding_id": "2" * 64,
    "category": "documentation",
    "severity": "advisory",
    "source_severity": "Nit",
    "path": None,
    "location": None,
    "rule": "assistants/shared/standards/documentation.md#repository-documentation",
    "evidence": (
        "The change introduces an ignored review directory that no repository "
        "documentation describes."
    ),
    "remediation": "Describe the ignored review directory in the repository README.",
    "contributors": ["review-project-standards"],
}
opt_in_skip = {
    "check": "opt-in-evaluation",
    "reason": (
        "Networked evaluation tests are explicit opt-in and outside the default suite."
    ),
    "effect": "none",
}

tests = reviewers["review-project-tests"]
tests["coverage"]["checks"] = [
    {
        "check": check,
        "required": True,
        "selected_scope": "changed",
        "completion": "completed",
    }
    for check in TEST_CHECKS
]
tests["findings"] = [residue]
tests["skips"] = [opt_in_skip]
tests["summary"] = {
    "counts": {"blocker": 0, "actionable": 1, "advisory": 0},
    "verdict": "needs_attention",
}

standards = reviewers["review-project-standards"]
standards["findings"].append(undocumented)
standards["summary"]["counts"]["advisory"] = 2

result["findings"].extend([residue, undocumented])
result["skips"] = [{**opt_in_skip, "contributors": ["review-project-tests"]}]
result["summary"]["counts"] = {"blocker": 0, "actionable": 2, "advisory": 1}

result["result_id"] = canonical_sha256(
    {
        key: value
        for key, value in result.items()
        if key not in {"created_at", "result_id", "result_digest"}
    }
)
result["result_digest"] = canonical_sha256(
    {key: value for key, value in result.items() if key != "result_digest"}
)

(REFERENCES / "self-review-result.example.json").write_text(
    json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
)
print(result["result_id"][:12])
```

Run: `rtk uv run --frozen python /tmp/generate_self_review_example.py`
Expected output: `dc67e7f04c1a`

If the printed prefix differs, the legacy example changed since this plan was
written. Use the printed value in Step 4 in place of `dc67e7f04c1a`.

- [ ] **Step 4: Replace the example Markdown with the rendered template**

Overwrite `self-review-result.example.md` with exactly:

````markdown
# Self-review: needs_attention

- Findings: 0 blocker, 2 actionable, 1 advisory
- Scope: resolved, jujutsu, 5 changed paths, scope `eeeeeeeeeeee`
- Result: `dc67e7f04c1a` ([machine result](self-review-result.example.json))

## Limitations

- `opt-in-evaluation` (none): Networked evaluation tests are explicit opt-in and outside the default suite.

## Actionable

- `555555555555` `src/review.py:18` · documentation/`DOCSTRING-SUMMARY` · review-project-quality, review-project-standards
  - Evidence: The public function uses an expanded docstring for a single-sentence contract.
  - Remediation: Collapse the docstring to a single summary line.
- `111111111111` `tests/assistants/test_review_contracts.py:40-46` · theatre/`tdd-residue` · review-project-tests
  - Evidence: The import-only test detects no owned regression that the behavioral contract tests would not also catch.
  - Remediation: Delete the import-only test; the behavioral contract tests already fail for every regression it detects.

## Advisories

- `222222222222` `repository` · documentation/`assistants/shared/standards/documentation.md#repository-documentation` · review-project-standards
  - Evidence: The change introduces an ignored review directory that no repository documentation describes.
  - Remediation: Describe the ignored review directory in the repository README.

## Coverage

| Reviewer | Applicability | Outcome | Checks |
| --- | --- | --- | --- |
| review-project-standards | applicable | completed | repository-standards: completed |
| review-project-quality | applicable | completed | configured-quality-gate: completed |
| review-project-tests | applicable | completed | behavioral-coverage: completed, assertions: completed, fixtures-doubles: completed, execution-policy: completed, theatre: completed, consolidation: completed, generated-output: completed, test-documentation: completed |
| review-python-types | applicable | completed | configured-type-checker: completed |
````

The file ends with a single trailing newline after the last table row.

- [ ] **Step 5: Run the contract tests to verify they pass**

Run: `rtk uv run --frozen pytest tests/assistants/test_review_contracts.py -q`
Expected: all tests pass, including
`test_self_review_example_markdown_renders_its_json_result` and
`test_self_review_artifact_example_is_portable_and_internally_consistent`.

Then prove the oracle can fail. Temporarily change `Collapse the docstring to a
single summary line.` in the Markdown to `Shorten the docstring.`, rerun the
command, and confirm
`test_self_review_example_markdown_renders_its_json_result` fails. Revert the
edit and confirm the test passes again.

- [ ] **Step 6: Update the artifact contract's destination preflight**

In `references/self-review-artifact-v1.md`, replace:

````markdown
After scope resolution, construct:

```text
<timestamp>-<scope-id-prefix>.md
```

The timestamp is UTC and filename-safe. The scope prefix is the shortest prefix
that distinguishes the full scope identity from identities already present in
the selected directory, with a minimum of 12 lowercase hexadecimal
characters. The complete scope identity remains in the JSON.

Open the final file with exclusive-create semantics. Never overwrite or append
to an existing artifact. If the same scope and timestamp collide, capture a
later UTC timestamp or fail safely; do not invent a suffix or replace the file.
````

with:

````markdown
After scope resolution, construct the stem:

```text
<timestamp>-<scope-id-prefix>
```

The timestamp is UTC and filename-safe. The scope prefix is the shortest prefix
that distinguishes the full scope identity from the stems already present in
the selected directory, with a minimum of 12 lowercase hexadecimal
characters. The complete scope identity remains in the JSON.

The stem is usable only when neither `<stem>.json` nor `<stem>.md` exists. Open
each file with exclusive-create semantics. Never overwrite or append to an
existing file. If the same scope and timestamp collide, capture a later UTC
timestamp or fail safely; do not invent a suffix or replace either file.
````

- [ ] **Step 7: Replace the file-layout section with the pair and template**

Replace the whole `## File layout` section, from its heading through the
paragraph ending `override, or reinterpret machine fields.`:

`````markdown
## File layout

The first line is exactly:

```text
<!-- ballen-config:self-review-result:v1 -->
```

The next line opens a fenced JSON block:

````text
```json
```
````

The complete JSON object follows, then the closing fence. Human-readable
Markdown follows the fence. No blank line, heading, or prose may precede the
marker or intervene between the marker and opening fence.

The JSON block is authoritative. The Markdown summary may restate the verdict,
counts, important blockers, and limitations for humans, but cannot add,
override, or reinterpret machine fields.
`````

with:

`````markdown
## Files

Each self-review writes one pair with a shared stem:

```text
<stem>.json
<stem>.md
```

The JSON file is authoritative. The Markdown file is a human rendering of it
and never an input to later workflows.

### JSON file

The JSON file contains exactly the top-level object defined below,
pretty-printed with a trailing newline. File formatting does not affect the
canonical hashes.

### Markdown file

Render the Markdown from the final JSON with this template:

````markdown
# Self-review: <verdict>

- Findings: <blocker> blocker, <actionable> actionable, <advisory> advisory
- Scope: <status>, <source>, <changed path count> changed paths, scope `<scope-id-prefix>`
- Result: `<result-id-prefix>` ([machine result](<stem>.json))

## Limitations

- `<reviewer>` (<outcome>)
- `<check>` (<effect>): <reason>
- `<code>` (diagnostic): <detail>

## Blockers

- `<finding-id-prefix>` `<location>` · <category>/`<rule>` · <contributors>
  - Evidence: <evidence>
  - Remediation: <remediation>

## Actionable

## Advisories

## Coverage

| Reviewer | Applicability | Outcome | Checks |
| --- | --- | --- | --- |
| <reviewer> | <applicability> | <outcome> | <check>: <completion>, ... |
````

Rendering rules:

- Separate the title, each heading, and each section body with one blank line.
- Use 12-character lowercase prefixes for the scope identity and result ID.
- Give every finding prefix in one artifact the same length: 12, or the
  shortest longer length that makes every prefix unique.
- Render `<location>` as `<path>:<line>` for one line, `<path>:<start>-<end>`
  for a range, `<path>` without a location, and `repository` without a path.
- Render the category alone when `rule` is null, and omit the Remediation line
  when `remediation` is null.
- Join contributors with `, ` in JSON order.
- Copy evidence, remediation, reasons, and details verbatim.
- Order severity sections blocker, actionable, advisory, and omit empty ones.
  Keep JSON finding order within a section.
- In Limitations, list reviewers whose outcome is not `completed`, then
  aggregate skips, then aggregate diagnostics, each in JSON order. Append
  `: <reason>` to a blocked-scope skip record, and render a diagnostic with a
  path as `` `<code>` (diagnostic, `<path>`): <detail> ``. When nothing
  qualifies, the section body is `None.`
- In Coverage, give one row per reviewer in JSON order. A blocked-scope skip
  record renders `skipped` as its outcome and `-` for applicability and
  checks. Join checks as `<check>: <completion>` with `, `.

The Markdown restates machine fields only through this template. It cannot
add, override, or reinterpret them.

This rendering is agent-authored and protected by read-back verification. If
verification keeps catching drift, or persisted pairs are found inconsistent
with their JSON, replace agent rendering with a deterministic renderer script.
`````

- [ ] **Step 8: Add required reviewer checks to the contract**

Replace:

```markdown
Do not fabricate empty reviewer results after blocked scope.
```

with:

```markdown
Do not fabricate empty reviewer results after blocked scope.

### Required reviewer checks

When `review-project-tests` is applicable, its coverage must list every
required check that skill declares. For each missing check, the orchestrator
adds one aggregate diagnostic with code `reviewer_check_missing`, path `null`,
a detail naming the reviewer and check, and contributor
`conduct-self-review`. It does not edit the specialist result.
```

Then replace:

```markdown
produce `unavailable`. Partial scope, unknown applicability, incomplete
reviewer work, or incomplete required skips produce `incomplete`. Findings
then determine `blockers_found`, `needs_attention`, or `advisories`.
```

with:

```markdown
produce `unavailable`. Partial scope, unknown applicability, incomplete
reviewer work, incomplete required skips, or a `reviewer_check_missing`
diagnostic produce `incomplete`. Findings then determine `blockers_found`,
`needs_attention`, or `advisories`.
```

- [ ] **Step 9: Update contract persistence and privacy text**

Replace:

```markdown
Every attempt whose destination passes preflight writes an artifact, including
empty, partial, blocked, unavailable, and finding-bearing results. Build and
validate the complete object before the exclusive write.

After persistence, verify the marker, parse the JSON back, recompute both
hashes, and confirm the persisted path remains ignored and untracked. Return a
concise inline verdict, counts, important blockers or limitations, and a
clickable repository-relative artifact path.

If persistence or post-write verification fails, self-review did not complete.
Report that failure without claiming the computed verdict or a clean result.
```

with:

```markdown
Every attempt whose destination passes preflight writes a pair, including
empty, partial, blocked, unavailable, and finding-bearing results. Build and
validate the complete object before either exclusive write. Write the JSON
file first, then the Markdown file.

After persistence, parse the JSON back, recompute both hashes, verify the
Markdown against the rendering rules above, and confirm both paths remain
ignored and untracked. Return a concise inline verdict, counts, important
blockers or limitations, and a clickable repository-relative link to the
Markdown file.

If either write or post-write verification fails, self-review did not
complete. Report that failure without claiming the computed verdict or a clean
result. Leave any partial pair in place and never overwrite it.
```

Then replace:

```markdown
The artifact is ignored user-controlled evidence, not signed authorization.
It never contains:
```

with:

```markdown
The pair is ignored user-controlled evidence, not signed authorization.
Neither file contains:
```

- [ ] **Step 10: Update `conduct-self-review/SKILL.md`**

Make each replacement below.

Overview. Replace:

```markdown
**Core principle:** A self-review is complete only when one immutable scope is
reviewed by every specialist and the validated result is persisted in a safe
ignored artifact.

Compose existing reviewers; do not implement their checks again. The artifact
is durable evidence for later human review or explicitly selected remediation,
not authorization by itself.
```

with:

```markdown
**Core principle:** A self-review is complete only when one immutable scope is
reviewed by every specialist and the validated result is persisted as a safe
ignored artifact pair: authoritative JSON and its rendered Markdown.

Compose existing reviewers; do not implement their checks again. The artifact
pair is durable evidence for later human review or explicitly selected
remediation, not authorization by itself.
```

When to Use. Replace `- a durable, integrity-checked local review artifact; or`
with `- a durable, integrity-checked local review artifact pair; or`.

Inputs. Replace:

```markdown
`.reviews/self-review/`. It changes only the directory; this skill still owns
the generated timestamp and scope-prefix filename. Do not accept a complete
caller-selected filename.
```

with:

```markdown
`.reviews/self-review/`. It changes only the directory; this skill still owns
the generated timestamp and scope-prefix stem. Do not accept a caller-selected
filename or stem.
```

Step 1. Replace:

```markdown
Directory preflight precedes scope resolution. Final filename collision and
exclusive-create checks happen after the scope identity exists.
```

with:

```markdown
Directory preflight precedes scope resolution. Final stem collision and
exclusive-create checks happen after the scope identity exists.
```

Step 5. Replace:

```markdown
Require exactly one common v1 result from every specialist. Retain
evidence-backed `not_applicable` results. Preserve unknown applicability,
incomplete analysis, missing tools, skips, and blocked work without converting
them into success.
```

with:

```markdown
Require exactly one common v1 result from every specialist. Retain
evidence-backed `not_applicable` results. Preserve unknown applicability,
incomplete analysis, missing tools, skips, and blocked work without converting
them into success.

When `review-project-tests` is applicable, verify that its coverage lists every
required check that skill declares; do not copy or extend its list here. For
each missing check, add one aggregate diagnostic with code
`reviewer_check_missing`, path `null`, a detail naming the reviewer and check,
and contributor `conduct-self-review`. Do not edit the specialist result.
```

Step 8. Replace:

```markdown
3. `incomplete` for partial scope, unknown applicability, incomplete reviewer
   work, or incomplete required skips;
```

with:

```markdown
3. `incomplete` for partial scope, unknown applicability, incomplete reviewer
   work, incomplete required skips, or a `reviewer_check_missing` diagnostic;
```

Step 10. Replace:

```markdown
### 10. Select a non-existing filename

Under the preflighted directory, choose the shortest unique prefix of the full
scope identity, with a minimum of 12 lowercase hexadecimal characters. Combine
it with the filename-safe UTC timestamp defined by the artifact contract.

Inspect only artifacts in the selected directory needed to establish prefix
uniqueness. Never infer authority from their contents. If the final path
exists, do not overwrite it; capture a later timestamp or fail safely.
```

with:

```markdown
### 10. Select a non-existing stem

Under the preflighted directory, choose the shortest unique prefix of the full
scope identity, with a minimum of 12 lowercase hexadecimal characters. Combine
it with the filename-safe UTC timestamp defined by the artifact contract to
form the stem.

Inspect only filenames in the selected directory needed to establish prefix
uniqueness. Never infer authority from their contents. The stem is usable only
when neither `<stem>.json` nor `<stem>.md` exists; otherwise capture a later
timestamp or fail safely. Never overwrite either file.
```

Step 11. Replace:

```markdown
Write:

1. the exact first-line marker;
2. the immediately following fenced JSON object; and
3. a concise human Markdown summary after the fence.

Use exclusive-create semantics. After writing:

- read the artifact back;
- verify the marker and JSON placement;
- recompute `result_id` and `result_digest`;
- confirm reviewer identities, counts, and verdict;
- confirm prohibited data and raw diffs are absent;
- confirm the path remains ignored and untracked; and
- confirm ordinary source-control status does not expose the artifact.

Every attempt whose directory passed preflight must persist its outcome,
including empty, partial, blocked, unavailable, or finding-bearing results.
If persistence or verification fails, self-review did not complete and cannot
claim the computed verdict or clean state.
```

with:

```markdown
Write, each with exclusive-create semantics:

1. `<stem>.json` containing exactly the machine result; then
2. `<stem>.md` rendered from that result with the Markdown template in the
   artifact contract.

Copy evidence, remediation, reasons, and details verbatim. The Markdown must
not add, override, or reinterpret machine fields.

After writing:

- read both files back;
- parse the JSON and recompute `result_id` and `result_digest`;
- confirm reviewer identities, counts, and verdict;
- confirm the Markdown verdict, counts, and result-ID prefix match the JSON;
- confirm every JSON finding appears exactly once under its severity section
  with matching path, lines, category, and rule, and that no other finding
  appears;
- confirm every aggregate skip and diagnostic appears under Limitations;
- confirm prohibited data and raw diffs are absent from both files;
- confirm both paths remain ignored and untracked; and
- confirm ordinary source-control status exposes neither file.

Every attempt whose directory passed preflight must persist its outcome,
including empty, partial, blocked, unavailable, or finding-bearing results.
If either write or any verification step fails, self-review did not complete
and cannot claim the computed verdict or clean state. Leave a partial pair in
place; never overwrite it.
```

Step 12. Replace `- a clickable repository-relative artifact path.` with
`- a clickable repository-relative link to the Markdown file.`

Output. Replace:

```markdown
The durable output is one validated v1 artifact in the selected ignored
directory. The inline output is a concise human summary and link to that exact
file.

The artifact remains ignored and uncommitted. It is user-controlled evidence,
not a signed result and not permission to edit findings.
```

with:

```markdown
The durable output is one validated artifact pair in the selected ignored
directory: authoritative v1 JSON and its rendered Markdown. The inline output
is a concise human summary and a link to that Markdown file.

Both files remain ignored and uncommitted. They are user-controlled evidence,
not a signed result and not permission to edit findings.
```

Quick Reference. Replace:

```markdown
| Quality result contains Ponytail coverage | Preserve it inside quality; keep four reviewers |
```

with:

```markdown
| Quality result contains Ponytail coverage | Preserve it inside quality; keep four reviewers |
| Applicable test review omits a declared check | Add `reviewer_check_missing`; verdict is at least incomplete |
```

and replace:

```markdown
| Artifact path exists | Never overwrite; choose a later timestamp or fail |
```

with:

```markdown
| Either file of the stem exists | Never overwrite; choose a later timestamp or fail |
```

Boundaries. Replace:

```markdown
This skill may write only its verified ignored review artifact and temporary
ignored persistence checks. It never edits tracked source, tests,
```

with:

```markdown
This skill may write only its verified ignored review artifact pair and
temporary ignored persistence checks. It never edits tracked source, tests,
```

Common Mistakes. Replace:

```markdown
- Writing a prose-only report without the exact marker, JSON, and hashes.
```

with:

```markdown
- Writing only one file of the pair, or Markdown that paraphrases evidence,
  omits a finding, or restates a field differently from the JSON.
- Accepting a test review whose coverage omits a check that
  `review-project-tests` declares as required.
```

- [ ] **Step 11: Confirm no stale layout language remains**

Run: `rtk grep -rn "self-review-result:v1\|first-line marker\|fenced JSON\|scope-prefix filename" assistants/shared/skills/conduct-self-review`
Expected: no matches.

- [ ] **Step 12: Run the assistant suite**

Run: `rtk uv run --frozen pytest tests/assistants -q`
Expected: all tests pass.

- [ ] **Step 13: Commit**

```bash
rtk jj commit -m "feat: split self-review artifacts into Markdown and JSON

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Address-self-review pair input and prefix selection

**Files:**
- Modify: `tests/assistants/test_review_contracts.py`
- Modify: `assistants/shared/skills/address-self-review/references/remediation-vectors.json`
- Modify: `assistants/shared/skills/address-self-review/SKILL.md`

**Interfaces:**
- Consumes: the pair layout and 12-character finding-prefix convention from
  Task 3, and the plain-hex fixture convention from Task 1.
- Produces: vector names `missing_sibling`, `prefix_selection`, and
  `short_prefix_selection`; baseline key `artifact_files`; and per-vector
  artifact key `files`, which replaces `marker`.

- [ ] **Step 1: Update the vector harness**

In `tests/assistants/test_review_contracts.py`, make each replacement below.

Case diagnostics. Replace:

```python
_REMEDIATION_CASE_DIAGNOSTICS: Final[dict[str, str]] = {
    "valid_selected_finding": "ok",
    "missing_marker": "artifact_marker_missing",
```

with:

```python
_REMEDIATION_CASE_DIAGNOSTICS: Final[dict[str, str]] = {
    "valid_selected_finding": "ok",
    "prefix_selection": "ok",
    "missing_sibling": "artifact_path_invalid",
    "short_prefix_selection": "selected_finding_unknown",
```

New constants. Replace:

```python
    "rehashed_in_scope_wrong_location": "finding_evidence_not_reproduced",
}
```

with:

```python
    "rehashed_in_scope_wrong_location": "finding_evidence_not_reproduced",
}
_REMEDIATION_PROCEED_CASES: Final[frozenset[str]] = frozenset(
    {"valid_selected_finding", "prefix_selection"}
)
_FINDING_SELECTION_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{1,64}$")
_FINDING_PREFIX_LENGTH: Final[int] = 12
```

Vocabulary. Replace:

```python
        "artifact_path_invalid",
        "artifact_marker_missing",
```

with:

```python
        "artifact_path_invalid",
```

Baseline. Replace:

```python
    assert set(baseline) == {
        "artifact_marker",
        "artifact_result",
        "selected_finding_reviewer",
        "reviewed_state",
    }
    assert baseline["artifact_marker"] == "<!-- ballen-config:self-review-result:v1 -->"
```

with:

```python
    assert set(baseline) == {
        "artifact_files",
        "artifact_result",
        "selected_finding_reviewer",
        "reviewed_state",
    }
    assert baseline["artifact_files"] == ["json", "markdown"]
```

Artifact keys. Replace:

```python
            "base",
            "marker",
            "json_state",
```

with:

```python
            "base",
            "files",
            "json_state",
```

Artifact resolution. Replace:

```python
        artifact_marker = (
            baseline["artifact_marker"]
            if artifact["marker"] == "inherit"
            else artifact["marker"]
        )
```

with:

```python
        artifact_files = (
            baseline["artifact_files"]
            if artifact["files"] == "inherit"
            else artifact["files"]
        )
```

Selection shape. Replace:

```python
        for finding_id in selected_finding_ids:
            _assert_sha256(finding_id)
```

with:

```python
        for finding_id in selected_finding_ids:
            assert _FINDING_SELECTION_PATTERN.fullmatch(finding_id)
```

Decision and case stories. Replace:

```python
        assert expected["decision"] == (
            "proceed" if name == "valid_selected_finding" else "block"
        )

        if name == "valid_selected_finding":
            assert artifact_marker == baseline["artifact_marker"]
            assert result_id_valid
            assert result_digest_valid
            assert finding_id_valid
            assert current_state == reviewed_state
            assert set(requested_edit["paths"]).issubset(
                requested_edit["authority_paths"]
            )
        elif name == "missing_marker":
            assert artifact_marker is None
```

with:

```python
        assert expected["decision"] == (
            "proceed" if name in _REMEDIATION_PROCEED_CASES else "block"
        )

        if name in _REMEDIATION_PROCEED_CASES:
            assert artifact_files == baseline["artifact_files"]
            assert result_id_valid
            assert result_digest_valid
            assert finding_id_valid
            assert current_state == reviewed_state
            assert set(requested_edit["paths"]).issubset(
                requested_edit["authority_paths"]
            )
            if name == "prefix_selection":
                assert selected_finding_ids == [
                    baseline_finding_id[:_FINDING_PREFIX_LENGTH]
                ]
        elif name == "missing_sibling":
            assert artifact_files == ["json"]
        elif name == "short_prefix_selection":
            (short_prefix,) = selected_finding_ids
            assert len(short_prefix) < _FINDING_PREFIX_LENGTH
            assert baseline_finding_id.startswith(short_prefix)
```

- [ ] **Step 2: Run the vector test to verify it fails**

Run: `rtk uv run --frozen pytest tests/assistants/test_review_contracts.py -q -k remediation_vectors`
Expected: FAIL at the diagnostic-vocabulary equality assertion, because the
fixture still lists `artifact_marker_missing`.

- [ ] **Step 3: Update the vector fixture**

Make these edits in `remediation-vectors.json`, preserving its two-space
indentation.

3a. Remove the vocabulary entry. Replace:

```json
    "artifact_json_malformed",
    "artifact_marker_missing",
```

with:

```json
    "artifact_json_malformed",
```

3b. Replace the baseline marker:

```json
    "artifact_marker": "<!-- ballen-config:self-review-result:v1 -->",
```

with:

```json
    "artifact_files": [
      "json",
      "markdown"
    ],
```

3c. Replace all 11 occurrences of `        "marker": "inherit",` with
`        "files": "inherit",`. Confirm the count first with
`rtk grep -c '"marker": "inherit"' assistants/shared/skills/address-self-review/references/remediation-vectors.json`.
Expected: `11`.

3d. Turn `missing_marker` into `missing_sibling`. Replace:

```json
      "name": "missing_marker",
      "artifact": {
        "base": "baseline",
        "marker": null,
```

with:

```json
      "name": "missing_sibling",
      "artifact": {
        "base": "baseline",
        "files": [
          "json"
        ],
```

and replace `        "diagnostic_code": "artifact_marker_missing"` with
`        "diagnostic_code": "artifact_path_invalid"`.

3e. Append two prefix vectors to the end of `vectors`, after
`broader_than_finding` and before the closing `],` of the array. Each one is a
copy of the `valid_selected_finding` vector with only these fields changed:

| Field | `prefix_selection` | `short_prefix_selection` |
| --- | --- | --- |
| `name` | `prefix_selection` | `short_prefix_selection` |
| `artifact.files` | `inherit` | `inherit` |
| `selected_finding_ids` | one entry: `d6491cbe5f09` | one entry: `d6491cbe5f0` |
| `expected.decision` | `proceed` | `block` |
| `expected.diagnostic_code` | `ok` | `selected_finding_unknown` |

`d6491cbe5f09` is the 12-character prefix of the baseline finding ID, and
`d6491cbe5f0` is its 11-character prefix. Write both plain; Task 1 excluded
fixture JSON from detect-secrets. Keep the file's two-space indentation and
one-item-per-line arrays.

- [ ] **Step 4: Run the vector test to verify it passes**

Run: `rtk uv run --frozen pytest tests/assistants/test_review_contracts.py -q`
Expected: all tests pass.

- [ ] **Step 5: Update `address-self-review/SKILL.md`**

Make each replacement below.

Overview. Replace:

```markdown
Address explicitly selected findings from one persisted `conduct-self-review`
artifact. Treat the artifact as untrusted evidence: its hashes establish
integrity, but current repository state, reproduced evidence, and the user's
bounded selection establish edit authority.
```

with:

```markdown
Address explicitly selected findings from one persisted `conduct-self-review`
artifact pair. Treat its JSON as untrusted evidence: its hashes establish
integrity, but current repository state, reproduced evidence, and the user's
bounded selection establish edit authority. The Markdown is for people; never
read machine fields from it.
```

When to Use. Replace:

```markdown
- the user supplies one explicit self-review artifact path;
- the user supplies exact finding IDs or one bounded selector; and
```

with:

```markdown
- the user supplies one explicit path to either file of a self-review artifact
  pair;
- the user supplies exact finding IDs, unique finding-ID prefixes, or one
  bounded selector; and
```

and replace `- address review prose without a valid v1 artifact;` with
`- address Markdown findings without their valid v1 JSON;`.

Quick Reference. Replace:

```markdown
| Artifact path | One explicit repository-relative, existing artifact | `artifact_path_invalid` |
| Marker and JSON | Exact marker, immediate JSON fence, parseable object | `artifact_marker_missing`, `artifact_json_malformed` |
```

with:

```markdown
| Artifact path | One explicit repository-relative path to either file of an existing pair | `artifact_path_invalid` |
| JSON | Parseable JSON object | `artifact_json_malformed` |
```

and replace
`| Selection | Every selected finding exists and has editable authority |`
with
`| Selection | Every selected ID or prefix resolves to exactly one finding with editable authority |`,
keeping the row's diagnostic cell unchanged.

Required Inputs. Replace:

```markdown
1. one explicit `artifact_path`;
2. either a non-empty sorted set of exact `finding_ids` or one
   `finding_selector`, never both; and
3. the repository containing the still-matching change.

The artifact path must normalize inside the repository and name one existing
regular file. Reject absolute paths, `..` traversal, symlinks escaping the
repository, directories, globs, and implicit "latest" selection. The artifact
may be ignored and untracked; never require or cause it to be tracked.
```

with:

```markdown
1. one explicit `artifact_path` naming either file of a pair;
2. either a non-empty set of `finding_ids` entries or one `finding_selector`,
   never both; and
3. the repository containing the still-matching change.

The artifact path must normalize inside the repository and name one existing
regular file ending in `.json` or `.md`. Derive the stem and require both
`<stem>.json` and `<stem>.md` to exist as regular files in the same
directory; a missing sibling means the self-review did not complete. Reject
absolute paths, `..` traversal, symlinks escaping the repository,
directories, globs, other extensions, and implicit "latest" selection. The
pair may be ignored and untracked; never require or cause it to be tracked.
Read and validate only the JSON file.

Each `finding_ids` entry is a full finding ID or a prefix of at least 12
lowercase hexadecimal characters, as the Markdown renders it. Every entry must
match exactly one aggregate finding in the JSON.
```

and replace:

```markdown
Normalize and sort the selected IDs. Do not infer selection from remediation
prose or severity.
```

with:

```markdown
Normalize resolved entries to full IDs and sort them. Do not infer selection
from remediation prose or severity.
```

Step 1. Replace:

```markdown
Open the artifact read-only. Do not modify its timestamps or contents.

Require:

- first line exactly
  `<!-- ballen-config:self-review-result:v1 -->`;
- an immediate fenced JSON block;
- parseable JSON with exact v1 top-level structure;
```

with:

```markdown
Open the JSON file read-only. Do not modify either file's timestamps or
contents.

Require:

- parseable JSON with exact v1 top-level structure;
```

and replace:

```markdown
contents. Use:

- `artifact_marker_missing`;
- `artifact_json_malformed`;
```

with:

```markdown
contents. Use:

- `artifact_json_malformed`;
```

Step 5. Replace:

```markdown
Resolve exact IDs or the one bounded selector against the aggregate artifact
findings. For every selected finding:
```

with:

```markdown
Resolve `finding_ids` entries or the one bounded selector against the aggregate
JSON findings. For every selected finding:
```

and replace:

```markdown
An unknown or duplicate selected ID blocks with
`selected_finding_unknown`. Ambiguous source ownership blocks with
```

with:

```markdown
An entry that matches no finding or more than one finding, a prefix shorter
than 12 characters, or two entries that resolve to the same finding block with
`selected_finding_unknown`. Ambiguous source ownership blocks with
```

Step 9. Replace:

```markdown
change. It writes a new ignored artifact using its own preflight and
persistence rules.
```

with:

```markdown
change. It writes a new ignored artifact pair using its own preflight and
persistence rules.
```

Step 10. Replace:

```markdown
One finding ID appears in only one selected-status group. Residual findings are
reported with their new IDs and artifact path, never fixed recursively.

Return:

- old artifact path and result ID;
- new artifact path and result ID when created;
- exact changed paths;
- focused verification summary;
- addressed, unresolved, blocked, and residual IDs;
```

with:

```markdown
One finding ID appears in only one selected-status group. Residual findings are
reported with their new prefixes and Markdown path, never fixed recursively.

Return:

- old Markdown path and result ID;
- new Markdown path and result ID when created;
- exact changed paths;
- focused verification summary;
- addressed, unresolved, blocked, and residual finding prefixes as the
  Markdown renders them;
```

Diagnostic Vocabulary. Replace:

```text
artifact_path_invalid
artifact_marker_missing
artifact_json_malformed
```

with:

```text
artifact_path_invalid
artifact_json_malformed
```

Common Mistakes. Replace:

```markdown
- Treating a valid result digest as approval to edit.
```

with:

```markdown
- Treating a valid result digest as approval to edit.
- Reading machine fields from the Markdown instead of its JSON sibling.
- Guessing a match for a short or ambiguous finding-ID prefix.
```

- [ ] **Step 6: Confirm no stale marker language remains**

Run: `rtk grep -rn "artifact_marker\|self-review-result:v1\|JSON fence" assistants/shared tests`
Expected: no matches.

- [ ] **Step 7: Run the assistant suite**

Run: `rtk uv run --frozen pytest tests/assistants -q`
Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
rtk jj commit -m "feat: accept self-review pairs and prefixes in remediation

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Full verification and bookmark

**Files:** none changed unless a check fails.

- [ ] **Step 1: Run the CI-equivalent checks**

Run each command and confirm that it succeeds:

```bash
rtk uv run --frozen pre-commit run --all-files
rtk uv run --frozen mypy
rtk uv run --frozen pytest -q
```

Expected: every pre-commit hook passes, mypy reports no issues, and all tests
pass. If detect-secrets flags a contract fixture, the Task 1 exclusion pattern
does not cover its path; fix the pattern rather than escaping values. If it
flags hex elsewhere, such as in this plan, move the value out of quotes or add
`# pragma: allowlist secret` where comments are allowed.

- [ ] **Step 2: Plan and doctor the bootstrap with the machine's selections**

Use the same profile, include, and skip selections this machine is normally
bootstrapped with, and ask the user if they are unknown. CI uses
`--profile wsh`.

```bash
rtk ./bootstrap plan --profile wsh
rtk ./bootstrap doctor --profile wsh
```

Expected: the plan lists updates for the three changed skills and no
unrelated changes. Doctor reports drift only for those installed skills until
bootstrap is applied. Do not apply bootstrap without the user's approval.

- [ ] **Step 3: Move the bookmark to the last task commit**

```bash
rtk jj bookmark set self-review-artifact-split -r @-
rtk jj log -n 8 | cat
```

Expected: `self-review-artifact-split` points at the Task 4 commit, and the
spec, plan, and four task commits sit above `main`.
