# Evaluating Agent Systems

Evaluation measures whether an Agent system is useful, structurally correct,
supported by evidence, safe, and operationally acceptable. No single score
captures all of those properties.

## Evaluation dimensions

Track dimensions separately before combining them:

| Dimension | Question |
| --- | --- |
| Task success | Did the system achieve the requested outcome? |
| Structural validity | Does output satisfy its schema and required invariants? |
| Factual support | Are claims grounded in allowed evidence? |
| Safety | Did the system respect capability, privacy, and approval boundaries? |
| Latency | Did the result arrive within the relevant service objective? |
| Cost | Were model, tool, and infrastructure costs proportionate? |

### Preserve dimensional results

Requirement: An evaluation report MUST retain material quality, safety, latency,
and cost dimensions separately even when it also publishes a summary score.

Rationale: A combined score can hide a safety regression behind quality gains
or a cost regression behind faster output.

Scope: Offline experiments, release gates, production monitoring, and vendor or
model comparisons.

Exceptions: A narrow deterministic component can report only the dimensions
relevant to its contract.

## Golden sets and controlled variation

Golden sets contain representative inputs, expected properties, and known hard
cases. They should cover ordinary traffic, boundary conditions, refusal cases,
and consequential effects. Controlled variation changes one factor at a time,
such as model, prompt, tool description, or retrieval policy.

### Keep comparisons interpretable

Requirement: Comparative evaluation SHOULD hold all non-target variables fixed
and use the same representative case set.

Rationale: Simultaneous changes make it impossible to attribute a result to the
factor under review.

Scope: Model bakeoffs, prompt changes, tool redesign, framework upgrades, and
orchestration-policy comparisons.

Exceptions: End-to-end system comparisons can vary several components when the
report explicitly evaluates the whole system rather than attributing causality.

## Deterministic checks first

Schema validation, required-field checks, policy assertions, link checks, and
known-answer calculations should run before model-based judging. Deterministic
failures need no probabilistic interpretation.

### Prefer deterministic evidence

Requirement: An evaluation pipeline MUST use deterministic checks for
properties that can be decided exactly before invoking a model judge.

Rationale: Exact checks are cheaper, reproducible, and easier to diagnose.

Scope: Structure, syntax, policy, calculations, references, and other
machine-decidable invariants.

Exceptions: None when an exact checker exists and is practical to run.

## Evaluation modes

### Offline

Offline evaluation runs against curated or replayed cases without affecting
users. It supports rapid iteration, controlled comparisons, and regression
testing.

### Pre-release

Pre-release evaluation exercises the integrated system in a production-like
environment, including real adapters, permissions, timeouts, and observability
without exposing unapproved behavior to users.

### Production

Production evaluation monitors sampled outcomes, operational metrics, safety
signals, user feedback, and drift. It complements rather than replaces offline
regression sets.

### Match evidence to the decision

Requirement: Release decisions SHOULD combine Offline, Pre-release, and
Production evidence appropriate to the change's risk and maturity.

Rationale: Each mode reveals different failure classes; relying on one creates
blind spots.

Scope: Changes to models, prompts, tools, capabilities, orchestration, and
external integrations.

Exceptions: A non-production experiment can use offline evidence only when its
limited use and lack of release claim are explicit.

## Metrics and thresholds

Choose thresholds from product risk, baseline performance, and the decision at
hand. Record case-set version, configuration, sample size, uncertainty, and
aggregation method. Avoid importing fixed counts or thresholds from an unrelated
system.

### Define gates locally

Requirement: Evaluation gates MUST document their metric definition, dataset,
aggregation, and decision rationale.

Rationale: A number without its measurement context is not a reproducible gate.

Scope: Automated release gates and claims comparing system versions.

Exceptions: Exploratory reports can omit a release threshold when they clearly
state that no go/no-go decision is being made.

## Model judges

Model judges can assess qualities that resist deterministic scoring, such as
clarity, relevance, or synthesis quality. They introduce their own model,
prompt, positional, verbosity, and self-preference biases.

### Calibrate judges

Requirement: Judge calibration MUST compare model-judge decisions with a
reviewed human-labeled sample before the judge controls a consequential gate.

Rationale: Agreement on a calibration set establishes what the score means and
reveals systematic bias.

Scope: LLM-as-judge scoring used for release, ranking, or published quality
claims.

Exceptions: A judge can support exploratory triage before calibration when its
output is not treated as authoritative.

### Prevent leakage and self-preference

Requirement: Comparative judging SHOULD blind irrelevant system identity,
randomize presentation order, and separate judge instructions from candidate
content.

Rationale: Judge calibration alone does not prevent leakage, positional bias,
or preference for a judge's own style.

Scope: Pairwise comparisons, benchmark reports, and repeated evaluation runs.

Exceptions: Identity can remain visible when it is itself a criterion, such as
checking required attribution.
