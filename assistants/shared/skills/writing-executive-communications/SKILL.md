---
name: writing-executive-communications
description: >-
  Use when drafting executive communications that should lead with the answer,
  stay MECE, apply situation-complication-resolution, quantify claims, and
  state confidence levels — without assuming a document format or renderer.
---

# Writing Executive Communications

## Core Principle: Lead with the Answer

Always structure communication using the **Pyramid Principle**:

1. **Start with the recommendation or conclusion** - Never bury the lead
2. **Support with key arguments** - Provide 2-4 supporting reasons
3. **Back with evidence** - Data, examples, or analysis underneath

```text
Bad: "I analyzed the codebase and found several patterns. First, there are
authentication issues. Second, performance problems. Third, some
security gaps. Therefore, we should refactor the auth module."

Good: "We should refactor the auth module. Three issues drive this:
1. Authentication failures increased 40% last quarter
2. Response times exceed SLA by 200ms on auth endpoints
3. Security audit flagged 3 critical vulnerabilities"
```

## MECE Framework

Structure all analysis to be **Mutually Exclusive, Collectively Exhaustive**:

- **Mutually Exclusive**: Categories do not overlap
- **Collectively Exhaustive**: Categories cover all possibilities

```text
Bad breakdown of code issues:
- Performance problems
- Slow database queries
- Memory issues
- Speed problems

Good MECE breakdown:
- Performance (CPU, memory, I/O)
- Reliability (error handling, edge cases)
- Maintainability (code structure, documentation)
- Security (authentication, authorization, data protection)
```

## Situation-Complication-Resolution (SCR)

Use SCR for problem framing:

1. **Situation**: Neutral context everyone agrees on
2. **Complication**: The problem or change that creates tension
3. **Resolution**: Your proposed solution

```text
Situation: "The API currently handles 10K requests per minute."
Complication: "Traffic projections show 50K RPM needed by Q3,
and current architecture cannot scale beyond 15K."
Resolution: "Implement horizontal scaling with load balancing.
This requires refactoring the session management
to be stateless."
```

## Action-Oriented Language

Use direct, actionable verbs:

| Avoid                              | Use Instead                |
| ---------------------------------- | -------------------------- |
| "We could potentially consider..." | "We recommend..."          |
| "It might be good to..."           | "Implement..."             |
| "There seems to be..."             | "The data shows..."        |
| "I think maybe..."                 | "Based on X, we should..." |

## The "So What?" Test

Every statement must pass the "so what?" test. If the implication is not clear, make it explicit:

```text
Bad: "The test suite takes 45 minutes to run."

Good: "The test suite takes 45 minutes to run, which means:
- Developers skip tests before commits, increasing bugs in main
- CI/CD pipeline bottlenecks delay deployments by 2 hours
Action: Parallelize tests to reduce runtime to under 10 minutes."
```

## Quantify Everything

Replace vague language with specific numbers:

| Vague                    | Quantified                              |
| ------------------------ | --------------------------------------- |
| "significantly improved" | "reduced latency by 40%"                |
| "many users affected"    | "impacting 12,000 daily active users"   |
| "takes a long time"      | "requires 3.5 hours to complete"        |
| "most of the codebase"   | "affects 73% of modules (42 of 57)"     |

## Issue Trees and Hypothesis-Driven Analysis

Structure problem-solving as a tree:

```text
Root Issue: API response times exceeding SLA

├── Is it a backend problem?
│   ├── Database queries slow? → Profile queries
│   ├── Business logic inefficient? → Review algorithms
│   └── External service latency? → Check third-party APIs
│
├── Is it a network problem?
│   ├── Load balancer misconfigured? → Review LB settings
│   └── Geographic latency? → Check CDN configuration
│
└── Is it a frontend problem?
├── Excessive API calls? → Audit request patterns
└── Poor caching? → Review cache headers
```

## Executive Summary Format

For longer communications, include a structured summary:

1. **Recommendation**: One sentence on what to do
2. **Impact**: Quantified benefit or risk mitigation
3. **Investment**: Time, cost, resources required
4. **Timeline**: Key milestones and delivery date
5. **Risks**: Top 1-2 risks and mitigations

## Crisp Writing Rules

1. **One idea per sentence** - Complex sentences obscure meaning
2. **Active voice** - "The team completed the migration" not "The migration was completed"
3. **Eliminate filler words** - Remove "basically," "actually," "really," "very," "just"
4. **Use parallel structure** - Lists should follow the same grammatical pattern
5. **Front-load key information** - Put the most important word at the start of sentences

## Presenting Options

When presenting alternatives, use a consistent structure:

```text
Incremental refactor:
- Pros: Lower risk, team can learn gradually
- Cons: 6-month timeline, technical debt persists longer
- Cost: 200 engineer-hours

Complete rewrite:
- Pros: Clean architecture, faster long-term velocity
- Cons: 3-month feature freeze, higher execution risk
- Cost: 800 engineer-hours

Recommendation: Incremental refactor, because the business cannot absorb a
3-month feature freeze given competitive pressure. Revisit a complete rewrite
in Q4.
```

## Handling Uncertainty

Be explicit about confidence levels:

- **High confidence**: "The data shows..." / "Testing confirms..."
- **Medium confidence**: "Analysis suggests..." / "Based on available data..."
- **Low confidence**: "Initial hypothesis is..." / "Requires validation, but..."

Never hide uncertainty. State what you know, what you do not know, and what you need to find out.

## Summary Checklist

Before delivering any executive communication, verify:

- [ ] Does it lead with the answer or recommendation?
- [ ] Is the structure MECE?
- [ ] Does every point pass the "so what?" test?
- [ ] Are claims quantified where possible?
- [ ] Is the language action-oriented?
- [ ] Is uncertainty explicitly stated?
- [ ] Can a busy executive understand it in 30 seconds?
