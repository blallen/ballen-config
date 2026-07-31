# Mechanistic Modeling Reference Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract Plato's portable mechanistic-modeling concepts into a
generic, passive reference library in `ballen-config`, preserving the approved
domain terminology while excluding source-code details and internal project
references.

**Architecture:** Add a five-document sibling library under
`assistants/shared/mechanistic-modeling/`. The root document fixes terminology,
package mechanics, and authority boundaries; separate documents explain the
data, runtime, composition, and validation layers. Keep model semantics
parallel to agent orchestration, record source-to-destination provenance in an
audit-only YAML manifest, and enforce machine-checkable terminology,
structure, links, privacy, and boundary claims with focused pytest tests.

**Tech Stack:** Markdown, YAML, Python 3.12, pytest, PyYAML, Ruff, mypy,
pre-commit, Markdownlint, and Jujutsu.

---

## Execution Model

- Execute tasks in order. Later prose depends on the terminology and source
  boundaries established in Tasks 0 through 2.
- Treat the exact names `MechanisticModel`, `Interaction`, `Variable`,
  `MathTerm`, `Block`, `Parameter`, `ConservationLaw`,
  `MechanisticModelComposer`, and `ModelSolution` as normative vocabulary.
  Clarifying translations may accompany them but may not replace or rename
  them.
- Author reader-facing prose from concepts, not by copying Plato code,
  signatures, package layouts, or internal identifiers.
- Keep Plato read-only. Never amend, restore, fold, or otherwise touch its
  working copy, including unrelated user changes.
- Treat Plato revision
  `0fa63b144251ca6b5c6fa99b49151c7e5d5ae276` as the reviewed source
  snapshot. Stop if a reviewed source or verification file differs from that
  revision.
- Record this plan and create a clean successor working copy before starting
  Task 0. The implementation begins only from that clean successor.
- Use `2026-07-31` only for sources actually re-read on that date. If execution
  starts later, re-read the canonical sources and replace every retrieval,
  review, and approval date in the manifest and tests with the actual dates.
- Keep `agent-architecture` and `mechanistic-modeling` as sibling authorities.
  Cross-links are informative and must not imply that either library owns the
  other's contracts.
- Use Luna extra-high for every subagent. Keep final specification and
  portability subagents read-only, and serialize any writing subagents so that
  terminology cannot drift between layers.
- Run the focused test and Markdown lint after each logical task. Run the full
  repository verification set only after the complete library exists.
- Do not add the library to `catalog.yaml`, bootstrap behavior, generated agent
  configuration, native agent directories, or the engineering-standards
  projection.

## File Map

### Files to create

```text
assistants/shared/mechanistic-modeling/
├── README.md
├── data-layer.md
├── runtime-layer.md
├── composition-layer.md
└── validation-boundaries.md

docs/superpowers/specs/
└── 2026-07-31-plato-mechanistic-modeling-provenance.yaml

tests/assistants/
└── test_mechanistic_modeling.py
```

### Files to modify

```text
assistants/shared/agent-architecture/README.md
```

Add one informative sibling-library link and one sentence preserving the
authority boundary. Do not move, duplicate, or rewrite agent-architecture
contracts.

### Files to read, not modify

```text
../plato/src/plato/mechanistic_model/README.md
../plato/src/plato/crate/mechanistic_model/README.md
../plato/src/plato/mechanistic_model/INTEGRATION_STATUS.md
docs/superpowers/specs/2026-07-31-plato-mechanistic-modeling-design.md
tests/assistants/test_agent_architecture.py
docs/superpowers/specs/2026-07-31-plato-agent-architecture-provenance.yaml
```

## Library-Wide Contracts

### Terminology

The root document must preserve these definitions exactly after whitespace
normalization:

- a `MechanisticModel` is the complete structured artifact;
- an `Interaction` is a named process;
- a `Variable` is a quantity that may be changed, read, or observed;
- a `MathTerm` is one atomic contribution to one target equation;
- a `Block` groups related model content;
- a `Parameter` supplies a named quantity used by the mathematics;
- a `ConservationLaw` declares a conserved relationship;
- a `MechanisticModelComposer` assembles models and scenario data into one
  runnable system; and
- a `ModelSolution` carries named simulation results and derived diagnostics.

The PascalCase terms identify conceptual roles. They do not require matching
class names, methods, modules, languages, or runtime frameworks.

### Authority

- `mechanistic-modeling` owns model entities, evaluation, composition, solver
  boundaries, serialization, solutions, and validation layers.
- `agent-architecture` owns agents, Director/Act/Scene orchestration,
  delegation, handoffs, retry, persistence, and resume.
- An Act or Scene may author, validate, compose, simulate, or pass a versioned
  `MechanisticModel`, but the model library remains authoritative for the
  artifact's semantics.
- The library describes an approved target architecture. It must not present
  every target capability as verified current Plato behavior.

### Layer direction

The reader-facing package map is one-way:

```text
data layer -> runtime layer -> composition layer -> downstream consumers
```

- The data layer defines persistent model entities and their serialization.
- The runtime layer evaluates those entities and produces transient rates and
  diagnostics.
- The composition layer resolves complete runnable state, scenarios, solver
  boundaries, and durable results.
- Downstream interfaces consume the public composition boundary and do not
  redefine model semantics.

### Portability and privacy

Reader-facing documents must contain no:

- absolute local paths;
- Plato package paths, imports, or source-specific APIs;
- Jira, merge-request, commit, Notion, or internal URL identifiers;
- authentication, trust, session, local project, or generated plugin state;
- copied executable source-code blocks; or
- claims that a named Python class or package layout is required.

Internal source locators belong only in the provenance manifest.

## Provenance Contract

Use these exact top-level keys in this order:

```yaml
schema_version: 1
design: docs/superpowers/specs/2026-07-31-plato-mechanistic-modeling-design.md
source_repositories: []
design_sources: []
sources: []
verification_evidence: []
destinations: []
review: {}
```

### Source repositories and design sources

Record one source repository:

| ID | Revision | Reviewed on |
| --- | --- | --- |
| `plato` | `0fa63b144251ca6b5c6fa99b49151c7e5d5ae276` | `2026-07-31` |

Record these privacy-reviewed design-source locators:

| ID | Title | Locator |
| --- | --- | --- |
| `mechanistic-model-overview` | QSP Wizard Meets Mechanistic Model | `notion:364043d22fe38182b0c6c602c82079ae` |
| `mechanistic-model-data-layer` | Data Layer | `notion:364043d22fe381c18c90eefe537031b0` |
| `mechanistic-model-runtime-layer` | Runtime Layer | `notion:364043d22fe381f39e66d15b7fb143b0` |
| `mechanistic-model-composition-layer` | Composition Layer | `notion:364043d22fe381b09129fdb76ff3c818` |

Every design source uses `retrieved_on: 2026-07-31`. Store only the opaque
locator above, never the copied browser URL.

### Prose-source inventory

| ID | Kind | Source pointer | Authority | Disposition | Destinations |
| --- | --- | --- | --- | --- | --- |
| `overview-design` | `design_page` | `notion:364043d22fe38182b0c6c602c82079ae` | `target_design` | `adapt` | `index`, `data-layer`, `runtime-layer`, `composition-layer`, `validation-boundaries` |
| `data-layer-design` | `design_page` | `notion:364043d22fe381c18c90eefe537031b0` | `target_design` | `adapt` | `data-layer`, `validation-boundaries` |
| `runtime-layer-design` | `design_page` | `notion:364043d22fe381f39e66d15b7fb143b0` | `target_design` | `adapt` | `runtime-layer`, `validation-boundaries` |
| `composition-layer-design` | `design_page` | `notion:364043d22fe381b09129fdb76ff3c818` | `target_design` | `adapt` | `composition-layer`, `validation-boundaries` |
| `package-readme` | `repository_document` | `src/plato/mechanistic_model/README.md` | `package_contract` | `adapt` | `index`, `data-layer`, `runtime-layer`, `composition-layer`, `validation-boundaries` |
| `crate-readme` | `repository_document` | `src/plato/crate/mechanistic_model/README.md` | `corroboration` | `qualify` | `index`, `composition-layer` |

Use destination IDs `index`, `data-layer`, `runtime-layer`,
`composition-layer`, and `validation-boundaries`. Every source record also has
a concise `notes` value stating what was adapted, qualified, or excluded.
Design-page records use a privacy-reviewed `locator` and have no repository
path. Repository-document records use `repository: plato` plus a normalized
repository-relative `path` and have no internal locator. Every path is resolved
against the explicitly named repository, never the current shell directory.

### Verification evidence

Record these two evidence entries. The repository file uses a pinned path and
revision:

```yaml
id: integration-status
kind: repository_file
repository: plato
path: src/plato/mechanistic_model/INTEGRATION_STATUS.md
revision: 0fa63b144251ca6b5c6fa99b49151c7e5d5ae276
claim: Target architecture must not be presented as complete current integration.
```

The work item uses an opaque locator and its actual review date:

```yaml
id: agtc-1038-status
kind: work_item
locator: jira:AGTC-1038
reviewed_on: 2026-07-31
claim: Delivery and dependency status must not become generic architecture wording.
```

Both entries check status boundaries only. Neither is a source of
reader-facing wording, and neither has a destination.

### Destination inventory

| ID | Path | Kind | Primary source |
| --- | --- | --- | --- |
| `index` | `assistants/shared/mechanistic-modeling/README.md` | `index` | `overview-design` |
| `data-layer` | `assistants/shared/mechanistic-modeling/data-layer.md` | `layer` | `data-layer-design` |
| `runtime-layer` | `assistants/shared/mechanistic-modeling/runtime-layer.md` | `layer` | `runtime-layer-design` |
| `composition-layer` | `assistants/shared/mechanistic-modeling/composition-layer.md` | `layer` | `composition-layer-design` |
| `validation-boundaries` | `assistants/shared/mechanistic-modeling/validation-boundaries.md` | `validation` | `overview-design` |

Every destination uses `authority: conceptual_contract`, a list of source
records with one `primary` role and zero or more `supporting` roles, a
`transformation` note, an `exclusions` list, and `semantic_review` plus
`privacy_review` statuses. Start both statuses as `pending`; Task 7 changes
them to `passed` after fresh review.

Use this exact destination-to-source role map:

| Destination | Primary | Supporting |
| --- | --- | --- |
| `index` | `overview-design` | `package-readme`, `crate-readme` |
| `data-layer` | `data-layer-design` | `overview-design`, `package-readme` |
| `runtime-layer` | `runtime-layer-design` | `overview-design`, `package-readme` |
| `composition-layer` | `composition-layer-design` | `overview-design`, `package-readme`, `crate-readme` |
| `validation-boundaries` | `overview-design` | `data-layer-design`, `runtime-layer-design`, `composition-layer-design`, `package-readme` |

The top-level review starts as:

```yaml
review:
  portability: portable_after_adaptation
  semantic: pending
  privacy: pending
  approved_on: null
```

## Task 0: Reconfirm the read-only source boundary

**Files:**

- Read: `../plato/src/plato/mechanistic_model/README.md`
- Read: `../plato/src/plato/crate/mechanistic_model/README.md`
- Read: `../plato/src/plato/mechanistic_model/INTEGRATION_STATUS.md`
- Read: `docs/superpowers/specs/2026-07-31-plato-mechanistic-modeling-design.md`
- Read: Notion page `QSP Wizard Meets Mechanistic Model`
- Read: Notion companion pages `Data Layer`, `Runtime Layer`, and
  `Composition Layer`
- Read: Jira work item `AGTC-1038`

- [ ] From `ballen-config`, confirm the destination working copy is clean:

  ```bash
  rtk jj status
  ```

  Expected: `The working copy has no changes.` This assumes the plan has
  already been recorded and `jj new` created a clean implementation change. If
  it is dirty, inspect and preserve every unrelated user change before
  proceeding.

- [ ] Record Plato's current status without modifying it:

  ```bash
  rtk jj --repository ../plato status
  ```

  Expected: no changes. If unrelated changes exist, preserve them and continue
  only when none overlap the reviewed source paths.

- [ ] Verify the reviewed paths still match the pinned revision:

  ```bash
  rtk jj --repository ../plato diff --from 0fa63b144251ca6b5c6fa99b49151c7e5d5ae276 --to @ --summary 'root:src/plato/mechanistic_model' 'root:src/plato/crate/mechanistic_model/README.md'
  ```

  Expected: no output. If a reviewed path appears, stop and revise the design
  and plan against the changed source.

- [ ] Re-read the three local source documents from the pinned revision with
  these exact commands. Do not substitute the mutable working tree or create a
  Plato commit:

  ```bash
  rtk jj --repository ../plato file show -r 0fa63b144251ca6b5c6fa99b49151c7e5d5ae276 'root:src/plato/mechanistic_model/README.md'
  rtk jj --repository ../plato file show -r 0fa63b144251ca6b5c6fa99b49151c7e5d5ae276 'root:src/plato/crate/mechanistic_model/README.md'
  rtk jj --repository ../plato file show -r 0fa63b144251ca6b5c6fa99b49151c7e5d5ae276 'root:src/plato/mechanistic_model/INTEGRATION_STATUS.md'
  ```

- [ ] Through the configured Notion and Jira connectors, re-read the four
  canonical design pages and AGTC-1038. Confirm their titles, authority roles,
  and current status still agree with the approved design. Record the actual
  retrieval dates. If a source is inaccessible or materially changed, stop and
  update the design before drafting reader prose; do not silently substitute a
  cached summary.

- [ ] Confirm the approved design still names exactly five destination
  documents and the nine normative terms before writing any reader prose.

## Task 1: Establish the provenance contract and typed test harness

**Files:**

- Create: `docs/superpowers/specs/2026-07-31-plato-mechanistic-modeling-provenance.yaml`
- Create: `tests/assistants/test_mechanistic_modeling.py`
- Reference: `tests/assistants/test_agent_architecture.py`

- [ ] Start `tests/assistants/test_mechanistic_modeling.py` with typed manifest
  shapes and fixed inventories:

  ```python
  """Contract tests for the shared mechanistic-modeling reference library."""

  import re
  from pathlib import Path, PurePosixPath
  from typing import Literal, NotRequired, TypedDict, cast

  import pytest
  import yaml

  SOURCE_REVISION = "0fa63b144251ca6b5c6fa99b49151c7e5d5ae276"  # pragma: allowlist secret
  REVIEW_DATE = "2026-07-31"
  APPROVED_DESIGN = (
      "docs/superpowers/specs/"
      "2026-07-31-plato-mechanistic-modeling-design.md"
  )
  PROVENANCE_MANIFEST = Path(
      "docs/superpowers/specs/"
      "2026-07-31-plato-mechanistic-modeling-provenance.yaml"
  )
  LIBRARY_ROOT = Path("assistants/shared/mechanistic-modeling")

  SourceKind = Literal["repository_document", "design_page"]
  SourceAuthority = Literal[
      "target_design",
      "package_contract",
      "corroboration",
  ]
  Disposition = Literal["adapt", "qualify", "exclude", "verify_only"]
  DocumentKind = Literal["index", "layer", "validation"]
  SourceRole = Literal["primary", "supporting"]
  ReviewStatus = Literal["pending", "passed"]

  class SourceRepository(TypedDict):
      """One pinned source repository."""

      id: str
      revision: str
      reviewed_on: str

  class DesignSource(TypedDict):
      """One privacy-reviewed internal design source."""

      id: str
      title: str
      retrieved_on: str
      locator: str

  class SourceRecord(TypedDict):
      """One prose source and its extraction disposition."""

      id: str
      kind: SourceKind
      repository: NotRequired[str]
      path: NotRequired[str]
      locator: NotRequired[str]
      authority: SourceAuthority
      disposition: Disposition
      destinations: list[str]
      notes: str

  class RepositoryEvidence(TypedDict):
      """One pinned repository file used only for verification."""

      id: str
      kind: Literal["repository_file"]
      repository: str
      path: str
      revision: str
      claim: str

  class WorkItemEvidence(TypedDict):
      """One reviewed work item used only for status verification."""

      id: str
      kind: Literal["work_item"]
      locator: str
      reviewed_on: str
      claim: str

  VerificationEvidence = RepositoryEvidence | WorkItemEvidence

  class DestinationSource(TypedDict):
      """One source's role in one destination."""

      id: str
      role: SourceRole

  class DestinationRecord(TypedDict):
      """Audit metadata for one reader-facing document."""

      id: str
      path: str
      kind: DocumentKind
      authority: Literal["conceptual_contract"]
      sources: list[DestinationSource]
      transformation: str
      exclusions: list[str]
      semantic_review: ReviewStatus
      privacy_review: ReviewStatus

  class ReviewRecord(TypedDict):
      """Program-level review result."""

      portability: Literal["portable_after_adaptation"]
      semantic: ReviewStatus
      privacy: ReviewStatus
      approved_on: str | None

  class ProvenanceManifest(TypedDict):
      """Complete extraction provenance manifest."""

      schema_version: int
      design: str
      source_repositories: list[SourceRepository]
      design_sources: list[DesignSource]
      sources: list[SourceRecord]
      verification_evidence: list[VerificationEvidence]
      destinations: list[DestinationRecord]
      review: ReviewRecord
  ```

- [ ] Define all test helpers locally in this module; do not import helpers from
  `test_agent_architecture.py`. Add `load_provenance()` using `yaml.safe_load`,
  `assert_relative_posix_path()` rejecting empty, absolute, backslash, `.`, and
  `..` paths, `index_by_id()` rejecting duplicate IDs, `read_document()` rooted
  at `LIBRARY_ROOT`, `local_markdown_targets()` excluding web, mail, and anchor
  links, and `assert_document_shape()` requiring one H1 with no frontmatter.

- [ ] Add a failing test for the exact eight top-level keys, approved design,
  source revision, and initial review state:

  ```python
  def test_provenance_records_fixed_program_metadata(repo_root: Path) -> None:
      """Pin the approved design and reviewed source snapshot."""
      manifest = load_provenance(repo_root)
      assert list(manifest) == [
          "schema_version",
          "design",
          "source_repositories",
          "design_sources",
          "sources",
          "verification_evidence",
          "destinations",
          "review",
      ]
      assert manifest["schema_version"] == 1
      assert manifest["design"] == APPROVED_DESIGN
      assert manifest["source_repositories"] == [
          {
              "id": "plato",
              "revision": SOURCE_REVISION,
              "reviewed_on": REVIEW_DATE,
          }
      ]
      assert manifest["review"] == {
          "portability": "portable_after_adaptation",
          "semantic": "pending",
          "privacy": "pending",
          "approved_on": None,
      }
  ```

- [ ] Run the focused test and confirm the intended failure:

  ```bash
  rtk uv run --frozen pytest tests/assistants/test_mechanistic_modeling.py -q
  ```

  Expected: failure because the provenance manifest does not exist.

- [ ] Create the manifest from the complete provenance contract above. Use
  full sentences for every source note, destination transformation, exclusion,
  and evidence claim. Do not use placeholder text.

- [ ] Add tests that enforce:

    - all source, design-source, evidence, and destination IDs are unique;
    - the exact six prose sources, two evidence entries, and five destinations
    exist;
    - every repository and destination path is normalized, relative, and
    interpreted against its explicitly named repository;
    - design-page sources have one `notion:` locator and no repository path;
    - repository-document sources have one repository/path pair and no locator;
    - work-item evidence has one `jira:` locator and review date;
    - repository-file evidence has one repository/path/revision tuple;
    - every prose source has at least one destination;
        - every destination source ID exists and has exactly one `primary` role;
        - destination source roles agree with each source's destination list; and
        - verification evidence is not reused as prose-source wording.

- [ ] Run focused tests and Ruff:

  ```bash
  rtk uv run --frozen pytest tests/assistants/test_mechanistic_modeling.py -q
  rtk uv run --frozen ruff check tests/assistants/test_mechanistic_modeling.py
  ```

  Expected: both commands exit zero.

- [ ] Record the provenance contract as one logical Jujutsu change:

  ```bash
  rtk jj describe -m "test: define mechanistic modeling provenance contract"
  rtk jj new
  ```

## Task 2: Add the library frame, exact terminology, and sibling cross-links

**Files:**

- Create: `assistants/shared/mechanistic-modeling/README.md`
- Create: `assistants/shared/mechanistic-modeling/data-layer.md`
- Create: `assistants/shared/mechanistic-modeling/runtime-layer.md`
- Create: `assistants/shared/mechanistic-modeling/composition-layer.md`
- Create: `assistants/shared/mechanistic-modeling/validation-boundaries.md`
- Modify: `assistants/shared/agent-architecture/README.md`
- Modify: `tests/assistants/test_mechanistic_modeling.py`

- [ ] Add the expected tree, Markdown-link parser, whitespace normalizer, and
  exact terminology definitions to the test module:

  ```python
  EXPECTED_DOCUMENTS = {
      "README.md",
      "data-layer.md",
      "runtime-layer.md",
      "composition-layer.md",
      "validation-boundaries.md",
  }

  TERMINOLOGY_DEFINITIONS = (
      "a `MechanisticModel` is the complete structured artifact;",
      "an `Interaction` is a named process;",
      "a `Variable` is a quantity that may be changed, read, or observed;",
      "a `MathTerm` is one atomic contribution to one target equation;",
      "a `Block` groups related model content;",
      "a `Parameter` supplies a named quantity used by the mathematics;",
      "a `ConservationLaw` declares a conserved relationship;",
      "a `MechanisticModelComposer` assembles models and scenario data "
      "into one runnable system; and",
      "a `ModelSolution` carries named simulation results and derived "
      "diagnostics.",
  )

  def normalize_whitespace(value: str) -> str:
      """Collapse layout whitespace for exact prose-contract checks."""
      return " ".join(value.split())

  @pytest.mark.parametrize("definition", TERMINOLOGY_DEFINITIONS)
  def test_root_preserves_exact_terminology(
      repo_root: Path,
      definition: str,
  ) -> None:
      """Keep approved terms and definitions stable across line wrapping."""
      text = normalize_whitespace(read_document(repo_root, "README.md"))
      assert definition in text
  ```

- [ ] Add failing tests for:

    - the exact five regular files, with no symlinks or special files;
    - one H1 per document and no YAML frontmatter;
    - each child linked exactly once from `README.md`;
    - every relative Markdown link resolving to a regular file;
    - each exact terminology definition appearing after whitespace
    normalization;
    - the headings `Authority and Scope`, `Terminology`, `Layer Map`, `Package
    Mechanics`, `Relationship to Agent Architecture`, and `Reading Order`;
    - a link from mechanistic modeling to `../agent-architecture/README.md`; and
    - a reciprocal link from agent architecture to
    `../mechanistic-modeling/README.md`.

  Exact prose matching is intentionally limited to the nine user-approved
  normative definitions. Later tests enforce stable structure and vocabulary;
  Task 7's semantic review evaluates explanatory meaning without freezing
  ordinary editorial sentences.

- [ ] Run the focused tests and confirm they fail because the library does not
  exist:

  ```bash
  rtk uv run --frozen pytest tests/assistants/test_mechanistic_modeling.py -q
  ```

- [ ] Write `README.md` in plain technical prose. Include:

  1. a passive-reference statement and the target-versus-current status
     boundary;
  2. the nine exact definitions, followed by a plain-language explanation that
     the names describe roles rather than code APIs;
  3. the one-way data, runtime, composition, and downstream layer map;
  4. package mechanics: each layer owns its persistent artifacts, runtime
     objects stay transient, a thin public facade may re-export stable concepts,
     and optional integrations point outward;
  5. the five-document library map and reading order; and
  6. the non-owning relationship to agent architecture.

- [ ] Create each child file with its final H1, an authority statement, and a
  concise scope paragraph. These are valid document frames, not `TODO` stubs:

  ```text
  # Data Layer
  # Runtime Layer
  # Composition Layer
  # Validation Boundaries
  ```

  Each scope paragraph states what the layer owns and explicitly names the
  adjacent responsibility it does not own.

- [ ] Add a `Related Reference Library` section to
  `assistants/shared/agent-architecture/README.md`. Link to the mechanistic
  library and state that agent architecture owns orchestration while the
  sibling library owns mechanistic-model semantics and numerical execution
  boundaries.

- [ ] Run focused tests and Markdown lint:

  ```bash
  rtk uv run --frozen pytest tests/assistants/test_mechanistic_modeling.py -q
  rtk uv run --frozen ruff check tests/assistants/test_mechanistic_modeling.py
  rtk npx --no-install markdownlint-cli2 --config assistants/shared/standards/templates/python/.markdownlint.json "assistants/shared/mechanistic-modeling/*.md" assistants/shared/agent-architecture/README.md
  ```

  Expected: all commands exit zero.

- [ ] Record the library frame:

  ```bash
  rtk jj describe -m "docs: add mechanistic modeling reference frame"
  rtk jj new
  ```

## Task 3: Explain the data layer and serialization boundary

**Files:**

- Modify: `assistants/shared/mechanistic-modeling/data-layer.md`
- Modify: `tests/assistants/test_mechanistic_modeling.py`

- [ ] Add a failing semantic contract test:

  ```python
  def test_data_layer_preserves_model_semantics(repo_root: Path) -> None:
      """Keep persistent entities and variable roles explicit."""
      text = read_document(repo_root, "data-layer.md")
      for heading in (
          "## Process-Centered Model",
          "## Targeted and External Variables",
          "## Atomic `MathTerm` Contributions",
          "## `Block`, `Parameter`, and `ConservationLaw`",
          "## Entity Provenance",
          "## Serialization",
          "## Construction Boundary",
      ):
          assert heading in text

      for term in (
          "`MechanisticModel`",
          "`Interaction`",
          "`Variable`",
          "`MathTerm`",
          "`Block`",
          "`Parameter`",
          "`ConservationLaw`",
      ):
          assert term in text

      lowered = text.lower()
      for concept in (
          "targeted variables",
          "external variables",
          "derived equations",
          "variable registry",
          "parameter registry",
          "schema version",
          "entity provenance",
          "extraction provenance",
      ):
          assert concept in lowered
  ```

- [ ] Run the single test and confirm the intended failure:

  ```bash
  rtk uv run --frozen pytest tests/assistants/test_mechanistic_modeling.py::test_data_layer_preserves_model_semantics -q
  ```

- [ ] Complete `data-layer.md` with these sections and contracts:

    - A `MechanisticModel` is process-centered: named `Interaction` objects
    contribute change to named `Variable` objects.
    - Targeted variables receive one or more contributions. External variables
    are read by the model but resolved outside that model during composition.
    - No `Interaction` or constituent model receives false exclusive ownership
    of a shared `Variable`.
    - A `MathTerm` is atomic: one expression, one target equation, stable identity,
    units, and optional provenance. Additive behavior comes from collecting
    terms, not hiding several contributions inside one term.
    - Topology and mathematics remain separate: a relationship can carry a
    weight or direction without rewriting its stored mathematical expression.
    - `Block`, `Parameter`, and `ConservationLaw` retain their exact meanings and
    do not silently alter interaction semantics.
    - Entity provenance belongs to scientific entities; extraction provenance
    belongs to this documentation program.
    - Equations, topology, variable registries, and parameter registries are
    derived views of the canonical model, not independent wiring authorities.
    - Serialization preserves durable entities, stable identities, units,
    mathematical representations, topology, scientific provenance, and a
    schema version or equivalent compatibility marker. It never persists a
    second equation object or generated executable as another authority.
    - Scenario-specific parameter values, authoritative initial conditions,
    solver settings, compiled evaluators, callbacks, caches, open resources,
    and live solver objects remain outside `MechanisticModel` identity.
        - Construction validates local artifact shape only. Cross-model coverage,
    scenario resolution, and solver readiness belong to later boundaries.

- [ ] Use no code blocks, concrete class signatures, framework names, or Plato
  paths. Examples must be prose examples such as a transfer, conversion, or
  regulatory process.

- [ ] Review targeted/external meaning, non-ownership, atomicity, and
  persistence authority semantically in Task 7. Do not add more exact-sentence
  assertions for those editorial explanations.

- [ ] Run focused tests and Markdown lint:

  ```bash
  rtk uv run --frozen pytest tests/assistants/test_mechanistic_modeling.py -q
  rtk uv run --frozen ruff check tests/assistants/test_mechanistic_modeling.py
  rtk npx --no-install markdownlint-cli2 --config assistants/shared/standards/templates/python/.markdownlint.json assistants/shared/mechanistic-modeling/data-layer.md
  ```

- [ ] Record the data-layer change:

  ```bash
  rtk jj describe -m "docs: explain mechanistic model data layer"
  rtk jj new
  ```

## Task 4: Explain evaluator and runtime mechanics

**Files:**

- Modify: `assistants/shared/mechanistic-modeling/runtime-layer.md`
- Modify: `tests/assistants/test_mechanistic_modeling.py`

- [ ] Add a failing semantic contract test:

  ```python
  def test_runtime_layer_separates_evaluation_from_solving(repo_root: Path) -> None:
      """Define deterministic term evaluation and transient runtime state."""
      text = read_document(repo_root, "runtime-layer.md")
      for heading in (
          "## Evaluator Responsibility",
          "## Restricted Mathematical Expressions",
          "## Determinism and Identity",
          "## Rate Accumulation and Ledger",
          "## Runtime Failures",
          "## Transient Runtime State",
      ):
          assert heading in text

      for term in ("`MechanisticModel`", "`MathTerm`", "`Variable`"):
          assert term in text

      lowered = text.lower()
      for concept in (
          "one point in time",
          "per-variable change map",
          "named rate ledger",
          "restricted mathematical expressions",
          "topology weights",
          "transient runtime state",
      ):
          assert concept in lowered
  ```

- [ ] Run the single test and confirm it fails against the document frame:

  ```bash
  rtk uv run --frozen pytest tests/assistants/test_mechanistic_modeling.py::test_runtime_layer_separates_evaluation_from_solving -q
  ```

- [ ] Complete `runtime-layer.md` with these responsibilities:

    - The evaluator accepts one complete `MechanisticModel` at one point in time,
    current variable values, and required parameter or constant values.
    - Evaluating each atomic `MathTerm` is an internal step. For each term, the
    evaluator computes a magnitude, records its stable named contribution,
    applies topology for the target, and accumulates the weighted contribution.
    - Model-level outputs are both a per-variable change map and a named rate
    ledger. The change map drives integration; the ledger supports diagnostics,
    conservation analysis, documentation, and diagrams without becoming a
    second wiring mechanism.
        - Mathematical expressions use a restricted, inspectable vocabulary. The
    prose explains the safety and reproducibility boundary without prescribing
    a parser, programming language, or source API.
        - Stable term identity ties rates and diagnostics back to persistent model
    entities.
        - Runtime evaluation applies topology weights and additively accumulates
    contributions per targeted `Variable`.
        - A named rate ledger retains per-term contributions before aggregation so
    diagnostics do not require reverse-engineering a total derivative.
        - Missing names, incompatible values, unsupported expressions, and non-finite
    results fail explicitly with term and target context.
        - The evaluator does not own time integration, event segmentation, scenario
    construction, or scientific validation.
    - Compiled representations and caches may improve execution but are
    transient and reconstructible from persistent model data.

- [ ] Review model-level evaluator inputs and outputs, deterministic naming,
  term-level attribution, and evaluator-versus-solver ownership semantically in
  Task 7. Do not freeze those explanations as exact sentences.

- [ ] Run focused tests and Markdown lint:

  ```bash
  rtk uv run --frozen pytest tests/assistants/test_mechanistic_modeling.py -q
  rtk uv run --frozen ruff check tests/assistants/test_mechanistic_modeling.py
  rtk npx --no-install markdownlint-cli2 --config assistants/shared/standards/templates/python/.markdownlint.json assistants/shared/mechanistic-modeling/runtime-layer.md
  ```

- [ ] Record the runtime-layer change:

  ```bash
  rtk jj describe -m "docs: explain mechanistic model runtime layer"
  rtk jj new
  ```

## Task 5: Explain composition, solver, and solution mechanics

**Files:**

- Modify: `assistants/shared/mechanistic-modeling/composition-layer.md`
- Modify: `tests/assistants/test_mechanistic_modeling.py`

- [ ] Add a failing semantic contract test:

  ```python
  def test_composition_layer_defines_one_runnable_path(repo_root: Path) -> None:
      """Keep composition, scenarios, solving, and results distinct."""
      text = read_document(repo_root, "composition-layer.md")
      for heading in (
          "## `MechanisticModelComposer`",
          "## Composition Validation",
          "## Scenario Boundary",
          "## Solver Boundary",
          "## Events and Interventions",
          "## One Composition Path",
          "## `ModelSolution`",
          "## Composition Serialization",
      ):
          assert heading in text

      for term in (
          "`MechanisticModelComposer`",
          "`MechanisticModel`",
          "`Variable`",
          "`Parameter`",
          "`ConservationLaw`",
          "`ModelSolution`",
      ):
          assert term in text

      lowered = text.lower()
      for concept in (
          "targeted state",
          "external-only",
          "peer model",
          "scenario input",
          "natural sum",
          "conflicting defaults",
          "initial-condition override",
          "same composition path",
          "independently interpretable",
          "reproducibility bundle",
      ):
          assert concept in lowered
  ```

- [ ] Run the single test and confirm it fails against the document frame:

  ```bash
  rtk uv run --frozen pytest tests/assistants/test_mechanistic_modeling.py::test_composition_layer_defines_one_runnable_path -q
  ```

- [ ] Complete `composition-layer.md` with these contracts:

    - `MechanisticModelComposer` is the conceptual boundary that combines one or
    more `MechanisticModel` artifacts with scenario data into one runnable
    system. It does not imply a required class or method.
    - The union of targeted variables forms solver state. Variables that are only
    read remain explicit exogenous inputs; they are never silently promoted to
    state or hidden in a closure.
    - Composition validates shared variable identity, external-variable
    coverage, parameter coverage, and initial conditions before numerical
    integration. Every external read resolves from a compatible peer model or
    a declared scenario input. An initial-condition override never satisfies
    an external read.
    - Multiple models may target the same `Variable`; the composed change is the
    natural sum of all contributions. The composer also aggregates compatible
    `ConservationLaw` declarations and diagnostic metadata.
    - Initial conditions never receive a silent numerical default. A domain
    policy may supply one only when that policy is explicit, inspectable, and
    recorded with the run specification.
    - Default precedence is deterministic and documented. Explicit scenario
    values override compatible declared defaults; conflicting defaults without
    an explicit precedence rule fail composition.
    - Scenario values may change while stable `Parameter` identity, units,
    description, and provenance remain unchanged. Interventions and solver
    settings configure a run but do not rewrite persistent model identity.
        - The solver repeatedly requests combined per-variable change and owns time
    grids, numerical integration, event boundaries, discontinuity handling,
    restarts, and numerical diagnostics.
        - One-model and multi-model runs pass through identical validation,
    composition, solver, and diagnostic boundaries.
    - `ModelSolution` contains sampled times, named state trajectories and units,
    stable state ordering or identity, applied interventions, solver outcome
    metadata, model and composition identities with schema versions, resolved
    initial conditions, parameters, and scenario inputs or immutable
    integrity-checked references, and runtime compatibility information.
    - A serialized `ModelSolution` remains independently interpretable. It is not
    necessarily rerunnable: a reproducibility bundle additionally contains or
    immutably references every versioned model, complete composition and
    scenario specification, resolved input, intervention, solver setting,
    compatible runtime, and integrity record required to repeat the run.
    - Composition serialization stores selected model identities, parameter
    values, complete scenario defaults, interventions, initial conditions, and
    relevant solver configuration. It excludes live callbacks, caches, solver
    instances, closures, and open resources.

- [ ] Review additive shared-target behavior, external resolution, default
  precedence, stable parameter identity, one-path execution, independent
  solution interpretation, and solution-versus-bundle meaning semantically in
  Task 7. Do not freeze those explanations as exact sentences.

- [ ] Run focused tests and Markdown lint:

  ```bash
  rtk uv run --frozen pytest tests/assistants/test_mechanistic_modeling.py -q
  rtk uv run --frozen ruff check tests/assistants/test_mechanistic_modeling.py
  rtk npx --no-install markdownlint-cli2 --config assistants/shared/standards/templates/python/.markdownlint.json assistants/shared/mechanistic-modeling/composition-layer.md
  ```

- [ ] Record the composition-layer change:

  ```bash
  rtk jj describe -m "docs: explain mechanistic model composition layer"
  rtk jj new
  ```

## Task 6: Define layered validation and representative failures

**Files:**

- Modify: `assistants/shared/mechanistic-modeling/validation-boundaries.md`
- Modify: `tests/assistants/test_mechanistic_modeling.py`

- [ ] Add a failing test that requires the five validation boundaries in this
  order:

  ```python
  def test_validation_boundaries_are_ordered_and_distinct(repo_root: Path) -> None:
      """Assign each failure to the earliest responsible boundary."""
      text = read_document(repo_root, "validation-boundaries.md")
      headings = (
          "## Data Construction",
          "## Composition",
          "## Runtime Evaluation",
          "## Solver",
          "## Scientific Review",
      )
      positions = [text.index(heading) for heading in headings]
      assert positions == sorted(positions)

      for failure in (
          "duplicate stable identity",
          "invalid target",
          "compound term",
          "unknown block",
          "unresolved external variable",
          "missing parameter",
          "missing initial condition",
          "incompatible shared variables",
          "ambiguous namespace",
          "unknown mathematical name",
          "invalid expression",
          "non-finite contribution",
          "invalid event boundary",
          "integration cannot complete reliably",
          "unstable trajectory",
          "unit mismatch",
          "conservation residual",
          "impossible state",
          "scientifically implausible result",
          "diagnostic context",
      ):
          assert failure in text
  ```

- [ ] Run the single test and confirm it fails against the document frame:

  ```bash
  rtk uv run --frozen pytest tests/assistants/test_mechanistic_modeling.py::test_validation_boundaries_are_ordered_and_distinct -q
  ```

- [ ] Complete `validation-boundaries.md` with one responsibility table and one
  section for each boundary:

  1. Data construction checks local shape, stable identities, references,
     units, expression form, and serializability.
  2. Composition checks cross-model compatibility, targeted-state union,
     external and parameter resolution, initial conditions, scenarios, and
     intervention readiness.
  3. Runtime evaluation checks name resolution, supported mathematical
     operations, value compatibility, and finite per-term contributions.
  4. Solver validation checks numerical configuration, integration progress,
     event handling, tolerances, and reliable completion.
  5. Scientific review checks conservation expectations, dimensions,
     plausibility, calibration, sensitivity, and fitness for the intended use.

  State that a later layer may add diagnostic context but must not silently
  repair an earlier invalid artifact, and that passing one layer never implies
  passing a later layer. Show each required failure label in the table at its
  earliest responsible boundary.

- [ ] Run focused tests and Markdown lint:

  ```bash
  rtk uv run --frozen pytest tests/assistants/test_mechanistic_modeling.py -q
  rtk uv run --frozen ruff check tests/assistants/test_mechanistic_modeling.py
  rtk npx --no-install markdownlint-cli2 --config assistants/shared/standards/templates/python/.markdownlint.json assistants/shared/mechanistic-modeling/validation-boundaries.md
  ```

- [ ] Record the validation-layer change:

  ```bash
  rtk jj describe -m "docs: define mechanistic model validation boundaries"
  rtk jj new
  ```

## Task 7: Enforce portability, complete provenance, and verify the program

**Files:**

- Modify: `tests/assistants/test_mechanistic_modeling.py`
- Modify: `docs/superpowers/specs/2026-07-31-plato-mechanistic-modeling-provenance.yaml`
- Review: `assistants/shared/mechanistic-modeling/*.md`
- Review: `assistants/shared/agent-architecture/README.md`
- Verify unchanged: `../plato/src/plato/mechanistic_model/`
- Verify unchanged: `../plato/src/plato/crate/mechanistic_model/README.md`

- [ ] Add a library-wide privacy and implementation-neutrality test:

  ```python
  FORBIDDEN_READER_PATTERNS = (
      re.compile(r"/Users/"),
      re.compile(r"(?<!\w)/(?:home|private|tmp|var|opt)/", re.IGNORECASE),
      re.compile(r"[A-Za-z]:\\"),
      re.compile(r"src/plato/", re.IGNORECASE),
      re.compile(r"\b(?:from|import)\s+plato\b", re.IGNORECASE),
      re.compile(
          r"\b(?:Plato|AMi|Avogadro|QSP Autopilot|QSP|PK/PD|TMDD)\b",
          re.IGNORECASE,
      ),
      re.compile(r"\bAGTC-\d+\b"),
      re.compile(r"flagshippioneering\.atlassian\.net", re.IGNORECASE),
      re.compile(r"(?:app\.)?notion\.com", re.IGNORECASE),
      re.compile(r"gitlab\.com", re.IGNORECASE),
      re.compile(r"\bMR\s*!?\d+\b", re.IGNORECASE),
      re.compile(r"\bmerge request\b", re.IGNORECASE),
      re.compile(r"\bcommit\s+[0-9a-f]{7,40}\b", re.IGNORECASE),
      re.compile(r"\bbranch\s+[A-Za-z0-9._/-]+\b", re.IGNORECASE),
      re.compile(r"notion:[0-9a-f]+", re.IGNORECASE),
      re.compile(
          r"\b(?:credentials?|authentication|access tokens?|session history|"
          r"generated plugin state)\b",
          re.IGNORECASE,
      ),
      re.compile(r"```(?:python|py|javascript|typescript|bash|shell)?\s*\n"),
  )

  def test_reader_documents_are_portable_and_prose_only(repo_root: Path) -> None:
      """Exclude internal locators, copied code, and local state."""
      reader_paths = [LIBRARY_ROOT / path for path in EXPECTED_DOCUMENTS]
      reader_paths.append(Path("assistants/shared/agent-architecture/README.md"))
      for relative_path in reader_paths:
          text = (repo_root / relative_path).read_text(encoding="utf-8")
          for pattern in FORBIDDEN_READER_PATTERNS:
              assert pattern.search(text) is None, (
                  f"{relative_path} contains prohibited content: {pattern.pattern}"
              )
  ```

- [ ] Add tests that verify:

    - the package direction appears in README in data, runtime, composition, and
    downstream order;
    - evaluator, solver, serialization, and package mechanics each appear in a
    reader-facing heading or explicit responsibility statement;
    - persistent artifacts are distinguished from transient evaluators, caches,
    callbacks, and live solver objects;
    - scenario data is distinguished from `MechanisticModel` identity;
    - the agent and model libraries cross-link once without duplicating each
    other's terminology definitions;
    - every manifest destination path matches exactly one regular library file;
    and
    - all destination and top-level review statuses are `passed` with
    `approved_on: 2026-07-31`.

- [ ] Run the focused tests. Confirm the review-status test fails while the
  manifest is still pending:

  ```bash
  rtk uv run --frozen pytest tests/assistants/test_mechanistic_modeling.py -q
  ```

- [ ] Perform the inline semantic self-review before asking subagents:

    - Map every goal, non-goal, source disposition, and success criterion in the
    approved design to a destination paragraph or test.
    - Search for placeholder text, copied implementation names, ticket IDs,
    internal links, absolute paths, and framework assumptions.
    - Verify each of the nine terms retains one distinct meaning in every file.
    - Verify targeted and external variables remain distinct without introducing
    model ownership.
    - Verify evaluator and solver responsibilities do not overlap.
    - Verify data, composition, runtime, solver, and scientific validation remain
    separate.
    - Verify serialization excludes transient runtime state at both data and
    composition boundaries.
    - Verify one-model and multi-model execution use the same path.
    - Verify target design is not described as complete current behavior.

- [ ] Dispatch two independent read-only Luna extra-high reviewers in parallel:

  1. A terminology and specification reviewer maps every approved definition,
     layer responsibility, and source disposition to exact file and line
     references.
  2. A portability reviewer checks for source-code leakage, internal project
     details, false current-state claims, cross-library authority drift,
     unresolved links, and sensitive state.

  Ask each reviewer for findings only, with severity and exact file/line
  evidence. Do not let either reviewer edit files.

- [ ] Resolve every confirmed finding inline. Re-run the focused pytest and
  Markdownlint commands after each correction group.

- [ ] Change all destination `semantic_review` and `privacy_review` values to
  `passed`, then update the top-level review:

  ```yaml
  review:
    portability: portable_after_adaptation
    semantic: passed
    privacy: passed
    approved_on: 2026-07-31
  ```

- [ ] Invoke `superpowers:verification-before-completion`, then run the complete
  repository verification set from fresh processes:

  ```bash
  rtk uv run --frozen pytest tests/assistants/test_mechanistic_modeling.py -q
  rtk uv run --frozen pytest -q
  rtk uv run --frozen ruff check .
  rtk uv run --frozen mypy
  rtk uv run --frozen pre-commit run --files \
    assistants/shared/mechanistic-modeling/README.md \
    assistants/shared/mechanistic-modeling/data-layer.md \
    assistants/shared/mechanistic-modeling/runtime-layer.md \
    assistants/shared/mechanistic-modeling/composition-layer.md \
    assistants/shared/mechanistic-modeling/validation-boundaries.md \
    assistants/shared/agent-architecture/README.md \
    docs/superpowers/specs/2026-07-31-plato-mechanistic-modeling-design.md \
    docs/superpowers/specs/2026-07-31-plato-mechanistic-modeling-provenance.yaml \
    docs/superpowers/plans/2026-07-31-plato-mechanistic-modeling.md \
    tests/assistants/test_mechanistic_modeling.py
  rtk npx --no-install markdownlint-cli2 --config assistants/shared/standards/templates/python/.markdownlint.json "assistants/shared/mechanistic-modeling/*.md" assistants/shared/agent-architecture/README.md docs/superpowers/specs/2026-07-31-plato-mechanistic-modeling-design.md
  rtk npx --no-install markdownlint-cli2 --config assistants/shared/standards/templates/python/.markdownlint.json docs/superpowers/plans/2026-07-31-plato-mechanistic-modeling.md
  ```

  Expected: every command exits zero. Report the fresh test count rather than
  predicting it in this plan.

- [ ] Reconfirm Plato remained unchanged at the reviewed paths:

  ```bash
  rtk jj --repository ../plato diff --from 0fa63b144251ca6b5c6fa99b49151c7e5d5ae276 --to @ --summary 'root:src/plato/mechanistic_model' 'root:src/plato/crate/mechanistic_model/README.md'
  rtk jj --repository ../plato status
  ```

  Expected: the focused diff has no output and the working copy remains clean.
  Never remove or rewrite unrelated Plato changes if the status differs.

- [ ] Inspect the complete `ballen-config` range and Markdown-only diff:

  ```bash
  rtk jj diff --from xxsylskr --to @ --summary
  rtk jj diff --from xxsylskr --to @ --stat
  rtk jj status
  ```

  Expected: only this plan, the provenance manifest, the five-document library,
  the agent-architecture README cross-link, and the focused test file appear.

- [ ] Record final review corrections as one coherent change, then create a
  clean successor working copy:

  ```bash
  rtk jj describe -m "docs: verify mechanistic modeling reference library"
  rtk jj new
  rtk jj status
  ```

  Expected: `The working copy has no changes.` Re-run the complete verification
  set after the final recorded correction; do not claim completion from an
  earlier run.

## Completion Criteria

- [ ] The five-document mechanistic-modeling library exists as a sibling of
  `agent-architecture`.
- [ ] All nine approved terms retain exact spelling, capitalization, and
  distinct meanings.
- [ ] Data, runtime, composition, evaluator, solver, serialization, package,
  solution, and validation mechanics are explained in implementation-neutral
  prose.
- [ ] Targeted and external variables remain distinct without false ownership.
- [ ] Persistent model data, run configuration, and transient runtime state are
  visibly separate.
- [ ] `MechanisticModelComposer` and `ModelSolution` remain conceptual roles,
  not prescribed code APIs.
- [ ] One-model and multi-model runs share one composition path.
- [ ] Agent architecture and mechanistic modeling cross-link without merging
  authority.
- [ ] Every source, evidence item, and destination has exactly one auditable
  provenance record.
- [ ] Reader-facing documents contain no copied source code, internal project
  identifiers, sensitive state, or false current-implementation claims.
- [ ] Focused tests, full tests, Ruff, mypy, pre-commit, Markdownlint, local link
  checks, manual review, and Luna extra-high reviews all pass.
- [ ] The final diff contains only approved `ballen-config` changes and Plato
  remains unchanged.
